/**
 * Yahoo!フリマ公式メール通知 -> Cloudflare Worker 取り込み口
 *
 * 完全無料の Google Apps Script (GAS) / Gmail / Cloudflare Workers Free を利用。
 * これは「保存した検索条件」の新着メールを取り込むための補助ルートです。
 * フリマ全件の取得や30秒以内の配信はできません。
 *
 * 重要: 署名のないメールのテキストで売却可能性を確定しない。
 * Gmail アカウントへの同意と個人の初回設定が必要。
 * このコードはGoogleでメールを検索するだけで、元メールを削除・変更しません。
 */

var WATCH_QUERY_DEFAULT_ = 'newer_than:2d "Yahoo!フリマ"';
var WATCH_SEEN_PROP_ = 'WATCH_SEEN_IDS';
var WATCH_LAST_PROP_ = 'WATCH_LAST_RUN';

/**
 * 商品への直接リンクだけを取り出す。追跡・リダイレクト URL は無視。
 * メール本文は送らず、公開の商品URLと価格候補だけを送る。
 */
function parseYahooFurimaNotice_(subject, text) {
  var s = String(subject || '').slice(0, 180);
  var t = String(text || '').slice(0, 50000).replace(/&amp;/g, '&');
  var urlMatch = t.match(/https:\/\/paypayfleamarket\.yahoo\.co\.jp\/item\/([a-zA-Z0-9_-]{6,80})(?=[\s"'?&#<>]|$)/i);
  if (!urlMatch) return null;
  var url = 'https://paypayfleamarket.yahoo.co.jp/item/' + urlMatch[1];
  // 件名やメール本文に金額が複数ある場合は誤認を避けて未指定にする。
  var money = Array.from(t.matchAll(/(?:[¥￥]\s*([\d,]+)|([\d,]+)\s*円)/g))
    .map(function(m) { return Number((m[1] || m[2]).replace(/,/g, '')); })
    .filter(function(v) { return Number.isSafeInteger(v) && v >= 100 && v <= 1000000; });
  var unique = Array.from(new Set(money));
  var out = {
    source: 'yahoo_furima',
    title: s,
    body: 'Yahoo!フリマの新着通知: ' + url,
    url: url
  };
  if (unique.length === 1) {
    out.price = unique[0];
    out.body += '\n' + unique[0] + '円';
  }
  // match_key と condition は不確かなメール内容から推定しない。
  // 従って取得済み相場と一致するまで購入推奨通知は送られない。
  return out;
}

/** 1回だけ実行して Gmail の毎分チェックを登録する。 */
function setupYahooMailWatch() {
  var p = PropertiesService.getScriptProperties();
  var endpoint = p.getProperty('WORKER_BASE_URL');
  var token = p.getProperty('INGEST_TOKEN');
  if (!/^https:\/\/[a-z0-9-]+(?:\.[a-z0-9-]+)*\.workers\.dev\/?$/i.test(endpoint || '')) {
    throw new Error('Script Properties に WORKER_BASE_URL (自分の Cloudflare Worker URL) を設定してください。');
  }
  if (!token || token.length < 24) {
    throw new Error('Script Properties に24文字以上の INGEST_TOKEN を設定してください。');
  }
  ScriptApp.getProjectTriggers().filter(function(t) {
    return t.getHandlerFunction() === 'scanYahooFurimaMail';
  }).forEach(function(t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('scanYahooFurimaMail').timeBased().everyMinutes(1).create();
  return 'Yahoo!フリマ通知メールの毎分取り込みを設定しました。';
}

/**
 * 定期実行関数。フリマサービス側がメールを配信して初めて検出できる。
 * Webブラウザの画面操作や非公開 API、サイトの自動巡回はしない。
 */
function scanYahooFurimaMail() {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(300)) return;
  try {
    var p = PropertiesService.getScriptProperties();
    var endpoint = String(p.getProperty('WORKER_BASE_URL') || '').replace(/\/$/, '');
    var token = String(p.getProperty('INGEST_TOKEN') || '');
    if (!/^https:\/\/[a-z0-9-]+(?:\.[a-z0-9-]+)*\.workers\.dev$/i.test(endpoint) || token.length < 24)
      throw new Error('先に WORKER_BASE_URL と INGEST_TOKEN を設定してください。');
    var query = p.getProperty('WATCH_GMAIL_QUERY') || WATCH_QUERY_DEFAULT_;
    var threads = GmailApp.search(query, 0, 30);
    var mails = GmailApp.getMessagesForThreads(threads)
      .reduce(function(a, b) { return a.concat(b); }, [])
      .sort(function(a, b) { return a.getDate().getTime() - b.getDate().getTime(); });
    var oldIds;
    try { oldIds = JSON.parse(p.getProperty(WATCH_SEEN_PROP_) || '[]'); }
    catch (_) { oldIds = []; }
    var seen = new Set(oldIds);
    var delivered = 0, found = 0;
    mails.slice(-70).forEach(function(mail) {
      var id = String(mail.getId());
      if (seen.has(id)) return;
      var record = parseYahooFurimaNotice_(mail.getSubject(), mail.getPlainBody());
      if (!record) record = parseYahooFurimaNotice_(mail.getSubject(), mail.getBody());
      if (!record) {
        // Yahoo!フリマの商品リンクが無ければ非対象として記録する。
        seen.add(id);
        return;
      }
      found++;
      var res = UrlFetchApp.fetch(endpoint + '/api/notice', {
        method: 'post',
        contentType: 'application/json; charset=utf-8',
        headers: { Authorization: 'Bearer ' + token },
        payload: JSON.stringify(record),
        muteHttpExceptions: true
      });
      if (res.getResponseCode() === 202) {
        seen.add(id);
        delivered++;
      } else {
        // 通信失敗時は次回再試行。失敗通知はユーザーへ送らない。
        console.error('Worker intake failed HTTP ' + res.getResponseCode());
      }
    });
    p.setProperty(WATCH_SEEN_PROP_, JSON.stringify(Array.from(seen).slice(-160)));
    p.setProperty(WATCH_LAST_PROP_, new Date().toISOString() + ' scanned=' + mails.length + ' detected=' + found + ' accepted=' + delivered);
  } finally {
    lock.releaseLock();
  }
}

/** 初回テスト時に作動記録をApps Scriptログで見る。iPhoneへは送らない。 */
function viewYahooMailWatchStatus() {
  var p = PropertiesService.getScriptProperties();
  console.log(p.getProperty(WATCH_LAST_PROP_) || 'まだ実行していません');
}

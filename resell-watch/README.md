# 仕入れ新着通知ブリッジ (iPhone / Cloudflare Free)

**現状：コードはGitHubのmainブランチのresell-watch/に配置済み。PRでの自動テストは成功。Cloudflare本番デプロイと本人のiPhoneショートカット登録は未完了。**

## 何ができるか

iOS 27の「ショートカット」通知トリガーから、iPhoneに実際に届いたフリマアプリの通知を、1つのCloudflare Workerへ送信して保存する。送られた通知に商品URL・価格・正確な型番・状態が揃い、登録済みの買い取り／Yahoo!フリマ実売記録で費用控除後ROI50%以上かつ1,000円以上が確認された場合のみ、無料ntfyで知らせる。該当なし・エラー・情報不足のときはプッシュ通知しない。重複案件も通知を抑止する。

**注意：** 市場の全出品を読み込むAPIは持たない。各アプリが通知した商品だけが入口で、フリマの通知は商品URL・型番等を含まない場合がある。その場合は保存だけし、利益通知は行わない。出品から30秒以内は実証も保証もできない。買い取り額や売れ行きの外部データを自動取得・検証する仕組みも未完成。

## 初期設定（本人承認のみ必要）

1. Cloudflareにログイン。Workers & PagesでGitHubリポジトリ ga19840227-sudo/keirin-data を接続し、mainブランチの resell-watch ディレクトリをルートとしてWorkerをデプロイする。GitHub連携の画面がディレクトリ指定に対応しない場合はWrangler CLIを使用する必要がある。
2. WorkerのSecretsに、他人に共有しない24文字以上の異なる秘密文字列 INGEST_TOKEN, ADMIN_TOKEN と、推測困難な20文字以上の ntfy トピック NTFY_TOPIC を入力する。これらの秘密文字列をGitHubへコミットしたりチャットに貼ったりしない。
3. iPhoneに無料の ntfy アプリを入れ、ntfy.sh の自分の秘密トピックを購読する。通知の受信にはインターネット接続が必要。
4. iPhoneショートカットの「オートメーション」→「通知」で、最初はメルカリだけを指定。「URLの内容を取得」をPOSTにしてWorkerの https://(Worker URL)/api/notice に送る。ヘッダ Authorization: Bearer (INGEST_TOKEN) を付ける。JSON本文は source=mercari, title=(通知のTitle), body=(通知のMessage) にする。初回のロック画面での実行許可も必要。
5. 動作テスト：公開URLの /health は匿名で閲覧可。/api/events はADMIN_TOKEN認証で受信記録を表示。Yahoo!フリマ等はsourceと対象アプリを変えて追加する。

## 重要な入力仕様

- /api/notice : INGEST_TOKENで認証する。source は mercari, yahoo_furima, rakuma, yahoo_auction のいずれか。title, body 以外に、URL・価格・正確な型番match_key・商品状態condition(new/used_good/used_fair)がある場合のみ自動スコアリングする。
- /api/reference : ADMIN_TOKENで認証する。store (店頭参考買取) または yahoo_sold (Yahoo!フリマ成約) の参照記録を登録する。参考URLの正確性や本人確認は自動検証していない。店頭は20%減額バッファと交通費500円、Yahoo!フリマは手数料5%・送料250円・梱包50円を控除する。参考価格が変われば再判定が必要。
- /api/status, /api/events : ADMIN_TOKENで認証する。
- /health : Workerのデプロイ確認（公開）。

## 無料枠について

SQLite-backed Cloudflare Durable ObjectsはWorkers Freeで利用可能。ただし無料枠上限があり、一定量を超えると失敗する。ntfy無料公開サーバーのトピックは秘密保持が重要。公式仕様：
- https://developers.cloudflare.com/durable-objects/platform/pricing/
- https://support.apple.com/en-az/guide/shortcuts/apd932ff833f/ios
- https://help.jp.mercari.com/guide/articles/240/

## 手元でテスト

Node.js 22以降で resell-watch ディレクトリから npm test。ワーカーの実行は npx wrangler deploy。認証トークンはCloudflareのSecret環境変数に設定する。既存の競輪データ収集ファイルには手を加えていない。

## Cloudflare ビルド設定（既存プロジェクト）

- Production branch: `main`
- Root directory: `resell-watch`
- Build command: 空欄（None）
- Deploy command: `npx wrangler deploy`

Cloudflare で設定を保存後、`resell-watch/` 以下の新しい GitHub コミットにより再ビルドを試す。以前の失敗した Deployments に表示される「Active deployment」は、新版のビルド成功を意味しない。今回の Worker はフリマ各社の全件取得や30秒以内の検知を保証しない。

## 公式の Yahoo!フリマ新着メールを取得する無料アダプタ（追加）

追加ファイル: connectors/yahoo-furima-mail.gs

Yahoo!フリマは保存した検索条件について新着通知メールを公式に提供している（2026年2月開始）。メールが届いた後に Google Apps Script がGmailを一定間隔で読んで、商品への直接リンクがある通知だけを既存の Cloudflare Worker の /api/notice に送信する。

これは正式な通知を取得する方式であり、非公開API・出品ページの大量スクレイピングを行わない。動作にはYahoo!フリマ側の検索条件保存とメール通知設定、Gmail受信、Google Apps Scriptの初回承認が必要。**こちらから利用者のGmailを勝手に読んだり、アプリへのログインや認証を済ませたりすることはできない。**

### 初回セットアップ（本人による承認が必要な部分）

1. Yahoo!フリマで保存した検索条件について「すぐに通知」＋「メール」を選び、Gmailに届くことを確認。
2. https://script.google.com/ で新規 Apps Script を作り、connectors/yahoo-furima-mail.gs のコードを貼り付ける。
3. プロジェクトの Script Properties（スクリプト プロパティ）で、WORKER_BASE_URL に公開済みの自分の Worker URL、INGEST_TOKEN にCloudflareのSecretと同じ文字列（24文字以上）を設定する。値はGitHubやチャットに貼らない。
4. setupYahooMailWatch を一度実行し、Googleから求められるGmail検索・HTTP送信・トリガー作成の権限を確認して承認する。
5. viewYahooMailWatchStatus を実行するとApps Scriptログで直近の取り込み回数を確認できる。メールがないとき、未確認・条件未達のときはiPhoneへの通知はない。

メール検索が見つからない場合は Script Properties の WATCH_GMAIL_QUERY に Gmailで検索できるYahoo!フリマの通知メールの検索式を設定する（不明な送信元メールアドレスは勝手に仮定しない）。初期値は newer_than:2d "Yahoo!フリマ"。

**未達の条件:** すべての商品を検索するわけではない。フリマ側からの通知メールの遅延 + Apps Script毎分チェックがあるので出品から30秒以内は保証しない。メール本文だけで商品状態・型番・成約相場を証明できない場合はWorkerで INCOMPLETE として保存し、利益率50%の通知は出さない。店頭買取価格や売却履歴の自動取得は引き続き未実装。

### 確認した公式仕様

- 公式メール通知: https://paypayfleamarket.yahoo.co.jp/notice/function/post_1193/
- 公式即時通知: https://paypayfleamarket.yahoo.co.jp/notice/function/post_1047/
- 検索条件・上限: https://support.yahoo-net.jp/SccPaypayfleamarket/s/article/H000013029

GitHubの検証は npm test (Node.js 22)。Apps Script実機のGmailアクセス許可・トリガーは利用者の環境でのみ実行できる。

### iPhoneショートカットを1つにまとめる（追加）

Worker は /api/notice の JSON に source="auto" と app_name="メルカリ" / "Yahoo!フリマ" / "ラクマ" / "Yahoo!オークション" のいずれかを受け取ると通知元を自動判定できる。ショートカット側で選択したアプリの名前を app_name に渡せれば、複数アプリを同一オートメーションから送信できる（ただし実機通知の内容と「App」値の形式は別途動作確認が必要）。URL・商品状態・正確な型番が揃わない通知を勝手に利益確定と扱わない。

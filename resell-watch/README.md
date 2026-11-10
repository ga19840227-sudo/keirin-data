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

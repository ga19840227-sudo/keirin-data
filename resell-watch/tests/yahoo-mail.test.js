import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { parseNotice } from "../src/worker.js";

// Run the actual Apps Script source, with Apps Script host functions unused.
const code = fs.readFileSync(new URL("../connectors/yahoo-furima-mail.gs",import.meta.url),"utf8");
const ctx = {};
vm.createContext(ctx);
vm.runInContext(code,ctx);
const parse=(s,t)=>ctx.parseYahooFurimaNotice_(s,t);

test("Official notification email URL can enter common Worker intake",()=>{
  const a=parse("Yahoo!フリマで新着商品","商品URL https://paypayfleamarket.yahoo.co.jp/item/z12345678 値段 1,800円");
  assert.equal(a.source,"yahoo_furima");
  assert.equal(a.url,"https://paypayfleamarket.yahoo.co.jp/item/z12345678");
  assert.equal(a.price,1800);
  const b=parseNotice(a);
  assert.equal(b.listing_url,a.url);
  // A mail alone cannot prove exact SKU, condition, or profit.
  assert.equal(b.status,"INCOMPLETE");
});

test("Unrelated emails and links to search pages are ignored",()=>{
  assert.equal(parse("広告","https://paypayfleamarket.yahoo.co.jp/search"),null);
  assert.equal(parse("フィッシング","https://paypayfleamarket.yahoo.co.jp.evil.example/item/z123456"),null);
});

test("Ambiguous amount never guesses item price",()=>{
  const a=parse("ご案内","https://paypayfleamarket.yahoo.co.jp/item/z12345678\n通常 2,500円、割引 1,800円");
  assert.equal(a.price,undefined);
  assert.equal(parseNotice(a).price,null);
});

test("URL query strings stripped and no email body information transferred",()=>{
  const a=parse("通知","ID=private-account 連絡先 secret@example.com\nhttps://paypayfleamarket.yahoo.co.jp/item/z12345678?utm_source=mail&x=1\n1,300円");
  assert.equal(a.url,"https://paypayfleamarket.yahoo.co.jp/item/z12345678");
  assert.ok(!JSON.stringify(a).includes("secret@example.com"));
  assert.ok(!JSON.stringify(a).includes("private-account"));
});

test("Need direct item URL; impossible to claim every marketplace listing",()=>{
  assert.equal(parse("商品追加","https://jp.mercari.com/item/m123456789"),null);
});

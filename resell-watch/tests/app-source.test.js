import test from "node:test";
import assert from "node:assert/strict";
import {sourceFromApp,parseNotice} from "../src/worker.js";

test("Recognize officially named marketplace app notifications",()=>{
  assert.equal(sourceFromApp("メルカリ"),"mercari");
  assert.equal(sourceFromApp("Yahoo!フリマ"),"yahoo_furima");
  assert.equal(sourceFromApp("ラクマ"),"rakuma");
  assert.equal(sourceFromApp("Yahoo!オークション"),"yahoo_auction");
});
test("Unknown app cannot insert a counterfeit marketplace feed",()=>{
  assert.equal(sourceFromApp("銀行"),null);
  assert.equal(parseNotice({source:"auto",app_name:"銀行",title:"商品が売れた",body:"1500円"}).error,"unknown_marketplace");
});
test("One iOS Shortcut can submit app name instead of source name",()=>{
  const x=parseNotice({source:"auto",app_name:"Yahoo!フリマ",title:"新着",body:"1,400円 https://paypayfleamarket.yahoo.co.jp/item/z12345678"});
  assert.equal(x.source,"yahoo_furima");
  assert.equal(x.listing_url,"https://paypayfleamarket.yahoo.co.jp/item/z12345678");
  assert.equal(x.status,"INCOMPLETE");
});

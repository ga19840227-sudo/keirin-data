import test from "node:test";
import assert from "node:assert/strict";
import { parseNotice, evaluateListing } from "../src/worker.js";
const now=Math.floor(Date.now()/1000);
const listing={source:"mercari",title:"ヘッドホン ABC-2",body:"3,000円",url:"https://jp.mercari.com/item/m0000111",price:3000,match_key:"ABC-2",condition:"used_good"};
test("iPhone notification without URL and model is incomplete and silent",()=>{
 const a=parseNotice({source:"mercari",title:"商品出品",body:"ヘッドホン 3,000円"});
 assert.equal(a.status,"INCOMPLETE");assert.equal(a.price,3000);assert.equal(a.listing_url,null);
});
test("No fake URL accepted",()=>{
 const a=parseNotice({...listing,url:"https://jp.mercari.com.evil.test/item/m0000111"});
 assert.equal(a.status,"INCOMPLETE");assert.equal(a.listing_url,null);
});
test("Full listing may enter manual review queue",()=>{
 const a=parseNotice(listing);assert.equal(a.status,"REVIEW");
});
test("No references means no profitable alert",()=>{
 assert.equal(evaluateListing(parseNotice(listing),[],{now}).eligible,false);
});
test("Store quote requires net ROI 50% after 20 percent haircut and transport",()=>{
 const a=parseNotice({...listing,price:1500,body:"1,500円"});
 const x={type:"store",match_key:"ABC-2",condition:"used_good",price:5000,observed_at:now,shop:"架空店",reference_url:"https://shop.example/buy"};
 const result=evaluateListing(a,[x],{now});assert.equal(result.eligible,true);assert.equal(result.best.profit,2000);
 assert.equal(evaluateListing(a,[{...x,price:2500}],{now}).eligible,false);
});
test("Yahoo resale requires at least 3 quick completed sales",()=>{
 const item=parseNotice({...listing,price:1800,body:"1,800円"});
 const sale={type:"yahoo_sold",match_key:"ABC-2",condition:"used_good",price:5500,observed_at:now,hours_to_sell:12,reference_url:"https://paypayfleamarket.yahoo.co.jp/item/z0001"};
 assert.equal(evaluateListing(item,[sale,sale],{now}).eligible,false);
 const b=evaluateListing(item,[sale,sale,sale],{now});assert.equal(b.eligible,true);assert.equal(b.best.channel,"Yahoo!フリマ");
});
test("Stale or different product references cannot authorize",()=>{
 const item=parseNotice(listing);
 const x={type:"store",match_key:"OTHER",condition:"used_good",price:50000,observed_at:now,shop:"架空店",reference_url:"https://shop.example/buy"};
 assert.equal(evaluateListing(item,[x],{now}).eligible,false);
 assert.equal(evaluateListing(item,[{...x,match_key:"ABC-2",observed_at:now-35*86400}],{now}).eligible,false);
});

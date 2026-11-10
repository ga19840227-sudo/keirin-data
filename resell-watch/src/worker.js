// Free Cloudflare Worker: iPhone Shortcuts notification bridge.
// This does not scrape marketplace sites or promise 30-second delivery.
export const HOSTS = {
  mercari: ["jp.mercari.com"],
  yahoo_furima: ["paypayfleamarket.yahoo.co.jp"],
  rakuma: ["item.fril.jp"],
  yahoo_auction: ["page.auctions.yahoo.co.jp", "auctions.yahoo.co.jp"]
};
const CONDITIONS = new Set(["new", "used_good", "used_fair"]);
const sources = new Set(Object.keys(HOSTS));
const stamp = () => Math.floor(Date.now() / 1000);
const clean = (s,n=400) => String(s ?? "").trim().slice(0,n);
const num = (n) => Number.isSafeInteger(Number(n)) ? Number(n) : null;
function validUrl(source, link) {
  try { const u=new URL(link); return u.protocol==="https:" && HOSTS[source]?.includes(u.hostname) && !u.username && !u.password; }
  catch { return false; }
}
export function parseNotice(obj) {
  if(!obj || typeof obj!=="object" || Array.isArray(obj)) return {error:"invalid_json"};
  const source=clean(obj.source,40);
  if(!sources.has(source)) return {error:"unknown_marketplace"};
  const title=clean(obj.title,200),body=clean(obj.body,1600);
  if(!title&&!body) return {error:"empty_notification"};
  const found=(title+"\n"+body).match(/https:\/\/[^\s<>"'）]+/i)?.[0]?.replace(/[.,。、]+$/,"") || "";
  const url=clean(obj.url,800) || found;
  const listing_url=validUrl(source,url)?url:null;
  const amounts=[...(title+"\n"+body).matchAll(/(?:[¥￥]\s*([\d,]+)|([\d,]+)\s*円)/g)]
     .map(x=>num((x[1]||x[2]).replace(/,/g,""))).filter(x=>x!==null&&x>=100&&x<=1000000);
  const explicit=(obj.price===undefined||obj.price===null)?null:num(obj.price);
  const price=(explicit!==null&&explicit>=100&&explicit<=1000000)?explicit:(amounts.length===1?amounts[0]:null);
  const match_key=clean(obj.match_key,100).normalize("NFKC").toUpperCase();
  const condition=clean(obj.condition,20);
  return {source,title,body,listing_url,price,match_key,
    condition:CONDITIONS.has(condition)?condition:null,
    status:(listing_url&&price!==null&&match_key&&CONDITIONS.has(condition))?"REVIEW":"INCOMPLETE"};
}
export function evaluateListing(item, refs, opts={}) {
  const price=num(item.price), inbound=num(opts.inbound??0);
  if(price===null||price<100||inbound===null||inbound<0||!item.match_key||!CONDITIONS.has(item.condition))
    return {eligible:false,reason:"incomplete_item"};
  const cost=price+inbound, now=opts.now??stamp();
  const same=(refs||[]).filter(r=>r.match_key===item.match_key&&r.condition===item.condition&&r.observed_at<=now&&r.observed_at>=now-30*86400);
  const candidates=[];
  const store=same.filter(r=>r.type==="store"&&r.observed_at>=now-86400&&r.shop&&r.reference_url);
  for(const r of store) {
    const resale=Math.floor(r.price*0.8),transport=500,profit=resale-cost-transport;
    if(profit>=1000&&profit/cost>=0.5) candidates.push({channel:"札幌店頭",shop:r.shop,profit,roi:profit/cost,resale,fees:transport,reference_url:r.reference_url});
  }
  const sold=same.filter(r=>r.type==="yahoo_sold"&&Number.isFinite(r.hours_to_sell)&&r.hours_to_sell>=0&&r.reference_url);
  if(sold.length>=3&&sold.filter(r=>r.hours_to_sell<=48).length>=3){
    const amounts=sold.map(r=>r.price).sort((a,b)=>a-b),resale=amounts[Math.floor((amounts.length-1)*.25)];
    const fees=Math.ceil(resale*0.05)+250+50,profit=resale-cost-fees;
    if(profit>=1000&&profit/cost>=0.5) candidates.push({channel:"Yahoo!フリマ",profit,roi:profit/cost,resale,fees,reference_url:sold[0].reference_url});
  }
  candidates.sort((a,b)=>b.profit-a.profit);
  return {eligible:candidates.length>0,best:candidates[0]??null,reference_count:same.length,reason:candidates.length?"manual_listing_check_required":"no_margin_or_sales_evidence"};
}
function json(data,status=200){return new Response(JSON.stringify(data),{status,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store"}});}
async function hash(data) {const d=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(data));return [...new Uint8Array(d)].map(x=>x.toString(16).padStart(2,"0")).join("");}
async function notify(env,item,result) {
  const topic=env.NTFY_TOPIC;
  if(!topic||!/^[A-Za-z0-9_-]{20,}$/.test(topic)) return false;
  const b=result.best;
  const msg="【要確認】仕入れ候補\n"+item.title+"\n仕入 "+item.price+"円 / 想定売却 "+b.resale+"円\n費用控除後利益 "+b.profit+"円 / ROI "+(b.roi*100).toFixed(1)+"%\n売却先 "+b.channel+"\n査定額と48時間売却は保証外。購入前に商品状態・在庫を確認\n"+item.listing_url;
  const response=await fetch("https://ntfy.sh/"+topic,{method:"POST",
    headers:{"Content-Type":"text/plain; charset=utf-8","Title":"利益50%候補","Click":item.listing_url},body:msg});
  return response.ok;
}
export class Inbox {
  constructor(ctx,env){
    this.ctx=ctx;this.env=env;
    this.ready=ctx.blockConcurrencyWhile(async()=>{
      ctx.storage.sql.exec("CREATE TABLE IF NOT EXISTS notices (id TEXT PRIMARY KEY, source TEXT, title TEXT, body TEXT, listing_url TEXT, price INTEGER, match_key TEXT, condition TEXT, status TEXT, at INTEGER)");
      ctx.storage.sql.exec("CREATE TABLE IF NOT EXISTS refs (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, match_key TEXT, condition TEXT, price INTEGER, observed_at INTEGER, hours_to_sell REAL, shop TEXT, reference_url TEXT)");
      ctx.storage.sql.exec("CREATE TABLE IF NOT EXISTS alerts (id TEXT PRIMARY KEY, at INTEGER)");
    });
  }
  async fetch(request){
    await this.ready;
    const p=new URL(request.url).pathname,db=this.ctx.storage.sql;
    if(p==="/notice"&&request.method==="POST"){
      const body=await request.json().catch(()=>null),item=parseNotice(body);
      if(item.error) return json({error:item.error},400);
      const id=await hash([item.source,item.title,item.body,item.listing_url??"",Math.floor(stamp()/60)].join("|"));
      db.exec("INSERT OR IGNORE INTO notices VALUES (?,?,?,?,?,?,?,?,?,?)",id,item.source,item.title,item.body,item.listing_url,item.price,item.match_key,item.condition,item.status,stamp());
      let candidate=false,delivered=false;
      if(item.status==="REVIEW"){
        const rows=[...db.exec("SELECT * FROM refs WHERE match_key=? AND condition=? AND observed_at>=? ORDER BY observed_at DESC LIMIT 100",item.match_key,item.condition,stamp()-30*86400)];
        const result=evaluateListing(item,rows);
        candidate=result.eligible;
        if(candidate){
          const key=await hash(item.listing_url+"|"+item.price);
          if(![...db.exec("SELECT id FROM alerts WHERE id=?",key)].length){
            delivered=await notify(this.env,item,result);
            if(delivered) db.exec("INSERT INTO alerts(id,at) VALUES (?,?)",key,stamp());
          }
        }
      }
      return json({accepted:true,status:item.status,candidate,delivered,warning:"iPhone notification is not a verified listing; purchase and buyback must be checked"},202);
    }
    if(p==="/reference"&&request.method==="POST"){
      const x=await request.json().catch(()=>null);
      if(!x||!["store","yahoo_sold"].includes(x.type)||!CONDITIONS.has(x.condition)) return json({error:"invalid_reference"},400);
      const key=clean(x.match_key,100).normalize("NFKC").toUpperCase(),price=num(x.price),t=num(x.observed_at??stamp()),url=clean(x.reference_url,800),h=(x.hours_to_sell==null?null:Number(x.hours_to_sell));
      let host="";try{const u=new URL(url);if(u.protocol!=="https:")throw Error();host=u.hostname;}catch{return json({error:"reference_url_https_required"},400);}
      if(!key||price===null||price<100||t===null||t>stamp()+60||t<stamp()-30*86400|| (x.type==="yahoo_sold"&&(host!=="paypayfleamarket.yahoo.co.jp"||!Number.isFinite(h)||h<0||h>720)))
        return json({error:"invalid_price_key_timestamp_or_sales_evidence"},400);
      const shop=clean(x.shop,100);
      if(x.type==="store"&&!shop) return json({error:"shop_required"},400);
      db.exec("INSERT INTO refs(type,match_key,condition,price,observed_at,hours_to_sell,shop,reference_url) VALUES (?,?,?,?,?,?,?,?)",x.type,key,x.condition,price,t,h,shop,url);
      return json({saved:true,warning:"reference URL and store price are user submitted, not independently verified"});
    }
    if(p==="/events"&&request.method==="GET") return json({notices:[...db.exec("SELECT source,title,listing_url,price,match_key,condition,status,at FROM notices ORDER BY at DESC LIMIT 30")]});
    if(p==="/status"&&request.method==="GET") {
      const rows=[...db.exec("SELECT COUNT(*) AS n FROM notices")];
      return json({received:rows[0]?.n??0,real_marketplace_api:false,live_30_second_guarantee:false,notification_only:true});
    }
    return json({error:"not_found"},404);
  }
}
export default {
  async fetch(request,env) {
    const p=new URL(request.url).pathname;
    if(p==="/") return new Response("<!doctype html><html lang='ja'><meta name='viewport' content='width=device-width, initial-scale=1'><title>仕入れ監視</title><body style='font:16px system-ui;margin:35px'><h2>仕入れ監視・無料版</h2><p>iPhone通知を受ける入口。30秒以内の新着取得・利益保証はありません。</p><p>Cloudflare Secretsの設定とショートカット連携が必要です。</p></body></html>",{headers:{"content-type":"text/html; charset=utf-8"}});
    if(p==="/health") return json({ok:true,mode:"notification_bridge",live_marketplace_connection:false});
    const admin=["/api/reference","/api/events","/api/status"].includes(p);
    const ingest=p==="/api/notice";
    if(!admin&&!ingest) return json({error:"not_found"},404);
    const expected=admin?env.ADMIN_TOKEN:env.INGEST_TOKEN;
    if(!expected||expected.length<24||request.headers.get("Authorization")!=="Bearer "+expected) return json({error:"unauthorized"},401);
    if(ingest&&request.method!=="POST") return json({error:"method_not_allowed"},405);
    const route={"/api/notice":"/notice","/api/reference":"/reference","/api/events":"/events","/api/status":"/status"}[p];
    const id=env.INBOX.idFromName("default");
    return env.INBOX.get(id).fetch(new Request("https://internal"+route,request));
  }
};
"""Backfill archived racecards from KEIRIN HEX, preserving historical provenance.
Historical page retrieval is NOT proof of a pre-start snapshot.
"""
import argparse,json,re,time,urllib.parse,urllib.robotparser
from datetime import datetime,date,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from collect_prerace_hex import BASE,UA,Page,fetch
from parse_hex_prerace_riders import parse_rows
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--start",default="2026-10-13")
 ap.add_argument("--end",default="2026-10-16")
 ap.add_argument("--limit",type=int,default=120)
 args=ap.parse_args()
 robot=urllib.robotparser.RobotFileParser();robot.set_url(BASE+"/robots.txt")
 try:robot.read()
 except Exception as e:
  Path("results").mkdir(exist_ok=True)
  Path("results/historical_hex_backfill_audit.json").write_text(json.dumps({"error":"robots unavailable","detail":str(e)},ensure_ascii=False),encoding="utf-8")
  return
 out=Path("historical_hex");out.mkdir(exist_ok=True)
 report={"start":args.start,"end":args.end,"visited":0,"saved":0,"line_and_sbh":0,"errors":[],"provenance":"archived page retrieved after race; pre-race originality not independently certified"}
 day=date.fromisoformat(args.start);end=date.fromisoformat(args.end)
 while day<=end and report["visited"]<args.limit:
  ds=day.strftime("%Y%m%d")
  try:
   raw_html=fetch(BASE+"/races/"+ds+"/",robot)
   index=Page();index.feed(raw_html)
   daily_text="".join(index.parts)
   daily_dir=out/ds;daily_dir.mkdir(parents=True,exist_ok=True)
   (daily_dir/"day_archive.json").write_text(json.dumps({
    "source_url":BASE+"/races/"+ds+"/","race_date":day.isoformat(),
    "retrieved_jst":datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(),
    "verified_pre_race":False,"historical_retrieval":True,
    "page_text":daily_text[:200000],
    "warning":"Historical daily archive; validate lineup extraction and pre-race provenance before training."
   },ensure_ascii=False,indent=2),encoding="utf-8")
   report["daily_pages_saved"]=report.get("daily_pages_saved",0)+1
   urls=sorted(set(urllib.parse.urljoin(BASE,u).split("?")[0].split("#")[0] for u in index.links if re.search(r"/races/"+ds+r"/[0-9]+/?(?:[?#].*)?$",u)))
   # Fallback: historical daily archive may include race IDs in embedded HTML rather than anchors.
   ids=set(re.findall(r"/races/"+ds+r"/([0-9]{8,20})/?",raw_html))
   urls=sorted(set(urls)|{BASE+"/races/"+ds+"/"+rid+"/" for rid in ids})
   report.setdefault("daily_link_audit",[]).append({"date":ds,"links":len(urls),"embedded_ids":len(ids)})
   if not urls:
    report["errors"].append(ds+": archive date index returned no race links")
   report.setdefault("dates",[]).append({"date":ds,"links":len(urls)})
   for url in urls:
    if report["visited"]>=args.limit:break
    try:
     time.sleep(1.5)
     pg=Page();pg.feed(fetch(url,robot));report["visited"]+=1
     txt=re.sub(r"[ \t]+"," ","".join(pg.parts))
     m=re.search(r"並び予想は\s*([0-9０-９/／\-－=\s]+)",txt)
     raw=m.group(1).strip() if m else None
     groups=None
     if raw:
      norm=raw.translate(str.maketrans("０１２３４５６７８９／－","0123456789/-"))
      bits=[x.strip() for x in norm.split("/")]
      if all(re.fullmatch(r"[1-9](?:-[1-9])*",x) for x in bits):
       groups=[[int(n) for n in x.split("-")] for x in bits]
     riders=parse_rows(txt)
     ok=bool(groups and set(riders)==set(n for g in groups for n in g))
     rec={"source_url":url,"race_date":day.isoformat(),"retrieved_jst":datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(),
          "historical_retrieval":True,"verified_pre_race":False,
          "line_groups":groups,"lineup_raw":raw,"riders":list(riders.values()),
          "line_and_sbh_complete":ok,
          "page_text":txt[:30000],"warning":"Historical archived page, cannot certify pre-race unchanged content."}
     dest=out/ds;dest.mkdir(exist_ok=True)
     (dest/(url.rstrip("/").split("/")[-1]+".json")).write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding="utf-8")
     report["saved"]+=1;report["line_and_sbh"]+=int(ok)
    except Exception as e:report["errors"].append(url+": "+str(e))
  except Exception as e:report["errors"].append(ds+": "+str(e))
  day+=timedelta(days=1)
 Path("results").mkdir(exist_ok=True)
 Path("results/historical_hex_backfill_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()

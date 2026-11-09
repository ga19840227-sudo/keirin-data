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
   index=Page();index.feed(fetch(BASE+"/races/"+ds+"/",robot))
   urls=sorted(set(urllib.parse.urljoin(BASE,u).split("?")[0] for u in index.links if re.search(r"/races/"+ds+r"/\\d+/?$",u)))
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

"""Daily nationwide result coverage; archived pages are NOT verified pre-race snapshots."""
import argparse,json,re,time,urllib.parse,urllib.robotparser
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from collect_prerace_hex import BASE,UA,Page,fetch
from collect_postrace_results import Text,order
JST=ZoneInfo("Asia/Tokyo")
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--date",default=datetime.now(JST).strftime("%Y%m%d"));args=ap.parse_args()
 ds=args.date;out=Path("results/nationwide")/ds;out.mkdir(parents=True,exist_ok=True)
 robot=urllib.robotparser.RobotFileParser();robot.set_url(BASE+"/robots.txt")
 report={"date":ds,"retrieved_jst":datetime.now(JST).isoformat(),"source":BASE,"listed":0,"checked":0,"result_confirmed":0,"pending":[],"errors":[],"official_payout_confirmed":0,"warning":"Archived results only; not a pre-race model backtest."}
 try:
  robot.read()
  html=fetch(BASE+"/races/"+ds+"/",robot)
  page=Page();page.feed(html)
  urls=set(urllib.parse.urljoin(BASE,u).split("?")[0].split("#")[0] for u in page.links if re.search(r"/races/"+ds+r"/\d+/?$",u))
  urls|={BASE+"/races/"+ds+"/"+rid+"/" for rid in re.findall(r"/races/"+ds+r"/(\d{8,20})/?",html)}
  report["listed"]=len(urls)
  for url in sorted(urls):
   rid=url.rstrip("/").split("/")[-1];target=out/(rid+".json")
   try:
    # Keep existing confirmed outcomes and do not overwrite with weaker evidence.
    if target.exists() and json.loads(target.read_text()).get("status")=="result_confirmed":
     report["result_confirmed"]+=1;continue
    raw=fetch(url,robot);p=Text();p.feed(raw);txt="".join(p.parts)
    actual=order(txt);report["checked"]+=1
    if actual:
     rec={"race_id":rid,"race_date":ds,"source_url":url,"retrieved_jst":datetime.now(JST).isoformat(),"status":"result_confirmed","actual_first_second_third":actual,"official_trifecta_payout_per_100_yen":None,"payout_status":"unverified","verified_pre_race":False}
     target.write_text(json.dumps(rec,ensure_ascii=False,indent=2));report["result_confirmed"]+=1
    else:report["pending"].append(rid)
   except Exception as e:report["errors"].append({"race_id":rid,"error":str(e)[:200]})
   time.sleep(0.2)
 except Exception as e:report["errors"].append({"stage":"index","error":str(e)[:300]})
 (out/"audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()

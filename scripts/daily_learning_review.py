"""Daily, forward-only review of frozen forecasts; compare experimental model without deploying it."""
import json,sys
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
sys.path.insert(0,"scripts")
from integrated_race_forecast import forecast
JST=timezone(timedelta(hours=9))
today=datetime.now(JST).date()
results={}
for p in list(Path("results/auto_settlement").glob("*.json"))+list(Path("results/nationwide").glob("20*/*.json")):
 try:
  d=json.loads(p.read_text(encoding="utf-8"));a=d.get("actual_first_second_third")
  if isinstance(a,list) and len(a)==3 and len(set(a))==3:results[d["race_id"]]=a
 except (OSError,ValueError,KeyError):pass
bydate=defaultdict(lambda:{"races":0,"old_top1":0,"old_top5":0,"old_top10":0,"experimental_top1":0,"experimental_top5":0,"experimental_top10":0,"pair_top1":0,"errors":[],"miss_examples":[]})
for p in sorted(Path("results/real_integrated_predictions").glob("*.json")):
 try:
  old=json.loads(p.read_text(encoding="utf-8"));rid=old["race_id"]
  if rid not in results:continue
  day=rid[-8:];date=datetime.strptime(day,"%Y%m%d").date()
  if date>today:continue
  snapshot=Path("results/verified_model_inputs")/(rid+".json")
  if not snapshot.exists():continue
  data=json.loads(snapshot.read_text(encoding="utf-8"))
  # Only compare forecasts that were already saved, never retroactively replace them.
  if data["race_id"]!=rid:continue
  if old.get("model_version")!="scenario_order_v1":continue
  exp=forecast(data,variant="sashi_makuri_v1")
  actual=results[rid];a=bydate[day];a["races"]+=1
  old_top=[x["combination"] for x in old.get("top_trifecta",[])]
  new_top=[x["combination"] for x in exp["top_trifecta"]]
  for k in (1,5,10):
   a["old_top"+str(k)]+=int(actual in old_top[:k])
   a["experimental_top"+str(k)]+=int(actual in new_top[:k])
  pairs=[x["pair"] for x in old.get("predicted_first_second",[])]
  a["pair_top1"]+=int(actual[:2] in pairs[:1])
  if actual not in old_top[:5] and len(a["miss_examples"])<8:
   a["miss_examples"].append({"race_id":rid,"actual":actual,"old_top3":old_top[:3],"experimental_top3":new_top[:3],"lines":data.get("line_groups")})
 except Exception as e:
  bydate[p.stem[-8:]]["errors"].append({"race_id":p.stem,"error":str(e)})
for a in bydate.values():
 n=a["races"]
 for key in ("old_top1","old_top5","old_top10","experimental_top1","experimental_top5","experimental_top10","pair_top1"):
  a[key+"_rate"]=round(a[key]/n,4) if n else None
recent=[(today-timedelta(days=i)).strftime("%Y%m%d") for i in range(7)]
report={"generated_jst":datetime.now(JST).isoformat(),"last_7_days":{d:bydate[d] for d in recent},
 "policy":"DO NOT auto-promote. Any experiment needs subsequent untouched future dates and verified payout/odds for profitability claims.",
 "warning":"Experimental comparisons use a model conceived after earlier outcomes; only later dates count as prospective evidence. No guaranteed ROI."}
out=Path("results/prediction_accuracy/daily_learning_review.json")
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"generated_jst":report["generated_jst"],"days":{d:{"races":bydate[d]["races"],"old_top5":bydate[d]["old_top5"],"experimental_top5":bydate[d]["experimental_top5"]} for d in recent}},ensure_ascii=False))

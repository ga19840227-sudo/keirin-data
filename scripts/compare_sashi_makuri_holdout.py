"""Automated date holdout comparison: existing production heuristic vs experimental sashi/makuri.
Train/tuning cutoff 2026-11-10; 2026-11-11 held out. No parameter fitting on holdout.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,"scripts")
from integrated_race_forecast import forecast
actual={}
for p in list(Path("results/auto_settlement").glob("*.json"))+list(Path("results/nationwide").glob("20*/*.json")):
 try:
  d=json.loads(p.read_text());a=d.get("actual_first_second_third")
  if isinstance(a,list) and len(a)==3:actual[d["race_id"]]=a
 except (ValueError,KeyError):pass
stats={day:{v:{str(k):{"n":0,"hits":0} for k in (1,3,5,10,20)} for v in ("current","sashi_makuri_v1")} for day in ("development","holdout")}
errors=[];examples=[]
for p in sorted(Path("results/verified_model_inputs").glob("*.json")):
 rid=p.stem
 if rid not in actual:continue
 day="holdout" if rid.endswith("20261111") else "development" if rid.endswith(("20261109","20261110")) else None
 if day is None:continue
 try:
  d=json.loads(p.read_text());a=actual[rid];row={"race_id":rid,"actual":a}
  for variant in ("current","sashi_makuri_v1"):
   q=forecast(d,variant=variant)
   top=[x["combination"] for x in q["top_trifecta"]]
   row[variant]=top[:5]
   for k in (1,3,5,10,20):
    s=stats[day][variant][str(k)];s["n"]+=1;s["hits"]+=int(a in top[:k])
  if day=="holdout" and len(examples)<10:examples.append(row)
 except Exception as e:errors.append({"race_id":rid,"error":str(e)})
for day in stats:
 for v in stats[day].values():
  for s in v.values():s["rate"]=round(s["hits"]/s["n"],4) if s["n"] else None
out={"date_split":"2026-11-11 holdout; 2026-11-09/10 exploratory development","stats":stats,"holdout_examples":examples,"errors":errors,
"warning":"Variant is a hypothesis suggested by exploratory prior-day diagnostics. Date holdout is not fully independent of design choices; no profitability claim without verified payouts. Current production predictions unchanged."}
dest=Path("results/prediction_accuracy/sashi_makuri_holdout.json");dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps({"stats":stats,"errors":errors},ensure_ascii=False))

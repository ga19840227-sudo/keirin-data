import csv,glob,json,re,collections
from pathlib import Path
files=sorted(glob.glob("keirin_data/*_keirin.csv"))
counts=collections.Counter();months=[];seen=set();race=collections.defaultdict(lambda:{"ranks":set(),"payout":False,"rows":0})
for f in files:
 m=collections.Counter()
 with open(f,encoding="utf-8-sig",newline="") as h:
  for r in csv.DictReader(h):
   m["rows"]+=1
   key=(r.get("date"),r.get("race_id"))
   if not all(key):continue
   race[key]["rows"]+=1
   rank=str(r.get("rank") or "").strip()
   if rank in ("1","2","3"):race[key]["ranks"].add(rank)
   if re.search(r"\d+\s*[-=]\s*\d+\s*[-=]\s*\d+\s+[\d,]+\s*円",str(r.get("san_ren_tan") or "")):race[key]["payout"]=True
  months.append({"file":Path(f).name,"rows":m["rows"]})
complete=sum(x["ranks"]=={"1","2","3"} for x in race.values())
payout=sum(x["payout"] for x in race.values())
both=sum(x["ranks"]=={"1","2","3"} and x["payout"] for x in race.values())
report={"files":len(files),"rider_rows":sum(x["rows"] for x in months),"races":len(race),
"races_with_1st_2nd_3rd":complete,"races_with_trifecta_payout":payout,
"races_with_both_for_backtest":both,"recent_months":months[-8:],
"limitations":["lineup column contains tipster marks, not verified line positions",
"no structured pre-race trifecta odds or S/H/B in historical CSV"]}
Path("results").mkdir(exist_ok=True)
Path("results/historical_data_readiness.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False))

"""Settle archived integrated predictions against real historical race results.
Never use outcomes to choose predictions. Missing payout => unverifiable.
"""
import csv,glob,json,re
from pathlib import Path
def norm(x):return re.sub(r"[^0-9]","",str(x))
def number(x):
 try:return int(float(str(x)))
 except:return None
def actual(rows):
 ordered=sorted([(number(r.get("rank")),number(r.get("banum"))) for r in rows
                 if number(r.get("rank")) is not None and number(r.get("rank"))>0 and number(r.get("banum")) is not None])
 if len(ordered)<3 or [x[0] for x in ordered[:3]]!=[1,2,3]:return None
 return [x[1] for x in ordered[:3]]
def payout(text,order):
 s=str(text or "").replace("－","-").replace("ー","-").replace("−","-")
 for m in re.finditer(r"(?<!\d)(\d)\s*[-=]\s*(\d)\s*[-=]\s*(\d)\s+([\d,]+)\s*円",s):
  if [int(m.group(i)) for i in (1,2,3)]==order:return int(m.group(4).replace(",",""))
 return None
def main():
 predictions={}
 for p in glob.glob("results/real_integrated_predictions/*.json"):
  d=json.loads(Path(p).read_text(encoding="utf-8"))
  if d.get("status")!="HEURISTIC_NOT_VALIDATED":continue
  predictions[d["race_id"]]=d
 grouped={rid:[] for rid in predictions}
 files=0
 for p in sorted(glob.glob("keirin_data/*_keirin.csv")):
  files+=1
  with open(p,encoding="utf-8-sig",newline="") as f:
   for r in csv.DictReader(f):
    rid=r.get("race_id","")
    if rid in grouped:grouped[rid].append(r)
 report={"historical_files_scanned":files,"predictions":len(predictions),"matched_races":0,
         "settled_races":0,"results":[],"unmatched":[]}
 for rid,d in predictions.items():
  rows=grouped[rid]
  if not rows:
   report["unmatched"].append(rid);continue
  report["matched_races"]+=1
  order=actual(rows)
  if not order:
   report["results"].append({"race_id":rid,"status":"unverifiable_finishing_order"});continue
  returns=payout(rows[0].get("san_ren_tan"),order)
  plans=[]
  for plan in d["plans"]:
   pairs=[tuple(x) for x in plan["first_second_pairs"]]
   hit=tuple(order[:2]) in pairs
   if hit and returns is None:status="unverifiable_payout"
   else:status="settled"
   plans.append({"ticket_count":plan["ticket_count"],"cost_yen":plan["cost_yen"],
                 "hit":hit,"return_yen":returns if hit and returns is not None else 0 if not hit else None,
                 "profit_yen":(returns if hit else 0)-plan["cost_yen"] if status=="settled" else None,
                 "status":status})
  report["settled_races"]+=int(all(p["status"]=="settled" for p in plans))
  report["results"].append({"race_id":rid,"actual_first_second_third":order,
                            "official_payout_per_100_yen":returns,"plans":plans})
 Path("results").mkdir(exist_ok=True)
 Path("results/real_integrated_settlement.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":main()

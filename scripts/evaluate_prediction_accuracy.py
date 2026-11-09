"""Evaluate frozen pre-start forecasts against confirmed results, without odds or hindsight."""
import json
from pathlib import Path
def main():
 out=Path("results/prediction_accuracy");out.mkdir(parents=True,exist_ok=True)
 preds=Path("results/real_integrated_predictions")
 resultfiles=list(Path("results/nationwide").glob("20*/*.json"))+list(Path("results/auto_settlement").glob("*.json"))
 actual={}
 for p in resultfiles:
  if p.name in ("audit.json","latest_audit.json"):continue
  try:
   d=json.loads(p.read_text());a=d.get("actual_first_second_third")
   if isinstance(a,list) and len(a)==3:actual[d["race_id"]]=a
  except (ValueError,KeyError):pass
 report={"forecasts":0,"settled_forecasts":0,"top1_pair_hits":0,"top3_pair_hits":0,"top10_pair_hits":0,"missing_results":[],"per_race":[],"note":"Pre-start forecasts only; pair hit means exact first and second; odds/payout excluded."}
 for p in sorted(preds.glob("*.json")):
  try:
   d=json.loads(p.read_text());rid=d["race_id"];report["forecasts"]+=1
   if rid not in actual:report["missing_results"].append(rid);continue
   a=actual[rid];pairs=[x["pair"] for x in d.get("predicted_first_second",[])]
   true=a[:2];report["settled_forecasts"]+=1
   for k in (1,3,10):
    if true in pairs[:k]:report["top"+str(k)+"_pair_hits"]+=1
   report["per_race"].append({"race_id":rid,"actual":a,"top1_pair":pairs[0] if pairs else None,"top1_hit":true in pairs[:1],"top3_hit":true in pairs[:3],"top10_hit":true in pairs[:10]})
  except Exception as e:report.setdefault("errors",[]).append({"file":str(p),"error":str(e)})
 for k in (1,3,10):
  n=report["settled_forecasts"];report["top"+str(k)+"_pair_hit_rate"]=round(report["top"+str(k)+"_pair_hits"]/n,4) if n else None
 (out/"latest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()

"""Evaluate frozen pre-start forecasts against confirmed results, without odds or hindsight."""
import json
from pathlib import Path
def main():
 out=Path("results/prediction_accuracy");out.mkdir(parents=True,exist_ok=True)
 preds=Path("results/real_integrated_predictions")
 resultfiles=list(Path("results/nationwide").glob("20*/*.json"))+list(Path("results/auto_settlement").glob("*.json"))
 actual={}
 payouts={}
 for p in resultfiles:
  if p.name in ("audit.json","latest_audit.json"):continue
  try:
   d=json.loads(p.read_text());a=d.get("actual_first_second_third")
   if isinstance(a,list) and len(a)==3:
    actual[d["race_id"]]=a
    pay=d.get("official_trifecta_payout_per_100_yen")
    if pay is not None and d.get("payout_status")=="verified":payouts[d["race_id"]]=float(pay)
  except (ValueError,KeyError):pass
 trifecta={"settled_races":0,"plans":{str(k):{"races":0,"hits":0,"stake_yen":0,"verified_payout_yen":0,"payout_verified_races":0} for k in (1,2,3)},"warning":"Third-place ALL plans; actual payout/ROI cannot be claimed without verified official payout data."}
 report={"forecasts":0,"settled_forecasts":0,"top1_pair_hits":0,"top3_pair_hits":0,"top10_pair_hits":0,"missing_results":[],"per_race":[],"note":"Pre-start forecasts only; pair hit means exact first and second; odds/payout excluded."}
 for p in sorted(preds.glob("*.json")):
  try:
   d=json.loads(p.read_text());rid=d["race_id"];report["forecasts"]+=1
   if rid not in actual:report["missing_results"].append(rid);continue
   a=actual[rid];pairs=[x["pair"] for x in d.get("predicted_first_second",[])]
   trifecta["settled_races"]+=1
   for plan in d.get("plans",[]):
    selected=plan.get("first_second_pairs",[])
    k=len(selected)
    if k not in (1,2,3) or plan.get("third")!="ALL_EXCEPT_FIRST_SECOND":continue
    s=trifecta["plans"][str(k)];s["races"]+=1
    s["stake_yen"]+=int(plan["cost_yen"])
    hit=a[:2] in selected
    s["hits"]+=int(hit)
    if rid in payouts:
     s["payout_verified_races"]+=1
     if hit:s["verified_payout_yen"]+=payouts[rid]
   true=a[:2];report["settled_forecasts"]+=1
   for k in (1,3,10):
    if true in pairs[:k]:report["top"+str(k)+"_pair_hits"]+=1
   report["per_race"].append({"race_id":rid,"actual":a,"top1_pair":pairs[0] if pairs else None,"top1_hit":true in pairs[:1],"top3_hit":true in pairs[:3],"top10_hit":true in pairs[:10]})
  except Exception as e:report.setdefault("errors",[]).append({"file":str(p),"error":str(e)})
 for k in (1,3,10):
  n=report["settled_forecasts"];report["top"+str(k)+"_pair_hit_rate"]=round(report["top"+str(k)+"_pair_hits"]/n,4) if n else None
 scenario_scores={}
 for p in sorted(Path("results/development_scenarios").glob("*.json")):
  try:
   d=json.loads(p.read_text());rid=p.stem
   if rid not in actual or "scenarios" not in d:continue
   truth=actual[rid][:2]
   for name,scenario in d["scenarios"].items():
    s=scenario_scores.setdefault(name,{"races":0,"top1_hits":0,"top3_hits":0,"top10_hits":0})
    s["races"]+=1
    for k in (1,3,10):s["top"+str(k)+"_hits"]+=int(truth in scenario["top_pairs"][:k])
  except Exception as e:report.setdefault("scenario_errors",[]).append(str(e))
 for s in scenario_scores.values():
  for k in (1,3,10):s["top"+str(k)+"_hit_rate"]=round(s["top"+str(k)+"_hits"]/s["races"],4) if s["races"] else None
 for s in trifecta["plans"].values():
  s["hit_rate"]=round(s["hits"]/s["races"],4) if s["races"] else None
  s["roi"]=round(s["verified_payout_yen"]/s["stake_yen"],4) if s["races"] and s["payout_verified_races"]==s["races"] else None
 report["trifecta"]=trifecta
 report["development_scenarios"]=scenario_scores
 report["scenario_warning"]="Six fixed hypotheses; no fitting or verified improvement. Small samples cannot establish superiority."
 (out/"latest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()

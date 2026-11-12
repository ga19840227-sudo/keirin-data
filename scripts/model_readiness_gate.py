"""Independent daily readiness gate: never recommend a bet without verified odds and calibrated probabilities.
Summarizes settled evidence and blocks auto-promotion on weak evidence.
"""
import json
from pathlib import Path
from datetime import datetime,timezone,timedelta
JST=timezone(timedelta(hours=9))
def read(path):
 try:return json.loads(Path(path).read_text(encoding="utf-8"))
 except (OSError,ValueError):return {}
review=read("results/prediction_accuracy/daily_learning_review.json")
accuracy=read("results/prediction_accuracy/latest.json")
days=review.get("last_7_days",{})
settled=accuracy.get("trifecta",{})
plans=settled.get("plans",{})
verified={k:{"races":v.get("races",0),"payout_verified_races":v.get("payout_verified_races",0),"roi":v.get("roi")} for k,v in plans.items()}
# Only observations after the experimental model was introduced count as prospective evidence.
prospective=[(day,d) for day,d in days.items() if day>="20261112" and d.get("races",0)>0]
n=sum(d["races"] for _,d in prospective)
old=sum(d.get("old_top5",0) for _,d in prospective)
new=sum(d.get("experimental_top5",0) for _,d in prospective)
report={
 "generated_jst":datetime.now(JST).isoformat(),
 "production_model":"scenario_order_v1",
 "experimental_model":"sashi_makuri_v1",
 "prospective_from_date":"20261112",
 "prospective_comparable_races":n,
 "prospective_old_top5_hits":old,
 "prospective_experimental_top5_hits":new,
 "payout_coverage":verified,
 "automatic_promotion":False,
 "bet_recommendation_allowed":False,
 "blocking_reasons":[],
 "next_steps":["Collect independently verified trifecta payout and pre-start odds","Calibrate outcome probabilities on strictly prior dates","Validate both ROI and risk on untouched future races before any recommendation"]
}
if n<200:report["blocking_reasons"].append("Fewer than 200 forward-comparable settled races")
if new<=old:report["blocking_reasons"].append("Experimental model has not beaten existing top5 on prospective races")
if not plans or any(v.get("payout_verified_races",0)<v.get("races",0) for v in plans.values()):
 report["blocking_reasons"].append("Official trifecta payout verification incomplete")
report["blocking_reasons"].append("No validated calibrated probability and pre-start odds edge")
out=Path("results/prediction_accuracy/model_readiness.json")
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False))

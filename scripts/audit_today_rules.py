"""Run same fixed historical rules on today's genuinely timestamped pre-race snapshots.
Do not invent odds, realized returns, or after-the-fact results.
"""
import glob,json,itertools,re
from pathlib import Path
from datetime import datetime
records=[]
for p in sorted(glob.glob("results/verified_model_inputs/*.json")):
 d=json.loads(Path(p).read_text(encoding="utf-8"))
 if not d["start_jst"].startswith("2026-11-09"):continue
 if datetime.fromisoformat(d["captured_jst"])>=datetime.fromisoformat(d["start_jst"]):continue
 groups=d["line_groups"];riders=d["riders"]
 pos={n:(len(g),i) for g in groups for i,n in enumerate(g)}
 if set(pos)!={r["banum"] for r in riders}:continue
 options=[]
 for method in ("score","score_line","score_sbh","score_line_sbh","score_recent_win"):
  def score(r):
   n=r["banum"];v=float(r.get("race_score") or 0)
   sbh=sum(float(r.get(k) or 0) for k in ("s_count","h_count","b_count"))
   if method=="score_line":v+=2*(pos[n][0]-1)-1.5*pos[n][1]
   elif method=="score_sbh":v+=0.12*sbh
   elif method=="score_line_sbh":v+=1.5*(pos[n][0]-1)-1.5*pos[n][1]+0.12*sbh
   elif method=="score_recent_win":v+=0.1*float(r.get("win_rate_4m") or 0)
   return v
  ordered=[r["banum"] for r in sorted(riders,key=lambda r:(-score(r),r["banum"]))]
  for depth in (3,4,5):
   nums=ordered[:depth]
   options.append({"method":method,"depth":depth,"ranked":nums,"tickets":["-".join(map(str,x)) for x in itertools.permutations(nums,3)],"stake_yen":100*depth*(depth-1)*(depth-2)})
 records.append({"race_id":d["race_id"],"captured_jst":d["captured_jst"],"start_jst":d["start_jst"],"line_groups":groups,"riders":len(riders),"options":options,"trifecta_odds_verified":False,"status":"PRE_RACE_RULES_ONLY_ODDS_NOT_STORED"})
out={"date":"2026-11-09","eligible_races":len(records),"races":records,"warning":"Not a real-money recommendation. No verified exact-combination odds or settlement; cannot calculate expected value or ROI."}
Path("results/today_20261109_rules_audit.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"eligible_races":len(records),"races":[{"id":r["race_id"],"start":r["start_jst"],"score_recent_win_4car":next((o["ranked"] for o in r["options"] if o["method"]=="score_recent_win" and o["depth"]==4),None)} for r in records]},ensure_ascii=False))

"""Exploratory fixed-rule trifecta hit-rate check. No payout data: ROI unavailable."""
import glob,json,itertools
from pathlib import Path
files=sorted(glob.glob("results/historical_joined/*.json"))
methods=["score","score_line","score_sbh","score_line_sbh","score_recent_win"]
depths=[3,4,5]
out={"sample_size":0,"results":[],"caveat":"Retrospective archive is not certified unchanged pre-race; no payout or pre-race odds, so no ROI or profitability claim."}
records=[]
for f in files:
 d=json.loads(Path(f).read_text(encoding="utf-8"))
 actual=tuple(int(next(r["banum"] for r in d["results"] if r["rank"]==str(i))) for i in (1,2,3))
 riders=d["riders"]
 if len({r["banum"] for r in riders})!=len(riders):continue
 groups=d["line_groups"]
 line={n:(len(g),idx) for g in groups for idx,n in enumerate(g)}
 if set(line)!=set(r["banum"] for r in riders):continue
 records.append((d,actual,line))
out["sample_size"]=len(records)
for method in methods:
 for depth in depths:
  hit=0;staked=0;won_examples=[]
  for d,actual,line in records:
   def val(r):
    n=r["banum"];score=float(r.get("race_score") or 0)
    sbh=float(r.get("s_count") or 0)+float(r.get("h_count") or 0)+float(r.get("b_count") or 0)
    if method=="score":return score
    if method=="score_line":return score+2.0*(line[n][0]-1)-1.5*line[n][1]
    if method=="score_sbh":return score+0.12*sbh
    if method=="score_line_sbh":return score+1.5*(line[n][0]-1)-1.5*line[n][1]+0.12*sbh
    return score+0.1*float(r.get("win_rate_4m") or 0)
   ranked=sorted(d["riders"],key=lambda r:(-val(r),r["banum"]))
   nums=[r["banum"] for r in ranked[:depth]]
   picks=set(itertools.permutations(nums,3))
   staked+=100*len(picks)
   if actual in picks:
    hit+=1
    if len(won_examples)<5:won_examples.append({"race":d["key"],"actual":actual})
  out["results"].append({"method":method,"depth":depth,"races":len(records),"hits":hit,"hit_rate":round(hit/len(records),4) if records else None,"tickets_per_race":depth*(depth-1)*(depth-2),"total_stake_yen":staked,"return_yen":None,"roi":None,"examples":won_examples})
Path("results/historical_line_exploratory_test.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"sample_size":out["sample_size"],"results":out["results"]},ensure_ascii=False))

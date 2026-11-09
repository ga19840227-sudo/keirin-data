"""Compare fixed, interpretable race-development hypotheses on genuine pre-start snapshots."""
import json,math,itertools
from pathlib import Path
from datetime import datetime
def compare(data):
 riders={int(x["banum"]):x for x in data["riders"]}
 lines=data["line_groups"];nums=list(riders)
 if datetime.fromisoformat(data["captured_jst"])>=datetime.fromisoformat(data["start_jst"]):raise ValueError("post-start input")
 if sorted(n for g in lines for n in g)!=sorted(nums):raise ValueError("line mismatch")
 pos={n:(i,j,len(g)) for i,g in enumerate(lines) for j,n in enumerate(g)}
 def val(n,k):return float(riders[n].get(k) or 0)
 scenarios={}
 for mode in ("ability","front_control","makuri","second_sashi","line_cohesion","mixed"):
  scores={}
  for n in nums:
   i,j,size=pos[n];lead=lines[i][0]
   base=.035*(val(n,"race_score")-85)+.013*val(n,"win_rate_4m")+.008*val(n,"top2_rate_4m")
   front=.018*val(n,"b_count")+.016*val(n,"nige_4m")+.008*val(n,"h_count")
   makuri=.025*val(n,"maku_4m")+.009*val(n,"h_count")
   sashi=.025*val(n,"sashi_4m")+.012*val(n,"mark_4m")
   effect={"ability":0,"front_control":front if j==0 else 0,"makuri":makuri if j==0 else 0,"second_sashi":sashi+.08*val(lead,"b_count") if j==1 else 0,"line_cohesion":.16*(size-1)-.07*j,"mixed":(.4*front+.35*makuri if j==0 else .4*sashi+.025*val(lead,"b_count") if j==1 else 0)}[mode]
   scores[n]=base+effect
  w={n:math.exp(max(-12,min(12,v))) for n,v in scores.items()}
  pairs={}
  for a,b in itertools.permutations(nums,2):
   synergy=1.25 if mode in ("line_cohesion","mixed") and pos[a][0]==pos[b][0] and pos[b][1]==pos[a][1]+1 else 1
   pairs[(a,b)]=w[a]*w[b]*synergy
  ranked=sorted(pairs,key=lambda p:(-pairs[p],p))
  scenarios[mode]={"top_pairs":[list(p) for p in ranked[:10]],"assumed_development":{"ability":"individual ability","front_control":"early leader holds","makuri":"outside attack succeeds","second_sashi":"second rider overtakes leader","line_cohesion":"line finishes together","mixed":"combined factors"}[mode]}
 return scenarios
def main():
 result={}
 for p in sorted(Path("results/verified_model_inputs").glob("*.json")):
  try:
   d=json.loads(p.read_text());result[d["race_id"]]={"captured_jst":d["captured_jst"],"start_jst":d["start_jst"],"scenarios":compare(d)}
  except Exception as e:result[p.stem]={"error":str(e)}
 out=Path("results/development_scenarios");out.mkdir(parents=True,exist_ok=True)
 for rid,rec in result.items():(out/(rid+".json")).write_text(json.dumps(rec,ensure_ascii=False,indent=2))
 print(json.dumps({"processed":len(result),"valid":sum("scenarios" in x for x in result.values())},ensure_ascii=False))
if __name__=="__main__":main()

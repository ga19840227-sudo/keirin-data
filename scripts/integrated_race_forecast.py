"""Integrated pre-race keirin forecast.
Inputs: one JSON file with race_id, start_jst, captured_jst, riders and
explicit line_groups. Each rider requires banum, race_score, running_style,
win_rate_4m, top2_rate_4m, top3_rate_4m, nige_4m, maku_4m,
s_count, b_count, h_count. Optional odds_by_combo for EV.
Never infer lines from prefecture or use final ranks.
"""
import argparse,itertools,json,math
from datetime import datetime
from pathlib import Path

def timestamp(v):
    d=datetime.fromisoformat(v.replace("Z","+00:00"))
    if d.tzinfo is None:raise ValueError("timestamps must include timezone")
    return d

def number(r,key):
    if key not in r or r[key] is None:raise ValueError("missing rider field "+key)
    return float(r[key])

def forecast(data):
    if timestamp(data["captured_jst"])>=timestamp(data["start_jst"]):
        raise ValueError("snapshot was not captured before start")
    riders=data["riders"];nums=[int(r["banum"]) for r in riders]
    if len(set(nums))!=len(nums) or len(nums)<5:raise ValueError("invalid rider numbers")
    groups=data["line_groups"]
    flat=[int(n) for group in groups for n in group]
    if sorted(flat)!=sorted(nums):raise ValueError("line groups must contain every rider exactly once")
    if any(not isinstance(g,list) or not g for g in groups):raise ValueError("invalid line groups")
    required=("race_score","win_rate_4m","top2_rate_4m","top3_rate_4m","nige_4m","maku_4m","s_count","b_count","h_count")
    for r in riders:
        for k in required:number(r,k)
        if not r.get("running_style"):raise ValueError("missing running_style")
    bynum={int(r["banum"]):r for r in riders}
    # Explicit line-position features, not prefecture proxy.
    positions={int(n):(gi,pi,len(g)) for gi,g in enumerate(groups) for pi,n in enumerate(g)}
    lead_pressure=sum(number(bynum[int(g[0])],"b_count")+number(bynum[int(g[0])],"nige_4m") for g in groups)
    strength={}
    for n,r in bynum.items():
        gi,pi,sz=positions[n]
        lead=pi==0;second=pi==1
        base=.025*(number(r,"race_score")-85)+.012*number(r,"win_rate_4m")+.007*number(r,"top2_rate_4m")+.004*number(r,"top3_rate_4m")
        front=.012*number(r,"b_count")+.009*number(r,"s_count")+.012*number(r,"nige_4m")
        chase=.015*number(r,"maku_4m")+.012*number(r,"h_count")
        pressure=max(0,lead_pressure-8)/max(1,len(groups))
        leader_effect=(front-.025*pressure) if lead else 0
        # A second rider benefits from their own leader's strength.
        leader=bynum[int(groups[gi][0])]
        second_effect=(.13+.004*number(leader,"race_score")-.32) if second else 0
        solo_effect=-.10 if sz==1 else 0
        strength[n]=base+leader_effect+chase+second_effect+solo_effect
    # Conditional Plackett-Luce with same-line position interaction.
    # Heuristic initial coefficients: NOT trained or calibrated probabilities.
    weights={n:math.exp(max(-8,min(8,v))) for n,v in strength.items()}
    triples={}
    for a,b,c in itertools.permutations(nums,3):
        same=positions[a][0]==positions[b][0]
        pos_a,pos_b=positions[a][1],positions[b][1]
        synergy=1.18 if same and pos_a==0 and pos_b==1 else 1.10 if same and pos_a==1 and pos_b==0 else 1.0
        raw=weights[a]*weights[b]*weights[c]*synergy
        triples[(a,b,c)]=raw
    total=sum(triples.values())
    probs={k:v/total for k,v in triples.items()}
    pairs={}
    for (a,b,c),p in probs.items():pairs[(a,b)]=pairs.get((a,b),0)+p
    ranked=sorted(pairs,key=pairs.get,reverse=True)
    odds=data.get("odds_by_combo",{})
    plans=[]
    for count in (1,2,3):
        selected=ranked[:count]
        tickets=[(a,b,c) for a,b in selected for c in nums if c not in (a,b)]
        ticket_probs=[probs[t] for t in tickets]
        ev=None
        if odds and all("-".join(map(str,t)) in odds for t in tickets):
            ev=sum(p*float(odds["-".join(map(str,t))]) for t,p in zip(tickets,ticket_probs))/len(tickets)
        plans.append({"first_second_pairs":[list(p) for p in selected],
                      "third":"ALL_EXCEPT_FIRST_SECOND","ticket_count":len(tickets),
                      "cost_yen":100*len(tickets),"hit_probability_uncalibrated":round(sum(ticket_probs),6),
                      "expected_return_ratio_uncalibrated":round(ev,5) if ev is not None else None})
    return {"race_id":data["race_id"],"status":"HEURISTIC_NOT_VALIDATED",
            "line_groups":groups,"predicted_first_second":[{"pair":list(p),"uncalibrated_probability":round(pairs[p],6)} for p in ranked[:10]],
            "plans":plans,"warning":"Illustrative integrated model; probabilities and EV must be calibrated and tested on genuine pre-race snapshots."}

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("snapshot_json");ap.add_argument("--out",default="results/integrated_prediction.json")
    args=ap.parse_args()
    result=forecast(json.loads(Path(args.snapshot_json).read_text(encoding="utf-8")))
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

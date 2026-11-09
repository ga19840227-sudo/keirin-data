"""Trifecta structure comparison, strictly chronological, no post-race predictors.
This is a provisional structure study; it is NOT the full line/SBH/odds model.
"""
import csv, itertools
from collections import defaultdict
from pathlib import Path
from backtest import load, actual_order, parse_payout, num

OUT=Path("results"); OUT.mkdir(exist_ok=True)

def rank_players(players,h,mode):
    def score(p):
        name=p.get("player_name","").strip()
        n,w,two,three=h[name]
        base=num(p.get("race_score"),80) or 80
        win=(w+1)/(n+8)
        podium=(three+3)/(n+12)
        style=p.get("running_style","")
        if mode==0:return base
        if mode==1:return base*.7+win*30
        if mode==2:return base*.65+podium*35
        if mode==3:return base*.6+win*20+podium*20
        if mode==4:return base+.9*("逃" in style)-.5*("追" in style)
        return base+.9*("追" in style)-.5*("逃" in style)
    ordered=sorted(players,key=score,reverse=True)
    return list(dict.fromkeys(int(num(p["banum"])) for p in ordered if num(p.get("banum")) is not None))

def tickets(ranked,shape):
    if len(ranked)<5:return []
    all_b=ranked
    if shape=="top1-all-all":
        a=all_b[:1];b=all_b;c=all_b
    elif shape=="top2-all-all":
        a=all_b[:2];b=all_b;c=all_b
    elif shape=="top1-top3-all":
        a=all_b[:1];b=all_b[:3];c=all_b
    elif shape=="top2-top4-all":
        a=all_b[:2];b=all_b[:4];c=all_b
    elif shape=="top2-all-top5":
        a=all_b[:2];b=all_b;c=all_b[:5]
    elif shape=="top3-top4-top5":
        a=all_b[:3];b=all_b[:4];c=all_b[:5]
    elif shape=="top1-all-top4":
        a=all_b[:1];b=all_b;c=all_b[:4]
    elif shape=="top1-top4-all":
        a=all_b[:1];b=all_b[:4];c=all_b
    else:raise ValueError(shape)
    return list(dict.fromkeys((x,y,z) for x in a for y in b for z in c if len({x,y,z})==3))

def metrics(rows):
    stake=sum(x[0] for x in rows); returned=sum(x[1] for x in rows)
    eq=peak=dd=0
    for cost,pay,hit in rows:
        eq+=pay-cost;peak=max(peak,eq);dd=max(dd,peak-eq)
    return {"races":len(rows),"stake":stake,"returned":returned,
            "profit":returned-stake,"roi":round(returned/stake,5) if stake else None,
            "hit_rate":round(sum(x[2] for x in rows)/len(rows),5) if rows else None,
            "max_drawdown":dd}

def main():
    races,_=load()
    dates=sorted({d for d,_ in races})
    if len(dates)<30:raise SystemExit("Need at least 30 days")
    train_end=dates[int(len(dates)*.6)-1]
    val_end=dates[int(len(dates)*.8)-1]
    hist=defaultdict(lambda:[0,0,0,0])
    events={"train":[],"validation":[],"test":[]}
    for date in dates:
        today=[p for (d,_),p in races.items() if d==date]
        split="train" if date<=train_end else "validation" if date<=val_end else "test"
        for players in today:
            actual=actual_order(players)
            if actual is None:continue
            pay=parse_payout(players[0].get("san_ren_tan"),actual)
            ranked={mode:rank_players(players,hist,mode) for mode in range(6)}
            events[split].append((ranked,actual,pay))
        for players in today:
            for p in players:
                name=p.get("player_name","").strip();r=num(p.get("rank"))
                if name and r is not None and r>0:
                    h=hist[name];h[0]+=1;h[1]+=r==1;h[2]+=r<=2;h[3]+=r<=3
    shapes=("top1-all-all","top2-all-all","top1-top3-all","top2-top4-all",
            "top2-all-top5","top3-top4-top5","top1-all-top4","top1-top4-all")
    caps=(1000,3000,6000,12000)
    strategies=list(itertools.product(range(6),shapes,caps))
    def run(s,split):
        mode,shape,cap=s;records=[];missing=0
        for ranked,actual,pay in events[split]:
            picks=tickets(ranked[mode],shape)
            if not picks or len(picks)*100>cap:continue
            hit=actual in picks
            if hit and pay is None:
                missing+=1;continue
            records.append((len(picks)*100,pay if hit else 0,int(hit)))
        return metrics(records),missing
    train=[(s,*run(s,"train")) for s in strategies]
    eligible=[x for x in train if x[1]["races"]>=500]
    eligible.sort(key=lambda x:x[1]["roi"] if x[1]["roi"] is not None else -1,reverse=True)
    best=eligible[0] if eligible else None
    output=OUT/"structure_backtest.csv"
    with output.open("w",encoding="utf-8-sig",newline="") as fh:
        writer=csv.writer(fh)
        writer.writerow(["mode","shape","budget_cap","split","races","stake","returned","profit","roi","hit_rate","max_drawdown","unverifiable"])
        if best:
            for split in ("train","validation","test"):
                m,missing=run(best[0],split)
                writer.writerow([*best[0],split,*[m[k] for k in ("races","stake","returned","profit","roi","hit_rate","max_drawdown")],missing])
                print("SELECTED",best[0],split,m,"unverifiable",missing)
    print("scenarios",len(strategies),"eligible",len(eligible))
    print("WARNING: no verified pre-race lineup, SBH, or timestamped odds. Do not use for live betting.")
    print("Output:",output)

if __name__=="__main__":main()

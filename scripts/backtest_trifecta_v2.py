"""Chronological, leakage-conscious trifecta-only baseline.
No claims of pre-race odds, SBH or timestamped lineup availability.
"""
import csv, itertools, math, re
from collections import defaultdict
from pathlib import Path

ROOT=Path("keirin_data")
OUT=Path("results")
OUT.mkdir(exist_ok=True)

def number(s, default=None):
    try: return float(str(s).replace(",", ""))
    except (TypeError, ValueError): return default

def payout(text, target):
    text=str(text or "").replace("－","-").replace("ー","-").replace("−","-")
    for m in re.finditer(r"(?<!\\d)(\\d)\\s*[-=]\\s*(\\d)\\s*[-=]\\s*(\\d)\\s+([\\d,]+)\\s*円",text):
        if tuple(map(int,m.groups()[:3]))==target:
            return int(m.group(4).replace(",",""))
    return None

def finish(players):
    vals=[]
    for p in players:
        r=number(p.get("rank")); b=number(p.get("banum"))
        if r is not None and r>0 and b is not None: vals.append((r,int(b)))
    vals.sort()
    if len(vals)<3 or len({v[0] for v in vals[:3]})<3:return None
    return tuple(v[1] for v in vals[:3])

def load():
    races=defaultdict(list)
    for f in sorted(ROOT.glob("????_??_keirin.csv")):
        with f.open(encoding="utf-8-sig",newline="") as fh:
            for p in csv.DictReader(fh):
                if p.get("date") and p.get("race_id"):
                    races[(p["date"],p["race_id"])].append(p)
    return races

def features(p,h,mode):
    n,w,t2,t3=h[p.get("player_name","")]
    score=number(p.get("race_score"),80) or 80
    win=(w+1)/(n+8)
    podium=(t3+3)/(n+12)
    style=p.get("running_style","")
    if mode==0:return score
    if mode==1:return score*.75+100*win*.25
    if mode==2:return score*.65+100*podium*.35
    if mode==3:return score*.50+100*win*.25+100*podium*.25
    if mode==4:return score+.8*("逃" in style)-.4*("追" in style)
    if mode==5:return score+.8*("追" in style)-.4*("逃" in style)
    return score

def evaluate(rec):
    stake=sum(x[0] for x in rec); returned=sum(x[1] for x in rec)
    equity=peak=dd=0
    for cost,back,hit in rec:
        equity+=back-cost;peak=max(peak,equity);dd=max(dd,peak-equity)
    return dict(races=len(rec),stake=stake,returned=returned,
                profit=returned-stake,roi=round(returned/stake,5) if stake else None,
                hit_rate=round(sum(x[2] for x in rec)/len(rec),5) if rec else None,
                max_drawdown=dd)

def main():
    races=load()
    if not races:raise RuntimeError("No monthly CSVs")
    dates=sorted({d for d,_ in races})
    if len(dates)<30:raise RuntimeError("Insufficient dates")
    a=dates[int(len(dates)*.6)-1];b=dates[int(len(dates)*.8)-1]
    hist=defaultdict(lambda:[0,0,0,0])
    splits={s:[] for s in ("train","validation","test")}
    for day in dates:
        today=[p for (d,_),p in races.items() if d==day]
        split="train" if day<=a else "validation" if day<=b else "test"
        for players in today:
            actual=finish(players)
            if not actual:continue
            ranked={}
            for mode in range(6):
                ranked[mode]=[int(number(p.get("banum"))) for p in
                    sorted(players,key=lambda p:features(p,hist,mode),reverse=True)
                    if number(p.get("banum")) is not None]
            # Only retain realized payout for scoring, never as input to rank.
            pay=payout(players[0].get("san_ren_tan"),actual)
            splits[split].append((ranked,actual,pay))
        # Update histories AFTER all races for this date.
        for players in today:
            for p in players:
                name=p.get("player_name","").strip();r=number(p.get("rank"))
                if name and r is not None and r>0:
                    h=hist[name];h[0]+=1;h[1]+=r==1;h[2]+=r<=2;h[3]+=r<=3
    def test(strategy,split):
        mode,depth,tickets=strategy
        rows=[];unverified=0
        for ranked,actual,pay in splits[split]:
            nums=list(dict.fromkeys(ranked[mode]))[:depth]
            if len(nums)<depth:continue
            picks=list(itertools.islice(itertools.permutations(nums,3),tickets))
            if len(picks)<tickets:continue
            hit=actual in picks
            if hit and pay is None:
                unverified+=1
                continue
            rows.append((len(picks)*100,(pay or 0) if hit else 0,int(hit)))
        return evaluate(rows),unverified
    strategies=list(itertools.product(range(6),(3,4,5),(1,2,3,4,6,10)))
    # Select with training only; validation is a gate, not a second optimization.
    train=sorted([(s,*test(s,"train")) for s in strategies],
                 key=lambda x:x[1]["roi"] if x[1]["roi"] is not None else -1,reverse=True)
    eligible=[x for x in train if x[1]["races"]>=1000]
    best=eligible[0] if eligible else None
    path=OUT/"trifecta_v2_summary.csv"
    with path.open("w",newline="",encoding="utf-8-sig") as fh:
        w=csv.writer(fh)
        w.writerow(["strategy","split","races","stake","returned","profit","roi","hit_rate","max_drawdown","unverified_hits"])
        if best:
            s=best[0]
            for split in ("train","validation","test"):
                st,missing=test(s,split)
                w.writerow([str(s),split,*[st[k] for k in ("races","stake","returned","profit","roi","hit_rate","max_drawdown")],missing])
                print("SELECTED",s,split,st,"unverified_hits",missing)
    print("scenarios",len(strategies),"train_eligible",len(eligible))
    print("IMPORTANT: no verified pre-race odds or SBH; this is a ranking baseline, not EV or bankroll optimization.")
    print("Output",path)

if __name__=="__main__":main()

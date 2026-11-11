"""Audit genuine frozen forecasts by race date, outcome, line finish and rider traits.
Descriptive diagnosis only; no result is used to change a past forecast.
"""
import json,collections
from pathlib import Path

def load(p):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except (OSError,ValueError):return None

actual={}
payouts={}
for p in list(Path("results/auto_settlement").glob("*.json"))+list(Path("results/nationwide").glob("20*/*.json")):
    d=load(p)
    if not isinstance(d,dict):continue
    rid=d.get("race_id");a=d.get("actual_first_second_third")
    if isinstance(rid,str) and isinstance(a,list) and len(a)==3:
        actual[rid]=a
        if d.get("payout_status")=="verified" and isinstance(d.get("official_trifecta_payout_per_100_yen"),(int,float)):
            payouts[rid]=d["official_trifecta_payout_per_100_yen"]

def metric():return {"races":0,"top1_pair_hits":0,"top3_pair_hits":0,"top5_trifecta_hits":0,"top10_trifecta_hits":0,"top20_trifecta_hits":0}
def add(s,pairs,triples,a):
    s["races"]+=1
    s["top1_pair_hits"]+=int(a[:2] in pairs[:1])
    s["top3_pair_hits"]+=int(a[:2] in pairs[:3])
    for k in (5,10,20):
        s["top"+str(k)+"_trifecta_hits"]+=int(a in triples[:k])
def rates(d):
    for s in d.values():
        n=s["races"]
        for k,v in list(s.items()):
            if k.endswith("_hits"):s[k.replace("_hits","_rate")]=round(v/n,4) if n else None
def binned(v):
    if v<3:return "low_0_2"
    if v<8:return "mid_3_7"
    return "high_8_plus"

by_day=collections.defaultdict(metric)
by_finish=collections.defaultdict(metric)
by_prediction=collections.defaultdict(metric)
by_leader_b=collections.defaultdict(metric)
by_leader_maku=collections.defaultdict(metric)
by_leader_sashi=collections.defaultdict(metric)
by_line_count=collections.defaultdict(metric)
by_top_pick=collections.defaultdict(metric)
examples=collections.defaultdict(list)
missing=[]
rows=[]
for p in sorted(Path("results/real_integrated_predictions").glob("*.json")):
    pred=load(p)
    if not isinstance(pred,dict):continue
    rid=pred.get("race_id")
    if rid not in actual:continue
    data=load(Path("results/verified_model_inputs")/(rid+".json"))
    if not data:missing.append(rid);continue
    a=actual[rid]
    pairs=[x["pair"] for x in pred.get("predicted_first_second",[])]
    triples=[x["combination"] for x in pred.get("top_trifecta",[])]
    if not pairs:continue
    groups=data.get("line_groups",[])
    pos={int(n):(gi,pi) for gi,g in enumerate(groups) for pi,n in enumerate(g)}
    riders={int(x["banum"]):x for x in data.get("riders",[])}
    if any(n not in pos for n in a):continue
    same=pos[a[0]][0]==pos[a[1]][0]
    order=(pos[a[0]][1],pos[a[1]][1])
    finish=("leader_then_second" if same and order==(0,1) else
            "second_then_leader" if same and order==(1,0) else
            "same_line_other" if same else "cross_line")
    predicted_first=pairs[0][0]
    r=riders.get(predicted_first,{})
    buckets={
      "day":rid[-8:],
      "finish":finish,
      "prediction":"same_line_pair" if pos[pairs[0][0]][0]==pos[pairs[0][1]][0] else "cross_line_pair",
      "leader_b":binned(float(r.get("b_count",0))),
      "leader_maku":binned(float(r.get("maku_4m",0))),
      "leader_sashi":binned(float(r.get("sashi_4m",0))),
      "line_count":str(len(groups)),
      "top_pick":"first_correct" if predicted_first==a[0] else "first_wrong"
    }
    for key,target in [("day",by_day),("finish",by_finish),("prediction",by_prediction),("leader_b",by_leader_b),("leader_maku",by_leader_maku),("leader_sashi",by_leader_sashi),("line_count",by_line_count),("top_pick",by_top_pick)]:
        add(target[buckets[key]],pairs,triples,a)
    hit=a in triples[:10]
    if len(examples[finish])<8:examples[finish].append({"race_id":rid,"actual":a,"top1":pairs[0],"top_trifecta":triples[:3],"top10_hit":hit})
    rows.append({"race_id":rid,"actual":a,"top1_pair":pairs[0],"top10_trifecta_hit":hit,"finish_type":finish,"features":buckets})
for d in (by_day,by_finish,by_prediction,by_leader_b,by_leader_maku,by_leader_sashi,by_line_count,by_top_pick):rates(d)
out={"scope":"Frozen pre-start predictions with verified pre-start rider inputs and confirmed finish only",
"n":len(rows),"by_day":dict(by_day),"by_actual_finish":dict(by_finish),"by_predicted_pair":dict(by_prediction),
"by_predicted_first_b_count":dict(by_leader_b),"by_predicted_first_maku":dict(by_leader_maku),
"by_predicted_first_sashi":dict(by_leader_sashi),"by_line_count":dict(by_line_count),
"by_first_place_correctness":dict(by_top_pick),"examples":dict(examples),"missing_inputs":missing,
"payout_verified_count":sum(x["race_id"] in payouts for x in rows),"per_race":rows,
"caution":"Descriptive association, not causal proof; do not fit and claim success on same races. Exact trifecta topK metrics count only forecasts with top_trifecta; check date and availability."}
dest=Path("results/prediction_accuracy/diagnostic_audit.json")
dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in out.items() if k not in ("per_race","examples")},ensure_ascii=False))

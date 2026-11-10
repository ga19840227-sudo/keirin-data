"""Retrospective paired comparison on identical verified pre-start inputs.
This is in-sample exploratory replay, not forward validation or proof of profit.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,"scripts")
from integrated_race_forecast import forecast

actual={}
for p in list(Path("results/auto_settlement").glob("*.json"))+list(Path("results/nationwide").glob("20*/*.json")):
    if p.name=="audit.json":continue
    try:
        d=json.loads(p.read_text(encoding="utf-8"))
        a=d.get("actual_first_second_third")
        if isinstance(a,list) and len(a)==3:actual[d["race_id"]]=a
    except (ValueError,KeyError):pass

scores={v:{str(k):{"races":0,"hits":0} for k in (1,2,3)} for v in ("baseline","scenario")}
ranked={v:{str(k):{"races":0,"hits":0} for k in (1,3,5,10,20)} for v in ("baseline","scenario")}
rows=[];errors=[]
for p in sorted(Path("results/verified_model_inputs").glob("*.json")):
    rid=p.stem
    if rid not in actual:continue
    try:
        data=json.loads(p.read_text(encoding="utf-8"))
        if data.get("race_id")!=rid:raise ValueError("race ID mismatch")
        a=actual[rid];row={"race_id":rid,"actual":a}
        for version,flag in (("baseline",False),("scenario",True)):
            pred=forecast(data,scenario=flag)
            pairs=[x["pair"] for x in pred["predicted_first_second"]]
            top=[x["combination"] for x in pred["top_trifecta"]]
            row[version]={}
            for k in (1,2,3):
                hit=a[:2] in pairs[:k]
                scores[version][str(k)]["races"]+=1
                scores[version][str(k)]["hits"]+=int(hit)
                row[version]["third_all_"+str(k)]=hit
            for k in (1,3,5,10,20):
                hit=a in top[:k]
                ranked[version][str(k)]["races"]+=1
                ranked[version][str(k)]["hits"]+=int(hit)
                row[version]["ranked_"+str(k)]=hit
        rows.append(row)
    except Exception as e:errors.append({"race_id":rid,"error":str(e)})
for group in (scores,ranked):
    for v in group.values():
        for s in v.values():
            s["hit_rate"]=round(s["hits"]/s["races"],4) if s["races"] else None
out={"sample_size":len(rows),"third_all_plans":scores,"ranked_trifecta":ranked,"per_race":rows,"errors":errors,
"warning":"Retrospective paired replay, using the same saved pre-start inputs. Scenario coefficients are unvalidated; results are not forward accuracy or profitability. Official payout not included."}
dest=Path("results/prediction_accuracy/scenario_replay.json");dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in out.items() if k!="per_race"},ensure_ascii=False))

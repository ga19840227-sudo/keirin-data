"""Inspect actual saved pre-race snapshots, never count raw page text as structured features."""
import json,glob
from pathlib import Path
out={"files_checked":0,"verified_pre_race":0,"parsed_line_groups":0,"valid_line_groups":0,"structured_sbh":0,"structured_odds":0,"ready_for_integrated_model":0,"examples":[],"issues":[]}
for p in sorted(glob.glob("snapshots/20*/*.json")):
    if p.endswith("collection_audit.json"):continue
    try:d=json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception as e:out["issues"].append(p+": "+str(e));continue
    out["files_checked"]+=1
    pre=d.get("verified_pre_race") is True
    line=d.get("line_groups")
    parsed=isinstance(line,list) and len(line)>0
    flat=[n for g in line for n in g] if parsed and all(isinstance(g,list) for g in line) else []
    valid=bool(flat) and len(set(flat))==len(flat) and all(isinstance(n,int) and 1<=n<=9 for n in flat)
    sbh=d.get("sbh_structured") is True
    odds=d.get("odds_structured") is True
    out["verified_pre_race"]+=int(pre)
    out["parsed_line_groups"]+=int(parsed)
    out["valid_line_groups"]+=int(valid)
    out["structured_sbh"]+=int(sbh)
    out["structured_odds"]+=int(odds)
    out["ready_for_integrated_model"]+=int(pre and valid and sbh and odds)
    if len(out["examples"])<12:out["examples"].append({"file":p,"source_url":d.get("source_url"),"pre_race":pre,"line_groups":line,"lineup_raw":d.get("lineup_raw"),"sbh":sbh,"odds":odds,"start_jst":d.get("start_jst")})
Path("results").mkdir(exist_ok=True)
Path("results/snapshot_readiness_audit.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(out,ensure_ascii=False,indent=2))

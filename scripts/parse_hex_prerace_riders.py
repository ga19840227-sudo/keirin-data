"""Parse rider ability and pre-race S/H/B from stored public page text.
Conservative: reject ambiguous rows, do not guess. No odds means no EV claim.
"""
import json,re,glob
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
def parse_rows(text):
    lines=[s.strip() for s in text.splitlines() if s.strip()]
    rows={}
    for i in range(len(lines)-4):
        if not re.fullmatch(r"[1-9]",lines[i]):continue
        n=int(lines[i])
        if not re.fullmatch(r"\d{2,3}\.\d{2}",lines[i+2]):continue
        if lines[i+3] not in ("逃","追","両"):continue
        # Next rider boundary is a number followed by name, score, and running style.
        end=next((j for j in range(i+4,len(lines)-3)
                  if re.fullmatch(r"[1-9]",lines[j]) and
                  re.fullmatch(r"\d{2,3}\.\d{2}",lines[j+2]) and lines[j+3] in ("逃","追","両")),len(lines))
        section=lines[i+4:end]
        rates=next((j for j in range(len(section)-2) if all(re.fullmatch(r"(?:\d+(?:\.\d+)?%|—)",x) for x in section[j:j+3])),None)
        if rates is None:continue
        # Following rates: 1st,2nd,3rd,other,S,H,B,逃,捲,差,マ
        numbers=section[rates+3:rates+14]
        if len(numbers)<11 or not all(re.fullmatch(r"\d+",x) for x in numbers):continue
        def pct(v):return float(v.strip("%")) if v!="—" else None
        vals=[pct(v) for v in section[rates:rates+3]]
        if any(v is None for v in vals):continue
        rows[n]={"banum":n,"player_name_raw":lines[i+1],"race_score":float(lines[i+2]),
                 "running_style":lines[i+3],"win_rate_4m":vals[0],"top2_rate_4m":vals[1],"top3_rate_4m":vals[2],
                 "s_count":int(numbers[4]),"h_count":int(numbers[5]),"b_count":int(numbers[6]),
                 "nige_4m":int(numbers[7]),"maku_4m":int(numbers[8]),
                 "sashi_4m":int(numbers[9]),"mark_4m":int(numbers[10])}
    return rows
def main():
    report={"files":0,"verified":0,"parsed_riders":0,"complete_integrated_inputs":0,"examples":[],"failures":[]}
    dest=Path("results/verified_model_inputs");dest.mkdir(parents=True,exist_ok=True)
    for path in sorted(glob.glob("snapshots/20*/*.json")):
        if path.endswith("collection_audit.json"):continue
        d=json.loads(Path(path).read_text(encoding="utf-8"));report["files"]+=1
        if not d.get("verified_pre_race"):continue
        rows=parse_rows(d.get("page_text",""))
        # Girls races do not have a fixed line formation. Explicitly model
        # independent riders; never invent a conventional line.
        is_girls="ガールズ" in d.get("page_text","")[:700]
        groups=d.get("line_groups")
        if not groups and is_girls and len(rows)>=5:
            groups=[[n] for n in sorted(rows)]
        if not groups:
            report["failures"].append({"file":path,"reason":"line_unavailable","parsed":sorted(rows)})
            continue
        report["verified"]+=1
        report["parsed_riders"]+=len(rows)
        nums=[int(n) for g in groups for n in g]
        if len(nums)!=len(set(nums)) or set(nums)!=set(rows):
            report["failures"].append({"file":path,"parsed":sorted(rows),"expected":sorted(nums)})
            continue
        payload={"race_id":d["source_url"].rstrip("/").split("/")[-1],
                 "source_url":d["source_url"],"captured_jst":d["captured_jst"],
                 "start_jst":d["start_jst"],"line_groups":groups,"line_status":"no_fixed_lines_girls" if is_girls else "published",
                 "riders":[rows[n] for n in nums]}
        name=payload["race_id"]
        (dest/(name+".json")).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
        report["complete_integrated_inputs"]+=1
        report["examples"].append({"race_id":name,"line_groups":groups,"riders":len(rows)})
    Path("results/hex_rider_parse_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()

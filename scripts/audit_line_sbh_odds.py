"""Audit verified PRE-RACE line, SBH and odds availability.
No historical field is trusted without a timestamp and explicit pre-race source.
"""
import csv,json,re
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT=Path("keirin_data");OUT=Path("results");OUT.mkdir(exist_ok=True)
LINE_KEYS=("lineup","predicted_lineup","line_order","line_prediction")
ODDS_KEYS=("trifecta_odds","sanrentan_odds","odds_3t","odds")
SBH_KEYS=("s_count","b_count","h_count","S","B","H","sbh")
TIMESTAMP_KEYS=("captured_at_jst","collected_jst","odds_captured_at","snapshot_jst")
START_KEYS=("start_jst","scheduled_start_jst","start_time_jst")
def parse_ts(x):
    try:
        d=datetime.fromisoformat(str(x).strip().replace("Z","+00:00"))
        return d if d.tzinfo else None
    except (TypeError,ValueError):return None
def valid_snapshot(r):
    captured=next((parse_ts(r.get(k)) for k in TIMESTAMP_KEYS if r.get(k)),None)
    start=next((parse_ts(r.get(k)) for k in START_KEYS if r.get(k)),None)
    return captured is not None and start is not None and captured<start
def line_groups(s):
    """Only explicit numbered groups, e.g. 1-2-3/4-5/6-7; no prefecture inference."""
    if not s:return None
    s=str(s).strip()
    s=re.sub(r"[｜|／]","/",s)
    groups=s.split("/")
    if not groups or any(not re.fullmatch(r"[1-9](?:[-=][1-9])*",g.strip()) for g in groups):return None
    nums=[[int(x) for x in re.split(r"[-=]",g.strip())] for g in groups]
    flat=[x for g in nums for x in g]
    if len(flat)!=len(set(flat)):return None
    return nums

files=sorted(ROOT.glob("????_??_keirin.csv"))
counts=Counter();examples=defaultdict(list);fields=set()
for f in files:
    with f.open(encoding="utf-8-sig",newline="") as fh:
        rd=csv.DictReader(fh);fields.update(rd.fieldnames or [])
        for r in rd:
            counts["rows"]+=1
            if r.get("race_id"):counts["race_rows"]+=1
            if r.get("lineup"):
                counts["lineup_filled"]+=1
                if line_groups(r["lineup"]):counts["lineup_structurally_parseable"]+=1
                elif len(examples["lineup_unparsed"])<5:examples["lineup_unparsed"].append(r["lineup"][:120])
            if valid_snapshot(r):
                counts["timestamp_verified_rows"]+=1
                if any(r.get(k) for k in LINE_KEYS) and line_groups(next((r[k] for k in LINE_KEYS if r.get(k)),"")):
                    counts["verified_line_rows"]+=1
                if any(r.get(k) for k in ODDS_KEYS):counts["verified_odds_rows"]+=1
                if any(r.get(k) for k in SBH_KEYS):counts["verified_sbh_rows"]+=1
report={"files":len(files),"counts":dict(counts),
        "available_columns":sorted(fields),
        "sample_unparsed_lineups":examples["lineup_unparsed"],
        "required_to_train_full_model":["pre-race timestamped line order with position","pre-race SBH rider stats","pre-race odds by exact trifecta combination"],
        "decision":"READY" if min(counts["verified_line_rows"],counts["verified_sbh_rows"],counts["verified_odds_rows"])>0 else "BLOCKED_MISSING_VERIFIED_PRERACE_DATA",
        "warning":"Do not infer lines from prefecture or interpret post-race S/B/H as pre-race data."}
(OUT/"line_sbh_odds_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))

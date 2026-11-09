"""Prepare real line-based model inputs; reject missing or mismatched rider features."""
import argparse,csv,json,re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
JST=ZoneInfo("Asia/Tokyo")
REQUIRED=("race_score","win_rate_4m","top2_rate_4m","top3_rate_4m","nige_4m","maku_4m")
def load_features(path):
    rows=list(csv.DictReader(open(path,encoding="utf-8-sig",newline="")))
    byid={}
    for row in rows:
        rid=row.get("race_id")
        if rid:byid.setdefault(rid,[]).append(row)
    return byid
def prepare(snap,rows):
    if snap.get("verified_pre_race") is not True:return None,"not verified pre-race"
    groups=snap.get("line_groups")
    if not groups:return None,"line groups absent"
    nums=[int(n) for g in groups for n in g]
    if len(nums)!=len(set(nums)):return None,"duplicate line rider"
    bynum={}
    for r in rows:
        raw=r.get("banum","")
        if not str(raw).strip().isdigit():continue
        n=int(raw)
        if n in bynum:return None,"duplicate feature rider"
        bynum[n]=r
    if set(nums)!=set(bynum):return None,"line and feature rider numbers differ"
    riders=[]
    for n in nums:
        row=bynum[n]
        if any(not str(row.get(k,"")).strip() for k in REQUIRED):return None,"missing ability feature"
        # Historical CSV has no verified pre-race SBH. Do not substitute current-race outcome.
        if any(not str(row.get(k,"")).strip() for k in ("s_count","b_count","h_count")):
            return None,"missing verified pre-race SBH; no invented values"
        riders.append({k:row[k] for k in REQUIRED+("s_count","b_count","h_count","running_style")}|{"banum":n})
    return {"race_id":snap["source_url"].rstrip("/").split("/")[-1],
            "captured_jst":snap["captured_jst"],"start_jst":snap["start_jst"],
            "line_groups":groups,"riders":riders},None
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--features",help="CSV of verified pre-race rider features")
    args=ap.parse_args()
    report={"snapshots":0,"with_real_line":0,"model_ready":0,"rejected":[]}
    byid=load_features(args.features) if args.features else {}
    out=Path("results/verified_model_inputs");out.mkdir(parents=True,exist_ok=True)
    for p in sorted(Path("snapshots").glob("20*/*.json")):
        if p.name=="collection_audit.json":continue
        snap=json.loads(p.read_text(encoding="utf-8"));report["snapshots"]+=1
        if snap.get("line_groups"):report["with_real_line"]+=1
        rid=snap.get("source_url","").rstrip("/").split("/")[-1]
        prepared,reason=prepare(snap,byid.get(rid,[]))
        if prepared:
            (out/(rid+".json")).write_text(json.dumps(prepared,ensure_ascii=False,indent=2),encoding="utf-8")
            report["model_ready"]+=1
        else:report["rejected"].append({"race_id":rid,"reason":reason})
    Path("results/verified_merge_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":main()

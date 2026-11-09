"""Check every day's pre-start forecast coverage; missing inputs never count as predicted."""
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
def main():
 ds=datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y%m%d")
 audit=Path("snapshots")/ds/"collection_audit.json"
 a=json.loads(audit.read_text()) if audit.exists() else {}
 snapshots=list((Path("snapshots")/ds).glob("*.json"))
 ids={p.stem for p in snapshots if p.stem!="collection_audit"}
 verified={p.stem for p in snapshots if p.stem!="collection_audit" and json.loads(p.read_text()).get("verified_pre_race")}
 inputs={p.stem for p in Path("results/verified_model_inputs").glob("*.json") if p.stem in verified}
 scenarios={p.stem for p in Path("results/development_scenarios").glob("*.json") if p.stem in inputs and "scenarios" in json.loads(p.read_text())}
 predictions={p.stem for p in Path("results/real_integrated_predictions").glob("*.json") if p.stem in inputs}
 report={"date":ds,"indexed_races":a.get("indexed_races"),"visited_in_latest_run":a.get("visited"),"latest_run_new_snapshots":a.get("snapshot_count"),"verified_snapshots":len(verified),"complete_rider_inputs":len(inputs),"six_scenario_forecasts":len(scenarios),"integrated_forecasts":len(predictions),"missing_rider_inputs":sorted(verified-inputs),"missing_scenarios":sorted(inputs-scenarios),"missing_integrated":sorted(inputs-predictions),"warning":"Coverage is not accuracy; a forecast is counted only when saved before the race."}
 out=Path("results/coverage");out.mkdir(parents=True,exist_ok=True)
 (out/(ds+".json")).write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":main()

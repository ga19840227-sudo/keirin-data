"""Deterministic integration smoke test with SYNTHETIC pre-race data.
Never present this as real race prediction or backtest.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,"scripts")
from integrated_race_forecast import forecast

riders=[]
for n in range(1,8):
    riders.append({"banum":n,"race_score":87+n,"running_style":"逃" if n in (1,4,6) else "追",
    "win_rate_4m":10+n,"top2_rate_4m":20+n,"top3_rate_4m":35+n,
    "nige_4m":n if n in (1,4,6) else 0,"maku_4m":n//2,
    "s_count":n,"b_count":n+2 if n in (1,4,6) else 0,"h_count":n//2})
data={"race_id":"SYNTHETIC_TEST","start_jst":"2026-11-10T12:00:00+09:00",
"captured_jst":"2026-11-10T11:30:00+09:00",
"riders":riders,"line_groups":[[1,2,3],[4,5],[6,7]]}
result=forecast(data)
assert len(result["predicted_first_second"])==10
assert [p["ticket_count"] for p in result["plans"]]==[5,10,15]
assert sum(p["uncalibrated_probability"] for p in result["predicted_first_second"])<1
try:
    forecast({**data,"captured_jst":"2026-11-10T12:01:00+09:00"})
    raise AssertionError("post-race data accepted")
except ValueError:pass
try:
    forecast({**data,"line_groups":[[1,2,3],[4,5],[6,6]]})
    raise AssertionError("duplicate rider accepted")
except ValueError:pass
Path("results").mkdir(exist_ok=True)
Path("results/integrated_smoke_test.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("PASS: integrated prediction with line/position/SBH, trifecta 3rd ALL, pre-race checks")

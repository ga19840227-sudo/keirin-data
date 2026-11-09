"""Audit which historical keirin CSV columns can support pre-race prediction.
Run: python scripts/audit_prerace.py
"""
import csv
import json
from collections import Counter
from pathlib import Path

files = sorted(Path("keirin_data").glob("????_??_keirin.csv"))
counts = Counter()
columns = set()
races = set()
for file in files:
    with file.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns.update(reader.fieldnames or [])
        for row in reader:
            counts["rows"] += 1
            if row.get("date") and row.get("race_id"):
                races.add((row["date"], row["race_id"]))
            for key, value in row.items():
                if key and value and value.strip():
                    counts[key] += 1

report = {
    "files": len(files),
    "races": len(races),
    "rows": counts["rows"],
    "fields": {
        key: {"exists": key in columns, "filled_rows": counts[key]}
        for key in sorted(columns | {"lineup", "S", "B", "H", "odds", "odds_timestamp"})
    },
    "warning": "Lineup lacks verified capture timestamp. Never use payouts, ranks, or other post-race outcomes as prediction inputs."
}
Path("results").mkdir(exist_ok=True)
Path("results/prerace_audit.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(report, ensure_ascii=False, indent=2))

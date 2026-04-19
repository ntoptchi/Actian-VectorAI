"""Quick inspector: print AADT distribution + top risky segments.

Run after _qa_call.ps1 writes scripts/trip-brief-sample.json.
"""
from __future__ import annotations

import json
from pathlib import Path

p = Path(__file__).parent / "trip-brief-sample.json"
d = json.loads(p.read_text(encoding="utf-8-sig"))

segs = d["segments"]
aadts = [s["aadt"] for s in segs if s.get("aadt")]
print(
    f"segs: {len(segs)} | AADT range: {min(aadts)}-{max(aadts)} "
    f"| unique values: {len(set(aadts))}"
)

risky = sorted(
    (s for s in segs if s["n_crashes"] > 0),
    key=lambda x: -x["n_crashes"],
)[:8]
print("Top risky segments:")
for s in risky:
    print(
        f"  km {s['from_km']:6.1f}-{s['to_km']:6.1f}  "
        f"AADT {s['aadt']:>6}  "
        f"crashes {s['n_crashes']:>3}  "
        f"intensity {s['intensity_ratio']:>4.2f}x  "
        f"band {s['risk_band']}"
    )

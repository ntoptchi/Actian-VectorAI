"""Stream the synthetic sensor sample through the pipeline.

Prints one human-readable AnomalyReport per detected event, plus a final JSON
dump of the first report so you can see the exact shape the dashboard /
HTTP layer will consume.

Usage::

    python scripts/run_demo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import get_settings
from backend.db.client import get_client
from backend.pipeline.orchestrator import stream_window
from backend.schemas import AnomalyReport
from backend.seed.sample_sensors import generate_sample_stream


def _print_report(report: AnomalyReport) -> None:
    a = report.anomaly
    bar = "-" * 70
    print(bar)
    print(f"[{a.severity}] {a.ts.isoformat()}  asset={a.asset_id}")
    print(f"  summary: {a.summary}")

    print("  top deviations:")
    worst = sorted(a.deviations, key=lambda d: abs(d.z_score), reverse=True)[:3]
    for d in worst:
        print(
            f"    - {d.sensor:<20} value={d.value:>8.2f}  "
            f"expected={d.expected_mean:>7.2f} +/- {d.expected_std:>5.2f}  "
            f"z={d.z_score:+.2f}"
        )

    print("  closest past incidents:")
    if not report.matches:
        print("    (none)")
    for m in report.matches:
        print(
            f"    - {m.incident.incident_id} {m.incident.incident_name} "
            f"(score={m.score:.3f}, text={m.text_similarity:.3f}, "
            f"num={m.numeric_similarity:.3f})"
        )

    print("  recommended guidance:")
    if not report.guidance:
        print("    (none)")
    for g in report.guidance:
        print(
            f"    - {g.manual.manual_name} (score={g.score:.4f})"
        )
        print(
            f"        chunk {g.best_chunk.chunk_id}: "
            f"{g.best_chunk.text[:120]}{'...' if len(g.best_chunk.text) > 120 else ''}"
        )


def main() -> None:
    cfg = get_settings()
    print(f"Connecting to VectorAI DB at {cfg.vectorai_host} ...")

    stream = generate_sample_stream()
    print(f"Generated {len(stream)} sample sensor readings.")

    reports: list[AnomalyReport] = []
    with get_client() as client:
        for report in stream_window(
            client,
            stream,
            window_size=30,
            persist_readings=True,
        ):
            _print_report(report)
            reports.append(report)

    print("-" * 70)
    print(f"Total anomalies detected: {len(reports)}")

    if reports:
        print("\nFirst report as JSON (for dashboard / HTTP layer):")
        print(reports[0].model_dump_json(indent=2))


if __name__ == "__main__":
    main()

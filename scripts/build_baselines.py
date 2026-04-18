"""Compute per-road-class crash-rate baselines.

Used by hotspot ranking to express intensity as a *ratio* against a
sensible reference (ROUTEWISE.md s3.4 + s5.2.8).

Day-3 work; this scaffold writes a placeholder JSON that downstream
ranking can read so the pipeline doesn't break before real numbers exist.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import get_settings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("build_baselines")


PLACEHOLDER_BASELINES = {
    # crashes per million vehicle-passes, *all conditions*, FL averages.
    # TODO(day 3): replace with values computed by scrolling the VDB
    # collection grouped by road_type with AADT denominators.
    "interstate": 0.20,
    "us_highway": 0.30,
    "state_route": 0.35,
    "arterial": 0.50,
    "ramp": 0.40,
    "local": 0.45,
    "unknown": 0.30,
}


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    default_out = settings.processed_dir / "baselines.json"

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=default_out)
    args = p.parse_args(argv)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(PLACEHOLDER_BASELINES, indent=2))
    logger.info("wrote placeholder baselines to %s", args.out)
    logger.warning(
        "These are placeholder values. Day-3 task: re-run after real "
        "ingestion to compute baselines from the indexed corpus."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

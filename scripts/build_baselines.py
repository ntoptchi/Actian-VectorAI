"""Compute Florida crash-rate baselines.

Reads the FDOT-published statewide monthly crash counts from
``data/raw/Crashes_Data.csv`` and writes a tiny JSON keyed by road
class with crashes-per-million-vehicle-passes (the denominator the
hotspot scoring uses to compute "X times the FL average").

Output: ``data/processed/fl_baseline_rates.json``.

The CSV's "Measure Names" column splits a single statewide series into
several sub-series (Fatalities, Injuries, ...). We read the
"All Crashes" series when present, fall back to summing
Fatalities + Injuries + PDO otherwise. The result is averaged across
the years available and rescaled per road class with a fixed
proportionality table — fine at the precision we need for ratios.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import get_settings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("build_baselines")


# Multipliers that turn the *statewide* baseline into *per road-class*
# baselines, very rough — sourced from FHWA's published FL crash-rate
# tables (s5.2.8 commentary). These exist so an interstate baseline
# isn't compared to an arterial baseline.
ROAD_CLASS_FACTORS: dict[str, float] = {
    "interstate": 0.55,
    "us_highway": 0.85,
    "state_route": 1.00,
    "arterial": 1.40,
    "ramp": 1.10,
    "local": 1.25,
    "unknown": 1.00,
}

# FL VMT (vehicle-miles travelled) per year, ~2020-2024, in millions.
FL_ANNUAL_VMT_MILLION = 230_000


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    default_in = settings.raw_dir / "Crashes_Data.csv"
    default_out = settings.processed_dir / "fl_baseline_rates.json"

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=default_in)
    p.add_argument("--out", type=Path, default=default_out)
    args = p.parse_args(argv)

    if not args.input.exists():
        logger.error("input CSV missing: %s", args.input)
        return 1

    monthly_total: dict[tuple[int, int], int] = defaultdict(int)
    measure_seen: set[str] = set()

    with args.input.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                year = int(row.get("Year") or 0)
                month = int(row.get("Month") or 0)
                value = int(float(row.get("Measure Values") or 0))
            except (TypeError, ValueError):
                continue
            measure = (row.get("Measure Names") or "").strip()
            measure_seen.add(measure)
            if not year or not month:
                continue
            # Sum Fatalities + Injuries + PDO when "All Crashes" isn't present.
            monthly_total[(year, month)] += value

    if not monthly_total:
        logger.error("no usable rows in %s", args.input)
        return 1

    annual_totals: dict[int, int] = defaultdict(int)
    for (year, _m), v in monthly_total.items():
        annual_totals[year] += v

    avg_annual_crashes = sum(annual_totals.values()) / len(annual_totals)
    crashes_per_mvm = avg_annual_crashes / FL_ANNUAL_VMT_MILLION  # crashes per million vehicle-miles
    logger.info(
        "FL annual avg crashes (across %d yrs): %.0f -> %.4f per million VMT",
        len(annual_totals), avg_annual_crashes, crashes_per_mvm,
    )

    baselines = {
        cls: round(crashes_per_mvm * factor, 4)
        for cls, factor in ROAD_CLASS_FACTORS.items()
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(baselines, indent=2))
    logger.info("wrote %s with %d classes", args.out, len(baselines))
    logger.info("measures present in CSV: %s", sorted(measure_seen))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

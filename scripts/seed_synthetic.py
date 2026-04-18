"""Seed VDB with ~500 synthetic FL crashes covering the three demo trips.

Lets us prove the brief endpoint round-trips through VectorAI DB before
real data lands. Crashes cluster around realistic interstate corridors
(I-75 Miami<->Tampa, I-10 Jax<->Pensacola, I-4 Orlando<->Tampa) so the
hotspot retrieval has something to find once Day-3 cluster logic lands.

Usage::

    python scripts/seed_synthetic.py --n 500
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.ingest.upsert import upsert_docs  # noqa: E402
from backend.schemas import SituationDoc  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("seed_synthetic")


# Anchor points along the three demo corridors (lat, lon, road_name).
CORRIDORS: list[tuple[str, list[tuple[float, float]]]] = [
    (
        "I-75",
        [
            (25.86, -80.30), (26.12, -80.40), (26.42, -80.85),
            (26.30, -81.40), (26.45, -81.65), (26.61, -81.82),
            (26.95, -81.95), (27.30, -82.15), (27.55, -82.30),
            (27.80, -82.45), (27.95, -82.46),
        ],
    ),
    (
        "I-10",
        [
            (30.33, -81.66), (30.30, -82.10), (30.42, -82.95),
            (30.45, -83.50), (30.46, -84.28), (30.55, -85.20),
            (30.65, -86.10), (30.50, -86.85), (30.42, -87.20),
        ],
    ),
    (
        "I-4",
        [
            (28.54, -81.38), (28.40, -81.50), (28.20, -81.85),
            (28.05, -82.05), (27.97, -82.30), (27.95, -82.46),
        ],
    ),
]

WEATHERS = ["clear", "rain", "fog", "clear", "clear"]  # weighted clear-heavy
LIGHTING = ["daylight", "dawn_dusk", "dark_lighted", "dark_unlighted"]
SURFACES_FOR = {"clear": "dry", "rain": "wet", "fog": "wet"}
CRASH_TYPES = ["rear_end", "single_vehicle", "angle", "sideswipe_same"]
SEVERITIES = ["minor", "minor", "serious", "fatal", "pdo"]


def _gen(n: int, seed: int) -> list[SituationDoc]:
    rng = random.Random(seed)
    docs: list[SituationDoc] = []
    base = datetime(2022, 1, 1, tzinfo=timezone.utc)

    for i in range(n):
        road, anchors = rng.choice(CORRIDORS)
        anchor_lat, anchor_lon = rng.choice(anchors)
        # tight jitter — keeps clusters geographically meaningful for DBSCAN
        lat = anchor_lat + rng.gauss(0, 0.005)
        lon = anchor_lon + rng.gauss(0, 0.005)

        weather = rng.choice(WEATHERS)
        lighting = rng.choice(LIGHTING)
        surface = SURFACES_FOR[weather]
        crash_type = rng.choice(CRASH_TYPES)
        severity = rng.choice(SEVERITIES)

        when = base + timedelta(
            days=rng.randint(0, 365 * 4),
            hours=rng.randint(0, 23),
            minutes=rng.randint(0, 59),
        )

        doc = SituationDoc(
            source="FDOT",
            case_id=f"SYN-{i:06d}",
            state="FL",
            county="synthetic",
            lat=lat,
            lon=lon,
            h3_cell=_h3(lat, lon),
            road_type="interstate",
            road_function=road,
            speed_limit_mph=70,
            aadt=rng.choice([45_000, 60_000, 82_000, 110_000, 195_000]),
            aadt_segment_id=f"SYN-SEG-{anchor_lat:.2f}-{anchor_lon:.2f}",
            timestamp=when,
            hour_bucket=when.hour,
            day_of_week=when.weekday(),
            month=when.month,
            weather=weather,
            precipitation_mm_hr=(
                rng.uniform(0.5, 8.0) if weather == "rain" else 0.0
            ),
            visibility_m=200.0 if weather == "fog" else 10_000.0,
            lighting=lighting,
            surface=surface,
            crash_type=crash_type,
            num_vehicles=rng.choice([1, 2, 2, 2, 3]),
            num_injuries=rng.choice([0, 0, 1, 1, 2]),
            num_fatalities=1 if severity == "fatal" else 0,
            severity=severity,
            has_narrative=False,
            narrative="",
        )
        docs.append(doc)
    return docs


def _h3(lat: float, lon: float) -> str:
    try:
        import h3

        return h3.latlng_to_cell(lat, lon, 9)
    except ImportError:
        return ""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n", type=int, default=500, help="Number of synthetic crashes")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--batch-size", type=int, default=128)
    args = p.parse_args(argv)

    docs = _gen(args.n, args.seed)
    n = upsert_docs(iter(docs), batch_size=args.batch_size)
    logger.info("seeded %d synthetic FL crashes into VDB", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

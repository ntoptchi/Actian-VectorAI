"""Persist FDOT's CAR35 "high night-time crash share" segments.

The CSV ``CAR35PctNightTime_*.csv`` lists Florida State Highway System
segments where >=35% of crashes happened at night (lighting != daylight
and != unknown). We persist a slim copy keyed by
``(ROUTEID, BMP, EMP)`` so the segments service can tag any segment
that overlaps one of these as ``night_skewed=True``.

Output: ``data/processed/night_segments.parquet`` (or .csv fallback).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import get_settings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("load_night_segments")


def _find(raw: Path) -> Path | None:
    files = sorted(raw.glob("CAR35PctNightTime_*.csv"))
    return files[0] if files else None


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    raw = settings.raw_dir
    default_in = _find(raw)
    default_out = settings.processed_dir / "night_segments.parquet"

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=default_in)
    p.add_argument("--out", type=Path, default=default_out)
    args = p.parse_args(argv)

    if args.input is None or not args.input.exists():
        logger.error("CAR35 CSV missing under %s", raw)
        return 1

    try:
        import pandas as pd  # type: ignore[import-not-found]
    except ImportError:
        logger.error("pandas required. `pip install pandas pyarrow`.")
        return 1

    df = pd.read_csv(args.input)
    keep = [c for c in (
        "ID", "ROUTEID", "BMP", "EMP", "LENGTH", "DISTRICT", "URBAN",
        "TOTCRSH_NU", "TOTCRSH_AL",
    ) if c in df.columns]
    df = df[keep].copy()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(args.out, index=False)
    except Exception as exc:  # noqa: BLE001
        csv_out = args.out.with_suffix(".csv")
        logger.warning("parquet write failed (%s); writing %s instead", exc, csv_out)
        df.to_csv(csv_out, index=False)
        args.out = csv_out

    logger.info("wrote %d night-skewed segments -> %s", len(df), args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

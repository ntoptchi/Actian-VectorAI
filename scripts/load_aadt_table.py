"""Join FDOT AADT + Speed-Limit + LRS-Routes CSVs into one parquet.

These three CSVs share the (ROADWAY, milepost) key, so combining them
gives a per-segment table with AADT *and* speed limit *and* mileposts.
The runtime API uses this for fast non-spatial AADT lookups (e.g.
attaching AADT to a FARS row that knows its ROADWAYID but doesn't have
geometry handy) and as a fallback when the AADT shapefile spatial join
returns nothing.

Outputs:
  - data/processed/fdot_segments.parquet  (per-segment table)
  - data/processed/aadt_by_road_class_county.parquet  (rollup for FARS-no-snap fallback)

Falls back to CSV outputs if pyarrow / pandas's parquet engine isn't
installed (the runtime can read either).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import get_settings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("load_aadt_table")


def _find(raw: Path, prefix: str) -> Path | None:
    files = sorted(raw.glob(f"{prefix}*.csv"))
    return files[0] if files else None


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    raw = settings.raw_dir
    out_dir = settings.processed_dir

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=out_dir / "fdot_segments.parquet")
    p.add_argument(
        "--rollup-out",
        type=Path,
        default=out_dir / "aadt_by_road_class_county.parquet",
    )
    args = p.parse_args(argv)

    try:
        import pandas as pd  # type: ignore[import-not-found]
    except ImportError:
        logger.error(
            "pandas required for load_aadt_table. `pip install pandas pyarrow`."
        )
        return 1

    aadt_csv = _find(raw, "Annual_Average_Daily_Traffic_TDA_")
    speed_csv = _find(raw, "Maximum_Speed_Limit_TDA_")
    lrs_csv = _find(raw, "LRS_Routes_with_Measures_TDA_")

    if not aadt_csv or not speed_csv or not lrs_csv:
        logger.error(
            "missing one of the FDOT CSVs: aadt=%s speed=%s lrs=%s",
            aadt_csv, speed_csv, lrs_csv,
        )
        return 1

    logger.info("reading AADT CSV: %s", aadt_csv.name)
    aadt = pd.read_csv(aadt_csv)
    logger.info("reading Speed CSV: %s", speed_csv.name)
    speed = pd.read_csv(speed_csv)
    logger.info("reading LRS CSV: %s", lrs_csv.name)
    lrs = pd.read_csv(lrs_csv)

    # Normalise key column names: each table uses ROADWAY + BEGIN_POST/END_POST.
    aadt_keep = {
        "ROADWAY", "COUNTY", "DISTRICT", "BEGIN_POST", "END_POST",
        "AADT", "DESC_FRM", "DESC_TO", "YEAR_",
    }
    aadt = aadt[[c for c in aadt.columns if c in aadt_keep]].copy()
    speed_keep = {"ROADWAY", "BEGIN_POST", "END_POST", "SPEED", "COUNTY"}
    speed = speed[[c for c in speed.columns if c in speed_keep]].copy()
    speed = speed.rename(columns={"SPEED": "SPEED_LIMIT"})

    # AADT is one row per (ROADWAY, BEGIN_POST..END_POST) — same key as speed.
    # We do a "best-effort" milepost-overlap join via merge_asof on BEGIN_POST.
    #
    # pandas 2.x is strict: the asof "on" column must be globally sorted AND
    # contain no NaN, even when paired with `by=`. The FDOT CSVs ship a
    # handful of rows with empty BEGIN_POST — drop those, coerce to numeric,
    # then sort. (Without this we hit "left keys must be sorted".)
    for df_ in (aadt, speed):
        df_["BEGIN_POST"] = pd.to_numeric(df_["BEGIN_POST"], errors="coerce")
        # ROADWAY arrives as int in one CSV and str in another (FDOT
        # exports both shapes); cast to a common string key or merge_asof
        # bails with "trying to merge on int64 and str columns".
        df_["ROADWAY"] = df_["ROADWAY"].astype("string")
    aadt = aadt.dropna(subset=["ROADWAY", "BEGIN_POST"]).sort_values("BEGIN_POST")
    speed = speed.dropna(subset=["ROADWAY", "BEGIN_POST"]).sort_values("BEGIN_POST")

    merged = pd.merge_asof(
        aadt, speed[["ROADWAY", "BEGIN_POST", "SPEED_LIMIT"]],
        on="BEGIN_POST", by="ROADWAY", direction="nearest",
        tolerance=0.5,
    )

    # Optionally enrich with LRS roadway descriptors (mostly section IDs).
    lrs_keep = {"ROADWAY", "COUNTY", "COUNTYNM"}
    lrs_small = lrs[[c for c in lrs.columns if c in lrs_keep]].drop_duplicates(
        subset=["ROADWAY"]
    )
    merged = merged.merge(lrs_small, on=["ROADWAY"], how="left", suffixes=("", "_lrs"))

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_table(merged, args.out)
    logger.info("wrote %s rows -> %s", len(merged), args.out)

    # Rollup for the FARS-no-snap fallback: median AADT by (county, district).
    rollup = (
        merged.dropna(subset=["AADT"])
        .groupby(["COUNTY", "DISTRICT"], dropna=True)["AADT"]
        .median()
        .reset_index()
        .rename(columns={"AADT": "median_aadt"})
    )
    _write_table(rollup, args.rollup_out)
    logger.info("wrote %s rows -> %s", len(rollup), args.rollup_out)
    return 0


def _write_table(df, path: Path) -> None:
    """Write parquet if available, else CSV alongside."""
    try:
        df.to_parquet(path, index=False)
    except Exception as exc:  # noqa: BLE001
        csv_path = path.with_suffix(".csv")
        logger.warning("parquet write failed (%s); writing %s instead", exc, csv_path)
        df.to_csv(csv_path, index=False)


if __name__ == "__main__":
    raise SystemExit(main())

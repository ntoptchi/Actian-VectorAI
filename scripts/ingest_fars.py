"""Ingest FARS fatal-crash records (FL subset, 2018-2022) into VDB.

Usage::

    python scripts/ingest_fars.py --year 2022
    python scripts/ingest_fars.py --years 2018,2019,2020,2021,2022 --limit 5000

Reads from ``data/raw/FARS/<year>/accident.CSV`` (case-insensitive on
``.csv`` extension). Filters to STATE==12 (Florida) before normalizing.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from collections.abc import Iterator
from pathlib import Path

# Make ``backend`` importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import get_settings  # noqa: E402
from backend.ingest.normalize import from_fars_row  # noqa: E402
from backend.ingest.upsert import upsert_docs  # noqa: E402
from backend.schemas import SituationDoc  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("ingest_fars")


def _candidate_year_dirs(raw_root: Path, year: int) -> list[Path]:
    """Find a per-year FARS directory across the layouts the user has used.

    We accept any of:
      - data/raw/FARS/<year>/                (canonical)
      - data/raw/FARS<year>NationalCSV/      (NHTSA's zip filename)
      - data/raw/FARS_<year>/                (alt)
    """
    candidates = [
        raw_root / "FARS" / str(year),
        raw_root / f"FARS{year}NationalCSV",
        raw_root / f"FARS_{year}",
        raw_root / f"FARS{year}",
    ]
    return [c for c in candidates if c.exists()]


def _iter_rows(year_dir: Path) -> Iterator[dict]:
    accident_csv = next(
        (p for p in year_dir.glob("*.[Cc][Ss][Vv]") if p.stem.lower() == "accident"),
        None,
    )
    if accident_csv is None:
        logger.warning("no accident.csv found in %s", year_dir)
        return
    with accident_csv.open(newline="", encoding="latin-1") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row.get("STATE") or row.get("State") or "") not in {"12", "FL"}:
                continue
            yield row


def _docs(years: list[int], limit: int | None) -> Iterator[SituationDoc]:
    raw_root = get_settings().raw_dir
    n = 0
    for year in years:
        year_dirs = _candidate_year_dirs(raw_root, year)
        if not year_dirs:
            logger.warning(
                "no FARS dir for %d under %s (tried FARS/<year>, FARS<year>NationalCSV); skipping",
                year, raw_root,
            )
            continue
        for year_dir in year_dirs:
            for row in _iter_rows(year_dir):
                doc = from_fars_row(row)
                if doc is None:
                    continue
                yield doc
                n += 1
                if limit is not None and n >= limit:
                    return


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--year", type=int, help="Single year to ingest (e.g. 2022)")
    p.add_argument(
        "--years",
        type=str,
        help="Comma-separated list of years (overrides --year)",
        default="",
    )
    p.add_argument("--limit", type=int, default=None, help="Cap rows per run")
    p.add_argument("--batch-size", type=int, default=256)
    args = p.parse_args(argv)

    if args.years:
        years = [int(y.strip()) for y in args.years.split(",") if y.strip()]
    elif args.year:
        years = [args.year]
    else:
        years = [2021, 2022, 2023, 2024]

    n = upsert_docs(_docs(years, args.limit), batch_size=args.batch_size)
    logger.info("FARS ingest complete: %d points upserted", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

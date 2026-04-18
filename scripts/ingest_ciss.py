"""Ingest CISS investigator-narrative cases into VDB.

CISS is national, not FL-specific (ROUTEWISE.md s4 prelude). Narratives
are surfaced by similarity at query time, so we keep all states.

Reads from ``data/raw/CISS/<year>/`` containing the standard CISS export
(case header CSVs + narrative text blobs).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Iterator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import get_settings  # noqa: E402
from backend.ingest.normalize import from_ciss_case  # noqa: E402
from backend.ingest.upsert import upsert_docs  # noqa: E402
from backend.schemas import SituationDoc  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("ingest_ciss")


def _iter_cases(year_dir: Path) -> Iterator[dict]:
    """Yield one merged dict per case.

    TODO(day 1): real CISS exports interleave case header tables, scene
    tables, and narrative documents. Join them by ``CASEID`` here.
    For now we accept a pre-flattened JSONL at ``cases.jsonl`` so the
    ingestion loop is exercisable end-to-end against synthetic data.
    """
    flat = year_dir / "cases.jsonl"
    if not flat.exists():
        logger.warning("no cases.jsonl found in %s", year_dir)
        return
    with flat.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def _docs(years: list[int], limit: int | None) -> Iterator[SituationDoc]:
    raw_root = get_settings().raw_dir / "CISS"
    n = 0
    for year in years:
        year_dir = raw_root / str(year)
        if not year_dir.exists():
            logger.warning("missing CISS year dir %s; skipping", year_dir)
            continue
        for case in _iter_cases(year_dir):
            try:
                doc = from_ciss_case(case)
            except NotImplementedError:
                logger.error(
                    "from_ciss_case is still a stub. Implement it before "
                    "running ingest_ciss."
                )
                return
            if doc is None:
                continue
            yield doc
            n += 1
            if limit is not None and n >= limit:
                return


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--years", type=str, default="2018,2019,2020,2021,2022")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--batch-size", type=int, default=128)
    args = p.parse_args(argv)

    years = [int(y.strip()) for y in args.years.split(",") if y.strip()]
    n = upsert_docs(_docs(years, args.limit), batch_size=args.batch_size)
    logger.info("CISS ingest complete: %d points upserted", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

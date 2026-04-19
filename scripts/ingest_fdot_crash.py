"""Ingest FDOT crash GeoJSON chunks into the VDB.

PRIMARY corpus for RouteWise. The user pre-fetched ~50K crash records
from the FDOT ArcGIS REST API in 1K-record chunks named
``data/raw/crash{1000..50000}.json``. Each feature is a full crash
record with AADT and speed limit *already attached*, so we don't need
the AADT shapefile snap step for these.

Usage::

    python scripts/ingest_fdot_crash.py
    python scripts/ingest_fdot_crash.py --limit 5000
    python scripts/ingest_fdot_crash.py --pattern 'crash*.json'
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
from backend.ingest.normalize import from_fdot_crash_row  # noqa: E402
from backend.ingest.upsert import upsert_docs  # noqa: E402
from backend.schemas import SituationDoc  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("ingest_fdot")


def _iter_features(crash_dir: Path, pattern: str) -> Iterator[dict]:
    """Yield one row dict per FDOT crash feature.

    Reads the ``crash*.json`` chunks directly (they are GeoJSON
    FeatureCollections), pulling lat/lon out of ``feature.geometry``
    and merging it with ``feature.properties``.
    """
    files = sorted(crash_dir.glob(pattern))
    if not files:
        logger.warning("no files matching %s under %s", pattern, crash_dir)
        return

    logger.info("found %d crash chunk(s) to ingest", len(files))
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.warning("skipping %s (not JSON: %s)", f.name, exc)
            continue
        features = data.get("features") or []
        for feat in features:
            props = dict(feat.get("properties") or {})
            geom = feat.get("geometry") or {}
            coords = geom.get("coordinates")
            if isinstance(coords, list) and len(coords) >= 2:
                try:
                    props["__lon"] = float(coords[0])
                    props["__lat"] = float(coords[1])
                except (TypeError, ValueError):
                    pass
            yield props


def _docs(pattern: str, limit: int | None) -> Iterator[SituationDoc]:
    crash_dir = get_settings().raw_dir
    n = 0
    skipped = 0
    for row in _iter_features(crash_dir, pattern):
        try:
            doc = from_fdot_crash_row(row)
        except Exception as exc:  # noqa: BLE001
            logger.debug("normalize failed: %s", exc)
            skipped += 1
            continue
        if doc is None:
            skipped += 1
            continue
        yield doc
        n += 1
        if n % 5000 == 0:
            logger.info("normalised %d docs (%d skipped so far)", n, skipped)
        if limit is not None and n >= limit:
            return
    logger.info("normalisation complete: %d kept, %d skipped", n, skipped)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--pattern",
        default="crash*.json",
        help="Glob pattern under data/raw/ (default: crash*.json)",
    )
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--batch-size", type=int, default=512)
    args = p.parse_args(argv)
    n = upsert_docs(_docs(args.pattern, args.limit), batch_size=args.batch_size)
    logger.info("FDOT ingest complete: %d points upserted", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

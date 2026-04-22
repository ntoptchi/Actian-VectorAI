"""Ingest FDOT crash GeoJSON chunks into the VDB.

PRIMARY corpus for RouteWise. The user pre-fetched ~150K crash records
from the FDOT ArcGIS REST API in 1K-record chunks named
``data/raw/crash{1000..150000}.json``. Each feature is a full crash
record with AADT and speed limit *already attached*, so we don't need
the AADT shapefile snap step for these.

Usage::

    python scripts/ingest_fdot_crash.py
    python scripts/ingest_fdot_crash.py --limit 5000           # first-N (biased to early chunks)
    python scripts/ingest_fdot_crash.py --sample 20000         # uniform Bernoulli sample
    python scripts/ingest_fdot_crash.py --pattern 'crash*.json'
"""

from __future__ import annotations

import argparse
import json
import logging
import random
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


# Rough size of the committed FDOT corpus. Used purely to pick the
# per-row keep probability when ``--sample N`` is passed. Slight drift
# (e.g. FDOT refreshes the ArcGIS export) is fine — we only need a
# close-enough denominator to hit the target count in expectation.
_ESTIMATED_TOTAL_FEATURES = 150_000


def _docs(
    pattern: str,
    limit: int | None,
    sample: int | None,
    seed: int,
) -> Iterator[SituationDoc]:
    """Stream normalised docs from the FDOT chunks.

    ``--limit`` truncates deterministically at the first N *post-
    normalisation* rows (biased toward early crash IDs / early
    chunks). ``--sample`` does single-pass Bernoulli sampling over
    every raw feature so the resulting corpus is uniform in time
    and geography — important because hotspot retrieval is density-
    based and a chunk-prefix bias would over-represent whichever
    date range sorts first.
    """
    crash_dir = get_settings().raw_dir
    rng = random.Random(seed) if sample is not None else None
    # Expected N rows ≈ keep_rate * total_features. We don't know the
    # exact survival rate of normalisation (mostly missing CRASH_TIME
    # ≈ 6% drop), so we target ~1.1x the ask to compensate and then
    # rely on ``limit`` to cap the tail.
    keep_rate = (
        min(1.0, 1.1 * sample / _ESTIMATED_TOTAL_FEATURES)
        if sample is not None
        else 1.0
    )
    effective_limit = sample if (limit is None and sample is not None) else limit

    n = 0
    skipped = 0
    sampled_out = 0
    for row in _iter_features(crash_dir, pattern):
        if rng is not None and rng.random() >= keep_rate:
            sampled_out += 1
            continue
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
            logger.info(
                "normalised %d docs (%d skipped, %d dropped by sample)",
                n, skipped, sampled_out,
            )
        if effective_limit is not None and n >= effective_limit:
            return
    logger.info(
        "normalisation complete: %d kept, %d skipped, %d dropped by sample",
        n, skipped, sampled_out,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--pattern",
        default="crash*.json",
        help="Glob pattern under data/raw/ (default: crash*.json)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Hard cap on kept rows (first-N order, biased to early chunks).",
    )
    p.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Target a uniform Bernoulli sample of ~N rows across the "
             "whole corpus (preferred over --limit when you want a fast "
             "install without skewing geography).",
    )
    p.add_argument("--seed", type=int, default=42, help="Sampling seed.")
    p.add_argument(
        "--batch-size",
        type=int,
        default=256,
        help="Docs per upsert call. 256 is a good balance — bigger batches "
             "(512+) occasionally exceed the server's gRPC deadline under "
             "sustained write pressure once the collection passes ~10K "
             "points; smaller batches wall-clock more total gRPC overhead.",
    )
    args = p.parse_args(argv)
    n = upsert_docs(
        _docs(args.pattern, args.limit, args.sample, args.seed),
        batch_size=args.batch_size,
    )
    logger.info("FDOT ingest complete: %d points upserted", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

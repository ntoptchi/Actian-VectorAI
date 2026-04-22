"""Ingest scraped news articles into the VDB.

Reads the scraper JSON format (semanticCrashes array with paired
article + FDOT crash features) and upserts each article as a
``source="NEWS"`` SituationDoc. Conditions are inherited from the
linked crash record, not parsed from article text.

Usage::

    python scripts/ingest_news.py
    python scripts/ingest_news.py --file data/raw/news_mock.json
    python scripts/ingest_news.py --pattern 'news*.json'
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
from backend.ingest.normalize import from_news_article  # noqa: E402
from backend.ingest.upsert import upsert_docs  # noqa: E402
from backend.schemas import SituationDoc  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("ingest_news")


def _iter_entries(raw_dir: Path, pattern: str, file: str | None) -> Iterator[dict]:
    """Yield one scraper entry per news article."""
    if file:
        files = [Path(file)]
    else:
        files = []
        for pat in pattern.split(","):
            files.extend(raw_dir.glob(pat.strip()))
        files = sorted(set(files))

    if not files:
        logger.warning("no files matching %s under %s", pattern, raw_dir)
        return

    logger.info("found %d news file(s) to ingest", len(files))
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.warning("skipping %s (not JSON: %s)", f.name, exc)
            continue
        entries = data.get("semanticCrashes") or []
        logger.info("%s: %d entries", f.name, len(entries))
        yield from entries


def _docs(pattern: str, file: str | None, limit: int | None) -> Iterator[SituationDoc]:
    raw_dir = get_settings().raw_dir
    n = 0
    skipped = 0
    for entry in _iter_entries(raw_dir, pattern, file):
        try:
            doc = from_news_article(entry)
        except Exception as exc:  # noqa: BLE001
            logger.debug("normalize failed: %s", exc)
            skipped += 1
            continue
        if doc is None:
            skipped += 1
            continue
        logger.info(
            "  [%s] %s (score=%s, linked=%s)",
            doc.publisher,
            doc.headline[:60],
            entry.get("matchScore"),
            doc.linked_crash_ids,
        )
        yield doc
        n += 1
        if limit is not None and n >= limit:
            return
    logger.info("normalisation complete: %d kept, %d skipped", n, skipped)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--pattern",
        default="*news*.json,semantic_crashes*.json",
        help="Comma-separated glob patterns under data/raw/ (default: *news*.json,semantic_crashes*.json)",
    )
    p.add_argument("--file", default=None, help="Specific file path to ingest")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--batch-size", type=int, default=64)
    args = p.parse_args(argv)
    n = upsert_docs(_docs(args.pattern, args.file, args.limit), batch_size=args.batch_size)
    logger.info("news ingest complete: %d points upserted", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

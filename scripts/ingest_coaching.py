"""Ingest LLM-enriched crash lessons into the ``routewise_coaching`` VDB.

Reads ``data/raw/enriched_semantic_crashes.json`` (produced by the
offline enrichment pipeline — see ``data/raw`` for format) and upserts
one multi-vector point per enriched entry.

Each point carries:

  - three dense 384-d vectors: ``lesson`` (lesson_advice), ``incident``
    (retelling), ``factors_text`` (space-joined risk factor tags);
  - one sparse ``factors`` vector over the frozen factor vocabulary
    (skipped if the server doesn't support sparse);
  - payload: lesson text, retelling, normalised factor tags, crash
    coordinates, h3 cell, county, severity, and the citation-level
    article metadata (publisher, URL, date, headline).

Usage::

    python scripts/ingest_coaching.py
    python scripts/ingest_coaching.py --limit 25
    python scripts/ingest_coaching.py --file data/raw/enriched_semantic_crashes.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import uuid
from collections.abc import Iterable, Iterator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.coaching_vdb import (  # noqa: E402
    VEC_FACTORS_TEXT,
    VEC_INCIDENT,
    VEC_LESSON,
    VEC_SPARSE,
    coaching_collection_name,
    ensure_coaching_collection,
)
from backend.config import get_settings  # noqa: E402
from backend.embeddings import embed  # noqa: E402
from backend.ingest.factor_vocab import (  # noqa: E402
    driver_action_to_rich_tags,
    encode_tags,
)
from backend.ingest.upsert import _upsert_with_retry  # noqa: E402
from backend.vdb import get_client  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("ingest_coaching")

# Stable uuid5 namespace for coaching point IDs. Distinct from the crash
# corpus namespace so a news article can sit in both collections without
# ID collisions.
NAMESPACE = uuid.UUID("aa31f4f0-1f2a-4b38-8e21-e01a1ac00001")

BATCH_SIZE = 64


def _insight_id(crash_id: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"coaching:{crash_id}"))


def _h3_cell(lat: float, lon: float) -> str | None:
    """Best-effort H3 cell (res 8). Returns None if h3 isn't available."""
    try:
        import h3

        return h3.latlng_to_cell(lat, lon, 8)
    except Exception:  # noqa: BLE001
        return None


def _normalise_factor_tags(tags: Iterable[str]) -> list[str]:
    """Deduped lowercase tags, in original order. Skips empties."""
    seen: set[str] = set()
    out: list[str] = []
    for t in tags:
        if not t:
            continue
        key = t.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _extract_entries(raw_json: dict) -> list[dict]:
    entries = raw_json.get("semanticCrashes") or []
    kept: list[dict] = []
    for e in entries:
        enrichment = e.get("enrichment") or {}
        if not enrichment.get("lesson_advice"):
            continue
        if not enrichment.get("retelling"):
            continue
        coords = (e.get("crashGeometry") or {}).get("coordinates") or []
        if len(coords) < 2:
            crash = e.get("crash") or {}
            lat = crash.get("LATITUDE")
            lon = crash.get("LONGITUDE")
            if lat is None or lon is None:
                continue
            coords = [lon, lat]
        kept.append({"entry": e, "coords": coords})
    return kept


def _build_payload(entry: dict, coords: list[float]) -> dict:
    enrichment = entry["enrichment"]
    article = entry.get("article") or {}
    crash = entry.get("crash") or {}
    lon, lat = coords[0], coords[1]

    tags = _normalise_factor_tags(enrichment.get("factor_tags") or [])
    # Fold driver_action into the tag bag so the sparse index picks up
    # that signal even when it wasn't explicitly tagged.
    tags += [
        t
        for t in driver_action_to_rich_tags(enrichment.get("primary_driver_action"))
        if t not in tags
    ]

    road_name = (
        crash.get("US_ROAD_NUMBER")
        or crash.get("STATE_ROAD_NUMBER")
        or crash.get("ON_ROADWAY_NAME")
        or ""
    )

    return {
        "crash_id": entry.get("crash_id"),
        "lat": lat,
        "lon": lon,
        "h3_cell": _h3_cell(lat, lon),
        "county": crash.get("COUNTY_TXT"),
        "road_name": road_name,
        "crash_date": entry.get("crashDate"),
        "crash_tier": entry.get("crashTier"),
        "lesson_advice": enrichment.get("lesson_advice", ""),
        "lesson_cause": enrichment.get("lesson_cause", ""),
        "retelling": enrichment.get("retelling", ""),
        "context_conditions": enrichment.get("context_conditions", ""),
        "context_road": enrichment.get("context_road", ""),
        "factor_tags": tags,
        "primary_driver_action": enrichment.get("primary_driver_action"),
        "preventability": enrichment.get("preventability"),
        "driver_demographic": enrichment.get("driver_demographic"),
        "outcome_severity": enrichment.get("outcome_severity"),
        # Citation-level metadata — surfaced only in the insight modal footer.
        "publisher": article.get("source") or "",
        "article_url": article.get("link") or "",
        "publish_date": article.get("publishedDate"),
        "article_headline": article.get("title") or "",
    }


def _chunks(items: list, size: int) -> Iterator[list]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _build_points(
    items: list[dict],
    *,
    sparse_enabled: bool,
):  # type: ignore[no-untyped-def]
    """Materialise PointStruct objects for one batch."""
    from actian_vectorai import PointStruct

    if sparse_enabled:
        from actian_vectorai import SparseVector

    lesson_texts = [it["payload"]["lesson_advice"] for it in items]
    incident_texts = [it["payload"]["retelling"] for it in items]
    factor_texts = [
        " ".join(it["payload"]["factor_tags"]) or it["payload"]["lesson_cause"]
        for it in items
    ]

    lesson_vecs = embed(lesson_texts)
    incident_vecs = embed(incident_texts)
    factor_vecs = embed(factor_texts)

    points: list = []
    for i, it in enumerate(items):
        vec: dict = {
            VEC_LESSON: lesson_vecs[i].tolist(),
            VEC_INCIDENT: incident_vecs[i].tolist(),
            VEC_FACTORS_TEXT: factor_vecs[i].tolist(),
        }
        if sparse_enabled:
            indices, values = encode_tags(it["payload"]["factor_tags"])
            if indices:
                vec[VEC_SPARSE] = SparseVector(indices=indices, values=values)
        points.append(
            PointStruct(
                id=_insight_id(it["payload"]["crash_id"]),
                vector=vec,
                payload=it["payload"],
            )
        )
    return points


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--file",
        default=str(get_settings().raw_dir / "enriched_semantic_crashes.json"),
        help="Path to the enriched JSON (default: data/raw/enriched_semantic_crashes.json)",
    )
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    args = p.parse_args(argv)

    path = Path(args.file)
    if not path.exists():
        logger.error("enriched JSON not found: %s", path)
        return 2

    sparse_enabled = ensure_coaching_collection()
    if not sparse_enabled:
        logger.warning(
            "sparse vectors disabled for this collection — retrieval will "
            "fall back to dense-only for the keyword channel"
        )
    collection = coaching_collection_name()
    client = get_client()

    raw = json.loads(path.read_text(encoding="utf-8"))
    entries_pre = raw.get("semanticCrashes") or []
    entries = _extract_entries(raw)
    logger.info(
        "loaded %d entries from %s (kept %d with lesson+retelling+coords)",
        len(entries_pre), path, len(entries),
    )

    if args.limit:
        entries = entries[: args.limit]
        logger.info("truncated to --limit=%d", args.limit)

    items = [
        {"entry": e["entry"], "coords": e["coords"], "payload": _build_payload(e["entry"], e["coords"])}
        for e in entries
    ]

    n_total = 0
    started = time.time()
    for batch in _chunks(items, args.batch_size):
        points = _build_points(batch, sparse_enabled=sparse_enabled)
        _upsert_with_retry(client, collection, points)
        n_total += len(points)
        logger.info("upserted %d (running total %d)", len(points), n_total)

    logger.info(
        "coaching ingest complete: %d points in %.1fs (sparse=%s)",
        n_total, time.time() - started, sparse_enabled,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""VDB-driven coaching/insight retrieval.

Powers two entry points that both return :class:`CrashInsight`:

  * :func:`retrieve_for_segment` — single best-matched lesson for a
    hotspot's segment (used to populate ``HotspotSummary.insight`` and
    to dynamically author the coaching line).
  * :func:`retrieve_for_route` — per-segment lessons across the whole
    chosen route, deduped + snapped to the nearest segment midpoint,
    used to build ``TripBriefResponse.insights`` (map pins + right-rail
    list).

Both wrap every VDB call in try/except so the endpoint degrades cleanly
when the collection is missing or the server is down.

Retrieval strategy (three-channel fusion):

  1. Dense search on the ``lesson`` vector with a prose query built from
     the segment's conditions + rich factor tags.
  2. Dense search on the ``incident`` vector with a prose query
     describing what a matching crash would look like.
  3. Sparse search on the ``factors`` vector (server-side BM25-style)
     when the collection supports it; otherwise dense search on
     ``factors_text`` as a keyword proxy.

Client-side reciprocal rank fusion combines the three rankings (pattern
from ``vectorai-db-beta/examples/15_hybrid_fusion.py``). RRF is stable
under per-channel score-scale differences and doesn't require tuning a
weight per channel.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend.coaching_vdb import (
    VEC_FACTORS_TEXT,
    VEC_INCIDENT,
    VEC_LESSON,
    VEC_SPARSE,
    coaching_collection_name,
)
from backend.embeddings import embed_one
from backend.ingest.factor_vocab import (
    coarse_to_rich_tags,
    encode_tags,
)
from backend.schemas import (
    CrashInsight,
    FactorWeight,
    InsightSource,
    LatLon,
    SituationDoc,
)
from backend.vdb import get_client

if TYPE_CHECKING:
    from backend.schemas import RouteSegment

logger = logging.getLogger(__name__)

# Retrieval knobs. Kept as module constants so smoke tests can override
# them without rebuilding the whole service.
PER_CHANNEL_LIMIT = 8
PER_SEGMENT_KEEP = 1
RRF_K = 60
MAX_INSIGHTS_PER_ROUTE = 8
MIN_SIMILARITY = 0.15  # below this, the retrieval is noise — discard


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def retrieve_for_segment(
    segment: "RouteSegment",
    query_doc: SituationDoc,
) -> CrashInsight | None:
    """Best-matched insight for a single segment. ``None`` on failure."""
    try:
        return _retrieve_for_segment_inner(segment, query_doc, dedupe=None)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "coaching retrieval failed for segment %s: %s",
            getattr(segment, "segment_id", "?"), exc,
        )
        return None


def retrieve_for_route(
    segments: list["RouteSegment"],
    query_doc: SituationDoc,
) -> list[CrashInsight]:
    """Per-segment insights for the whole route, deduped across segments.

    Segments are scanned in order so the first segment that retrieves
    a given insight "wins" that insight's pin placement. Later
    segments that would have pulled the same lesson skip it silently.
    """
    try:
        return _retrieve_for_route_inner(segments, query_doc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("coaching route retrieval failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _retrieve_for_route_inner(
    segments: list["RouteSegment"],
    query_doc: SituationDoc,
) -> list[CrashInsight]:
    if not segments:
        return []

    client, collection, has_sparse = _get_client_and_caps()
    if client is None:
        return []

    insights: list[CrashInsight] = []
    seen: set[str] = set()

    # Walk risky segments first so pin placement favours where the
    # lesson most applies, not where the route happens to start.
    ranked = sorted(
        segments,
        key=lambda s: (
            s.intensity_ratio if s.intensity_ratio is not None else 0.0,
            s.n_crashes,
        ),
        reverse=True,
    )

    for seg in ranked:
        if len(insights) >= MAX_INSIGHTS_PER_ROUTE:
            break
        insight = _retrieve_for_segment_inner(
            seg, query_doc, dedupe=seen,
            client=client, collection=collection, has_sparse=has_sparse,
        )
        if insight is None:
            continue
        insights.append(insight)
        seen.add(insight.insight_id)

    return insights


def _retrieve_for_segment_inner(
    segment: "RouteSegment",
    query_doc: SituationDoc,
    *,
    dedupe: set[str] | None,
    client=None,   # type: ignore[no-untyped-def]
    collection: str | None = None,
    has_sparse: bool | None = None,
) -> CrashInsight | None:
    if client is None or collection is None or has_sparse is None:
        client, collection, has_sparse = _get_client_and_caps()
        if client is None:
            return None

    lesson_query, incident_query, tag_query_text, tag_list = _build_queries(
        segment, query_doc
    )

    # --- Three-channel search ------------------------------------------------
    try:
        results_lesson = client.points.search(
            collection,
            vector=embed_one(lesson_query),
            using=VEC_LESSON,
            limit=PER_CHANNEL_LIMIT,
            with_payload=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("lesson search failed: %s", exc)
        results_lesson = []

    try:
        results_incident = client.points.search(
            collection,
            vector=embed_one(incident_query),
            using=VEC_INCIDENT,
            limit=PER_CHANNEL_LIMIT,
            with_payload=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("incident search failed: %s", exc)
        results_incident = []

    results_factors = _search_factors(
        client, collection, tag_list, tag_query_text, has_sparse
    )

    ranked = _fuse([results_lesson, results_incident, results_factors])
    if not ranked:
        return None

    best = _pick_best(ranked, dedupe=dedupe)
    if best is None:
        return None

    payload = _payload_of(best) or {}
    similarity = _score_of(best) or 0.0
    if similarity < MIN_SIMILARITY and _fused_score_of(best) < 0.02:
        # Nothing in the collection semantically resembles this segment.
        return None

    return _insight_from(best, payload, segment, similarity)


# ---------------------------------------------------------------------------
# Query construction
# ---------------------------------------------------------------------------


def _build_queries(
    segment: "RouteSegment",
    query_doc: SituationDoc,
) -> tuple[str, str, str, list[str]]:
    """Return (lesson_query, incident_query, factors_query_text, tag_list).

    The first two are prose strings used for dense embedding. The third
    is the space-joined rich tags (used as a dense proxy when sparse is
    unavailable). The list is the rich tags used to build the sparse
    query vector.
    """
    coarse_factors = [f.factor for f in segment.top_factors]
    rich_tags = coarse_to_rich_tags(coarse_factors)

    # Also fold in environmental state from the query doc so night/wet
    # queries match enriched crashes with matching tags even when the
    # segment's local factors don't explicitly mention them.
    env_tags: list[str] = []
    if query_doc.weather in {"rain", "snow", "sleet"}:
        env_tags.append("rain")
    if query_doc.surface == "wet":
        env_tags.append("wet")
    elif query_doc.surface in {"icy", "snowy"}:
        env_tags.append("wet")
    if query_doc.lighting == "dark_unlighted":
        env_tags.append("dark_unlighted")
    elif query_doc.lighting == "dark_lighted":
        env_tags.append("dark_lighted")
    elif query_doc.lighting == "daylight":
        env_tags.append("daylight")

    # De-dupe while preserving order.
    seen: set[str] = set()
    tags: list[str] = []
    for t in rich_tags + env_tags:
        if t not in seen:
            tags.append(t)
            seen.add(t)

    cond_phrase = _condition_phrase(query_doc)
    factor_phrase = ", ".join(coarse_factors) if coarse_factors else "mixed factors"

    lesson_query = (
        f"What should a driver do on a segment with {factor_phrase} "
        f"under {cond_phrase}? Give actionable advice."
    )
    incident_query = (
        f"A crash on a segment with {factor_phrase} under {cond_phrase}."
    )
    factors_text = " ".join(tags) if tags else factor_phrase

    return lesson_query, incident_query, factors_text, tags


def _condition_phrase(q: SituationDoc) -> str:
    parts: list[str] = []
    if q.lighting == "dark_unlighted":
        parts.append("dark unlit conditions")
    elif q.lighting == "dark_lighted":
        parts.append("night with streetlights")
    elif q.lighting == "dawn_dusk":
        parts.append("dawn or dusk")
    else:
        parts.append("daylight")
    if q.weather and q.weather != "clear" and q.weather != "unknown":
        parts.append(q.weather)
    if q.surface == "wet":
        parts.append("wet pavement")
    elif q.surface == "icy":
        parts.append("icy pavement")
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Factor channel (sparse-preferred, dense-fallback)
# ---------------------------------------------------------------------------


def _search_factors(
    client,  # type: ignore[no-untyped-def]
    collection: str,
    tags: list[str],
    tag_query_text: str,
    has_sparse: bool,
):
    """Sparse keyword search when possible, dense keyword proxy otherwise."""
    if has_sparse and tags:
        indices, values = encode_tags(tags)
        if indices:
            try:
                from actian_vectorai import SparseVector

                return client.points.search(
                    collection,
                    vector=SparseVector(indices=indices, values=values),
                    using=VEC_SPARSE,
                    limit=PER_CHANNEL_LIMIT,
                    with_payload=True,
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("sparse factors search failed, falling back to dense: %s", exc)

    try:
        return client.points.search(
            collection,
            vector=embed_one(tag_query_text),
            using=VEC_FACTORS_TEXT,
            limit=PER_CHANNEL_LIMIT,
            with_payload=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("dense factors_text search failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Fusion + ranking
# ---------------------------------------------------------------------------


def _fuse(channel_results: list) -> list:
    """Combine multiple ranked channels via reciprocal rank fusion.

    Prefers the library's RRF helper when available so the math matches
    the official example; falls back to a local RRF implementation if
    the helper import fails (shouldn't happen on supported clients but
    keeps us robust to minor version skew).
    """
    channel_results = [c for c in channel_results if c]
    if not channel_results:
        return []
    try:
        from actian_vectorai import reciprocal_rank_fusion

        return reciprocal_rank_fusion(
            channel_results,
            limit=PER_CHANNEL_LIMIT,
            ranking_constant_k=RRF_K,
        )
    except Exception:  # noqa: BLE001
        return _local_rrf(channel_results)


def _local_rrf(channel_results: list) -> list:
    """Fallback RRF so the service never dies on an import skew."""
    scores: dict = {}
    best_obj: dict = {}
    for channel in channel_results:
        for rank, r in enumerate(channel):
            pid = _id_of(r)
            if pid is None:
                continue
            scores[pid] = scores.get(pid, 0.0) + 1.0 / (RRF_K + rank + 1)
            if pid not in best_obj or (_score_of(r) or 0) > (_score_of(best_obj[pid]) or 0):
                best_obj[pid] = r
    items = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    fused: list = []
    for pid, fused_score in items[:PER_CHANNEL_LIMIT]:
        obj = best_obj[pid]
        # Attach the fused score so downstream code sees consistent field.
        try:
            obj.score = float(fused_score)
        except Exception:  # noqa: BLE001
            pass
        fused.append(obj)
    return fused


def _pick_best(ranked: list, *, dedupe: set[str] | None):
    if dedupe is None:
        return ranked[0] if ranked else None
    for r in ranked:
        pid = _id_of(r)
        if pid and pid not in dedupe:
            return r
    return None


# ---------------------------------------------------------------------------
# CrashInsight assembly
# ---------------------------------------------------------------------------


def _insight_from(
    hit,  # type: ignore[no-untyped-def]
    payload: dict,
    segment: "RouteSegment",
    similarity: float,
) -> CrashInsight:
    pin = _segment_midpoint(segment, payload)
    return CrashInsight(
        insight_id=_id_of(hit) or payload.get("crash_id") or "",
        headline=_synthesize_headline(payload, segment.top_factors),
        lesson=_clean_llm_field(payload.get("lesson_advice")),
        incident_summary=_clean_llm_field(payload.get("retelling")),
        risk_factors=list(payload.get("factor_tags") or []),
        pin_location=pin,
        segment_id=segment.segment_id,
        similarity=round(float(similarity), 4),
        source=InsightSource(
            publisher=payload.get("publisher") or None,
            article_url=payload.get("article_url") or None,
            publish_date=payload.get("publish_date") or None,
            article_headline=payload.get("article_headline") or None,
        ),
    )


def _segment_midpoint(segment: "RouteSegment", payload: dict) -> LatLon:
    """Nearest-segment placement: pin sits where the lesson applies tonight.

    Falls back to the payload's original lat/lon only when the segment has
    no polyline (shouldn't happen in practice — segments always have at
    least two points — but we guard so ingestion quirks don't 500 the API).
    """
    poly = segment.polyline or []
    if poly:
        mid = poly[len(poly) // 2]
        if len(mid) >= 2:
            return LatLon(lat=mid[1], lon=mid[0])
    lat = payload.get("lat")
    lon = payload.get("lon")
    if lat is None or lon is None:
        return LatLon(lat=0.0, lon=0.0)
    return LatLon(lat=float(lat), lon=float(lon))


# Placeholders the upstream LLM occasionally emits when a field is genuinely
# missing from the article. Treat these as empty so we fall back to the tag
# synthesis path rather than displaying "NOT_STATED" as a headline.
_LLM_PLACEHOLDERS = {"", "not_stated", "not stated", "unknown", "n/a", "none"}


def _clean_llm_field(value: object) -> str:
    """Normalise an LLM-sourced string field; return ``""`` for placeholders."""
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if text.lower() in _LLM_PLACEHOLDERS:
        return ""
    return text


def _synthesize_headline(
    payload: dict, coarse_factors: list[FactorWeight]
) -> str:
    """Short phrase derived from lesson + dominant factor.

    Deliberately avoids using the news article's headline: the modal is
    a lesson artifact, not a news summary. We prefer the LLM's
    ``lesson_cause`` (which is neutral, one sentence) trimmed to a
    scannable length, with a factor suffix when helpful.
    """
    base = _clean_llm_field(payload.get("lesson_cause")) or _clean_llm_field(
        payload.get("lesson_advice")
    )
    if base:
        if len(base) > 90:
            # Trim to the first sentence fragment if too long.
            for punct in (". ", "; ", ", "):
                idx = base.find(punct, 40, 90)
                if idx != -1:
                    base = base[:idx]
                    break
            else:
                base = base[:90].rsplit(" ", 1)[0] + "…"
        return base

    tags = payload.get("factor_tags") or []
    if tags:
        return f"Crash pattern: {', '.join(tags[:3])}"
    if coarse_factors:
        return f"Crash pattern: {coarse_factors[0].factor}"
    return "Crash lesson"


# ---------------------------------------------------------------------------
# Small VDB adapters (keep result-object field access in one place so a
# library shape change only edits here).
# ---------------------------------------------------------------------------


def _get_client_and_caps() -> tuple[object | None, str, bool]:
    collection = coaching_collection_name()
    try:
        client = get_client()
    except Exception as exc:  # noqa: BLE001
        logger.debug("VDB client unavailable: %s", exc)
        return None, collection, False
    try:
        if not client.collections.exists(collection):
            logger.debug("coaching collection %s missing — returning empty", collection)
            return None, collection, False
    except Exception as exc:  # noqa: BLE001
        logger.debug("coaching collection existence check failed: %s", exc)
        return None, collection, False

    has_sparse = _detect_sparse(client, collection)
    return client, collection, has_sparse


def _detect_sparse(client, collection: str) -> bool:  # type: ignore[no-untyped-def]
    """Probe whether the existing coaching collection has a working sparse channel.

    Cached at module level via :data:`_SPARSE_CACHE` — the round-trip
    probe in coaching_vdb is reliable but has a real cost, and the
    answer doesn't change within a server's lifetime.
    """
    cached = _SPARSE_CACHE.get(collection)
    if cached is not None:
        return cached
    try:
        from backend.coaching_vdb import _probe_sparse_support

        result = bool(_probe_sparse_support(client, collection))
    except Exception:  # noqa: BLE001
        result = False
    _SPARSE_CACHE[collection] = result
    return result


_SPARSE_CACHE: dict[str, bool] = {}


def _id_of(hit) -> str | None:  # type: ignore[no-untyped-def]
    pid = getattr(hit, "id", None)
    if pid is None and isinstance(hit, dict):
        pid = hit.get("id")
    return str(pid) if pid is not None else None


def _score_of(hit) -> float | None:  # type: ignore[no-untyped-def]
    score = getattr(hit, "score", None)
    if score is None and isinstance(hit, dict):
        score = hit.get("score")
    try:
        return float(score) if score is not None else None
    except (TypeError, ValueError):
        return None


def _fused_score_of(hit) -> float:  # type: ignore[no-untyped-def]
    """Return the RRF-assigned score; 0.0 if missing."""
    return _score_of(hit) or 0.0


def _payload_of(hit) -> dict | None:  # type: ignore[no-untyped-def]
    payload = getattr(hit, "payload", None)
    if payload is None and isinstance(hit, dict):
        payload = hit.get("payload")
    if payload is None:
        return None
    if not isinstance(payload, dict):
        try:
            return dict(payload)
        except Exception:  # noqa: BLE001
            return None
    return payload

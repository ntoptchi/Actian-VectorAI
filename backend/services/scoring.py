"""VDB-driven safety scoring.

This is where the vector DB earns its keep:

  1. Build a *query* :class:`SituationDoc` from the trip's environmental
     conditions (weather, lighting, hour, ...). Embed it.
  2. For each route candidate, search the VDB for crashes that
     (a) match the query semantically and (b) have an ``h3_cell``
     filter that intersects any segment of this route.
  3. Bucket the retrieved crashes back onto segments by H3 cell.
  4. Per-segment risk = min(1.0, crashes / (aadt * exposure_factor)) —
     normalised against an FL baseline so the number means "X times the
     state average for a road of this AADT in conditions like these".
  5. Per-route risk = exposure-weighted mean of per-segment intensities.

Retrieval is wrapped in try/except: if the VDB is empty/down, every
score collapses to 0 and segments render as neutral. That's the
honesty test in s2.4 — the briefing degrades, the API doesn't 500.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path

from backend.config import get_settings
from backend.embeddings import embed_one
from backend.ingest.situation_doc import render_narrative
from backend.schemas import (
    FactorWeight,
    LatLon,
    RiskBand,
    RouteSegment,
    SeverityMix,
    SituationDoc,
    WeatherSegment,
)
from backend.services.segments import SegmentGeom

logger = logging.getLogger(__name__)


# How many crashes to pull from the VDB per route. Generous — we filter
# down to per-segment counts in memory.
TOP_K = 200

# crashes per million vehicle-passes considered "average" by road type.
_FALLBACK_BASELINES: dict[str, float] = {
    "interstate": 0.20,
    "us_highway": 0.30,
    "state_route": 0.35,
    "arterial": 0.50,
    "ramp": 0.40,
    "local": 0.45,
    "unknown": 0.30,
}


def _load_baselines() -> dict[str, float]:
    """Load FL baseline crash rates from disk, or fall back to literals."""
    p: Path = get_settings().processed_dir / "fl_baseline_rates.json"
    if p.exists():
        try:
            return {**_FALLBACK_BASELINES, **json.loads(p.read_text())}
        except Exception as exc:  # noqa: BLE001
            logger.warning("could not parse %s: %s", p, exc)
    return dict(_FALLBACK_BASELINES)


# --- Query construction ---------------------------------------------------


def build_query_doc(
    *,
    departure: datetime,
    weather_segments: list[WeatherSegment],
    sunset_iso: datetime | None,
) -> SituationDoc:
    """Compose a conditions-only :class:`SituationDoc` for embedding.

    We pick the *first* weather segment as a coarse proxy — for the
    hackathon scope this is fine; per-segment weather queries would
    multiply embedding cost without meaningfully changing what surfaces.
    """
    weather_label = "unknown"
    surface_label = "unknown"
    if weather_segments:
        weather_label = weather_segments[0].weather or "unknown"
        surface_label = weather_segments[0].surface or "unknown"

    hour = departure.hour
    is_dark = sunset_iso is not None and departure >= sunset_iso
    if is_dark:
        lighting = "dark_unlighted"
    elif 5 <= hour < 7 or 18 <= hour < 20:
        lighting = "dawn_dusk"
    else:
        lighting = "daylight"

    return SituationDoc(
        weather=weather_label if weather_label in {  # type: ignore[arg-type]
            "clear", "rain", "snow", "fog", "sleet", "severe_wind"
        } else "unknown",
        surface=surface_label if surface_label in {  # type: ignore[arg-type]
            "dry", "wet", "icy", "snowy"
        } else "unknown",
        lighting=lighting,  # type: ignore[arg-type]
        hour_bucket=hour,
        day_of_week=departure.weekday(),
        month=departure.month,
    )


# --- Retrieval -----------------------------------------------------------


def retrieve_crashes_for_cells(
    cells: set[str],
    query_doc: SituationDoc,
    *,
    top_k: int = TOP_K,
) -> list[dict]:
    """Run the VDB similarity search filtered by route cells.

    Returns a list of ``{score, payload}`` dicts. On any VDB error or
    empty collection, returns ``[]`` so the caller can still produce
    a valid (just neutral) response.
    """
    if not cells:
        return []
    try:
        from backend.vdb import get_client
        from backend.config import get_settings as _gs
    except Exception as exc:  # noqa: BLE001
        logger.warning("VDB import failed: %s", exc)
        return []

    text = render_narrative(query_doc, for_query=True)
    if not text:
        return []

    try:
        vec = embed_one(text)
    except Exception as exc:  # noqa: BLE001
        logger.warning("embed_one failed: %s", exc)
        return []

    client = get_client()
    name = _gs().vdb_collection
    cell_list = list(cells)

    # actian_vectorai's sync client mirrors the Qdrant-style API: search
    # takes a positional `vector` and `filter=` (NOT `query_vector=` /
    # `query_filter=`, which is what an older docstring suggested and
    # what we shipped to QA — that's the bug that made every segment
    # collapse to "0 matched crashes").
    #
    # We try a server-side IN-list filter on h3_cell first. The free
    # build of VectorAI silently returns zero hits for IN-lists on
    # unindexed payload fields (no error, just an empty page), so we
    # detect that case (empty page + non-empty cell set + non-empty
    # collection) and re-issue without the filter, then post-filter in
    # Python. That lossy fallback is fine for k=200 — the routing pass
    # has already narrowed the cell set, so the client-side prune is
    # cheap.
    cell_set = set(cell_list)
    results = []
    try:
        from actian_vectorai import (
            Condition,
            FieldCondition,
            Filter,
            Match,
        )

        flt = Filter(
            must=[
                Condition(
                    field=FieldCondition(
                        key="h3_cell",
                        match=Match(keywords=cell_list[:1024]),
                    )
                )
            ]
        )
        results = client.points.search(
            name, vec, limit=top_k, filter=flt
        )
    except Exception as exc:  # noqa: BLE001
        logger.info(
            "server-side h3 filter unsupported, post-filtering client-side: %s",
            exc,
        )

    if not results:
        # Either the server-side filter raised, or it silently returned
        # nothing (UNIMPLEMENTED for IN-lists on unindexed payload — the
        # exact failure mode we hit in QA). Re-pull a wider page and
        # filter in Python.
        try:
            results = client.points.search(name, vec, limit=top_k * 5)
        except Exception as exc2:  # noqa: BLE001
            logger.warning("VDB search failed: %s", exc2)
            return []
        results = [
            r for r in results
            if (getattr(r, "payload", None) or {}).get("h3_cell") in cell_set
        ][:top_k]

    out: list[dict] = []
    for r in results:
        payload = getattr(r, "payload", None) or {}
        score = float(getattr(r, "score", 0.0))
        out.append({"score": score, "payload": payload})
    return out


# --- Scoring -------------------------------------------------------------


def score_segments(
    segs: list[SegmentGeom],
    crashes: list[dict],
) -> list[RouteSegment]:
    """Bucket crashes onto segments by H3 cell and compute per-segment risk.

    Returns one :class:`RouteSegment` per input segment, in the same
    order. Empty inputs produce empty outputs.
    """
    baselines = _load_baselines()

    # Cell -> list of segment indexes that contain it. Used to bucket
    # each crash onto every segment whose H3 ring covers it. (A crash
    # near a segment boundary may bucket into both, which is the right
    # behaviour for visualisation.)
    cell_to_segs: dict[str, list[int]] = {}
    for i, seg in enumerate(segs):
        for cell in seg.cells:
            cell_to_segs.setdefault(cell, []).append(i)

    seg_crashes: list[list[dict]] = [[] for _ in segs]
    for cr in crashes:
        cell = (cr.get("payload") or {}).get("h3_cell")
        if not cell:
            continue
        for idx in cell_to_segs.get(cell, []):
            seg_crashes[idx].append(cr)

    out: list[RouteSegment] = []
    for seg, crs in zip(segs, seg_crashes):
        n = len(crs)
        intensity = _intensity_ratio(n, seg, baselines)
        band = _risk_band(n, intensity)
        factors = _top_factors([c.get("payload") or {} for c in crs])
        out.append(
            RouteSegment(
                segment_id=seg.segment_id,
                polyline=seg.polyline,
                from_km=seg.from_km,
                to_km=seg.to_km,
                aadt=seg.aadt,
                speed_limit_mph=seg.speed_limit_mph,
                n_crashes=n,
                intensity_ratio=intensity,
                risk_band=band,
                top_factors=factors,
            )
        )
    return out


def aggregate_route_risk(segments: list[RouteSegment]) -> tuple[float, int]:
    """Reduce per-segment scores to one number per route, plus a count.

    Risk score is the exposure-weighted mean of segment intensities,
    where exposure ≈ segment length in km. Lower is safer.
    """
    if not segments:
        return 0.0, 0
    total_w = 0.0
    weighted = 0.0
    n_total = 0
    for s in segments:
        w = max(0.001, s.to_km - s.from_km)
        total_w += w
        weighted += w * (s.intensity_ratio or 0.0)
        n_total += s.n_crashes
    return (weighted / total_w if total_w > 0 else 0.0), n_total


def route_risk_band(score: float) -> RiskBand:
    """Map an aggregate score to a categorical band for the UI."""
    if score >= 1.5:
        return "high"
    if score >= 1.0:
        return "elevated"
    if score >= 0.5:
        return "moderate"
    return "low"


# --- Helpers -------------------------------------------------------------


def _intensity_ratio(
    n: int,
    seg: SegmentGeom,
    baselines: dict[str, float],
) -> float:
    """X-times-FL-average intensity for this segment.

    Compares the *observed crash density* (crashes per
    million-vehicle-passes through the segment) against the baseline
    rate for a road of similar function. Caps at 5.0 so a single tiny
    segment doesn't dominate the route average.
    """
    if n == 0:
        return 0.0
    aadt = seg.aadt or 12_000
    seg_km = max(0.1, seg.to_km - seg.from_km)
    # Approx years of crash coverage in the corpus (FDOT goes back ~14y).
    years = 5.0
    vehicle_passes_million = (aadt * 365.0 * years * seg_km / 1.609) / 1_000_000.0
    rate = n / max(vehicle_passes_million, 0.001)
    # Use a generic state-route baseline since we don't yet know the
    # segment's road class with certainty.
    baseline = baselines.get("state_route", 0.35)
    return min(5.0, rate / baseline)


def _risk_band(n_crashes: int, intensity: float) -> RiskBand:
    if intensity >= 1.5 or n_crashes >= 8:
        return "high"
    if intensity >= 1.0 or n_crashes >= 4:
        return "elevated"
    if intensity >= 0.5 or n_crashes >= 2:
        return "moderate"
    return "low"


def _top_factors(payloads: list[dict], *, top_n: int = 3) -> list[FactorWeight]:
    """Tally the most common factor tags across a bag of crashes."""
    if not payloads:
        return []
    counts: Counter[str] = Counter()
    for p in payloads:
        for key in ("weather", "lighting", "surface", "crash_type"):
            v = p.get(key)
            if v and v != "unknown":
                counts[str(v)] += 1
        sev = p.get("severity")
        if sev in {"fatal", "serious"}:
            counts[f"severity:{sev}"] += 1
    total = sum(counts.values()) or 1
    return [
        FactorWeight(factor=f, fraction=round(c / total, 3))
        for f, c in counts.most_common(top_n)
    ]


def severity_mix_from(payloads: list[dict]) -> SeverityMix:
    sev = SeverityMix()
    for p in payloads:
        s = p.get("severity") or "unknown"
        if s == "fatal":
            sev.fatal += 1
        elif s == "serious":
            sev.serious += 1
        elif s == "minor":
            sev.minor += 1
        elif s == "pdo":
            sev.pdo += 1
        else:
            sev.unknown += 1
    return sev


# --- Hotspot conversion ---------------------------------------------------


def hotspots_from_segments(
    scored_segments: list[RouteSegment],
    seg_crashes_payloads: list[list[dict]] | None = None,
    *,
    max_hotspots: int = 6,
) -> list[dict]:
    """Pick the top-N riskiest segments and project them to hotspot dicts.

    Used by the trip router to populate ``hotspots`` for the right-hand
    briefing panel. Each hotspot's centroid is the segment midpoint.
    """
    if not scored_segments:
        return []
    # Rank by (intensity, n_crashes) descending; require at least 1 crash.
    ranked = [
        s for s in scored_segments if s.n_crashes > 0
    ]
    ranked.sort(key=lambda s: (s.intensity_ratio or 0.0, s.n_crashes), reverse=True)
    picks = ranked[:max_hotspots]
    out: list[dict] = []
    for s in picks:
        if not s.polyline:
            continue
        mid = s.polyline[len(s.polyline) // 2]
        centroid = LatLon(lat=mid[1], lon=mid[0])
        out.append(
            {
                "segment": s,
                "centroid": centroid,
            }
        )
    return out

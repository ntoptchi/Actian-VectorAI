"""``POST /trip/brief`` — candidate-and-rerank pre-trip briefing.

Pivot architecture (overrides the original groundwork shape):

  1. Pull N route alternates from ORS (single OSRM route as fallback).
  2. For each alternate, slice into ~40 segments + attach AADT.
  3. Build a single conditions query :class:`SituationDoc`, embed once.
  4. For each alternate, retrieve crashes from the VDB filtered by the
     alternate's H3 cells, then bucket onto segments and score.
  5. Pick the chosen route as ``argmin(duration_norm + lambda * risk_norm)``
     so we rerank by safety without picking absurd detours.
  6. Build segments + hotspots + conditions banner + fatigue plan for
     the chosen route, return everything.

If the VDB is unreachable or the collection is empty, every score
collapses to 0 and the chosen route is just the fastest alternate.
The endpoint never 500s on a degraded backend (s2.4).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

from backend.schemas import (
    AlternateSummary,
    ConditionsBanner,
    CrashInsight,
    FatiguePlan,
    HotspotSummary,
    LatLon,
    NewsCrashPin,
    Route,
    RouteCandidate,
    RoutesOnlyResponse,
    SeverityMix,
    TripBriefRequest,
    TripBriefResponse,
)
from backend.services import (
    coaching,
    coaching_retrieval,
    fatigue,
    geocode,
    lesson_zones,
    routing,
    scoring,
    segments as segments_svc,
    sun,
    weather,
)
from backend.services.routing import RouteAlternate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trip", tags=["trip"])


PRE_TRIP_CHECKLIST: list[str] = [
    "Tires and fuel checked",
    "Offline maps cached (cell signal drops on rural interstates)",
    "Water and a snack in reach",
    "Headlights on by sunset; earlier under heavy cloud cover",
    "Phone mounted; passenger handles texts",
]


# How heavily we weight safety when picking the chosen route.
# 0.0 = always-fastest (Google Maps default).
# 1.0 = pick the safest at any time cost.
# 2.0 = safety-first: the safest route wins unless it's dramatically longer.
SAFETY_LAMBDA = 2.0


@router.post("/routes", response_model=RoutesOnlyResponse)
async def trip_routes(req: TripBriefRequest) -> RoutesOnlyResponse:
    """Fast path: return OSRM alternate geometries without any scoring."""
    departure = req.timestamp or datetime.now(timezone.utc)
    if departure.tzinfo is None:
        departure = departure.replace(tzinfo=timezone.utc)
    alts = await routing.alternates(req.origin, req.destination, departure)
    return RoutesOnlyResponse(
        candidates=[
            RouteCandidate(
                route_id=a.route_id,
                polyline=a.polyline,
                distance_m=a.distance_m,
                duration_s=a.duration_s,
            )
            for a in alts
        ]
    )


@router.post("/brief", response_model=TripBriefResponse)
async def trip_brief(req: TripBriefRequest) -> TripBriefResponse:
    departure = req.timestamp or datetime.now(timezone.utc)
    if departure.tzinfo is None:
        departure = departure.replace(tzinfo=timezone.utc)
    trip_id = f"t_{uuid.uuid4().hex[:16]}"

    # 1. Candidate alternates (always >=1; never raises).
    alts: list[RouteAlternate] = await routing.alternates(
        req.origin, req.destination, departure
    )

    # Use the first (fastest) alternate's polyline for conditions
    # services that don't care about per-route weather differences.
    fastest = alts[0]
    fastest_route = routing.to_route(fastest, departure)

    weather_segments = await weather.weather_along(
        fastest_route.polyline_geojson,
        fastest_route.departure_iso,
        fastest_route.duration_s,
    )
    sunset_iso = sun.sunset_for_route(
        fastest_route.polyline_geojson, fastest_route.departure_iso
    )
    dark_minutes = sun.dark_drive_minutes(fastest_route, sunset_iso)
    plan: FatiguePlan = fatigue.plan(fastest_route)

    # 2-4. Per-alternate scoring (sequential is fine at N=3; embedding
    #      is shared across all alts so the marginal cost is one VDB
    #      search per alternate).
    query_doc = scoring.build_query_doc(
        departure=departure,
        weather_segments=weather_segments,
        sunset_iso=sunset_iso,
    )

    scored_alts: list[_ScoredAlt] = []
    for a in alts:
        scored_alts.append(await _score_alternate(a, query_doc))

    # 5. Pick chosen route via cost = duration_norm + lambda * risk_norm.
    chosen_idx = _pick_chosen(scored_alts)
    chosen = scored_alts[chosen_idx]

    # Build alternate summaries with deltas vs the *fastest* (idx 0).
    alternate_summaries = _alternate_summaries(scored_alts)

    # 6. Hotspots from the chosen route's top-risk segments, with an
    #    anecdote retrieved from the coaching VDB attached to each.
    hotspots = _hotspots_for(chosen, query_doc)

    # 7. Route-wide crash lessons retrieved from the coaching VDB,
    #    snapped to the nearest segment midpoint. Empty list when the
    #    VDB is unavailable — the UI degrades gracefully.
    insights = _insights_for(chosen, hotspots, query_doc)
    zones = lesson_zones.build_zones(chosen.segments, insights)
    news_crashes = await asyncio.to_thread(_news_crashes_for, chosen, query_doc)

    # The chosen Route uses the chosen alternate's polyline so the
    # frontend can paint per-segment risk on it.
    chosen_route = routing.to_route(chosen.alt, departure)

    conditions = ConditionsBanner(
        summary=_compose_banner_summary(weather_segments, sunset_iso, dark_minutes),
        weather_segments=weather_segments,
        sunset_iso=sunset_iso,
        dark_drive_minutes=dark_minutes,
    )

    return TripBriefResponse(
        trip_id=trip_id,
        route=chosen_route,
        conditions_banner=conditions,
        fatigue_plan=plan,
        sunset_during_trip=dark_minutes > 0,
        hotspots=hotspots,
        pre_trip_checklist=PRE_TRIP_CHECKLIST,
        chosen_route_id=chosen.alt.route_id,
        alternates=alternate_summaries,
        segments=chosen.segments,
        insights=insights,
        lesson_zones=zones,
        news_crashes=news_crashes,
    )


# --- Per-alternate scoring -----------------------------------------------


class _ScoredAlt:
    __slots__ = ("alt", "segments", "risk_score", "n_crashes")

    def __init__(
        self,
        alt: RouteAlternate,
        segments_,
        risk_score: float,
        n_crashes: int,
    ) -> None:
        self.alt = alt
        self.segments = segments_
        self.risk_score = risk_score
        self.n_crashes = n_crashes


async def _score_alternate(alt: RouteAlternate, query_doc) -> _ScoredAlt:
    """Slice + AADT + retrieve + score one alternate."""
    seg_geoms = segments_svc.slice_route(alt.polyline)
    if not seg_geoms:
        return _ScoredAlt(alt, [], 0.0, 0)

    # AADT enrichment is sync + heavy; offload to a thread.
    await asyncio.to_thread(segments_svc.attach_aadt, seg_geoms)

    # Union of cells across all segments — what we filter the VDB on.
    cell_union: set[str] = set()
    for s in seg_geoms:
        cell_union |= s.cells

    all_results = await asyncio.to_thread(
        scoring.retrieve_crashes_for_cells, cell_union, query_doc
    )

    # Filter out any legacy NEWS docs that might still live in the crash
    # corpus — they're now served exclusively by the coaching VDB and
    # shouldn't inflate crash counts or risk scoring here.
    crashes = [
        r for r in all_results
        if (r.get("payload") or {}).get("source") != "NEWS"
    ]

    scored_segs = scoring.score_segments(seg_geoms, crashes)
    risk_score, n_crashes = scoring.aggregate_route_risk(scored_segs)
    logger.info(
        "route %s: %.2f crashes/km (%d crashes, %.0f km) → %s",
        alt.route_id, risk_score, n_crashes,
        alt.distance_m / 1000, scoring.route_risk_band(risk_score),
    )
    return _ScoredAlt(alt, scored_segs, risk_score, n_crashes)


def _pick_chosen(scored: list[_ScoredAlt]) -> int:
    """Cost = duration_norm + SAFETY_LAMBDA * risk_norm.

    Both terms are normalised to [0, 1] across the candidate set so the
    weight is comparable.
    """
    if len(scored) == 1:
        return 0
    durations = [s.alt.duration_s for s in scored]
    risks = [s.risk_score for s in scored]
    d_min, d_max = min(durations), max(durations)
    r_min, r_max = min(risks), max(risks)
    d_span = max(1e-6, d_max - d_min)
    r_span = max(1e-6, r_max - r_min)

    best_i = 0
    best_cost = float("inf")
    for i, s in enumerate(scored):
        d_norm = (s.alt.duration_s - d_min) / d_span
        r_norm = (s.risk_score - r_min) / r_span
        cost = d_norm + SAFETY_LAMBDA * r_norm
        if cost < best_cost:
            best_cost = cost
            best_i = i
    return best_i


def _alternate_summaries(scored: list[_ScoredAlt]) -> list[AlternateSummary]:
    if not scored:
        return []
    fastest_dur = scored[0].alt.duration_s
    fastest_risk = scored[0].risk_score or 0.0
    out: list[AlternateSummary] = []
    for s in scored:
        minutes_delta = (s.alt.duration_s - fastest_dur) / 60.0
        if fastest_risk > 0:
            risk_delta_pct = (s.risk_score - fastest_risk) / fastest_risk
        else:
            risk_delta_pct = 0.0
        out.append(
            AlternateSummary(
                route_id=s.alt.route_id,
                polyline=s.alt.polyline,
                distance_m=s.alt.distance_m,
                duration_s=s.alt.duration_s,
                risk_score=round(s.risk_score, 3),
                risk_band=scoring.route_risk_band(s.risk_score),
                n_crashes=s.n_crashes,
                minutes_delta_vs_fastest=round(minutes_delta, 1),
                risk_delta_vs_fastest=round(risk_delta_pct, 3),
                segments=s.segments,
            )
        )
    return out


def _hotspots_for(scored: _ScoredAlt, query_doc) -> list[HotspotSummary]:
    """Top-N riskiest segments, each with a VDB-retrieved anecdote + lesson.

    Coaching line priority:
      1. The retrieved insight's lesson (VDB-driven, context-aware).
      2. The rule-based fallback in ``backend.services.coaching`` (used
         when the VDB is unavailable, empty, or produces nothing that
         clears the similarity floor).
    """
    ranked = [s for s in scored.segments if s.n_crashes > 0]
    ranked.sort(
        key=lambda s: (s.intensity_ratio or 0.0, s.n_crashes), reverse=True
    )
    # Dedupe both coaching lines and insight IDs across the trip so a
    # reader doesn't see the same sentence or the same anecdote on
    # every hotspot.
    used_coaching: set[str] = set()
    used_insights: set[str] = set()
    hotspots: list[HotspotSummary] = []
    for i, seg in enumerate(ranked[:6]):
        if not seg.polyline:
            continue
        mid = seg.polyline[len(seg.polyline) // 2]
        centroid = LatLon(lat=mid[1], lon=mid[0])

        insight = coaching_retrieval.retrieve_for_segment(seg, query_doc)
        if insight is not None and insight.insight_id in used_insights:
            # Fall back to rule-based rather than reusing an anecdote.
            insight = None
        elif insight is not None:
            used_insights.add(insight.insight_id)

        if insight is not None and insight.lesson:
            line = insight.lesson
        else:
            line = coaching.coaching_line(
                seg.top_factors, seed=i, exclude=used_coaching
            )
        used_coaching.add(line)

        label = _segment_label(seg, centroid)
        hotspots.append(
            HotspotSummary(
                hotspot_id=f"h_{i}_{seg.segment_id}",
                label=label,
                road_name=None,
                centroid=centroid,
                km_into_trip=(seg.from_km + seg.to_km) / 2.0,
                n_crashes=seg.n_crashes,
                mean_similarity=(insight.similarity if insight else 0.0),
                aadt=seg.aadt,
                intensity_ratio=seg.intensity_ratio,
                exposure_intensity_ratio=seg.exposure_intensity_ratio,
                severity_mix=SeverityMix(),
                top_factors=seg.top_factors,
                coaching_line=line,
                insight=insight,
            )
        )
    return hotspots


def _insights_for(
    scored: _ScoredAlt,
    hotspots: list[HotspotSummary],
    query_doc,
) -> list[CrashInsight]:
    """Route-wide insights, deduping against anecdotes already attached to hotspots.

    Hotspot anecdotes already consume the highest-similarity pulls, so
    we pass their IDs as the initial dedupe set to avoid pinning the
    exact same lesson twice (once on the hotspot card, once on the
    "Lessons from the road" list).
    """
    used = {h.insight.insight_id for h in hotspots if h.insight is not None}
    existing = [h.insight for h in hotspots if h.insight is not None]

    # Retrieve for segments not already represented via hotspots.
    fresh = coaching_retrieval.retrieve_for_route(scored.segments, query_doc)
    merged: list[CrashInsight] = list(existing)
    for ins in fresh:
        if ins.insight_id in used:
            continue
        merged.append(ins)
        used.add(ins.insight_id)

    # Order by similarity desc so the most contextually relevant
    # lessons appear at the top of the right-rail list.
    merged.sort(key=lambda i: i.similarity, reverse=True)
    return merged


def _news_crashes_for(scored: _ScoredAlt, query_doc) -> list[NewsCrashPin]:
    """Return NEWS-sourced crash reports along the chosen route corridor."""
    seg_geoms = segments_svc.slice_route(scored.alt.polyline)
    if not seg_geoms:
        return []
    cell_union: set[str] = set()
    for seg in seg_geoms:
        cell_union |= seg.cells
    if not cell_union:
        return []

    results = scoring.retrieve_crashes_for_cells(cell_union, query_doc)
    news_payloads = [
        (r.get("payload") or {})
        for r in results
        if (r.get("payload") or {}).get("source") == "NEWS"
    ]
    if not news_payloads:
        return []

    deduped: dict[str, dict] = {}
    for p in news_payloads:
        crash_id = str(p.get("crash_id") or p.get("case_id") or "")
        if not crash_id:
            continue
        prev = deduped.get(crash_id)
        if prev is None:
            deduped[crash_id] = p
            continue
        prev_sev = _severity_rank(str(prev.get("severity") or "unknown"))
        cur_sev = _severity_rank(str(p.get("severity") or "unknown"))
        if cur_sev > prev_sev:
            deduped[crash_id] = p

    pins: list[NewsCrashPin] = []
    for p in deduped.values():
        lat = p.get("lat")
        lon = p.get("lon")
        if lat is None or lon is None:
            continue
        pins.append(
            NewsCrashPin(
                crash_id=str(p.get("crash_id") or p.get("case_id") or ""),
                lat=float(lat),
                lon=float(lon),
                headline=str(p.get("headline") or p.get("article_headline") or "Crash report"),
                article_url=(str(p.get("article_url")) if p.get("article_url") else None),
                publish_date=(str(p.get("publish_date")) if p.get("publish_date") else None),
                severity=str(p.get("severity") or "unknown"),  # type: ignore[arg-type]
            )
        )

    pins.sort(
        key=lambda pin: (
            _severity_rank(pin.severity),
            pin.publish_date or "",
        ),
        reverse=True,
    )
    return pins[:40]


def _severity_rank(severity: str) -> int:
    if severity == "fatal":
        return 4
    if severity == "serious":
        return 3
    if severity == "minor":
        return 2
    if severity == "pdo":
        return 1
    return 0


def _segment_label(seg, centroid: LatLon) -> str:
    """Human-readable headline for a hotspot pin.

    Prefers the nearest named FL city to the segment midpoint ("Near
    Fort Myers"); falls back to a km-into-trip phrasing when no city
    is within range so we never fabricate a place name.
    """
    city = geocode.nearest_city(centroid.lat, centroid.lon)
    if city:
        return f"Near {city}"
    km = (seg.from_km + seg.to_km) / 2.0
    return f"{km:.0f} km into the trip"


def _compose_banner_summary(segments, sunset_iso, dark_minutes: int) -> str:
    parts: list[str] = []
    weathers = {s.weather for s in segments}
    if weathers and weathers != {"clear"}:
        parts.append("Mixed conditions along the route.")
    elif weathers == {"clear"}:
        parts.append("Clear skies along the route.")
    if sunset_iso is not None and dark_minutes > 0:
        hours = dark_minutes // 60
        mins = dark_minutes % 60
        if hours and mins:
            parts.append(f"You will drive ~{hours}h {mins}m after dark.")
        elif hours:
            parts.append(f"You will drive ~{hours}h after dark.")
        else:
            parts.append(f"You will drive ~{mins}m after dark.")
    return " ".join(parts) if parts else "Conditions along the route."

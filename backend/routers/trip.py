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
    FatiguePlan,
    HotspotSummary,
    LatLon,
    Route,
    SeverityMix,
    TripBriefRequest,
    TripBriefResponse,
)
from backend.services import (
    coaching,
    fatigue,
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
# 0.4 lands "+5min for -25% risk" inside the chosen-route band.
SAFETY_LAMBDA = 0.4


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

    # 6. Hotspots from the chosen route's top-risk segments.
    hotspots = _hotspots_for(chosen)

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
    )


# --- Per-alternate scoring -----------------------------------------------


class _ScoredAlt:
    __slots__ = ("alt", "segments", "risk_score", "n_crashes")

    def __init__(self, alt: RouteAlternate, segments_, risk_score: float, n_crashes: int) -> None:
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

    crashes = await asyncio.to_thread(
        scoring.retrieve_crashes_for_cells, cell_union, query_doc
    )
    scored_segs = scoring.score_segments(seg_geoms, crashes)
    risk_score, n_crashes = scoring.aggregate_route_risk(scored_segs)
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
            )
        )
    return out


def _hotspots_for(scored: _ScoredAlt) -> list[HotspotSummary]:
    """Top-N riskiest segments, projected to hotspot summaries."""
    ranked = [s for s in scored.segments if s.n_crashes > 0]
    ranked.sort(
        key=lambda s: (s.intensity_ratio or 0.0, s.n_crashes), reverse=True
    )
    hotspots: list[HotspotSummary] = []
    for i, seg in enumerate(ranked[:6]):
        if not seg.polyline:
            continue
        mid = seg.polyline[len(seg.polyline) // 2]
        centroid = LatLon(lat=mid[1], lon=mid[0])
        coaching_line = coaching.coaching_line(seg.top_factors)
        hotspots.append(
            HotspotSummary(
                hotspot_id=f"h_{i}_{seg.segment_id}",
                label=_segment_label(seg, i),
                road_name=None,
                centroid=centroid,
                km_into_trip=(seg.from_km + seg.to_km) / 2.0,
                n_crashes=seg.n_crashes,
                mean_similarity=0.0,  # not surfaced per-segment yet
                aadt=seg.aadt,
                intensity_ratio=seg.intensity_ratio,
                severity_mix=SeverityMix(),
                top_factors=seg.top_factors,
                coaching_line=coaching_line,
            )
        )
    return hotspots


def _segment_label(seg, idx: int) -> str:
    km = (seg.from_km + seg.to_km) / 2.0
    return f"Hotspot {idx + 1} — ~{km:.0f} km in"


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

"""``POST /trip/brief`` — orchestrates routing, weather, sun, fatigue,
and VDB retrieval into a single trip-briefing payload.

Groundwork pass: the orchestration shape is correct end-to-end, but the
heavy lifters in ``backend/services/*`` are stubs. The endpoint already
returns a well-formed ``TripBriefResponse`` with empty hotspots so the
frontend can render against the real shape. Day-2/3/4 fills the bodies.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

from backend.schemas import (
    ConditionsBanner,
    FatiguePlan,
    Route,
    TripBriefRequest,
    TripBriefResponse,
)
from backend.services import cluster, fatigue, h3util, routing, sun, weather

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trip", tags=["trip"])


# Static checklist (ROUTEWISE.md s8.1; copy from s6.3 example)
PRE_TRIP_CHECKLIST: list[str] = [
    "Tires and fuel checked",
    "Offline maps cached (cell signal drops on rural interstates)",
    "Water and a snack in reach",
    "Headlights on by sunset; earlier under heavy cloud cover",
    "Phone mounted; passenger handles texts",
]


@router.post("/brief", response_model=TripBriefResponse)
async def trip_brief(req: TripBriefRequest) -> TripBriefResponse:
    """Build a pre-trip briefing for the given (origin, destination, time).

    Flow (ROUTEWISE.md s5.2):
      1. OSRM   -> route polyline, distance, duration.
      2. Open-Meteo -> weather along route.
      3. pysolar -> sunset at midpoint.
      4. Fatigue plan from duration.
      5. H3 cells along route -> VDB similarity search filtered by cells.
      6. DBSCAN cluster -> AADT-normalize -> rank top 3-6 hotspots.
    """
    departure = req.timestamp or datetime.now(timezone.utc)
    trip_id = f"t_{uuid.uuid4().hex[:16]}"

    # 1. Route
    route: Route = await routing.route(req.origin, req.destination, departure)

    # 2-4. Conditions, sunset, fatigue (all stubs for now)
    weather_segments = await weather.weather_along(
        route.polyline_geojson, route.departure_iso, route.duration_s
    )
    sunset_iso = sun.sunset_for_route(route.polyline_geojson, route.departure_iso)
    dark_minutes = sun.dark_drive_minutes(route, sunset_iso)
    conditions = ConditionsBanner(
        summary=_compose_banner_summary(weather_segments, sunset_iso, dark_minutes),
        weather_segments=weather_segments,
        sunset_iso=sunset_iso,
        dark_drive_minutes=dark_minutes,
    )
    plan: FatiguePlan = fatigue.plan(route)

    # 5-6. Hotspots — guarded so VDB outages don't 500 the endpoint.
    hotspots: list = []
    try:
        cells = h3util.cells_along(route.polyline_geojson, res=9, ring=1)
        hotspots = await cluster.find_hotspots(
            cells=cells,
            departure=route.departure_iso,
            weather_segments=weather_segments,
            sunset_iso=sunset_iso,
        )
    except Exception as exc:  # noqa: BLE001 — honesty test (s2.4)
        logger.warning("hotspot retrieval failed; returning empty list: %s", exc)
        hotspots = []

    return TripBriefResponse(
        trip_id=trip_id,
        route=route,
        conditions_banner=conditions,
        fatigue_plan=plan,
        sunset_during_trip=dark_minutes > 0,
        hotspots=hotspots,
        pre_trip_checklist=PRE_TRIP_CHECKLIST,
    )


def _compose_banner_summary(segments, sunset_iso, dark_minutes: int) -> str:
    """Plain-English banner copy (ROUTEWISE.md s2 example)."""
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

"""Routing client — fully local via self-hosted OSRM.

Fetches *alternative* driving routes (typically up to 3) from a local
OSRM instance so the candidate-and-rerank pipeline has a real choice
to make. A straight-line "as the crow flies" stub is the last-resort
fallback so /trip/brief never 500s on routing alone.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx

from backend.config import get_settings
from backend.schemas import GeoJsonLineString, LatLon, Route

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RouteAlternate:
    """One candidate route, before any safety scoring."""

    route_id: str
    polyline: list[list[float]]  # [[lon, lat], ...]
    distance_m: float
    duration_s: float


async def alternates(
    origin: LatLon,
    dest: LatLon,
    departure: datetime,
) -> list[RouteAlternate]:
    """Fetch >=1 candidate routes between origin and destination.

    Tries local OSRM with alternatives, falls back to a straight-line
    stub. The returned list is always non-empty.
    """
    try:
        return await _osrm_alternates(origin, dest)
    except Exception as exc:  # noqa: BLE001
        logger.warning("OSRM unreachable, using straight-line stub: %s", exc)

    distance_m = _haversine_m(origin, dest)
    return [
        RouteAlternate(
            route_id="alt_0",
            polyline=[[origin.lon, origin.lat], [dest.lon, dest.lat]],
            distance_m=distance_m,
            duration_s=distance_m / 27.0,
        )
    ]


def to_route(alt: RouteAlternate, departure: datetime) -> Route:
    """Pack a candidate as the legacy :class:`Route` shape used by
    weather / sun / fatigue services that pre-date the alternates pivot.
    """
    arrival = departure + timedelta(seconds=alt.duration_s)
    return Route(
        polyline_geojson=GeoJsonLineString(coordinates=alt.polyline),
        distance_m=alt.distance_m,
        duration_s=alt.duration_s,
        departure_iso=departure,
        arrival_iso=arrival,
    )


# --- Legacy single-route entry point (kept for compatibility with tests) ---


async def route(origin: LatLon, dest: LatLon, departure: datetime) -> Route:
    """Backward-compat single-route fetch — picks the first alternate."""
    alts = await alternates(origin, dest, departure)
    return to_route(alts[0], departure)


# --- Local OSRM with alternatives ----------------------------------------


async def _osrm_alternates(origin: LatLon, dest: LatLon) -> list[RouteAlternate]:
    """Fetch up to 3 alternative routes from the local OSRM instance."""
    settings = get_settings()
    url = (
        f"{settings.osrm_base_url}/route/v1/driving/"
        f"{origin.lon},{origin.lat};{dest.lon},{dest.lat}"
    )
    params = {
        "overview": "full",
        "geometries": "geojson",
        "alternatives": "3",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    routes = data.get("routes") or []
    if not routes:
        raise RuntimeError("OSRM returned no routes")

    out: list[RouteAlternate] = []
    for i, leg in enumerate(routes):
        coords = leg.get("geometry", {}).get("coordinates") or []
        if not coords:
            continue
        out.append(
            RouteAlternate(
                route_id=f"alt_{i}",
                polyline=[[float(lon), float(lat)] for lon, lat in coords],
                distance_m=float(leg["distance"]),
                duration_s=float(leg["duration"]),
            )
        )

    if not out:
        raise RuntimeError("OSRM returned routes but no usable polylines")

    logger.info("OSRM returned %d alternate(s)", len(out))
    return out


def _haversine_m(a: LatLon, b: LatLon) -> float:
    from math import asin, cos, radians, sin, sqrt

    R = 6_371_000.0
    lat1, lat2 = radians(a.lat), radians(b.lat)
    dlat = lat2 - lat1
    dlon = radians(b.lon - a.lon)
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(h))

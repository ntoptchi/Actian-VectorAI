"""Routing client.

Pivot: we now fetch *alternative* driving routes (typically 3) so the
candidate-and-rerank pipeline has a real choice to make. ORS is the
primary provider; OSRM (single route, no alternatives on the public
instance) is the fallback; a straight-line "as the crow flies" stub is
the last-resort fallback so /trip/brief never 500s on routing alone.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx

from backend.config import get_settings
from backend.schemas import GeoJsonLineString, LatLon, Route
from backend.services import ors_client

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

    Tries ORS first (real alternatives), falls back to OSRM (single
    route), then to a straight-line stub. The returned list is always
    non-empty.
    """
    # 1. ORS: real alternatives.
    try:
        ors_alts = await ors_client.directions(
            (origin.lat, origin.lon),
            (dest.lat, dest.lon),
            alternatives=3,
        )
        return [
            RouteAlternate(
                route_id=f"alt_{i}",
                polyline=a.polyline,
                distance_m=a.distance_m,
                duration_s=a.duration_s,
            )
            for i, a in enumerate(ors_alts)
        ]
    except Exception as exc:  # noqa: BLE001 — fall through to OSRM
        logger.warning("ORS alternates failed, falling back to OSRM: %s", exc)

    # 2. OSRM: single route, no alternatives.
    try:
        osrm = await _osrm_route(origin, dest)
        return [RouteAlternate(route_id="alt_0", **osrm)]
    except Exception as exc:  # noqa: BLE001
        logger.warning("OSRM unreachable, using straight-line stub: %s", exc)

    # 3. Straight-line stub.
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


# --- OSRM fallback ---------------------------------------------------------


async def _osrm_route(origin: LatLon, dest: LatLon) -> dict:
    settings = get_settings()
    url = (
        f"{settings.osrm_base_url}/route/v1/driving/"
        f"{origin.lon},{origin.lat};{dest.lon},{dest.lat}"
    )
    params = {"overview": "full", "geometries": "geojson", "alternatives": "false"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    leg = data["routes"][0]
    return {
        "polyline": leg["geometry"]["coordinates"],
        "distance_m": float(leg["distance"]),
        "duration_s": float(leg["duration"]),
    }


def _haversine_m(a: LatLon, b: LatLon) -> float:
    from math import asin, cos, radians, sin, sqrt

    R = 6_371_000.0
    lat1, lat2 = radians(a.lat), radians(b.lat)
    dlat = lat2 - lat1
    dlon = radians(b.lon - a.lon)
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(h))

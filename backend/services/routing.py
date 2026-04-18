"""OSRM routing client.

Public OSRM at ``router.project-osrm.org`` is used by default; a self-
hosted container can be swapped in via ``ROUTEWISE_OSRM_BASE_URL``.

Returns a :class:`Route` that downstream services index by km offset.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import httpx

from backend.config import get_settings
from backend.schemas import GeoJsonLineString, LatLon, Route

logger = logging.getLogger(__name__)


async def route(origin: LatLon, dest: LatLon, departure: datetime) -> Route:
    """Fetch a driving route from OSRM and pack it as a :class:`Route`.

    Falls back to a straight-line "as the crow flies" stub if OSRM is
    unreachable, so the briefing endpoint never 500s on routing alone.
    """
    settings = get_settings()
    url = (
        f"{settings.osrm_base_url}/route/v1/driving/"
        f"{origin.lon},{origin.lat};{dest.lon},{dest.lat}"
    )
    params = {"overview": "full", "geometries": "geojson", "alternatives": "false"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        leg = data["routes"][0]
        polyline = GeoJsonLineString(coordinates=leg["geometry"]["coordinates"])
        distance_m = float(leg["distance"])
        duration_s = float(leg["duration"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("OSRM unreachable, using straight-line fallback: %s", exc)
        polyline = GeoJsonLineString(
            coordinates=[[origin.lon, origin.lat], [dest.lon, dest.lat]]
        )
        distance_m = _haversine_m(origin, dest)
        duration_s = distance_m / 27.0  # ~60 mph average for fallback

    arrival = departure + timedelta(seconds=duration_s)
    return Route(
        polyline_geojson=polyline,
        distance_m=distance_m,
        duration_s=duration_s,
        departure_iso=departure,
        arrival_iso=arrival,
    )


def _haversine_m(a: LatLon, b: LatLon) -> float:
    """Great-circle distance in meters."""
    from math import asin, cos, radians, sin, sqrt

    R = 6_371_000.0
    lat1, lat2 = radians(a.lat), radians(b.lat)
    dlat = lat2 - lat1
    dlon = radians(b.lon - a.lon)
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(h))

"""Open-Meteo client.

ROUTEWISE.md s5.2 specifies sampling weather at 3-4 points along the
route, interpolated to the driving time at that point, and caching by
``(rounded_lat, rounded_lon, hour_bucket)``. Day-2 fills in the real
fetch + interpolation; for now we return a single "clear / dry" segment
covering the whole route so the response shape is correct.
"""

from __future__ import annotations

import logging
from datetime import datetime

from backend.schemas import GeoJsonLineString, WeatherSegment

logger = logging.getLogger(__name__)

# (rounded_lat, rounded_lon, hour_bucket) -> response cache
_CACHE: dict[tuple[float, float, int], dict] = {}


async def weather_along(
    polyline: GeoJsonLineString,
    departure_iso: datetime,
    duration_s: float,
) -> list[WeatherSegment]:
    """Return weather segments spanning the polyline's km range.

    TODO(day 2): sample 3-4 evenly-spaced polyline points; for each,
    pick the hour bucket the driver will be there at, hit
    ``forecast?latitude=&longitude=&hourly=...`` (or the archive API
    for past timestamps), and emit one ``WeatherSegment`` per
    contiguous (weather, surface) run.
    """
    if not polyline.coordinates:
        return []
    total_km = _approx_polyline_km(polyline)
    return [
        WeatherSegment(from_km=0.0, to_km=total_km, weather="clear", surface="dry"),
    ]


def _approx_polyline_km(polyline: GeoJsonLineString) -> float:
    """Fast great-circle sum across polyline vertices; good enough for s2."""
    from math import asin, cos, radians, sin, sqrt

    R = 6371.0
    coords = polyline.coordinates
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        p1, p2 = radians(lat1), radians(lat2)
        dp = p2 - p1
        dl = radians(lon2 - lon1)
        h = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
        total += 2 * R * asin(sqrt(h))
    return total

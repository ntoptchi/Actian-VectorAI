"""Sun position helper using ``pysolar``.

Computes sunset at the route midpoint and the number of minutes the
driver will spend after sunset on this trip.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from backend.schemas import GeoJsonLineString, Route

logger = logging.getLogger(__name__)


def sunset_for_route(polyline: GeoJsonLineString, departure: datetime) -> datetime | None:
    """Approximate sunset (UTC) at the polyline midpoint on departure date.

    TODO(day 2): for a long route the midpoint sunset is a coarse proxy;
    consider per-quartile sunset and surface that detail in the banner.
    """
    if not polyline.coordinates:
        return None
    midpoint = polyline.coordinates[len(polyline.coordinates) // 2]
    lon, lat = midpoint[0], midpoint[1]
    return _sunset_at(lat, lon, departure)


def dark_drive_minutes(route: Route, sunset_iso: datetime | None) -> int:
    """How many of the trip's minutes fall after the midpoint sunset."""
    if sunset_iso is None:
        return 0
    if route.arrival_iso <= sunset_iso:
        return 0
    after = (route.arrival_iso - max(route.departure_iso, sunset_iso)).total_seconds()
    return max(0, int(after // 60))


def _sunset_at(lat: float, lon: float, when: datetime) -> datetime | None:
    """Compute approximate sunset (UTC) by stepping the day in 5-min slices.

    Robust fallback if pysolar's ``get_sunset_time`` isn't available in
    the installed version. Returns the first instant after solar noon
    where altitude crosses below 0.
    """
    try:
        from pysolar import solar  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        logger.warning("pysolar unavailable: %s", exc)
        return None

    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    day_start = when.astimezone(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    prev_alt = solar.get_altitude(lat, lon, day_start)
    for step in range(1, 12 * 12 + 1):  # 12h ahead of noon, 5-min steps
        t = day_start + timedelta(minutes=5 * step)
        alt = solar.get_altitude(lat, lon, t)
        if prev_alt > 0 >= alt:
            return t
        prev_alt = alt
    return None

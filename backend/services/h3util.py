"""H3 cell utilities.

Used to (a) compute the set of cells covered by the route polyline at
resolution 9 (~150 m hex) and (b) buffer by 1 ring so crashes just off
the polyline still surface (ROUTEWISE.md s5.2.3).
"""

from __future__ import annotations

import logging
from math import asin, cos, radians, sin, sqrt

from backend.schemas import GeoJsonLineString

logger = logging.getLogger(__name__)


def latlon_to_cell(lat: float, lon: float, res: int = 9) -> str:
    import h3

    return h3.latlng_to_cell(lat, lon, res)


def cells_along(polyline: GeoJsonLineString, res: int = 9, ring: int = 1) -> set[str]:
    """Return the set of H3 cells the polyline crosses, buffered by ``ring``.

    Densifies edges to ~edge-length spacing so we don't skip cells on
    long polyline segments. Cheap enough at res 9 for a 300-mile route
    (~2-2.5K cells expected, per ROUTEWISE.md s5.2.3).
    """
    try:
        import h3
    except ImportError:
        logger.warning("h3 not installed; returning empty cell set")
        return set()

    cells: set[str] = set()
    edge_m = _edge_length_m(res)
    densify_step_m = max(edge_m * 0.7, 50.0)

    coords = polyline.coordinates
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        seg_m = _haversine_m(lat1, lon1, lat2, lon2)
        n = max(1, int(seg_m // densify_step_m))
        for i in range(n + 1):
            t = i / n if n else 0.0
            lat = lat1 + (lat2 - lat1) * t
            lon = lon1 + (lon2 - lon1) * t
            cells.add(h3.latlng_to_cell(lat, lon, res))

    if ring > 0:
        ringed: set[str] = set()
        for c in cells:
            ringed |= set(h3.grid_disk(c, ring))
        cells |= ringed

    return cells


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    p1, p2 = radians(lat1), radians(lat2)
    dp = p2 - p1
    dl = radians(lon2 - lon1)
    h = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * R * asin(sqrt(h))


def _edge_length_m(res: int) -> float:
    """Approx average H3 edge length per resolution."""
    table = {
        7: 1220.0,
        8: 461.0,
        9: 174.0,
        10: 65.0,
    }
    return table.get(res, 174.0)

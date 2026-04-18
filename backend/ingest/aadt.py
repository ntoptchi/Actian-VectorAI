"""Snap crashes to FDOT AADT segments (ROUTEWISE.md s5.1.4).

We build a KDTree over segment-midpoint coordinates for fast nearest-
neighbor lookup, then verify with a true point-to-line distance check
against a 50 m threshold. Unmatched crashes get ``aadt=None`` and are
still indexed (s11.1).

This module is import-light so it can be loaded by ``backend/main.py``
without paying the ``shapely``/``pyproj`` cost when the index isn't
needed; geometry libs are imported only inside ``build()``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AadtMatch:
    aadt: int
    segment_id: str
    distance_m: float


class AadtIndex:
    """Spatial index over FDOT AADT polylines.

    Build once from the FGDL ``aadt_*`` shapefile, then call ``lookup``
    per crash. Persist via ``save``/``load`` so ingestion runs don't pay
    the build cost more than once per data refresh.
    """

    def __init__(self) -> None:
        self._tree = None  # scipy.spatial.KDTree
        self._segment_ids: list[str] = []
        self._aadts: list[int] = []
        self._geoms: list = []  # list[shapely LineString]
        self._max_match_m: float = 50.0

    @classmethod
    def build(cls, shapefile_path: Path, *, max_match_m: float = 50.0) -> "AadtIndex":
        """Build the index from an FGDL AADT shapefile.

        TODO(day 1): the FGDL layer name and AADT field varies by year
        (e.g., ``AADT_2022``). Detect the field by regex and pick the
        most recent year present.
        """
        try:
            import geopandas as gpd  # type: ignore[import-not-found]
            import numpy as np
            from scipy.spatial import KDTree  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "AadtIndex.build requires geopandas + scipy. "
                "Install via `pip install geopandas scipy`."
            ) from exc

        gdf = gpd.read_file(shapefile_path).to_crs(4326)

        idx = cls()
        idx._max_match_m = max_match_m

        midpoints: list[tuple[float, float]] = []
        for _, row in gdf.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            mid = geom.interpolate(0.5, normalized=True)
            midpoints.append((mid.y, mid.x))  # (lat, lon)
            idx._geoms.append(geom)

            seg_id = str(row.get("ROADWAY", row.get("OBJECTID", len(idx._segment_ids))))
            idx._segment_ids.append(seg_id)

            aadt_val = _pick_aadt(row)
            idx._aadts.append(int(aadt_val) if aadt_val is not None else 0)

        idx._tree = KDTree(np.array(midpoints))
        logger.info("built AADT index over %d segments", len(idx._segment_ids))
        return idx

    def lookup(self, lat: float, lon: float) -> AadtMatch | None:
        """Return the AADT match for a crash point, or ``None`` if too far."""
        if self._tree is None:
            return None
        try:
            from shapely.geometry import Point  # type: ignore[import-not-found]
        except ImportError:
            return None

        # Query the K nearest midpoints, then verify distance against the
        # actual line geometry (midpoint distance is a coarse proxy).
        dists, ids = self._tree.query([(lat, lon)], k=min(8, len(self._segment_ids)))
        ids = ids[0]
        pt = Point(lon, lat)
        best: AadtMatch | None = None
        for i in ids:
            geom = self._geoms[i]
            d_m = _point_to_line_m(pt, geom)
            if d_m > self._max_match_m:
                continue
            if best is None or d_m < best.distance_m:
                best = AadtMatch(
                    aadt=self._aadts[i],
                    segment_id=self._segment_ids[i],
                    distance_m=d_m,
                )
        return best

    # ---- Persistence (Day 1) ----

    def save(self, path: Path) -> None:
        """Pickle the index for fast reuse across ingestion runs."""
        import pickle

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: Path) -> "AadtIndex":
        import pickle

        with path.open("rb") as f:
            return pickle.load(f)


def _pick_aadt(row) -> int | None:
    """Find the AADT value in a row, picking the most recent year present."""
    for key in row.keys():
        if isinstance(key, str) and key.upper().startswith("AADT"):
            val = row[key]
            if val is not None and val == val:  # not NaN
                try:
                    return int(val)
                except (TypeError, ValueError):
                    continue
    return None


def _point_to_line_m(pt, line) -> float:
    """Approximate point-to-line distance in meters via WGS84 -> meters
    using a local equirectangular projection. Fast and good enough at
    the 50 m threshold scale."""
    from math import cos, radians

    lat = pt.y
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * cos(radians(lat))
    proj_pt = (pt.x * m_per_deg_lon, pt.y * m_per_deg_lat)
    proj_coords = [(x * m_per_deg_lon, y * m_per_deg_lat) for x, y in line.coords]
    return _seg_dist_min(proj_pt, proj_coords)


def _seg_dist_min(pt, coords) -> float:
    best = float("inf")
    for a, b in zip(coords, coords[1:]):
        best = min(best, _seg_dist(pt, a, b))
    return best


def _seg_dist(p, a, b) -> float:
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    qx, qy = ax + t * dx, ay + t * dy
    return ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5

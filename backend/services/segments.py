"""Per-route segment slicing + AADT enrichment.

The chosen route gets sliced into ~40 equal-length segments. Each
segment is associated with a set of H3 cells (used by the scoring
service to bucket retrieved crashes back onto the line) and gets an
AADT estimate by intersecting its geometry with the FDOT AADT
shapefile, when available.

The shapefile load is module-cached so repeated /trip/brief calls
don't re-read 10MB of geometry.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

from backend.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SegmentGeom:
    """A sliced piece of route geometry, before risk scoring."""

    segment_id: str
    polyline: list[list[float]]  # [[lon, lat], ...]
    from_km: float
    to_km: float
    cells: set[str]
    aadt: int | None = None
    speed_limit_mph: int | None = None


# --- AADT shapefile cache --------------------------------------------------

_AADT_LOCK = threading.Lock()
_AADT_GDF = None  # geopandas.GeoDataFrame | None
_AADT_LOADED = False  # tri-state: not-loaded / loaded / load-failed


def _load_aadt_gdf():  # type: ignore[no-untyped-def]
    """Load the AADT shapefile once per process; return ``None`` on failure.

    The shapefile lives at ``data/raw/aadt/aadt.shp`` (per the user's
    data drop). We reproject to WGS84 so segment lon/lat queries match.
    """
    global _AADT_GDF, _AADT_LOADED
    if _AADT_LOADED:
        return _AADT_GDF
    with _AADT_LOCK:
        if _AADT_LOADED:
            return _AADT_GDF
        _AADT_LOADED = True
        try:
            import geopandas as gpd  # type: ignore[import-not-found]
        except ImportError as exc:
            logger.warning("geopandas unavailable, segments will skip AADT: %s", exc)
            return None
        shp = get_settings().raw_dir / "aadt" / "aadt.shp"
        if not shp.exists():
            logger.warning("AADT shapefile missing at %s; AADT will be None", shp)
            return None
        try:
            gdf = gpd.read_file(shp).to_crs(4326)
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to read AADT shapefile: %s", exc)
            return None
        # Normalise the AADT column. The FGDL shapefile uses ``AADT`` but
        # we also accept ``AADT_2025``-style names defensively.
        aadt_col = next(
            (c for c in gdf.columns if isinstance(c, str) and c.upper().startswith("AADT")
             and c != "AADTFLG"),
            None,
        )
        if aadt_col is None:
            logger.warning("no AADT column in shapefile (cols: %s)", list(gdf.columns)[:20])
            return None
        gdf = gdf[[aadt_col, "geometry"]].rename(columns={aadt_col: "_aadt"})
        gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
        # Pre-build a spatial index for fast bbox queries.
        try:
            gdf.sindex  # noqa: B018  - touch to trigger build
        except Exception:  # noqa: BLE001
            pass
        _AADT_GDF = gdf
        logger.info("loaded AADT shapefile: %d segments", len(gdf))
        return _AADT_GDF


# --- Slicing --------------------------------------------------------------


def slice_route(
    polyline: list[list[float]],
    *,
    target_segments: int = 40,
    h3_res: int = 9,
    h3_ring: int = 1,
) -> list[SegmentGeom]:
    """Slice a polyline into ~``target_segments`` equal-length pieces.

    Each segment carries the H3 cells it covers (resolution 9 by
    default, buffered by ``h3_ring`` so crashes just off the polyline
    still bucket in). Empty input yields an empty list.
    """
    if not polyline or len(polyline) < 2:
        return []

    total_km = _polyline_km(polyline)
    if total_km <= 0:
        return []

    n = max(1, min(target_segments, max(1, int(total_km // 0.5))))
    target_km_each = total_km / n

    segments: list[SegmentGeom] = []
    cur_seg: list[list[float]] = [polyline[0]]
    cur_seg_km = 0.0
    seg_start_km = 0.0
    cum_km = 0.0
    seg_idx = 0

    for (lon1, lat1), (lon2, lat2) in zip(polyline, polyline[1:]):
        edge_km = _haversine_km(lat1, lon1, lat2, lon2)
        # Walk along this edge, splitting at segment boundaries.
        remaining_in_edge = edge_km
        from_lon, from_lat = lon1, lat1
        while remaining_in_edge > 0:
            need = target_km_each - cur_seg_km
            if remaining_in_edge < need or seg_idx == n - 1:
                # Whole remaining edge fits in current segment.
                cur_seg.append([lon2, lat2])
                cur_seg_km += remaining_in_edge
                cum_km += remaining_in_edge
                remaining_in_edge = 0
            else:
                t = need / edge_km
                # Linear interp in lon/lat space; fine at segment scale.
                mid_lon = lon1 + (lon2 - lon1) * ((cum_km - seg_start_km + need) / edge_km - 0)  # noqa: E501
                mid_lat = lat1 + (lat2 - lat1) * ((cum_km - seg_start_km + need) / edge_km - 0)
                # Simpler interp from the *current* edge start:
                # how far have we already eaten into this edge?
                eaten = edge_km - remaining_in_edge
                frac = (eaten + need) / edge_km
                mid_lon = lon1 + (lon2 - lon1) * frac
                mid_lat = lat1 + (lat2 - lat1) * frac
                cur_seg.append([mid_lon, mid_lat])
                cum_km += need
                segments.append(
                    SegmentGeom(
                        segment_id=f"seg_{seg_idx:03d}",
                        polyline=cur_seg,
                        from_km=seg_start_km,
                        to_km=cum_km,
                        cells=_cells_for(cur_seg, h3_res, h3_ring),
                    )
                )
                seg_idx += 1
                seg_start_km = cum_km
                cur_seg = [[mid_lon, mid_lat]]
                cur_seg_km = 0.0
                remaining_in_edge -= need
                from_lon, from_lat = mid_lon, mid_lat

    if len(cur_seg) >= 2:
        segments.append(
            SegmentGeom(
                segment_id=f"seg_{seg_idx:03d}",
                polyline=cur_seg,
                from_km=seg_start_km,
                to_km=cum_km,
                cells=_cells_for(cur_seg, h3_res, h3_ring),
            )
        )

    return segments


def attach_aadt(segments: list[SegmentGeom]) -> None:
    """Mutate ``segments`` in place, attaching ``aadt`` per segment.

    Strategy: for each segment, build a shapely LineString, query the
    AADT GeoDataFrame's spatial index for nearby segments, and pick the
    closest with a non-zero AADT. Falls back to the FL state-route
    median (~12K) if no shapefile match is found, so downstream
    intensity ratios always have a denominator.
    """
    gdf = _load_aadt_gdf()
    if gdf is None or gdf.empty:
        for s in segments:
            if s.aadt is None:
                s.aadt = _FALLBACK_AADT
        return

    try:
        from shapely.geometry import LineString  # type: ignore[import-not-found]
    except ImportError:
        for s in segments:
            if s.aadt is None:
                s.aadt = _FALLBACK_AADT
        return

    sindex = getattr(gdf, "sindex", None)
    geoms = gdf.geometry.values
    aadt_vals = gdf["_aadt"].values

    for seg in segments:
        if len(seg.polyline) < 2:
            seg.aadt = _FALLBACK_AADT
            continue
        line = LineString(seg.polyline)
        candidates_idx: list[int]
        if sindex is not None:
            try:
                bbox = line.bounds  # (minx, miny, maxx, maxy)
                # Pad bbox by ~50m in degrees so adjacent AADT segments hit.
                pad = 0.0008
                candidates_idx = list(
                    sindex.intersection((bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad))
                )
            except Exception:  # noqa: BLE001
                candidates_idx = list(range(len(geoms)))
        else:
            candidates_idx = list(range(len(geoms)))

        best_aadt = None
        best_dist = float("inf")
        for i in candidates_idx[:200]:  # cap fan-out
            geom = geoms[i]
            try:
                d = line.distance(geom)
            except Exception:  # noqa: BLE001
                continue
            if d < best_dist and aadt_vals[i] and float(aadt_vals[i]) > 0:
                best_dist = d
                best_aadt = int(aadt_vals[i])

        seg.aadt = best_aadt if best_aadt is not None else _FALLBACK_AADT


# --- Helpers --------------------------------------------------------------


_FALLBACK_AADT = 12_000  # FL state-route median (rough; just a denominator)


def _cells_for(polyline: list[list[float]], res: int, ring: int) -> set[str]:
    """H3 cells covered by a polyline, buffered by ``ring`` neighbors.

    Densifies edges so we don't skip cells along long edges.
    """
    try:
        import h3
    except ImportError:
        return set()

    cells: set[str] = set()
    edge_m = {7: 1220.0, 8: 461.0, 9: 174.0, 10: 65.0}.get(res, 174.0)
    densify_m = max(edge_m * 0.7, 50.0)

    for (lon1, lat1), (lon2, lat2) in zip(polyline, polyline[1:]):
        seg_m = _haversine_km(lat1, lon1, lat2, lon2) * 1000
        n = max(1, int(seg_m // densify_m))
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


def _polyline_km(polyline: list[list[float]]) -> float:
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(polyline, polyline[1:]):
        total += _haversine_km(lat1, lon1, lat2, lon2)
    return total


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    p1, p2 = radians(lat1), radians(lat2)
    dp = p2 - p1
    dl = radians(lon2 - lon1)
    h = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * R * asin(sqrt(h))

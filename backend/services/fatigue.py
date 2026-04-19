"""Fatigue + rest-stop planner.

Rule-based: aim for stops at ~2h and ~3.5h into the trip, snapped to the
nearest known FL highway service plaza or rest area. Hard-coded lookup
table is fine — the corpus is small and v1 is FL-only (s8.1).
"""

from __future__ import annotations

from datetime import timedelta
from typing import NamedTuple

from backend.schemas import FatiguePlan, FatigueStop, Route


class _Plaza(NamedTuple):
    label: str
    lat: float
    lon: float


# Seed list of FL interstate service plazas / rest areas; expand on Day 3.
FL_PLAZAS: list[_Plaza] = [
    _Plaza("Pompano Beach Service Plaza (FL Turnpike)", 26.2354, -80.1431),
    _Plaza("West Palm Beach Service Plaza (FL Turnpike)", 26.7100, -80.1233),
    _Plaza("Fort Drum Service Plaza (FL Turnpike)", 27.5300, -80.7800),
    _Plaza("Canoe Creek Service Plaza (FL Turnpike)", 28.1700, -81.1900),
    _Plaza("Turkey Lake Service Plaza (FL Turnpike)", 28.4640, -81.4710),
    _Plaza("Okahumpka Service Plaza (FL Turnpike)", 28.7240, -81.9070),
    # I-75
    _Plaza("Naples-Collier Service Plaza (I-75)", 26.3500, -81.4000),
    _Plaza("Punta Gorda Rest Area (I-75)", 26.9000, -81.9500),
    # I-10
    _Plaza("Madison Rest Area (I-10)", 30.4900, -83.4500),
    _Plaza("Holmes County Rest Area (I-10)", 30.8200, -85.8900),
    # I-95
    _Plaza("St. Lucie West Rest Area (I-95)", 27.3500, -80.4000),
    _Plaza("Brevard County Rest Area (I-95)", 28.4500, -80.7800),
]


def plan(route: Route) -> FatiguePlan:
    """Compose a fatigue plan keyed off total driving duration."""
    total_minutes = int(route.duration_s // 60)
    stops: list[FatigueStop] = []

    # Only suggest stops on trips long enough to need them (>2h).
    if total_minutes >= 120:
        targets_min = [120]
        if total_minutes >= 210:
            targets_min.append(210)
        if total_minutes >= 300:
            targets_min.append(300)

        seen_labels: set[str] = set()
        for target in targets_min:
            km_into = (target / total_minutes) * (route.distance_m / 1000.0)
            eta = route.departure_iso + timedelta(minutes=target)
            label = _nearest_plaza_label(route, km_into)
            # Drop duplicates: when the route runs out of seeded plazas
            # (e.g. west of Holmes County on I-10) every "nearest plaza"
            # snaps to the same label, which read as a UX bug in QA
            # ("Holmes County Rest Area" listed twice). Skip the second
            # occurrence rather than confidently lying about a phantom
            # second stop.
            if label in seen_labels:
                continue
            seen_labels.add(label)
            stops.append(FatigueStop(label=label, km_into_trip=km_into, eta_iso=eta))

    return FatiguePlan(total_drive_minutes=total_minutes, suggested_stops=stops)


def _nearest_plaza_label(route: Route, km_into: float) -> str:
    """Pick the closest seeded plaza to the polyline at km_into.

    TODO(day 3): real point-along-polyline interpolation; currently uses
    a coarse proportional vertex pick, which is fine for the briefing.
    """
    coords = route.polyline_geojson.coordinates
    if not coords:
        return "Suggested stop"
    total_km = max(route.distance_m / 1000.0, 1e-6)
    frac = max(0.0, min(1.0, km_into / total_km))
    idx = int(frac * (len(coords) - 1))
    target_lon, target_lat = coords[idx][0], coords[idx][1]

    best = min(
        FL_PLAZAS,
        key=lambda p: (p.lat - target_lat) ** 2 + (p.lon - target_lon) ** 2,
        default=None,
    )
    return best.label if best else "Suggested stop"

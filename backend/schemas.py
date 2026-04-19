"""Pydantic schemas for RouteWise.

Defines the canonical ``SituationDoc`` (ROUTEWISE.md s6.1) used for both
indexed crashes and query construction, plus the request/response models
for ``POST /trip/brief`` and ``GET /hotspots/{id}`` (ROUTEWISE.md s6.3).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# --- Vocabulary types (kept narrow on purpose; see s6.1) -------------------

RoadType = Literal[
    "interstate",
    "us_highway",
    "state_route",
    "arterial",
    "ramp",
    "local",
    "unknown",
]

Weather = Literal[
    "clear",
    "rain",
    "snow",
    "fog",
    "sleet",
    "severe_wind",
    "unknown",
]

Lighting = Literal["daylight", "dawn_dusk", "dark_lighted", "dark_unlighted"]

Surface = Literal["dry", "wet", "icy", "snowy", "unknown"]

CrashType = Literal[
    "rear_end",
    "head_on",
    "angle",
    "sideswipe_same",
    "sideswipe_opp",
    "rollover",
    "single_vehicle",
    "pedestrian",
    "bicycle",
    "other",
    "unknown",
]

Severity = Literal["fatal", "serious", "minor", "pdo", "unknown"]

Source = Literal["FARS", "CISS", "FDOT"]


# --- SituationDoc -----------------------------------------------------------


class SituationDoc(BaseModel):
    """Unified crash record used at both index time and query time.

    Identity / location / outcome / narrative fields are populated only
    on indexed docs (real crashes). The query-time construction uses
    only environmental + temporal fields, so the rest are Optional.
    """

    model_config = ConfigDict(populate_by_name=True)

    # Identity (indexed only)
    source: Source | None = None
    case_id: str | None = None
    state: str | None = None
    county: str | None = None

    # Location (indexed only)
    lat: float | None = None
    lon: float | None = None
    h3_cell: str | None = None
    road_type: RoadType = "unknown"
    road_function: str | None = None
    speed_limit_mph: int | None = None

    # Exposure (indexed only)
    aadt: int | None = None
    aadt_segment_id: str | None = None

    # Time (both)
    timestamp: datetime | None = None
    hour_bucket: int = Field(0, ge=0, le=23)
    day_of_week: int = Field(0, ge=0, le=6)
    month: int = Field(1, ge=1, le=12)

    # Environmental state (both — what the query carries)
    weather: Weather = "unknown"
    precipitation_mm_hr: float | None = None
    visibility_m: float | None = None
    lighting: Lighting = "daylight"
    surface: Surface = "unknown"

    # Outcome (indexed only)
    crash_type: CrashType | None = None
    num_vehicles: int | None = None
    num_injuries: int | None = None
    num_fatalities: int | None = None
    severity: Severity = "unknown"

    # Narrative (indexed only)
    has_narrative: bool = False
    narrative: str = ""


# --- Request / response models for /trip/brief (s6.3) ----------------------


class LatLon(BaseModel):
    lat: float
    lon: float


class TripBriefRequest(BaseModel):
    origin: LatLon
    destination: LatLon
    timestamp: datetime | None = None  # defaults to "now" server-side


class GeoJsonLineString(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: list[list[float]]  # [[lon, lat], ...]


class Route(BaseModel):
    polyline_geojson: GeoJsonLineString
    distance_m: float
    duration_s: float
    departure_iso: datetime
    arrival_iso: datetime


class WeatherSegment(BaseModel):
    from_km: float
    to_km: float
    weather: str
    surface: Surface


class ConditionsBanner(BaseModel):
    summary: str
    weather_segments: list[WeatherSegment] = Field(default_factory=list)
    sunset_iso: datetime | None = None
    dark_drive_minutes: int = 0


class FatigueStop(BaseModel):
    label: str
    km_into_trip: float
    eta_iso: datetime


class FatiguePlan(BaseModel):
    total_drive_minutes: int
    suggested_stops: list[FatigueStop] = Field(default_factory=list)


class FactorWeight(BaseModel):
    factor: str
    fraction: float


class SeverityMix(BaseModel):
    fatal: int = 0
    serious: int = 0
    minor: int = 0
    pdo: int = 0
    unknown: int = 0


class HotspotSummary(BaseModel):
    """Inline hotspot card shown directly on the brief page."""

    hotspot_id: str
    label: str
    road_name: str | None
    centroid: LatLon
    km_into_trip: float
    n_crashes: int
    mean_similarity: float
    aadt: int | None
    intensity_ratio: float | None
    severity_mix: SeverityMix
    top_factors: list[FactorWeight] = Field(default_factory=list)
    coaching_line: str


# --- Routing pivot: per-segment risk + alternates --------------------------


RiskBand = Literal["low", "moderate", "elevated", "high"]


class RouteSegment(BaseModel):
    """One sliced piece of the chosen route, scored independently.

    The ``polyline`` is the segment's geometry (always a list of
    ``[lon, lat]`` pairs so the frontend can paint it directly with
    Leaflet). Risk fields are populated from VDB-retrieved crashes
    intersected with the segment's H3 cells.
    """

    segment_id: str
    polyline: list[list[float]]
    from_km: float
    to_km: float
    aadt: int | None = None
    speed_limit_mph: int | None = None
    n_crashes: int = 0
    intensity_ratio: float | None = None
    risk_band: RiskBand = "low"
    top_factors: list[FactorWeight] = Field(default_factory=list)
    night_skewed: bool = False


class AlternateSummary(BaseModel):
    """One ORS-suggested route alternative, scored end-to-end.

    Frontend uses these to render the "+3 min, -38% risk" deltas in the
    alternates panel; the chosen route is identified by
    ``TripBriefResponse.chosen_route_id``.
    """

    route_id: str
    polyline: list[list[float]]
    distance_m: float
    duration_s: float
    risk_score: float
    risk_band: RiskBand
    n_crashes: int
    minutes_delta_vs_fastest: float
    risk_delta_vs_fastest: float


class TripBriefResponse(BaseModel):
    trip_id: str
    route: Route
    conditions_banner: ConditionsBanner
    fatigue_plan: FatiguePlan
    sunset_during_trip: bool = False
    hotspots: list[HotspotSummary] = Field(default_factory=list)
    pre_trip_checklist: list[str] = Field(default_factory=list)

    # Pivot additions: candidate-and-rerank + per-segment risk on the map.
    chosen_route_id: str | None = None
    alternates: list[AlternateSummary] = Field(default_factory=list)
    segments: list[RouteSegment] = Field(default_factory=list)


# --- /hotspots/{id} response (s6.3) ----------------------------------------


class HotspotSummaryDetail(BaseModel):
    n_crashes: int
    mean_similarity: float
    aadt: int | None
    intensity_ratio: float | None
    severity_mix: SeverityMix
    top_factors: list[FactorWeight] = Field(default_factory=list)


class CrashExcerpt(BaseModel):
    crash_id: str
    source: Source
    similarity: float
    when: datetime | None
    severity: Severity
    snippet: str


class HotspotDetailResponse(BaseModel):
    hotspot_id: str
    label: str
    road_name: str | None
    centroid: LatLon
    summary: HotspotSummaryDetail
    coaching_line: str
    excerpts: list[CrashExcerpt] = Field(default_factory=list)

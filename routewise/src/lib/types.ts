// TypeScript mirror of backend/schemas.py response models.
// Hand-maintained for now; small surface. Keep in sync with
// backend/schemas.py if you change the Python side.

export interface LatLon {
  lat: number;
  lon: number;
}

export interface GeoJsonLineString {
  type: "LineString";
  coordinates: [number, number][]; // [lon, lat]
}

export interface Route {
  polyline_geojson: GeoJsonLineString;
  distance_m: number;
  duration_s: number;
  departure_iso: string;
  arrival_iso: string;
}

export interface WeatherSegment {
  from_km: number;
  to_km: number;
  weather: string;
  surface: "dry" | "wet" | "icy" | "snowy" | "unknown";
}

export interface ConditionsBanner {
  summary: string;
  weather_segments: WeatherSegment[];
  sunset_iso: string | null;
  dark_drive_minutes: number;
}

export interface FatigueStop {
  label: string;
  km_into_trip: number;
  eta_iso: string;
}

export interface FatiguePlan {
  total_drive_minutes: number;
  suggested_stops: FatigueStop[];
}

export interface FactorWeight {
  factor: string;
  fraction: number;
}

export interface SeverityMix {
  fatal: number;
  serious: number;
  minor: number;
  pdo: number;
  unknown: number;
}

export interface HotspotSummary {
  hotspot_id: string;
  label: string;
  road_name: string | null;
  centroid: LatLon;
  km_into_trip: number;
  n_crashes: number;
  mean_similarity: number;
  aadt: number | null;
  intensity_ratio: number | null;
  severity_mix: SeverityMix;
  top_factors: FactorWeight[];
  coaching_line: string;
}

export interface TripBriefRequest {
  origin: LatLon;
  destination: LatLon;
  timestamp?: string | null;
}

export interface TripBriefResponse {
  trip_id: string;
  route: Route;
  conditions_banner: ConditionsBanner;
  fatigue_plan: FatiguePlan;
  sunset_during_trip: boolean;
  hotspots: HotspotSummary[];
  pre_trip_checklist: string[];
}

export interface CrashExcerpt {
  crash_id: string;
  source: "FARS" | "CISS" | "FDOT";
  similarity: number;
  when: string | null;
  severity: "fatal" | "serious" | "minor" | "pdo" | "unknown";
  snippet: string;
}

export interface HotspotDetailResponse {
  hotspot_id: string;
  label: string;
  road_name: string | null;
  centroid: LatLon;
  summary: {
    n_crashes: number;
    mean_similarity: number;
    aadt: number | null;
    intensity_ratio: number | null;
    severity_mix: SeverityMix;
    top_factors: FactorWeight[];
  };
  coaching_line: string;
  excerpts: CrashExcerpt[];
}

"""Per-source adapters: raw row -> :class:`SituationDoc`.

These are the *only* schema-aware code in the pipeline. Everything
downstream (embedding, AADT snap, VDB upsert) operates on
``SituationDoc`` and does not care which source the record came from.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from backend.schemas import (
    CrashType,
    Lighting,
    Severity,
    SituationDoc,
    Surface,
    Weather,
)

logger = logging.getLogger(__name__)


# --- Helpers shared by adapters --------------------------------------------


_HOUR_FIX = {99: 0, 88: 0, 77: 0}


def safe_int(v: Any, default: int = 0) -> int:
    try:
        i = int(v)
    except (TypeError, ValueError):
        return default
    return _HOUR_FIX.get(i, i)


def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _h3_cell(lat: float | None, lon: float | None, res: int = 9) -> str | None:
    if lat is None or lon is None:
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    if lat == 0 and lon == 0:
        return None
    try:
        import h3
    except ImportError:
        return None
    return h3.latlng_to_cell(float(lat), float(lon), res)


# --- FDOT crash GeoJSON ---------------------------------------------------

# FDOT lighting code -> SituationDoc.Lighting
_FDOT_LIGHTING: dict[str, Lighting] = {
    "01": "daylight",
    "02": "dawn_dusk",
    "03": "dawn_dusk",
    "04": "dark_lighted",
    "05": "dark_unlighted",
    "06": "dark_lighted",
    "07": "dark_unlighted",
}

# FDOT weather code -> SituationDoc.Weather
_FDOT_WEATHER: dict[str, Weather] = {
    "01": "clear",
    "02": "clear",  # cloudy = clear-ish (no precip)
    "03": "rain",
    "04": "rain",  # heavy rain
    "05": "fog",
    "06": "sleet",
    "07": "snow",
    "08": "severe_wind",
    "09": "severe_wind",  # smoke / blowing dust
}

# FDOT road-surface code -> SituationDoc.Surface
_FDOT_SURFACE: dict[str, Surface] = {
    "01": "dry",
    "02": "wet",
    "03": "wet",  # standing water
    "04": "icy",
    "05": "snowy",
    "06": "snowy",  # slush
}

# FDOT first harm / collision -> SituationDoc.CrashType (best-effort)
_FDOT_FIRST_HARM_TO_CRASHTYPE: dict[str, CrashType] = {
    "01": "rear_end",
    "02": "head_on",
    "03": "angle",
    "04": "sideswipe_same",
    "05": "sideswipe_opp",
    "06": "rollover",
    "07": "single_vehicle",
}

# FDOT INJSEVER -> Severity
# 1=PDO, 2=Possible, 3=Non-Incapacitating, 4=Incapacitating, 5=Fatal
_FDOT_INJSEVER: dict[str, Severity] = {
    "1": "pdo",
    "2": "minor",
    "3": "minor",
    "4": "serious",
    "5": "fatal",
}


def from_fdot_crash_row(row: dict[str, Any]) -> SituationDoc | None:
    """Map one FDOT crash GeoJSON feature (already flattened by caller)
    into a :class:`SituationDoc`.

    The caller is expected to attach ``__lat`` / ``__lon`` from the
    feature geometry before calling. We also fall back to FDOT's own
    ``LATITUDE`` / ``LONGITUDE`` fields if geometry is absent.

    Returns ``None`` when the row has no usable lat/lon.
    """
    lat = row.get("__lat")
    lon = row.get("__lon")
    if lat is None or lon is None:
        lat = row.get("LATITUDE")
        lon = row.get("LONGITUDE")
    try:
        lat_f = float(lat) if lat is not None else None
        lon_f = float(lon) if lon is not None else None
    except (TypeError, ValueError):
        return None
    if lat_f is None or lon_f is None or lat_f == 0 or lon_f == 0:
        # FDOT often stores 0,0 for crashes without precise coords.
        return None

    case_id = _safe_str(row.get("CRASH_NUMBER")) or _safe_str(row.get("OBJECTID"))
    if not case_id:
        return None

    # Time. CRASH_DATE is epoch ms in the FDOT export; CRASH_TIME is "HHMM".
    # ~12.5% of FDOT rows have empty/0000 CRASH_TIME, which previously got
    # silently bucketed to hour=00 — that polluted the corpus with a fake
    # "midnight is 5x more dangerous" signal that wrecked the
    # time-of-day similarity search at query time. We now drop the row
    # outright when the time is unknown, since hour-of-day is a
    # first-class feature of the SituationDoc embedding.
    timestamp = _parse_fdot_datetime(row.get("CRASH_DATE"), row.get("CRASH_TIME"))
    if timestamp is None:
        return None
    hour = timestamp.hour
    dow = timestamp.weekday()
    month = timestamp.month

    weather = _FDOT_WEATHER.get(_safe_str(row.get("EVNT_WTHR_COND_CD")), "unknown")
    lighting = _FDOT_LIGHTING.get(_safe_str(row.get("LGHT_COND_CD")), "daylight")
    surface = _FDOT_SURFACE.get(_safe_str(row.get("RD_SRFC_COND_CD")), "unknown")
    crash_type = _FDOT_FIRST_HARM_TO_CRASHTYPE.get(
        _safe_str(row.get("FRST_HARM_LOC_CD")), "other"
    )
    severity = _FDOT_INJSEVER.get(_safe_str(row.get("INJSEVER")), "unknown")

    # Road type from STATE_ROAD_NUMBER / US_ROAD_NUMBER / FUNCLASS
    road_type = _fdot_road_type(row)

    aadt = row.get("AVERAGE_DAILY_TRAFFIC")
    try:
        aadt_int = int(aadt) if aadt is not None else None
    except (TypeError, ValueError):
        aadt_int = None
    speed = row.get("SPEED_LIMIT")
    try:
        speed_int = int(speed) if speed is not None else None
    except (TypeError, ValueError):
        speed_int = None

    county = _safe_str(row.get("COUNTY_TXT")).title() or None

    return SituationDoc(
        source="FDOT",
        case_id=case_id,
        state="FL",
        county=county,
        lat=lat_f,
        lon=lon_f,
        h3_cell=_h3_cell(lat_f, lon_f),
        road_type=road_type,
        speed_limit_mph=speed_int,
        aadt=aadt_int,
        aadt_segment_id=_safe_str(row.get("ROADWAYID")) or None,
        timestamp=timestamp,
        hour_bucket=hour,
        day_of_week=dow,
        month=month,
        weather=weather,
        lighting=lighting,
        surface=surface,
        crash_type=crash_type,
        num_vehicles=safe_int(row.get("NUMBER_OF_VEHICLES")) or None,
        num_injuries=safe_int(row.get("NUMBER_OF_INJURED")) or None,
        num_fatalities=safe_int(row.get("NUMBER_OF_KILLED")) or None,
        severity=severity,
        has_narrative=False,
        narrative="",
    )


def _fdot_road_type(row: dict[str, Any]):
    sr = _safe_str(row.get("STATE_ROAD_NUMBER"))
    us = _safe_str(row.get("US_ROAD_NUMBER"))
    funclass = _safe_str(row.get("FUNCLASS"))
    if sr.upper().startswith(("I-", "I ", "I7", "I9", "I1")):
        return "interstate"
    # FUNCLASS 11/12 = interstate, 14/16 = arterial, 17 = local (rough)
    if funclass in {"01", "11", "12"}:
        return "interstate"
    if us:
        return "us_highway"
    if sr:
        return "state_route"
    if funclass in {"14", "16"}:
        return "arterial"
    if funclass in {"17", "19"}:
        return "local"
    return "unknown"


def _parse_fdot_datetime(date_ms, time_hhmm) -> datetime | None:
    """Combine FDOT's epoch-ms CRASH_DATE with HHMM CRASH_TIME.

    Returns ``None`` when either piece is missing or unparseable, *or*
    when CRASH_TIME is the FDOT "no time recorded" sentinel ("0000",
    empty string, "00:00", etc.). Callers treat ``None`` as "unknown
    timestamp" and drop the row so the embedding's hour signal stays
    clean. (The previous version silently clamped unknown times to
    midnight, which over-represented hour=00 by ~5x in the corpus.)
    """
    if date_ms is None or time_hhmm is None:
        return None
    s = _safe_str(time_hhmm).replace(":", "").zfill(4)
    if not s or s == "0000":
        return None
    try:
        h = int(s[:2])
        m = int(s[2:4])
    except ValueError:
        return None
    if not (0 <= h < 24) or not (0 <= m < 60):
        return None
    try:
        ts = float(date_ms) / 1000.0
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None
    return dt.replace(hour=h, minute=m, second=0, microsecond=0)


# --- FARS (NHTSA) ---------------------------------------------------------


_FARS_WEATHER: dict[int, Weather] = {
    1: "clear",
    2: "rain",
    3: "sleet",
    4: "snow",
    5: "fog",
    6: "severe_wind",
    7: "severe_wind",  # blowing snow
    8: "clear",  # other - default to clear
    10: "rain",
    11: "rain",  # blowing snow with rain
    12: "rain",  # freezing rain or drizzle
}

_FARS_LIGHTING: dict[int, Lighting] = {
    1: "daylight",
    2: "dark_unlighted",
    3: "dark_lighted",
    4: "dawn_dusk",
    5: "dawn_dusk",
    6: "dark_unlighted",
}

_FARS_MANCOLL: dict[int, CrashType] = {
    0: "single_vehicle",
    1: "rear_end",
    2: "head_on",
    6: "angle",
    7: "sideswipe_same",
    8: "sideswipe_opp",
    9: "single_vehicle",
    10: "single_vehicle",
    11: "single_vehicle",
}


def from_fars_row(accident_row: dict[str, Any]) -> SituationDoc | None:
    """Map one FARS ``accident.csv`` row to :class:`SituationDoc`.

    Caller is expected to filter rows by STATE==12 (Florida) before
    invoking; we don't re-filter here. Returns ``None`` for rows
    without usable lat/lon (the FARS sentinel values 77/88/99).
    """
    try:
        lat = float(accident_row.get("LATITUDE", 0) or 0)
        lon = float(accident_row.get("LONGITUD", 0) or 0)
    except (TypeError, ValueError):
        return None
    # FARS uses 77.7777, 88.8888, 99.9999 as sentinels for unknown.
    if lat in {0.0, 77.7777, 88.8888, 99.9999} or lon in {
        0.0, 77.7777, 88.8888, 99.9999, -77.7777, -88.8888, -99.9999
    }:
        return None
    if not (24 <= lat <= 31.5 and -88 <= lon <= -79):
        # Bounding-box sanity check for Florida.
        return None

    case_id = _safe_str(accident_row.get("ST_CASE"))
    if not case_id:
        return None

    hour = safe_int(accident_row.get("HOUR"))
    dow = safe_int(accident_row.get("DAY_WEEK"))
    # FARS DAY_WEEK is 1=Sunday..7=Saturday; SituationDoc uses 0=Mon..6=Sun.
    if 1 <= dow <= 7:
        dow = (dow - 2) % 7
    else:
        dow = 0
    month = safe_int(accident_row.get("MONTH")) or 1

    timestamp: datetime | None = None
    year = safe_int(accident_row.get("YEAR")) or 0
    day = safe_int(accident_row.get("DAY")) or 0
    if year and day and 1 <= month <= 12 and 1 <= day <= 31:
        try:
            timestamp = datetime(
                year, month, day,
                min(hour, 23) if 0 <= hour <= 23 else 0,
                tzinfo=timezone.utc,
            )
        except ValueError:
            timestamp = None

    weather = _FARS_WEATHER.get(safe_int(accident_row.get("WEATHER")), "unknown")
    lighting = _FARS_LIGHTING.get(
        safe_int(accident_row.get("LGT_COND")), "daylight"
    )
    crash_type = _FARS_MANCOLL.get(
        safe_int(accident_row.get("MAN_COLL")), "other"
    )

    return SituationDoc(
        source="FARS",
        case_id=f"FARS-{year}-{case_id}",
        state="FL",
        county=_safe_str(accident_row.get("COUNTYNAME")) or None,
        lat=lat,
        lon=lon,
        h3_cell=_h3_cell(lat, lon),
        road_type="unknown",  # FARS ROUTE encoding is coarse; leave for now
        speed_limit_mph=None,
        aadt=None,  # filled by attach_aadt.py
        aadt_segment_id=None,
        timestamp=timestamp,
        hour_bucket=hour if 0 <= hour <= 23 else 0,
        day_of_week=dow,
        month=month,
        weather=weather,
        lighting=lighting,
        surface="unknown",  # FARS doesn't have surface as standalone
        crash_type=crash_type,
        num_vehicles=safe_int(accident_row.get("VE_TOTAL")) or None,
        num_injuries=None,
        num_fatalities=safe_int(accident_row.get("FATALS")) or None,
        severity="fatal",
        has_narrative=False,
        narrative="",
    )


# --- CISS placeholder -----------------------------------------------------


def from_ciss_case(case: dict[str, Any]) -> SituationDoc | None:
    """CISS ingestion is descoped for the hackathon — see ROUTEWISE.md s8.4."""
    return None

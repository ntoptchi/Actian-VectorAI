"""Per-source adapters: raw row -> :class:`SituationDoc`.

These are the *only* schema-aware code in the pipeline. Everything
downstream (embedding, AADT snap, VDB upsert) operates on
``SituationDoc`` and does not care which source the record came from.

Day-1 work is filling the bodies; the docstrings here are the field-
mapping plan.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.schemas import SituationDoc

logger = logging.getLogger(__name__)


# --- FARS (NHTSA) ----------------------------------------------------------


def from_fars_row(accident_row: dict[str, Any]) -> SituationDoc | None:
    """Map one FARS ``accident.csv`` row to :class:`SituationDoc`.

    Field plan (from FARS Analytical User's Manual):
      - ``ST_CASE``       -> case_id
      - ``STATE`` (==12)  -> state="FL"  (FL filter applied upstream)
      - ``COUNTY``        -> county (numeric FIPS; resolve later)
      - ``LATITUDE``,``LONGITUD`` -> lat/lon (drop 77/88/99 sentinels)
      - ``HOUR``,``DAY_WEEK``,``MONTH`` -> hour_bucket/day_of_week/month
      - ``WEATHER`` (1=clear, 2=rain, 3=sleet, 4=snow, 5=fog, ...)
        -> weather (mapping table)
      - ``LGT_COND`` -> lighting (1 daylight, 2 dark not lighted, 3 dark
        lighted, 4 dawn, 5 dusk -> dawn_dusk)
      - ``MAN_COLL`` -> crash_type (0 not collision, 1 rear-end, 2 head-on,
        ...)  via mapping table
      - ``ROUTE``,``RUR_URB`` -> road_type (1=interstate, 2=us_highway,
        3=state_route, ...)
      - severity = "fatal" (FARS is fatal-only)
      - num_vehicles = ``VE_TOTAL``; num_fatalities = ``FATALS``
      - has_narrative = False (FARS has no free text)
    """
    raise NotImplementedError("from_fars_row: see docstring for field plan (Day 1)")


# --- CISS (NHTSA Crash Investigation Sample) -------------------------------


def from_ciss_case(case: dict[str, Any]) -> SituationDoc | None:
    """Map one CISS case (header + scene + narrative joined) to a doc.

    Field plan (from CISS Coding Manual):
      - case_id = ``CASEID``
      - state = ``STATENUM`` -> 2-letter
      - lat/lon = scene coords; drop if missing
      - hour/day/month from ``HOUR``/``DAY_WEEK``/``MONTH``
      - weather = ``WEATHER`` (CISS uses similar coding to FARS)
      - lighting = ``LGTCON``
      - surface = ``SUR_COND`` (1 dry, 2 wet, 3 ice, 4 snow, ...)
      - crash_type = ``MANCOL``
      - severity from ``MAXSEV`` (4=fatal, 3=serious, 2=minor, ...)
      - has_narrative = True; narrative = the redacted investigator text
        (concatenate the SCENE / VEHICLE / OCCUPANT narrative blocks).
    """
    raise NotImplementedError("from_ciss_case: see docstring for field plan (Day 1)")


# --- FDOT Open Data (FL non-fatal crash layer) -----------------------------


def from_fdot_crash_row(row: dict[str, Any]) -> SituationDoc | None:
    """Map one FDOT crash-layer feature to a :class:`SituationDoc`.

    Field plan (FDOT Open Data Hub - Crash 2019 onward layer):
      - case_id = ``REPORTNUMBER`` (or ``OBJECTID``)
      - state = "FL"
      - county = ``COUNTYNAME``
      - lat/lon from feature.geometry
      - timestamp from ``CRASHDATETIME``
      - weather/lighting/surface from FDOT-coded fields (table in DOH)
      - crash_type from ``FIRSTHARMFULEVENT`` / ``MANNEROFCOLLISION``
      - severity from ``CRASHSEVERITY`` (K/A/B/C/O -> fatal/serious/minor/
        minor/pdo)
      - has_narrative = False
    """
    raise NotImplementedError(
        "from_fdot_crash_row: see docstring for field plan (Day 1)"
    )


# --- Helpers shared by adapters --------------------------------------------


_HOUR_FIX = {99: 0, 88: 0, 77: 0}


def safe_int(v: Any, default: int = 0) -> int:
    try:
        i = int(v)
    except (TypeError, ValueError):
        return default
    return _HOUR_FIX.get(i, i)

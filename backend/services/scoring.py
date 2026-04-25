"""VDB-driven safety scoring.

This is where the vector DB earns its keep:

  1. Build a *query* :class:`SituationDoc` from the trip's environmental
     conditions (weather, lighting, hour, ...). Embed it.
  2. For each route candidate, search the VDB for crashes that
     (a) match the query semantically and (b) have an ``h3_cell``
     filter that intersects any segment of this route.
  3. Bucket the retrieved crashes back onto segments by H3 cell.
  4. Per-segment risk = min(1.0, crashes / (aadt * exposure_factor)) —
     normalised against an FL baseline so the number means "X times the
     state average for a road of this AADT in conditions like these".
  5. Per-route risk = exposure-weighted mean of per-segment intensities.

Retrieval is wrapped in try/except: if the VDB is empty/down, every
score collapses to 0 and segments render as neutral. That's the
honesty test in s2.4 — the briefing degrades, the API doesn't 500.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime

from backend.embeddings import embed_one
from backend.ingest.situation_doc import render_narrative
from backend.schemas import (
    FactorWeight,
    LatLon,
    RiskBand,
    RouteSegment,
    SeverityMix,
    SituationDoc,
    WeatherSegment,
)
from backend.services.segments import SegmentGeom

logger = logging.getLogger(__name__)


# How many crashes to pull from the VDB per route. The retrieval is a
# single similarity search across the route's H3 cell union, so we
# need this to comfortably exceed (n_segments * crashes_per_segment).
# At 40 segments and a target of ~50 crashes per segment for a busy
# corridor, 2000 is the sweet spot — bigger pages cost more wire time
# but ensure dense corridors (Miami-Tampa) actually surface their
# hotspots instead of starving every segment to 1-2 hits.
TOP_K = 2000


# --- Query construction ---------------------------------------------------


def build_query_doc(
    *,
    departure: datetime,
    weather_segments: list[WeatherSegment],
    sunset_iso: datetime | None,
) -> SituationDoc:
    """Compose a conditions-only :class:`SituationDoc` for embedding.

    We pick the *first* weather segment as a coarse proxy — for the
    hackathon scope this is fine; per-segment weather queries would
    multiply embedding cost without meaningfully changing what surfaces.

    Hour-of-day is converted to *local* (Florida = Eastern) time before
    bucketing. The crash corpus stores hours in local time (FDOT's
    CRASH_TIME is local), so a UTC ``hour_bucket=21`` for a 5pm ET trip
    used to match against actual 9pm crashes — the embedding then
    flagged the trip as "night" and missed the rush-hour signal.
    """
    weather_label = "unknown"
    surface_label = "unknown"
    if weather_segments:
        weather_label = weather_segments[0].weather or "unknown"
        surface_label = weather_segments[0].surface or "unknown"

    try:
        from zoneinfo import ZoneInfo
        local = departure.astimezone(ZoneInfo("America/New_York"))
    except Exception:  # noqa: BLE001 — fall back to UTC if tzdata missing
        local = departure
    hour = local.hour
    is_dark = sunset_iso is not None and departure >= sunset_iso
    if is_dark:
        lighting = "dark_unlighted"
    elif 5 <= hour < 7 or 18 <= hour < 20:
        lighting = "dawn_dusk"
    else:
        lighting = "daylight"

    return SituationDoc(
        weather=weather_label if weather_label in {  # type: ignore[arg-type]
            "clear", "rain", "snow", "fog", "sleet", "severe_wind"
        } else "unknown",
        surface=surface_label if surface_label in {  # type: ignore[arg-type]
            "dry", "wet", "icy", "snowy"
        } else "unknown",
        lighting=lighting,  # type: ignore[arg-type]
        hour_bucket=hour,
        day_of_week=local.weekday(),
        month=local.month,
    )


# --- Retrieval -----------------------------------------------------------


_HOUR_WINDOW = 1  # ± hours kept around the trip's hour bucket


def retrieve_crashes_for_cells(
    cells: set[str],
    query_doc: SituationDoc,
    *,
    top_k: int = TOP_K,  # noqa: ARG001 — kept for API compat
) -> list[dict]:
    """Filter the in-memory crash corpus down to the route corridor.

    The Actian server in the dev environment doesn't implement payload
    indexes (``create_field_index`` returns 501), so any server-side
    filter on ``h3_cell`` does a sequential scan and times out around
    30 s — making the previous ``scroll(filter=...)`` path 90–160 s
    per request. We instead load the entire corpus into process memory
    once at startup (see :mod:`backend.services.crash_cache`) and do
    the filter as a pure Python comprehension; for 140K rows this is
    well under 100 ms.

    Two filters are applied in lock-step:
      * ``h3_cell IN cells`` — geographic corridor membership.
      * ``hour_bucket`` within ±2h of the trip's hour, wrapped mod 24,
        so 5pm pulls 3pm–7pm crashes (rush peak) and 3am pulls
        1am–5am (genuinely sparse). Without this both times return
        the same corridor-wide set and the user can't tell rush hour
        from the dead of night.
    """
    if not cells:
        return []

    cell_set = cells if isinstance(cells, set) else set(cells)
    hours_in_window = {
        (query_doc.hour_bucket + delta) % 24
        for delta in range(-_HOUR_WINDOW, _HOUR_WINDOW + 1)
    }

    try:
        from backend.services.crash_cache import get_crashes
    except Exception as exc:  # noqa: BLE001
        logger.warning("crash_cache import failed: %s", exc)
        return []

    try:
        corpus = get_crashes()
    except Exception as exc:  # noqa: BLE001
        logger.warning("crash_cache load failed: %s", exc)
        return []

    out: list[dict] = []
    for payload in corpus:
        if payload.get("h3_cell") not in cell_set:
            continue
        if payload.get("hour_bucket") not in hours_in_window:
            continue
        out.append({"score": 0.0, "payload": payload})

    logger.info(
        "retrieved %d crashes across %d H3 cells (in-memory filter)",
        len(out), len(cell_set),
    )
    return out


# --- Scoring -------------------------------------------------------------


def score_segments(
    segs: list[SegmentGeom],
    crashes: list[dict],
) -> list[RouteSegment]:
    """Bucket crashes onto segments by H3 cell and compute per-segment risk.

    Returns one :class:`RouteSegment` per input segment, in the same
    order. Empty inputs produce empty outputs.
    """
    # Cell -> list of segment indexes that contain it. Used to bucket
    # each crash onto every segment whose H3 ring covers it. (A crash
    # near a segment boundary may bucket into both, which is the right
    # behaviour for visualisation.)
    cell_to_segs: dict[str, list[int]] = {}
    for i, seg in enumerate(segs):
        for cell in seg.cells:
            cell_to_segs.setdefault(cell, []).append(i)

    seg_crashes: list[list[dict]] = [[] for _ in segs]
    for cr in crashes:
        cell = (cr.get("payload") or {}).get("h3_cell")
        if not cell:
            continue
        for idx in cell_to_segs.get(cell, []):
            seg_crashes[idx].append(cr)

    # Route-relative intensity: each segment's crash density compared to
    # the *route's own* mean density. The previous absolute-vs-FL-census
    # ratio collapsed to ~0.001x on every segment (the FDOT corpus is a
    # 50K-row sample, not the full census the baseline assumes). Switching
    # to a relative ratio surfaces the meaningful signal — "this segment
    # has 3x the crashes of an average mile of this trip" — which is what
    # the briefing UI actually wants to highlight.
    densities: list[float] = []
    exposure_densities: list[float] = []
    for seg, crs in zip(segs, seg_crashes):
        seg_km = max(0.1, seg.to_km - seg.from_km)
        densities.append(len(crs) / seg_km)
        exposure_densities.append(len(crs) / max(1.0, float(seg.aadt or 0)) / seg_km)
    nonzero = [d for d in densities if d > 0]
    mean_density = sum(nonzero) / len(nonzero) if nonzero else 0.0
    exposure_nonzero = [d for d in exposure_densities if d > 0]
    mean_exposure_density = (
        sum(exposure_nonzero) / len(exposure_nonzero) if exposure_nonzero else 0.0
    )

    out: list[RouteSegment] = []
    for seg, crs, dens, exposure_dens in zip(
        segs, seg_crashes, densities, exposure_densities
    ):
        n = len(crs)
        if n == 0 or mean_density <= 0:
            intensity = 0.0
        else:
            # Cap at 5x so a single tiny segment can't dominate the route
            # average; same cap the legacy formula used.
            intensity = min(5.0, dens / mean_density)
        if n == 0 or mean_exposure_density <= 0:
            exposure_intensity = 0.0
        else:
            exposure_intensity = min(5.0, exposure_dens / mean_exposure_density)
        band = _risk_band(n, intensity)
        factors = _top_factors([c.get("payload") or {} for c in crs])
        out.append(
            RouteSegment(
                segment_id=seg.segment_id,
                polyline=seg.polyline,
                from_km=seg.from_km,
                to_km=seg.to_km,
                aadt=seg.aadt,
                speed_limit_mph=seg.speed_limit_mph,
                n_crashes=n,
                intensity_ratio=intensity,
                exposure_intensity_ratio=exposure_intensity,
                risk_band=band,
                top_factors=factors,
            )
        )
    return out


def aggregate_route_risk(segments: list[RouteSegment]) -> tuple[float, int]:
    """Reduce per-segment scores to one number per route, plus a count.

    Returns ``(route_risk, n_total_crashes)`` where ``route_risk`` is the
    *absolute* crash density along this route (crashes per km). Used by
    the alternates picker to compare candidates; the per-segment
    ``intensity_ratio`` is route-relative (segment vs route mean) and
    therefore can't be averaged across alternates the way the legacy
    formula tried to.
    """
    if not segments:
        return 0.0, 0
    total_km = 0.0
    n_total = 0
    for s in segments:
        total_km += max(0.001, s.to_km - s.from_km)
        n_total += s.n_crashes
    return (n_total / total_km if total_km > 0 else 0.0), n_total


def route_risk_band(score: float) -> RiskBand:
    """Map a route's absolute crash density (crashes/km) to a UI band.

    Calibrated against the current ~150K-row FDOT sample so a typical
    Florida interstate (Miami-Tampa, Miami-Orlando) lands in
    "moderate"-"elevated" at peak hours and "low" off-peak. These
    thresholds will need to be re-tuned as the corpus grows.
    """
    if score >= 3.0:
        return "high"
    if score >= 1.5:
        return "elevated"
    if score >= 0.5:
        return "moderate"
    return "low"


# --- Helpers -------------------------------------------------------------


def _risk_band(n_crashes: int, intensity: float) -> RiskBand:
    if intensity >= 2.5 or n_crashes >= 20:
        return "high"
    if intensity >= 1.5 or n_crashes >= 10:
        return "elevated"
    if intensity >= 0.8 or n_crashes >= 4:
        return "moderate"
    return "low"


def _top_factors(payloads: list[dict], *, top_n: int = 3) -> list[FactorWeight]:
    """Tally the most common factor tags across a bag of crashes."""
    if not payloads:
        return []
    counts: Counter[str] = Counter()
    for p in payloads:
        for key in ("weather", "lighting", "surface", "crash_type"):
            v = p.get(key)
            if v and v != "unknown":
                counts[str(v)] += 1
        sev = p.get("severity")
        if sev in {"fatal", "serious"}:
            counts[f"severity:{sev}"] += 1
    total = sum(counts.values()) or 1
    return [
        FactorWeight(factor=f, fraction=round(c / total, 3))
        for f, c in counts.most_common(top_n)
    ]


def severity_mix_from(payloads: list[dict]) -> SeverityMix:
    sev = SeverityMix()
    for p in payloads:
        s = p.get("severity") or "unknown"
        if s == "fatal":
            sev.fatal += 1
        elif s == "serious":
            sev.serious += 1
        elif s == "minor":
            sev.minor += 1
        elif s == "pdo":
            sev.pdo += 1
        else:
            sev.unknown += 1
    return sev


# --- Hotspot conversion ---------------------------------------------------


def hotspots_from_segments(
    scored_segments: list[RouteSegment],
    seg_crashes_payloads: list[list[dict]] | None = None,
    *,
    max_hotspots: int = 6,
) -> list[dict]:
    """Pick the top-N riskiest segments and project them to hotspot dicts.

    Used by the trip router to populate ``hotspots`` for the right-hand
    briefing panel. Each hotspot's centroid is the segment midpoint.
    """
    if not scored_segments:
        return []
    # Rank by (intensity, n_crashes) descending; require at least 1 crash.
    ranked = [
        s for s in scored_segments if s.n_crashes > 0
    ]
    ranked.sort(key=lambda s: (s.intensity_ratio or 0.0, s.n_crashes), reverse=True)
    picks = ranked[:max_hotspots]
    out: list[dict] = []
    for s in picks:
        if not s.polyline:
            continue
        mid = s.polyline[len(s.polyline) // 2]
        centroid = LatLon(lat=mid[1], lon=mid[0])
        out.append(
            {
                "segment": s,
                "centroid": centroid,
            }
        )
    return out

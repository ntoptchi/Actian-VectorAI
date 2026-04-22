"""Render a :class:`SituationDoc` into the text we actually embed.

Two callers:
  - Ingestion: build text per crash, optionally append the CISS narrative.
  - Query time: build text from the trip's environmental conditions only
    (no road_type / no outcome) so similarity surfaces situations.

Keeping the template shared between the two paths is the contract that
makes retrieval sensible (ROUTEWISE.md s6.1 prelude).
"""

from __future__ import annotations

from backend.schemas import SituationDoc

_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_MONTH_NAMES = [
    "",
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _hour_phrase(hour: int) -> str:
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 20:
        return "evening"
    return "night"


def render_narrative(doc: SituationDoc, *, for_query: bool = False) -> str:
    """Build the embedding text for a doc.

    ``for_query=True`` emits a conditions-only sentence (no road_type,
    no outcome, no source) — used at trip-brief time.
    """
    parts: list[str] = []

    # Time
    if doc.day_of_week is not None and doc.month is not None:
        parts.append(
            f"On a {_DAY_NAMES[doc.day_of_week]} in {_MONTH_NAMES[doc.month]} "
            f"during the {_hour_phrase(doc.hour_bucket)} (hour {doc.hour_bucket:02d}),"
        )

    # Environment
    env_bits: list[str] = []
    if doc.lighting:
        env_bits.append(doc.lighting.replace("_", " "))
    if doc.weather and doc.weather != "unknown":
        env_bits.append(doc.weather)
    if doc.surface and doc.surface != "unknown":
        env_bits.append(f"{doc.surface} pavement")
    if doc.precipitation_mm_hr:
        env_bits.append(f"{doc.precipitation_mm_hr:.1f}mm/hr precipitation")
    if doc.visibility_m is not None:
        env_bits.append(f"visibility {doc.visibility_m:.0f}m")
    if env_bits:
        parts.append(f"conditions were {', '.join(env_bits)}.")

    if for_query:
        return " ".join(parts).strip()

    # Road context
    road_bits: list[str] = []
    if doc.road_type and doc.road_type != "unknown":
        road_bits.append(doc.road_type.replace("_", " "))
    if doc.speed_limit_mph:
        road_bits.append(f"{doc.speed_limit_mph} mph posted")
    if doc.county:
        road_bits.append(f"in {doc.county}")
    if doc.state:
        road_bits.append(doc.state)
    if road_bits:
        parts.append(f"Road: {', '.join(road_bits)}.")

    # Outcome (templated, even when narrative is missing)
    out_bits: list[str] = []
    if doc.crash_type and doc.crash_type != "unknown":
        out_bits.append(doc.crash_type.replace("_", " "))
    if doc.num_vehicles:
        out_bits.append(
            f"{doc.num_vehicles} vehicle{'s' if doc.num_vehicles != 1 else ''}"
        )
    if doc.num_injuries:
        out_bits.append(f"{doc.num_injuries} injured")
    if doc.num_fatalities:
        out_bits.append(f"{doc.num_fatalities} killed")
    if doc.severity and doc.severity != "unknown":
        out_bits.append(f"severity {doc.severity}")
    if out_bits:
        parts.append(f"Crash: {', '.join(out_bits)}.")

    # News article (NEWS source: headline + body for embedding)
    if doc.source == "NEWS" and doc.headline:
        parts.append(f"News report: {doc.headline.strip()}")
        if doc.narrative:
            parts.append(doc.narrative.strip())
        return " ".join(parts).strip()

    # Investigator narrative (CISS only, when present)
    if doc.has_narrative and doc.narrative:
        parts.append(f"Investigator narrative: {doc.narrative.strip()}")

    return " ".join(parts).strip()

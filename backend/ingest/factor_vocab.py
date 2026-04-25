"""Frozen vocabulary for the LLM-enriched crash factor tags.

The enriched JSON (``data/raw/enriched_semantic_crashes.json``) uses an
open-ended ``factor_tags: list[str]`` field produced by the LLM. We
freeze the observed tags into a deterministic vocabulary here so the
sparse/keyword retrieval path can build stable term vectors at both
ingestion time *and* query time without drifting when the data is
re-enriched.

Three surfaces depend on this module:

  1. ``scripts/ingest_coaching.py`` — builds the sparse ``factors``
     vector for each VDB point from ``factor_tags`` (+ normalised
     ``primary_driver_action``).
  2. ``backend/services/coaching_retrieval.py`` — builds the sparse
     query vector by translating a :class:`RouteSegment`'s coarse
     ``top_factors`` (``wet``, ``dark_unlighted``, ``rear_end``, …) into
     the richer tag space via :data:`COARSE_TO_RICH`.
  3. ``backend/coaching_vdb.py`` — exposes the vocabulary size so the
     collection's sparse vector space is sized consistently with the
     term indices.

If the enrichment job is ever re-run with a larger crash set, the new
tags will be logged at ingest time via :func:`encode_tags` and can be
promoted into :data:`VOCAB` in a follow-up PR. Unknown tags are
silently dropped at query time so we don't poison the sparse index
with one-off misspellings.
"""

from __future__ import annotations

from collections.abc import Iterable

# ---------------------------------------------------------------------------
# Frozen vocabulary
# ---------------------------------------------------------------------------
# The order here is the stable sparse index order — DO NOT reorder without
# re-ingesting. New tags must be appended to preserve existing indices.

VOCAB: tuple[str, ...] = (
    # Environment / road class
    "intersection",
    "daylight",
    "urban_arterial",
    "interstate",
    "rural_highway",
    "ramp",
    "merge",
    "curve",
    "work_zone",
    "dark_lighted",
    "dark_unlighted",
    "rain",
    "wet",
    # Crash types
    "single_vehicle",
    "head_on",
    "rollover",
    "angle",
    "rear_end",
    "sideswipe",
    "pedestrian",
    "bicycle",
    # Behavioural factors
    "speeding",
    "failure_to_yield",
    "following_too_close",
    "improper_lane_change",
    "wrong_way",
    "ran_red",
    "distracted",
    "phone",
    "impaired_alcohol",
    "impaired_drug",
    "fatigue",
    "seatbelt_unused",
    # Vehicle / actor
    "motorcycle",
    "senior_driver",
    "teen_driver",
    # Physical causes
    "deer",
    "mechanical",
    "tire_blowout",
    "lane_departure",
    "ran_off_road",
)

TAG_INDEX: dict[str, int] = {tag: idx for idx, tag in enumerate(VOCAB)}
VOCAB_SIZE: int = len(VOCAB)


# ---------------------------------------------------------------------------
# Coarse-to-rich tag bridge
# ---------------------------------------------------------------------------
# Segment-level `top_factors` (from backend.services.scoring._top_factors)
# carry coarse labels that predate the enrichment vocab. This map widens a
# coarse label into the rich enriched tags it implies so a query for
# "wet + rear_end" conditions matches enriched crashes tagged with the
# richer labels ("following_too_close", "wet", etc.).

COARSE_TO_RICH: dict[str, tuple[str, ...]] = {
    # Surface / weather
    "wet": ("wet", "rain"),
    "rain": ("rain", "wet"),
    "fog": ("rain",),  # fog doesn't have its own tag; rain is the closest proxy
    "snow": ("wet",),
    "ice": ("wet",),
    # Lighting
    "dark_lighted": ("dark_lighted",),
    "dark_unlighted": ("dark_unlighted",),
    "daylight": ("daylight",),
    "dusk": ("dark_lighted",),
    "dawn": ("daylight",),
    # Crash types
    "rear_end": ("rear_end", "following_too_close"),
    "head_on": ("head_on", "wrong_way"),
    "angle": ("angle", "intersection"),
    "rollover": ("rollover",),
    "single_vehicle": ("single_vehicle", "ran_off_road"),
    "sideswipe_same": ("sideswipe", "improper_lane_change"),
    "sideswipe_opp": ("sideswipe", "improper_lane_change"),
    "pedestrian": ("pedestrian",),
    "bicycle": ("bicycle",),
    # Severity bumps (used when `severity:fatal` shows up in top_factors)
    "severity:fatal": ("speeding", "impaired_alcohol"),
    "severity:serious": ("speeding",),
}


# Driver-action → rich tag map. `primary_driver_action` in the enrichment
# JSON uses a separate vocabulary; we normalise into the factor vocab so
# the sparse index captures the driver-action signal too.

DRIVER_ACTION_TO_RICH: dict[str, tuple[str, ...]] = {
    "failure_to_yield": ("failure_to_yield",),
    "following_too_close": ("following_too_close", "rear_end"),
    "unsafe_speed": ("speeding",),
    "wrong_way": ("wrong_way", "head_on"),
    "ran_off_road": ("ran_off_road", "single_vehicle"),
    "impaired_driving": ("impaired_alcohol",),
    "improper_lane_change": ("improper_lane_change", "sideswipe"),
    "ran_red_light": ("ran_red", "intersection"),
    "improper_turn": ("intersection",),
    "distracted_driving": ("distracted",),
    "mechanical_failure": ("mechanical",),
    "lost_control": ("ran_off_road",),
    # These don't map cleanly; intentionally omitted: "struck_by_other", "unknown"
}


# ---------------------------------------------------------------------------
# Encoding helpers
# ---------------------------------------------------------------------------


def encode_tags(tags: Iterable[str]) -> tuple[list[int], list[float]]:
    """Turn an iterable of tags into (indices, values) for a SparseVector.

    Unknown tags are silently dropped (logged at caller's discretion).
    Repeats bump the weight — which approximates TF without any IDF. That's
    fine for our small fixed vocab: a crash tagged both via
    ``factor_tags`` and via ``primary_driver_action`` should weigh more on
    that dimension than one tagged via only one source.
    """
    weights: dict[int, float] = {}
    for tag in tags:
        idx = TAG_INDEX.get(tag)
        if idx is None:
            continue
        weights[idx] = weights.get(idx, 0.0) + 1.0
    items = sorted(weights.items())
    indices = [i for i, _ in items]
    values = [v for _, v in items]
    return indices, values


def coarse_to_rich_tags(coarse_tags: Iterable[str]) -> list[str]:
    """Expand coarse segment factors into their rich-vocab equivalents."""
    out: list[str] = []
    seen: set[str] = set()
    for coarse in coarse_tags:
        for rich in COARSE_TO_RICH.get(coarse, ()):
            if rich not in seen:
                out.append(rich)
                seen.add(rich)
    return out


def driver_action_to_rich_tags(action: str | None) -> list[str]:
    """Translate a ``primary_driver_action`` value into rich-vocab tags."""
    if not action:
        return []
    return list(DRIVER_ACTION_TO_RICH.get(action, ()))

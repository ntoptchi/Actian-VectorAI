"""
Frozen closed vocab for LLM crash enrichment.

This module is the single source of truth for all fixed enums/tags used by
the enrichment schema. Keep downstream ingestion/query logic aligned by
importing from here instead of duplicating lists.
"""

from __future__ import annotations

from typing import Literal

# NOTE: The original planning note called this "42 terms", but the provided
# draft vocabulary contains 43 unique tags. We freeze the draft vocabulary
# exactly as provided.
FACTOR_TAGS = (
    "rear_end",
    "head_on",
    "angle",
    "rollover",
    "single_vehicle",
    "sideswipe",
    "pedestrian",
    "bicycle",
    "wet",
    "rain",
    "fog",
    "snow",
    "ice",
    "dark_unlighted",
    "dark_lighted",
    "dusk",
    "daylight",
    "intersection",
    "curve",
    "merge",
    "ramp",
    "work_zone",
    "rural_highway",
    "urban_arterial",
    "interstate",
    "phone",
    "speeding",
    "impaired_alcohol",
    "impaired_drug",
    "fatigue",
    "distracted",
    "following_too_close",
    "improper_lane_change",
    "failure_to_yield",
    "ran_red",
    "wrong_way",
    "deer",
    "mechanical",
    "tire_blowout",
    "teen_driver",
    "senior_driver",
    "passenger_distraction",
    "seatbelt_unused",
)

FactorTag = Literal[
    "rear_end",
    "head_on",
    "angle",
    "rollover",
    "single_vehicle",
    "sideswipe",
    "pedestrian",
    "bicycle",
    "wet",
    "rain",
    "fog",
    "snow",
    "ice",
    "dark_unlighted",
    "dark_lighted",
    "dusk",
    "daylight",
    "intersection",
    "curve",
    "merge",
    "ramp",
    "work_zone",
    "rural_highway",
    "urban_arterial",
    "interstate",
    "phone",
    "speeding",
    "impaired_alcohol",
    "impaired_drug",
    "fatigue",
    "distracted",
    "following_too_close",
    "improper_lane_change",
    "failure_to_yield",
    "ran_red",
    "wrong_way",
    "deer",
    "mechanical",
    "tire_blowout",
    "teen_driver",
    "senior_driver",
    "passenger_distraction",
    "seatbelt_unused",
]

Preventability = Literal["preventable", "partially_preventable", "unavoidable", "not_stated"]
PrimaryDriverAction = Literal[
    "following_too_close",
    "lost_control",
    "ran_off_road",
    "improper_lane_change",
    "ran_red_light",
    "failure_to_yield",
    "wrong_way",
    "unsafe_speed",
    "impaired_driving",
    "distracted_driving",
    "fatigued_driving",
    "improper_turn",
    "mechanical_failure",
    "struck_by_other",
    "unknown",
]
DriverDemographic = Literal["teen", "young_adult", "adult", "senior", "mixed", "not_stated"]
OutcomeSeverity = Literal["fatal", "serious", "minor", "pdo", "unknown"]
ExtractionConfidence = Literal["high", "medium", "low"]

PREVENTABILITY_VALUES = ("preventable", "partially_preventable", "unavoidable", "not_stated")
PRIMARY_DRIVER_ACTION_VALUES = (
    "following_too_close",
    "lost_control",
    "ran_off_road",
    "improper_lane_change",
    "ran_red_light",
    "failure_to_yield",
    "wrong_way",
    "unsafe_speed",
    "impaired_driving",
    "distracted_driving",
    "fatigued_driving",
    "improper_turn",
    "mechanical_failure",
    "struck_by_other",
    "unknown",
)
DRIVER_DEMOGRAPHIC_VALUES = ("teen", "young_adult", "adult", "senior", "mixed", "not_stated")
OUTCOME_SEVERITY_VALUES = ("fatal", "serious", "minor", "pdo", "unknown")
EXTRACTION_CONFIDENCE_VALUES = ("high", "medium", "low")


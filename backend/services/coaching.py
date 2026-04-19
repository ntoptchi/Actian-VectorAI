"""Rule-based coaching-line generator.

Keyed off the top-2 factor tuple computed for each hotspot
(ROUTEWISE.md s5.2.10). ~15 rules planned for v1; LLM synthesis is a
descope-restore item (s8.4).
"""

from __future__ import annotations

from backend.schemas import FactorWeight

# (factor_a, factor_b) -> coaching line. Order-insensitive: we try both.
COACHING_RULES: dict[tuple[str, str], str] = {
    ("wet", "rear_end"): (
        "Wet pavement plus rear-end crashes here. Double your following "
        "distance and watch for sudden brake lights — drivers who don't "
        "know the road brake late on this stretch."
    ),
    ("rain", "rear_end"): (
        "Rain pulls following distances apart. Leave 4 seconds, not 2, "
        "and stay out of the right lane through this segment."
    ),
    ("dark_unlighted", "single_vehicle"): (
        "Dark, unlit, single-vehicle crashes here — the lane edges are "
        "hard to read. Drop 5 mph, scan the shoulders for wildlife, and "
        "keep your high beams on when nobody is oncoming."
    ),
    ("dark_lighted", "rear_end"): (
        "Lighting changes confuse depth perception. Look past the car "
        "directly in front of you to spot brake lights two cars ahead."
    ),
    ("fog", "rear_end"): (
        "Fog kills your depth cues. Cut speed by 10 mph and use low "
        "beams — high beams in fog only blind you."
    ),
    ("rain", "single_vehicle"): (
        "Wet curves on this stretch. Brake before the curve, not in it, "
        "and stay off the inside line where puddles pool."
    ),
    ("daylight", "rear_end"): (
        "Daytime rear-ends here usually mean traffic backs up faster "
        "than drivers expect. Keep eyes well ahead, brake early."
    ),
    ("wet", "rollover"): (
        "Wet conditions plus rollover history — most likely lane "
        "departure with overcorrection. If a wheel drops off the "
        "pavement, ease off the gas and steer straight, don't yank back."
    ),
    ("dark_unlighted", "head_on"): (
        "Dark, unlit, head-on crashes here — likely an undivided road "
        "with risky passes. Don't pass; let frustrated drivers go by."
    ),
    ("rain", "angle"): (
        "Wet intersections lose traction in the turn. Approach slow, "
        "give yourself a longer gap before turning across traffic."
    ),
    ("severity:fatal", "single_vehicle"): (
        "Fatal single-vehicle history here. Eyes up, hands at 9-and-3, "
        "no phone — this is the kind of segment where a moment of "
        "inattention is unrecoverable."
    ),
}

CATCH_ALL = (
    "Stay alert through this segment — keep both hands on the wheel and "
    "leave more space than you would on a road you know."
)


def coaching_line(top_factors: list[FactorWeight]) -> str:
    """Pick a coaching line for a hotspot from its ranked factors."""
    if len(top_factors) < 2:
        return CATCH_ALL
    a, b = top_factors[0].factor, top_factors[1].factor
    return COACHING_RULES.get((a, b)) or COACHING_RULES.get((b, a)) or CATCH_ALL

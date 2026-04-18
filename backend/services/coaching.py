"""Rule-based coaching-line generator.

Keyed off the top-2 factor tuple computed for each hotspot
(ROUTEWISE.md s5.2.10). ~15 rules planned for v1; LLM synthesis is a
descope-restore item (s8.4).
"""

from __future__ import annotations

from backend.schemas import FactorWeight

# (factor_a, factor_b) -> coaching line. Order-insensitive: we try both.
COACHING_RULES: dict[tuple[str, str], str] = {
    # TODO(day 3): seed the 10-15 highest-leverage tuples here.
    # Examples (from ROUTEWISE.md s5.2.10):
    # ("wet", "rear_end"): "Double your following distance...",
    # ("dark_rural", "single_vehicle"): "Scan the shoulders for wildlife...",
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

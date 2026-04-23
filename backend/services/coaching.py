"""Rule-based coaching-line generator.

Keyed off the top-2 factor tuple computed for each hotspot
(ROUTEWISE.md s5.2.10). Falls through a deliberate cascade:

  1. ``COACHING_RULES`` — factor-pair rules (most specific).
  2. ``SINGLE_FACTOR_RULES`` — one-line-per-factor fallback so we don't
     collapse onto the generic catch-all every time a hotspot has one
     dominant factor without a second strong signal.
  3. ``CATCH_ALL_VARIANTS`` — deterministic rotation keyed on the
     ``seed`` arg (the hotspot's index in the trip brief). Guarantees
     each of the route's ~6 hotspots reads differently even when the
     underlying data doesn't meaningfully distinguish them; a copy-paste
     coaching line across every pin reads as boilerplate and teaches the
     driver to tune it out.

The ``exclude`` arg lets the caller suppress lines already used on
other hotspots in the same trip — belt-and-braces dedupe on top of the
seed rotation.
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

# One-shot fallback so single-factor hotspots still get a factor-aware
# line instead of silently hitting the catch-all.
SINGLE_FACTOR_RULES: dict[str, str] = {
    "rear_end": (
        "Most crashes here were rear-ends — traffic queues up faster "
        "than drivers expect. Keep four seconds of following distance "
        "and scan two cars ahead for brake lights."
    ),
    "angle": (
        "Intersection conflicts dominate this stretch. Watch for "
        "drivers turning across your lane and cover the brake when you "
        "approach green lights."
    ),
    "head_on": (
        "Head-on history here — this is likely an undivided road. "
        "Never pass on a solid line and hold the right edge when "
        "oncoming traffic drifts."
    ),
    "rollover": (
        "Rollover crashes cluster on this segment — stay centered in "
        "your lane, and if a tire drops off the pavement ease off the "
        "gas instead of yanking the wheel back."
    ),
    "single_vehicle": (
        "Single-vehicle run-offs dominate here. Eyes well ahead, both "
        "hands on the wheel, phone in the glovebox — this is where "
        "distraction actually bites."
    ),
    "sideswipe": (
        "Lane-change crashes cluster here. Signal early, check the "
        "blind spot twice, and don't drift while you're reading signs."
    ),
    "wet": (
        "Wet-pavement crashes cluster here. Cut speed five to ten mph "
        "below the limit and stay out of the tire-rut standing water "
        "in the right lane."
    ),
    "rain": (
        "Rain-driven crashes here. Back off, double your following "
        "distance, and run headlights + wipers on the same setting "
        "even if it feels bright enough without them."
    ),
    "fog": (
        "Fog-related crashes on this stretch. Low beams only — high "
        "beams just reflect off the fog wall — and drop well below the "
        "posted limit so you can stop inside your visibility."
    ),
    "dark_unlighted": (
        "Most crashes here happened after dark on an unlit road. Keep "
        "high beams on when nobody is oncoming, scan the shoulders, "
        "and plan for deer and stopped vehicles just outside the cone."
    ),
    "dark_lighted": (
        "After-dark crashes in a lit area — streetlight spacing here "
        "plays tricks on depth perception. Look past the car directly "
        "in front of you to catch brake lights two cars ahead."
    ),
    "daylight": (
        "Even in daylight this stretch catches drivers off guard. "
        "Keep eyes up the road, not on the car ahead, and brake early "
        "the moment traffic compresses."
    ),
    "dusk": (
        "Dusk crashes cluster here — your eyes haven't switched to "
        "night vision yet and headlights aren't fully effective. Turn "
        "them on early and drop a few mph."
    ),
    "clear": (
        "Crashes here happen in good weather, which usually means "
        "speed or inattention. Set cruise a few mph below the flow "
        "and keep your phone out of reach."
    ),
    "severity:fatal": (
        "Fatal crashes have happened on this exact stretch. No phone, "
        "no passenger tasks — this is a segment where one lapse is "
        "unrecoverable."
    ),
    "severity:serious": (
        "Serious-injury crashes cluster here. Drive it like something "
        "is about to go wrong, because for someone else it recently did."
    ),
}

# Catch-all rotation. Index into this by (hotspot_index % len(variants))
# so the 6 hotspots on a typical trip read differently even when the
# data can't tell them apart.
CATCH_ALL_VARIANTS: tuple[str, ...] = (
    "Stay alert through this segment — both hands on the wheel, and "
    "leave more space than you would on a road you already know.",
    "This stretch has produced enough crashes to flag it. Slow a few "
    "mph, widen your following gap, and skip the radio tweak until "
    "you're past it.",
    "Treat this segment as unfamiliar even if you've driven near here "
    "before. Drivers who thought they knew it are the ones in the "
    "crash dataset.",
    "The crashes here don't share one dominant cause — which usually "
    "means small distractions compound. Keep your eyes moving and "
    "your lane centered.",
    "Enough crashes on this stretch to notice. Phone face-down, music "
    "set before you arrive, and one car-length of extra space per "
    "10 mph over 30.",
    "A crash cluster without a single obvious pattern. Stay out of "
    "blind spots, leave trucks extra room, and don't pass unless "
    "you have a clean lane.",
    "This segment shows up in the data but not with a clean story. "
    "Assume nothing — maintain speed discipline and keep an escape "
    "lane open on either side.",
    "Crashes cluster here for reasons that aren't obvious from one "
    "trip. Play defense: scan mirrors every five seconds and leave a "
    "buffer you could brake hard into.",
)


def coaching_line(
    top_factors: list[FactorWeight],
    *,
    seed: int = 0,
    exclude: set[str] | None = None,
) -> str:
    """Pick a coaching line for a hotspot from its ranked factors.

    ``seed`` should be the hotspot's position in the trip brief (0-indexed)
    so fallbacks rotate instead of repeating. ``exclude`` lets the caller
    reject lines already used on other hotspots in the same brief.
    """
    exclude = exclude or set()

    candidates: list[str] = []

    # 1. factor-pair rules (most specific)
    if len(top_factors) >= 2:
        a, b = top_factors[0].factor, top_factors[1].factor
        pair = COACHING_RULES.get((a, b)) or COACHING_RULES.get((b, a))
        if pair:
            candidates.append(pair)

    # 2. single-factor fallbacks, in the order the scorer ranked them
    for f in top_factors:
        hit = SINGLE_FACTOR_RULES.get(f.factor)
        if hit and hit not in candidates:
            candidates.append(hit)

    # 3. catch-all variants, rotated by seed so sibling hotspots differ
    n = len(CATCH_ALL_VARIANTS)
    if n:
        offset = seed % n
        rotated = CATCH_ALL_VARIANTS[offset:] + CATCH_ALL_VARIANTS[:offset]
        for v in rotated:
            if v not in candidates:
                candidates.append(v)

    for c in candidates:
        if c not in exclude:
            return c

    # Everything excluded — return the seed-rotated catch-all so we still
    # have something to show, even if it collides.
    return CATCH_ALL_VARIANTS[seed % len(CATCH_ALL_VARIANTS)]

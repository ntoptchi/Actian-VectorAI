"""Build clustered lesson zones across a chosen route."""

from __future__ import annotations

from collections import Counter, defaultdict

from backend.schemas import CrashInsight, LessonZone, RouteSegment

_THEME_LABELS: dict[str, str] = {
    "wet_road": "Wet roads and hydroplaning risk",
    "rear_end_cluster": "Rear-end chain reaction zone",
    "dark_stretch": "Dark visibility-risk stretch",
    "curve_control": "Curves and loss-of-control risk",
    "intersection_caution": "Intersection conflict zone",
    "speed_control": "Speed and impact-severity zone",
}

_THEME_FALLBACK_LESSON: dict[str, str] = {
    "wet_road": "This stretch repeatedly shows wet-road crashes. Increase following distance and avoid abrupt braking.",
    "rear_end_cluster": "Rear-end crashes cluster here. Expect stop-and-go traffic and leave more space than usual.",
    "dark_stretch": "Crashes here skew to low-light visibility conditions. Slow down and scan farther ahead.",
    "curve_control": "Loss-of-control crashes appear frequently on this stretch. Enter curves slower and avoid sudden steering.",
    "intersection_caution": "Conflict crashes near intersections are common here. Cover the brake and expect late moves from others.",
    "speed_control": "Higher-speed impact patterns cluster in this section. Prioritize smooth speed control and larger safety margins.",
}


def build_zones(
    segments: list[RouteSegment],
    insights: list[CrashInsight],
) -> list[LessonZone]:
    if not segments:
        return []

    insight_by_segment: dict[str, list[CrashInsight]] = defaultdict(list)
    for ins in insights:
        if ins.segment_id:
            insight_by_segment[ins.segment_id].append(ins)

    themes: list[str | None] = []
    for seg in segments:
        themes.append(_segment_theme(seg, insight_by_segment.get(seg.segment_id, [])))

    _bridge_single_gaps(themes)

    zones: list[LessonZone] = []
    i = 0
    while i < len(segments):
        theme = themes[i]
        if theme is None:
            i += 1
            continue
        start = i
        j = i + 1
        while j < len(segments) and themes[j] == theme:
            j += 1

        zone_segments = segments[start:j]
        zone_insights: list[CrashInsight] = []
        for seg in zone_segments:
            zone_insights.extend(insight_by_segment.get(seg.segment_id, []))
        span_km = max(0.0, zone_segments[-1].to_km - zone_segments[0].from_km)
        if span_km < 10.0 and len(zone_insights) < 2:
            i = j
            continue

        representative = _representative(zone_insights)
        risk_factors = _risk_factors(zone_segments, zone_insights)
        lesson = (
            representative.lesson.strip()
            if representative and representative.lesson.strip()
            else _THEME_FALLBACK_LESSON.get(theme, "Use extra caution on this stretch.")
        )
        headline = _headline(theme, span_km)
        zones.append(
            LessonZone(
                zone_id=f"lz_{len(zones):02d}_{zone_segments[0].segment_id}",
                theme=theme,
                theme_label=_THEME_LABELS.get(theme, "Route lesson zone"),
                headline=headline,
                lesson=lesson,
                polyline=_join_polylines(zone_segments),
                from_km=zone_segments[0].from_km,
                to_km=zone_segments[-1].to_km,
                span_km=span_km,
                n_insights=len(zone_insights),
                n_crashes=sum(s.n_crashes for s in zone_segments),
                risk_factors=risk_factors,
                representative_insight_id=(
                    representative.insight_id if representative else None
                ),
            )
        )
        i = j
    return zones


def _segment_theme(segment: RouteSegment, segment_insights: list[CrashInsight]) -> str | None:
    if segment_insights:
        candidate = _theme_from_tokens(segment_insights[0].risk_factors)
        if candidate:
            return candidate
    top = segment.top_factors[0].factor if segment.top_factors else None
    return _theme_from_tokens([top] if top else [])


def _theme_from_tokens(tokens: list[str | None]) -> str | None:
    for raw in tokens:
        token = (raw or "").lower()
        if any(k in token for k in ("wet", "rain", "hydro", "fog")):
            return "wet_road"
        if any(k in token for k in ("rear_end", "following_too_close", "rear")):
            return "rear_end_cluster"
        if any(k in token for k in ("dark_unlighted", "dark_lighted", "night", "dark")):
            return "dark_stretch"
        if any(k in token for k in ("curve", "rollover", "ran_off_road", "single_vehicle")):
            return "curve_control"
        if any(k in token for k in ("intersection", "angle", "ran_red")):
            return "intersection_caution"
        if any(k in token for k in ("speed", "severity:fatal", "fatal")):
            return "speed_control"
    return None


def _bridge_single_gaps(themes: list[str | None]) -> None:
    for i in range(1, len(themes) - 1):
        if themes[i] is None and themes[i - 1] is not None and themes[i - 1] == themes[i + 1]:
            themes[i] = themes[i - 1]


def _join_polylines(segments: list[RouteSegment]) -> list[list[float]]:
    joined: list[list[float]] = []
    for seg in segments:
        for pt in seg.polyline:
            if not joined or joined[-1] != pt:
                joined.append(pt)
    return joined


def _representative(insights: list[CrashInsight]) -> CrashInsight | None:
    if not insights:
        return None
    return max(insights, key=lambda ins: ins.similarity)


def _risk_factors(segments: list[RouteSegment], insights: list[CrashInsight]) -> list[str]:
    counts: Counter[str] = Counter()
    for ins in insights:
        for f in ins.risk_factors:
            if f:
                counts[f] += 1
    if not counts:
        for seg in segments:
            for f in seg.top_factors:
                if f.factor:
                    counts[f.factor] += 1
    return [f for f, _ in counts.most_common(5)]


def _headline(theme: str, span_km: float) -> str:
    label = _THEME_LABELS.get(theme, "Route lesson zone")
    return f"{label} over {round(span_km)} km"

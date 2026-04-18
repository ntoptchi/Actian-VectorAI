"""Round-trip tests for SituationDoc rendering.

Verifies:
  - render_narrative produces non-empty, deterministic text from a doc.
  - for_query=True drops outcome / road / source fields, keeping only
    environmental + temporal context (the contract from ROUTEWISE.md s6.1).
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.ingest.situation_doc import render_narrative
from backend.schemas import SituationDoc


def _sample_doc() -> SituationDoc:
    return SituationDoc(
        source="CISS",
        case_id="2022FL00218",
        state="FL",
        county="Lee",
        lat=26.6102,
        lon=-81.8234,
        h3_cell="89283082837ffff",
        road_type="interstate",
        speed_limit_mph=70,
        timestamp=datetime(2022, 8, 14, 18, 40, tzinfo=timezone.utc),
        hour_bucket=18,
        day_of_week=6,
        month=8,
        weather="rain",
        precipitation_mm_hr=2.1,
        visibility_m=8000,
        lighting="dawn_dusk",
        surface="wet",
        crash_type="rear_end",
        num_vehicles=2,
        num_injuries=1,
        num_fatalities=0,
        severity="serious",
        has_narrative=True,
        narrative=(
            "Vehicle 1 northbound on I-75 decelerating in the right lane "
            "approaching the Colonial Boulevard exit under light rain."
        ),
    )


def test_render_full_includes_narrative_and_road_context() -> None:
    text = render_narrative(_sample_doc())
    assert text
    assert "rain" in text
    assert "wet pavement" in text
    assert "rear end" in text
    assert "interstate" in text
    assert "Investigator narrative" in text


def test_render_for_query_strips_outcome_and_road_fields() -> None:
    text = render_narrative(_sample_doc(), for_query=True)
    assert text
    assert "rain" in text
    assert "wet pavement" in text
    # query-time text must not leak the outcome or road context — that's
    # what makes situational similarity meaningful.
    assert "rear end" not in text
    assert "interstate" not in text
    assert "Investigator narrative" not in text


def test_render_handles_minimal_doc() -> None:
    """Even an almost-empty doc renders without raising."""
    doc = SituationDoc(weather="clear", surface="dry", lighting="daylight")
    text = render_narrative(doc)
    assert isinstance(text, str)

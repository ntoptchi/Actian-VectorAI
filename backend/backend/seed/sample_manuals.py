"""Seed repair manuals.

Three short manuals chunked into ~20 chunks total, covering the failure modes
in ``sample_incidents``.
"""

from __future__ import annotations

from ..schemas import RepairManual, RepairManualChunk


def _manual(
    manual_id: str,
    manual_name: str,
    summary: str,
    paragraphs: list[str],
) -> RepairManual:
    chunks = [
        RepairManualChunk(
            chunk_id=f"{manual_id}-C{idx:02d}",
            manual_id=manual_id,
            manual_name=manual_name,
            text=paragraph.strip(),
        )
        for idx, paragraph in enumerate(paragraphs, start=1)
    ]
    return RepairManual(
        manual_id=manual_id,
        manual_name=manual_name,
        summary=summary,
        chunks=chunks,
    )


REPAIR_MANUALS: list[RepairManual] = [
    _manual(
        manual_id="MAN-COMP-01",
        manual_name="Compressor Maintenance and Vibration Response",
        summary=(
            "Operating procedures, vibration thresholds, and bearing-care "
            "guidance for offshore compressor lines."
        ),
        paragraphs=[
            "If compressor vibration exceeds 12 mm/s sustained for more than "
            "two minutes, immediately reduce upstream load by at least 20 "
            "percent and notify the reliability engineer on shift.",
            "Bearing temperature above 78 C combined with falling lubricant "
            "pressure is the canonical signature of a flow restriction. "
            "Drop RPM to a maintenance idle and inspect the lubricant filter "
            "and supply line before resuming load.",
            "Resonance during load transitions is most often caused by rotor "
            "imbalance. Schedule a balance check after any three excursions "
            "within a 30-day window, even if each excursion clears on its own.",
            "After any high-vibration event, recalibrate the vibration sensor "
            "bank against the reference accelerometer before clearing the "
            "alarm. Stale calibration is the most common false-positive cause.",
            "Lubricant pressure below 2.0 bar at running RPM should be treated "
            "as a hard stop. Continued operation risks bearing damage that is "
            "not recoverable in the field.",
        ],
    ),
    _manual(
        manual_id="MAN-VIB-01",
        manual_name="Rotor Balance and Resonance Field Guide",
        summary=(
            "Field procedures for diagnosing rotor imbalance, harmonic "
            "resonance, and load-transition spikes on rotating equipment."
        ),
        paragraphs=[
            "A clean 1x rotational harmonic indicates pure imbalance. A 2x "
            "harmonic of comparable magnitude points to misalignment instead "
            "and changes the field response.",
            "When vibration spikes occur only on load step-ups, the root cause "
            "is almost always load-induced resonance. Smooth the load ramp "
            "to under 5 percent per second before re-attempting the step.",
            "Trim balancing in the field requires that the rotor be at "
            "operating temperature. Cold-balance corrections drift back out "
            "of tolerance within an hour of normal operation.",
            "Document every balance correction in the asset log together with "
            "the residual vibration reading. Future excursions are much easier "
            "to triage when the balance history is available.",
        ],
    ),
    _manual(
        manual_id="MAN-COOL-01",
        manual_name="Cooling Loop and Mud-System Stability",
        summary=(
            "Diagnostic and remediation steps for cooling-loop pressure "
            "instability, valve oscillation, and mud-pump cavitation."
        ),
        paragraphs=[
            "Pressure variance above 3 bar in the cooling loop is almost "
            "always a control valve symptom. Switch the affected loop to "
            "manual mode, damp the control band by 30 percent, and retune "
            "the actuator once flow stabilizes.",
            "Valve oscillation that resolves with manual mode but recurs on "
            "auto indicates a stale PID gain. Re-tune at the current operating "
            "point rather than restoring the previous gain set.",
            "Mud-pump cavitation shows up as a brief high-vibration spike "
            "with a simultaneous suction-pressure dip. Increase suction head "
            "before increasing pump speed.",
            "After any cavitation event, inspect the impeller for pitting "
            "during the next maintenance window even if performance has "
            "fully recovered.",
            "Cooling-loop instability that coincides with rising heat-exchanger "
            "outlet temperature suggests fouling, not control. Schedule a "
            "chemical clean before further controller adjustments.",
        ],
    ),
    _manual(
        manual_id="MAN-ENV-01",
        manual_name="Environmental and Electrical Anomalies",
        summary=(
            "Response procedures for storage humidity drift, gas-sensor "
            "anomalies, and switchgear thermal excursions."
        ),
        paragraphs=[
            "Humidity drift above 0.5 percent RH per minute across adjacent "
            "sensors is treated as a real environmental change, not a sensor "
            "fault. Check desiccant cartridges first.",
            "Switchgear thermal excursions almost always trace to a loose "
            "connection. Redistribute load away from the affected bus and "
            "isolate it for thermographic inspection during the next outage "
            "window.",
            "Gas-sensor drift that correlates with humidity changes can be "
            "ignored if it stays within calibration limits, but should be "
            "flagged for the next scheduled maintenance pass.",
            "Any electrical hot-spot above 85 C on a primary bus is grounds "
            "for immediate isolation regardless of load conditions.",
        ],
    ),
]

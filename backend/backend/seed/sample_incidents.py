"""Seed past incidents.

Six hand-written incidents covering the failure modes shown on the dashboard
in ``src/data/dashboardData.ts``. Signatures use the canonical ``SENSOR_ORDER``
keys so the numeric side of the classifier has something to work with.
"""

from __future__ import annotations

from ..schemas import PastIncident


PAST_INCIDENTS: list[PastIncident] = [
    PastIncident(
        incident_id="INC-8821",
        incident_name="Compressor resonance spike during high-load transition",
        failure_type="Rotor imbalance",
        severity="Critical",
        description=(
            "Rotor imbalance intensified during a load step-up and drove "
            "compressor vibration past the trip threshold. Resonance signature "
            "matched prior load-transition events on the same line."
        ),
        signature={
            "vibration": 18.4,
            "bearing_temp": 72.0,
            "pressure": 7.6,
            "rpm": 3450.0,
            "lubricant_pressure": 3.1,
            "humidity": 41.0,
        },
        related_manual_ids=["MAN-COMP-01", "MAN-VIB-01"],
    ),
    PastIncident(
        incident_id="INC-8619",
        incident_name="Bearing overheat after lubricant flow restriction",
        failure_type="Lubricant restriction",
        severity="Critical",
        description=(
            "A partial lubricant restriction reduced flow to the bearing "
            "housing. Bearing temperature climbed steadily while lubricant "
            "pressure dropped, with vibration harmonics rising in tandem."
        ),
        signature={
            "vibration": 11.8,
            "bearing_temp": 83.0,
            "pressure": 7.2,
            "rpm": 3380.0,
            "lubricant_pressure": 1.6,
            "humidity": 39.0,
        },
        related_manual_ids=["MAN-COMP-01"],
    ),
    PastIncident(
        incident_id="INC-8457",
        incident_name="Cooling loop instability from valve oscillation",
        failure_type="Control valve oscillation",
        severity="Elevated",
        description=(
            "Repeated valve over-correction caused loop pressure to swing "
            "outside the configured tolerance. Flow stabilization slowed and "
            "cooling efficiency dropped before manual lockout was applied."
        ),
        signature={
            "vibration": 6.4,
            "bearing_temp": 64.0,
            "pressure": 3.7,
            "rpm": 2950.0,
            "lubricant_pressure": 2.9,
            "humidity": 44.0,
        },
        related_manual_ids=["MAN-COOL-01"],
    ),
    PastIncident(
        incident_id="INC-8390",
        incident_name="Storage chamber humidity drift",
        severity="Watching",
        failure_type="Environmental drift",
        description=(
            "Persistent humidity rise across two adjacent environmental "
            "sensors in storage chamber 2. No mechanical correlation; root "
            "cause was a degraded desiccant cartridge."
        ),
        signature={
            "vibration": 0.4,
            "bearing_temp": 22.0,
            "pressure": 1.0,
            "rpm": 0.0,
            "lubricant_pressure": 0.0,
            "humidity": 71.0,
        },
        related_manual_ids=["MAN-ENV-01"],
    ),
    PastIncident(
        incident_id="INC-8201",
        incident_name="Mud pump cavitation under low suction",
        failure_type="Cavitation",
        severity="Elevated",
        description=(
            "Suction-side pressure fell below the cavitation threshold during "
            "a hot-swap of the mud reservoir. Vibration spiked briefly and "
            "pump efficiency dropped until suction recovered."
        ),
        signature={
            "vibration": 9.7,
            "bearing_temp": 58.0,
            "pressure": 1.4,
            "rpm": 2200.0,
            "lubricant_pressure": 2.7,
            "humidity": 46.0,
        },
        related_manual_ids=["MAN-COOL-01"],
    ),
    PastIncident(
        incident_id="INC-8044",
        incident_name="Switchgear thermal excursion",
        failure_type="Electrical hot-spot",
        severity="Critical",
        description=(
            "Localized temperature rise on a switchgear bus indicated a "
            "loose connection. Load was redistributed and the bus was "
            "isolated for inspection."
        ),
        signature={
            "vibration": 1.2,
            "bearing_temp": 91.0,
            "pressure": 1.0,
            "rpm": 0.0,
            "lubricant_pressure": 0.0,
            "humidity": 38.0,
        },
        related_manual_ids=["MAN-ENV-01"],
    ),
]

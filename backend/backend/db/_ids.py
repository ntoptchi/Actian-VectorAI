"""Deterministic UUIDs for human-readable business IDs.

VectorAI point IDs must be UUIDs or integers; our schemas use human-friendly
strings like ``INC-8821``. We hash them into UUID5 values so the same business
ID always lands on the same point across re-runs.
"""

from __future__ import annotations

import uuid


_NAMESPACE = uuid.UUID("6b8a4ef4-3f65-4f5e-9c2a-9bd0f3d5e7a1")


def stable_id(business_id: str) -> str:
    """Return a deterministic UUID string for ``business_id``."""
    return str(uuid.uuid5(_NAMESPACE, business_id))

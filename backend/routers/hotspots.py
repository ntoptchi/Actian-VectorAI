"""``GET /hotspots/{hotspot_id}`` — full briefing-card payload for a pin.

Groundwork pass returns a 404 unless the id matches a synthetic example;
the real implementation (Day 3-5) will resolve the cluster id back to its
crash members and assemble the card.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.schemas import HotspotDetailResponse
from backend.services import cluster

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/hotspots", tags=["hotspots"])


@router.get("/{hotspot_id}", response_model=HotspotDetailResponse)
async def get_hotspot(hotspot_id: str) -> HotspotDetailResponse:
    detail = await cluster.get_hotspot_detail(hotspot_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"hotspot {hotspot_id!r} not found")
    return detail

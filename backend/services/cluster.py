"""Hotspot retrieval, clustering, and ranking.

Day-3 work lives here. The shape:

  1. Build a *query* SituationDoc from the trip conditions.
  2. Embed it; search VDB top-k=40-60 with payload filter
     ``h3_cell IN cells_along(route)``.
  3. DBSCAN on lat/lon (eps ~300m), drop singletons / low-similarity.
  4. For each cluster: snap centroid to AADT segment, compute
     intensity (cluster_size / (AADT * years * 365)), label, factors,
     coaching line, excerpt picks.
  5. Sort by intensity, return top 3-6.

Groundwork pass: ``find_hotspots`` returns ``[]`` and ``get_hotspot_detail``
returns ``None`` so the API shape is honest about being empty.
"""

from __future__ import annotations

import logging
from datetime import datetime

from backend.schemas import (
    HotspotDetailResponse,
    HotspotSummary,
    WeatherSegment,
)

logger = logging.getLogger(__name__)


async def find_hotspots(
    *,
    cells: set[str],
    departure: datetime,
    weather_segments: list[WeatherSegment],
    sunset_iso: datetime | None,
) -> list[HotspotSummary]:
    """Retrieve, cluster, and rank hotspots for the given route.

    TODO(day 3):
      - build query :class:`SituationDoc` from conditions only.
      - call ``backend.embeddings.embed_one`` and ``client.points.search``
        with a ``Field("h3_cell").any_of(list(cells))`` filter, top-k 60.
      - fall back to top-300 + in-memory cell post-filter if VDB rejects
        the IN-list (see ROUTEWISE.md risk row in s10).
      - DBSCAN cluster on (lat, lon), eps ~300m / Earth-radius rad.
      - per-cluster: AADT lookup, intensity ratio, coaching line.
      - cache per-trip-id so ``get_hotspot_detail`` can resolve.
    """
    if not cells:
        logger.info("no cells along route; returning 0 hotspots")
        return []
    logger.info("hotspot retrieval stub: %d route cells, returning 0 hotspots", len(cells))
    return []


async def get_hotspot_detail(hotspot_id: str) -> HotspotDetailResponse | None:
    """Return the full briefing-card payload for a previously-emitted id.

    TODO(day 3): look up the cached cluster (in-memory dict keyed by
    hotspot_id, or Redis later) and assemble the card with 2-3 narrative
    excerpts picked for similarity + severity diversity.
    """
    logger.info("hotspot detail stub for id=%s", hotspot_id)
    return None

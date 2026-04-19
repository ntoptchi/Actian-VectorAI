"""OpenRouteService Directions client.

We pick ORS over OSRM for two reasons that matter to the pivot:

  1. The free public OSRM instance does not return alternative routes.
     ORS does (``alternative_routes`` parameter), and the
     candidate-and-rerank story needs >=2 alternatives.
  2. ORS lets us bias toward the *fastest* route while still asking for
     longer/less-shared variants — exactly the search space where the
     VDB-driven re-rank can find a safer-but-still-reasonable option.

Returns lightweight dicts (not Pydantic models) so callers can pass the
raw polyline straight to the segments + scoring pipeline.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

ORS_BASE = "https://api.openrouteservice.org"


@dataclass(slots=True)
class OrsAlternate:
    """One alternate returned by the ORS Directions API."""

    polyline: list[list[float]]  # [[lon, lat], ...]
    distance_m: float
    duration_s: float


class OrsError(RuntimeError):
    """Raised when ORS is unreachable or returns an unparseable response.

    The trip router catches this and falls back to a single OSRM-style
    straight-line route so /trip/brief never 500s on routing alone
    (ROUTEWISE.md s2.4 honesty test).
    """


def _api_key() -> str | None:
    # Accept every spelling we've seen in the wild — the canonical name
    # from ORS docs is OPENROUTESERVICE_API_KEY (no underscores), but our
    # internal docs and earlier copies of .env used OPEN_ROUTE_SERVICE_API_KEY.
    # Quietly preferring one would silently degrade routing to OSRM
    # single-route, which is exactly the QA bug we hit (1 alternate, no
    # rerank), so look up all of them.
    for name in (
        "OPENROUTESERVICE_API_KEY",
        "OPEN_ROUTE_SERVICE_API_KEY",
        "ORS_API_KEY",
        "ROUTEWISE_ORS_API_KEY",
    ):
        val = os.environ.get(name)
        if val:
            return val
    return None


async def directions(
    origin: tuple[float, float],
    destination: tuple[float, float],
    *,
    alternatives: int = 3,
    share_factor: float = 0.6,
    weight_factor: float = 1.4,
    timeout_s: float = 15.0,
) -> list[OrsAlternate]:
    """Fetch driving alternates from ``api.openrouteservice.org``.

    ``origin``/``destination`` are ``(lat, lon)``. ORS expects ``[lon, lat]``
    in the request body, which we adapt here so callers can stay in lat/lon.

    Returns alternates in ORS's order (the first one is the fastest, the
    rest are progressively slower / less-shared with the fastest).
    """
    key = _api_key()
    if not key:
        raise OrsError(
            "ORS API key not set. Put OPEN_ROUTE_SERVICE_API_KEY in .env"
        )

    body: dict = {
        "coordinates": [
            [origin[1], origin[0]],
            [destination[1], destination[0]],
        ],
        "instructions": False,
        "geometry": True,
        "preference": "fastest",
    }
    if alternatives > 1:
        body["alternative_routes"] = {
            "target_count": alternatives,
            "share_factor": share_factor,
            "weight_factor": weight_factor,
        }

    url = f"{ORS_BASE}/v2/directions/driving-car/geojson"
    headers = {
        "Authorization": key,
        "Content-Type": "application/json",
        "Accept": "application/geo+json",
    }

    async def _post(payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                # Bubble up the body text so callers can inspect ORS's
                # specific error code (e.g. 2004 = route too long for
                # alternative_routes on the free tier).
                raise httpx.HTTPStatusError(
                    f"{resp.status_code} {resp.text[:300]}",
                    request=resp.request,
                    response=resp,
                )
            return resp.json()

    try:
        try:
            data = await _post(body)
        except httpx.HTTPStatusError as exc:
            # ORS error 2004 fires when the requested route is longer than
            # the free-tier limit for alternative_routes (150 km on
            # driving-car). Most intercity trips trip that, so silently
            # retry without alternatives — a single real ORS route is
            # still strictly better than the OSRM fallback (right graph,
            # right turn restrictions, right speed model).
            text = (exc.response.text if exc.response is not None else "") or ""
            if "alternative_routes" in body and (
                "2004" in text or "must not be greater than" in text
            ):
                logger.info(
                    "ORS rejected alternatives (route too long); retrying without alternative_routes"
                )
                retry_body = {k: v for k, v in body.items() if k != "alternative_routes"}
                data = await _post(retry_body)
            else:
                raise
    except httpx.HTTPError as exc:
        raise OrsError(f"ORS request failed: {exc}") from exc

    features = data.get("features") or []
    if not features:
        raise OrsError("ORS returned no features")

    out: list[OrsAlternate] = []
    for feat in features:
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if not coords:
            continue
        summary = (
            (feat.get("properties") or {}).get("summary") or {}
        )
        distance_m = float(summary.get("distance") or 0.0)
        duration_s = float(summary.get("duration") or 0.0)
        out.append(
            OrsAlternate(
                polyline=[[float(lon), float(lat)] for lon, lat in coords],
                distance_m=distance_m,
                duration_s=duration_s,
            )
        )

    if not out:
        raise OrsError("ORS returned features but no usable polylines")

    logger.info("ORS returned %d alternate(s)", len(out))
    return out

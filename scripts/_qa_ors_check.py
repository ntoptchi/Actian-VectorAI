"""Direct ORS check to see why the request is rejected."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
import httpx


async def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    key = os.environ.get("OPENROUTESERVICE_API_KEY") or os.environ.get(
        "OPEN_ROUTE_SERVICE_API_KEY"
    )
    print("key prefix:", (key or "")[:24], "len", len(key or ""))

    body = {
        "coordinates": [
            [-80.1918, 25.7617],   # Miami
            [-82.4572, 27.9506],   # Tampa
        ],
        "instructions": False,
        "geometry": True,
        "preference": "fastest",
        "alternative_routes": {
            "target_count": 3,
            "share_factor": 0.6,
            "weight_factor": 1.4,
        },
    }
    headers = {
        "Authorization": key or "",
        "Content-Type": "application/json",
        "Accept": "application/geo+json",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            "https://api.openrouteservice.org/v2/directions/driving-car/geojson",
            json=body,
            headers=headers,
        )
        print("status:", resp.status_code)
        try:
            j = resp.json()
            print(json.dumps(j, indent=2)[:1500])
        except Exception:
            print(resp.text[:1500])


asyncio.run(main())

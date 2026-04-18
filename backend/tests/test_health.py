"""Smoke test: the FastAPI app boots and ``/health`` returns 200.

Does not require VectorAI DB to be running — the health endpoint
captures VDB unreachability in its payload but still returns 200 so
container-orchestrators don't kill the API box when the DB blips.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_health_ok() -> None:
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert body["service"] == "routewise-api"
    assert "vdb" in body

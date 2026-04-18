"""Offline smoke test.

Exercises every module without touching VectorAI DB or downloading MiniLM.
Used by the verification step to prove the framework wires together; the live
demo (``run_demo.py``) still needs a running container.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("USE_MOCK_EMBEDDINGS", "true")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import SENSOR_ORDER, get_settings
from backend.embeddings import embed
from backend.pipeline.classify import classify
from backend.pipeline.detect import BaselineStats, detect
from backend.pipeline.orchestrator import analyze
from backend.pipeline.retrieve import retrieve
from backend.schemas import AnomalyReport
from backend.seed.sample_incidents import PAST_INCIDENTS
from backend.seed.sample_manuals import REPAIR_MANUALS
from backend.seed.sample_sensors import generate_sample_stream


def _payload_for_incident(incident) -> dict:
    return {
        "incident_id": incident.incident_id,
        "incident_name": incident.incident_name,
        "failure_type": incident.failure_type,
        "severity": incident.severity,
        "description": incident.description,
        "signature": incident.signature,
        "related_manual_ids": incident.related_manual_ids,
    }


def _payload_for_manual(manual) -> dict:
    return {
        "manual_id": manual.manual_id,
        "manual_name": manual.manual_name,
        "summary": manual.summary,
    }


def _payload_for_chunk(chunk) -> dict:
    return {
        "chunk_id": chunk.chunk_id,
        "manual_id": chunk.manual_id,
        "manual_name": chunk.manual_name,
        "text": chunk.text,
    }


def _make_fake_client():
    """Build a MagicMock client whose .points.search returns canned hits."""
    client = MagicMock()

    cfg = get_settings()
    incident_payloads = [_payload_for_incident(i) for i in PAST_INCIDENTS]
    manual_payloads = [_payload_for_manual(m) for m in REPAIR_MANUALS]
    chunk_payloads_by_manual = {
        m.manual_id: [_payload_for_chunk(c) for c in m.chunks] for m in REPAIR_MANUALS
    }

    def _search(collection, vector=None, limit=10, filter=None):
        n = max(1, limit)
        if collection == cfg.past_incidents_collection:
            return [
                MagicMock(id=p["incident_id"], score=0.9 - 0.05 * i, payload=p)
                for i, p in enumerate(incident_payloads[:n])
            ]
        if collection == cfg.manuals_collection:
            return [
                MagicMock(id=p["manual_id"], score=0.85 - 0.05 * i, payload=p)
                for i, p in enumerate(manual_payloads[:n])
            ]
        if collection == cfg.manual_chunks_collection:
            manual_id = None
            try:
                if filter is not None:
                    inner = filter.get("must", [{}])[0]
                    manual_id = inner.get("match", {}).get("value")
            except (AttributeError, IndexError, TypeError):
                manual_id = None
            chunks = chunk_payloads_by_manual.get(manual_id) or [
                c for batch in chunk_payloads_by_manual.values() for c in batch
            ]
            return [
                MagicMock(id=p["chunk_id"], score=0.8 - 0.05 * i, payload=p)
                for i, p in enumerate(chunks[:n])
            ]
        return []

    client.points.search.side_effect = _search
    return client


def main() -> None:
    print("== smoke test (mock embeddings, mock VectorAI client) ==")

    print("[1] embedder ...")
    vec = embed("hello world")
    assert len(vec) == get_settings().embedding_dim, "embedding wrong size"
    print(f"    embedding dim = {len(vec)}  (mock={get_settings().use_mock_embeddings})")

    print("[2] sample stream ...")
    stream = generate_sample_stream()
    assert len(stream) > 60
    print(f"    {len(stream)} readings, sensors = {SENSOR_ORDER}")

    print("[3] detect ...")
    baseline = BaselineStats.from_window(stream[:60])
    spike_idx = 65
    anomaly = detect(stream[spike_idx], baseline, z_threshold=2.0)
    assert anomaly is not None, "expected an anomaly at the engineered spike"
    print(f"    detected severity={anomaly.severity}")
    print(f"    summary: {anomaly.summary}")

    print("[4] classify (mock client) ...")
    client = _make_fake_client()
    matches = classify(client, anomaly)
    assert matches, "classify returned nothing"
    print(f"    top match: {matches[0].incident.incident_id} score={matches[0].score:.3f}")

    print("[5] retrieve (mock client) ...")
    guidance = retrieve(client, matches)
    assert guidance, "retrieve returned nothing"
    print(f"    top guidance: {guidance[0].manual.manual_name} score={guidance[0].score:.4f}")

    print("[6] orchestrator.analyze ...")
    report = analyze(client, stream[spike_idx], baseline)
    assert isinstance(report, AnomalyReport)
    print(f"    AnomalyReport with {len(report.matches)} matches, {len(report.guidance)} guidance items")
    print(f"    JSON length = {len(report.model_dump_json())} bytes")

    print("\nAll smoke checks passed.")


if __name__ == "__main__":
    main()

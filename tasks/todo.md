# RigSense — Data Flow Framework

## Goal

Stand up the Python backend skeleton for RigSense so the dashboard (React, in
`src/`) and the hackathon judges can see a clean pipeline:

```
sensor stream  →  anomaly detection  →  incident classification  →  guidance retrieval
                                            (VectorAI DB)            (VectorAI DB)
```

This task is scaffolding only — every module gets real types, docstrings, and a
working stub backed by Actian VectorAI DB. No model training, no real LLM, no
React wiring yet.

## New folder layout

A new top-level folder `rigsense/` (sibling of `src/` and `vectorai-db-beta/`):

```
rigsense/
  README.md                  # how to run, env vars, demo script
  requirements.txt           # actian-vectorai wheel + sentence-transformers + numpy + pydantic + fastapi (optional)
  .env.example               # VECTORAI_HOST, EMBEDDING_MODEL, etc.
  pyproject.toml             # optional, keep it simple — start with requirements.txt only

  rigsense/
    __init__.py
    config.py                # Settings (collection names, dims, thresholds, host)
    schemas.py               # Pydantic models: SensorReading, PastIncident, RepairManual, RepairManualChunk, AnomalyEvent, ClassifiedAnomaly, GuidanceHit
    embeddings.py            # Lazy-loaded sentence-transformers wrapper (all-MiniLM-L6-v2, 384d)

    db/
      __init__.py
      client.py              # get_client() / async_client() context managers around VectorAIClient
      collections.py         # bootstrap_collections() — creates the 3 collections idempotently
      sensors.py             # upsert_reading(), recent_window(), baseline_stats()
      incidents.py           # upsert_incident(), search_similar(anomaly|text, k)
      manuals.py             # upsert_manual_chunks(), search_chunks(text|vector, k, manual_filter)

    pipeline/
      __init__.py
      detect.py              # rolling-window z-score / std-dev anomaly detector
      classify.py            # anomaly → top-k past incidents (cosine over description embedding + numeric distance over signature)
      retrieve.py            # incident_similarity × guide_similarity ranking
      orchestrator.py        # detect → classify → retrieve, returns a single AnomalyReport

    seed/
      __init__.py
      sample_sensors.py      # generates a baseline + injected anomalies for demo
      sample_incidents.py    # ~6 hand-written incidents covering the dashboard's metrics
      sample_manuals.py      # ~3 manuals chunked into ~20 chunks total

  scripts/
    bootstrap.py             # CLI: create collections + seed incidents + seed manuals
    run_demo.py              # CLI: stream sample sensors through the orchestrator and print AnomalyReports
```

## Data model

Three VectorAI collections, all keyed off the schemas in `schemas.py`:

1. `sensor_readings`
   - vector: the raw multi-sensor reading itself (length = number of tracked
     sensors, ordered by `config.SENSOR_ORDER`)
   - distance: `Euclid` (we want raw magnitude, not direction)
   - payload: `{ rig_id, asset_id, ts (iso), values: {sensor: float} }`

2. `past_incidents`
   - vector: semantic embedding of `description + failureType + incidentName`
     (384d, MiniLM)
   - distance: `Cosine`
   - payload: `{ incident_id, severity, description, failureType, incidentName, signature: {sensor: float} }`
     — `signature` is the snapshot sensor reading at the time of the incident,
     used for the numeric-distance side of classification.

3. `manual_chunks`
   - vector: semantic embedding of the chunk text (384d, MiniLM)
   - distance: `Cosine`
   - payload: `{ manual_id, manual_name, chunk_id, text, manual_summary }`
     — top-level manual metadata is duplicated onto each chunk so we don't need
     a separate `manuals` collection (keeps the demo to 3 collections, fewer
     round trips).

## Pipeline

- `detect.py`
  - `BaselineStats.from_window(readings, sensor_order)` → mean / std per sensor
  - `detect(reading, baseline, z_threshold=3.0)` → `AnomalyEvent | None`
    with a per-sensor z-score breakdown and an aggregate severity bucket
    (`Critical / Elevated / Watching`) matching the dashboard's `Severity` type.

- `classify.py`
  - Embed `f"{anomaly.metric} on {anomaly.scope} — {anomaly.signal}"` once
  - Hybrid score per candidate incident:
    `0.7 * cosine(text_emb, incident_emb) + 0.3 * (1 - normalized_l2(reading, incident.signature))`
  - Returns top-k `IncidentMatch` results.

- `retrieve.py`
  - For each top incident, embed
    `f"{incident.failureType}: {incident.description}"` (cache it on the
    payload at seed time so we don't re-embed at query time).
  - Search `manual_chunks` and rank chunks by
    `incident_similarity * chunk_similarity`, dedupe by `manual_id`, return the
    top `n_guides` distinct manuals with their best chunk.

- `orchestrator.py`
  - One function, `analyze_window(readings)`, that returns an `AnomalyReport`:

    ```python
    class AnomalyReport(BaseModel):
        anomaly: AnomalyEvent
        matches: list[IncidentMatch]   # top-k incidents
        guidance: list[GuidanceHit]    # top-n manual chunks
    ```

  - This is the single object the dashboard / API will consume later.

## Why this shape

- Mirrors the schema you sketched with ChatGPT 1:1 (SensorData / PastIncident /
  RepairManualChunk / RepairManual), but flattens manuals into chunks for fewer
  collections and fewer joins at query time.
- Keeps the three concerns (storage / detection / retrieval) in separate
  modules so subagents can iterate on each independently.
- Severity buckets match the dashboard's existing `Severity` type so the React
  side can stay untouched when we wire the API in a later task.
- No FastAPI yet — the orchestrator is a pure function; we add HTTP only when
  the dashboard needs it. Avoids over-engineering the scaffold.

## Checklist

- [ ] Create `rigsense/` folder structure (with `__init__.py` files)
- [ ] `requirements.txt` (pinned-ish) + `.env.example` + `README.md`
- [ ] `config.py` with collection names, dim, thresholds, sensor order, host
- [ ] `schemas.py` with all Pydantic models
- [ ] `embeddings.py` (lazy MiniLM wrapper, also exposes a deterministic mock
      for unit-test/no-network mode)
- [ ] `db/client.py`, `db/collections.py` (idempotent bootstrap)
- [ ] `db/sensors.py`, `db/incidents.py`, `db/manuals.py`
- [ ] `pipeline/detect.py`, `pipeline/classify.py`, `pipeline/retrieve.py`,
      `pipeline/orchestrator.py`
- [ ] `seed/sample_incidents.py`, `seed/sample_manuals.py`,
      `seed/sample_sensors.py`
- [ ] `scripts/bootstrap.py`, `scripts/run_demo.py`
- [ ] Verify: `python scripts/bootstrap.py` followed by `python scripts/run_demo.py`
      prints at least one well-formed `AnomalyReport`. (Requires the VectorAI
      Docker container running — README documents the prereq.)

## Out of scope for this task

- React/HTTP integration (separate task — the orchestrator returns a plain
  Pydantic object so wiring is trivial later).
- Real anomaly classifier / clustering. Z-score is enough for the scaffold.
- Real LLM-generated summaries. Guidance returns raw chunk text.
- Authentication, multi-rig fan-out, persistence outside VectorAI DB.

## Review

Scaffold landed under `backend/` (chose that over `rigsense/` per your pick)
with four VectorAI collections (`sensor_readings`, `past_incidents`, `manuals`,
`manual_chunks`) and the three-stage pipeline (detect -> classify -> retrieve)
orchestrated behind a single `analyze()` function that returns a Pydantic
`AnomalyReport`.

Verified end-to-end against a live `williamimoh/actian-vectorai-db:latest`
container:

- `python scripts/smoke_test.py` — offline, MiniLM mocked, VectorAI mocked.
  Exercises every module; passes.
- `python scripts/bootstrap.py` — live container. Creates all 4 collections,
  upserts 6 incidents, 4 manuals, 18 chunks. Exits 0.
- `python scripts/run_demo.py` — live container. Detects 21 anomalies across
  the synthetic stream; the engineered compressor event is correctly classified
  as `INC-8821 Compressor resonance spike during high-load transition` and the
  `Compressor Maintenance and Vibration Response` manual is returned as
  guidance. Final JSON `AnomalyReport` prints cleanly. Exits 0.

### Fixes made during implementation

- Point IDs must be UUIDs (server rejects `"INC-8821"` with 422). Added
  `backend/backend/db/_ids.py` with a `stable_id()` UUID5 helper so business
  IDs still map one-to-one onto VectorAI IDs deterministically across re-runs.
- `actian-vectorai` isn't on PyPI as a pre-release, so `requirements.txt`
  points at the bundled wheel in `../vectorai-db-beta/`.
- Added `backend/backend/embeddings.py` `_MockEmbedder` so the whole pipeline
  is runnable without downloading ~90 MB of MiniLM weights (flagged via
  `USE_MOCK_EMBEDDINGS=true`). Quality is obviously worse, but the pipeline
  shape is identical for scaffold verification.
- Added `scripts/smoke_test.py` to exercise the pipeline without touching
  VectorAI, so future CI can run it.

### Not done (intentional, per plan's "out of scope")

- No React / HTTP wiring. The orchestrator returns a Pydantic object that
  `model_dump_json()`s cleanly — adding a FastAPI wrapper later is a trivial
  follow-up task.
- No real classifier/clustering. Z-score is the scaffold's only detector.
- No LLM summary generation. Guidance returns raw chunk text.


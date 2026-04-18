# RigSense Backend

Python data-flow framework for RigSense: turn an offshore-rig sensor stream
into anomaly reports backed by Actian VectorAI DB.

```
sensor stream  ->  detect (rolling z-score)
                       |
                       v
                 classify (top-k past incidents)
                       |
                       v
                 retrieve (top manuals -> best chunks)
                       |
                       v
                 AnomalyReport (Pydantic) -> dashboard
```

## Layout

```
backend/
  backend/
    config.py          settings (host, collection names, dims, thresholds)
    schemas.py         pydantic models for the whole pipeline
    embeddings.py      MiniLM wrapper + deterministic offline mock
    db/                vectorai client + per-collection helpers
    pipeline/          detect / classify / retrieve / orchestrator
    seed/              sample incidents, manuals, sensor streams
  scripts/
    bootstrap.py       create collections + seed data
    run_demo.py        stream sample sensors and print AnomalyReports
```

## Prerequisites

1. Start the Actian VectorAI DB container (one-time, from
   `../vectorai-db-beta/`):

   ```bash
   cd ../vectorai-db-beta
   docker compose up -d
   ```

   Container exposes gRPC at `localhost:50051`.

2. Create a Python 3.10+ venv and install deps:

   ```bash
   python -m venv .venv
   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   # macOS / Linux
   source .venv/bin/activate

   pip install -r requirements.txt
   ```

3. (Optional) copy `.env.example` to `.env` and edit. All settings have
   sensible defaults so this is not required.

## Run

```bash
python scripts/bootstrap.py     # create collections + seed
python scripts/run_demo.py      # stream sensors and print reports
```

`bootstrap.py` is idempotent: re-running it drops and recreates the four
collections (`sensor_readings`, `past_incidents`, `manuals`, `manual_chunks`)
and re-seeds them.

## Mock embeddings

To run without downloading the MiniLM weights (e.g. on a fresh laptop with no
network), set `USE_MOCK_EMBEDDINGS=true` in `.env`. The mock is a deterministic
hash-based embedding so search is repeatable; quality is obviously much worse
than MiniLM but the pipeline shape is identical.

## Status

Scaffold only. The orchestrator returns plain Pydantic objects so wiring up
HTTP / the React dashboard in `../src/` is a separate, small task.

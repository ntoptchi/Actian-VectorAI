# RouteWise

**A pre-trip driving safety briefing for new drivers on unfamiliar long-distance routes, powered by Actian VectorAI DB.**

A 17-year-old has a 4-hour drive ahead — Miami to Tampa tonight, or Jacksonville to Pensacola tomorrow. They've never driven it. RouteWise takes the route and tonight's conditions, pulls real crashes that happened on roads like theirs in weather like theirs from an Actian VectorAI vector database, clusters them into the 3-6 places that actually deserve attention, and briefs the driver on each one — grounded in real investigator narratives, not model predictions.

Turn the vector database off and every briefing card goes blank. That's the honesty test.

---

## How Actian VectorAI DB Powers RouteWise

VectorAI DB is not a bolt-on in this project — it **is** the product. Two of the five deliverables in every trip briefing (route re-ranking and every coaching card) are literally powered by VectorAI DB retrieval. Without it, the chosen route collapses to "fastest" and every hotspot card goes blank.

### Two Collections, Two Shapes

We run two collections with deliberately different structures because they serve different jobs:

#### `routewise_crashes` — The Geographic Corpus

- ~140,000 FDOT crash records + 510 enriched news articles
- **Single dense vector** per point, 384-d, Cosine distance
- Payload carries `h3_cell`, `hour_bucket`, `weather`, `surface`, `lighting`, `severity`, `crash_type`, `aadt`, and the full `SituationDoc`
- Powers **route safety scoring** — filtering crashes by H3 cell corridors and time windows to score and re-rank route alternates

```python
client.collections.create(
    name,
    vectors_config=VectorParams(
        size=384,
        distance=Distance.Cosine,
    ),
)
```

#### `routewise_coaching` — The Lesson Corpus

- 518 LLM-enriched crash lessons built from Florida news reporting
- **Three dense named vectors** — `lesson`, `incident`, `factors_text` — for matching on distinct semantic facets
- **One sparse vector** (`factors`) over a frozen 40-term vocabulary for BM25-style keyword matching
- Powers **hotspot coaching cards** and **"Lessons from the road"** via three-channel hybrid retrieval + RRF fusion

```python
dense_config = {
    v: VectorParams(size=384, distance=Distance.Cosine)
    for v in ("lesson", "incident", "factors_text")
}
client.collections.create(
    name,
    vectors_config=dense_config,
    sparse_vectors_config={"factors": SparseVectorParams()},
)
```

### Three-Channel Hybrid Retrieval + RRF

For each hotspot, we run three parallel searches against `routewise_coaching`, each using a different named vector space, and fuse the rankings with Reciprocal Rank Fusion:

1. **`lesson` channel** — dense search matching the driver's situation against the LLM's `lesson_advice` field ("What should a driver do on a segment with following_too_close, rain, night?")
2. **`incident` channel** — dense search matching against the `retelling` field (incident summaries)
3. **`factors` sparse channel** — BM25-style keyword match over a frozen factor vocabulary, with fallback to dense `factors_text` if the server doesn't support sparse

```python
results_lesson = client.points.search(
    collection,
    vector=embed_one(lesson_query),
    using="lesson",
    limit=PER_CHANNEL_LIMIT,
    with_payload=True,
)
results_incident = client.points.search(
    collection,
    vector=embed_one(incident_query),
    using="incident",
    limit=PER_CHANNEL_LIMIT,
    with_payload=True,
)
# Sparse factor search
results_factors = client.points.search(
    collection,
    vector=SparseVector(indices=indices, values=values),
    using="factors",
    limit=PER_CHANNEL_LIMIT,
    with_payload=True,
)

# Fuse with RRF (from the actian_vectorai library)
fused = reciprocal_rank_fusion(channel_results, limit=limit, ranking_constant_k=60)
```

RRF is the right fusion method here because the three channels have different score scales (cosine vs sparse dot product) — RRF normalizes by rank, not score, so we don't have to tune per-channel weights.

### Connection via gRPC

RouteWise connects to the VectorAI DB over gRPC using the official `actian_vectorai` Python client:

```python
from actian_vectorai import VectorAIClient

client = VectorAIClient("localhost:50051", timeout=120.0)
client.connect()
```

The 120s timeout is a deliberate bump from the library's 30s default to survive bulk ingestion pauses when the engine flushes its index.

### VectorAI DB Library Features Used

| Feature | Library example | Where in RouteWise |
|---|---|---|
| Named vectors | `examples/29_named_vectors.py` | `backend/coaching_vdb.py` — three dense vectors per coaching point |
| Sparse vectors | `examples/33_sparse_vectors.py` | `backend/coaching_vdb.py` — factor keyword matching |
| Hybrid fusion (RRF) | `examples/15_hybrid_fusion.py` | `backend/services/coaching_retrieval.py` — fusing 3 channels |
| Batched upsert | core API | `backend/ingest/upsert.py` — 256-point batches with retry |
| Collection management | core API | `backend/vdb.py`, `backend/coaching_vdb.py` |

---

## Embedding Model

**Model:** [`sentence-transformers/all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)

- **Dimensions:** 384
- **Normalization:** L2-normalized (cosine distance on normalized vectors = dot product)
- **Runs offline:** model weights are bundled locally in `models/all-MiniLM-L6-v2/`, no HuggingFace download at runtime
- **Device auto-detection:** CUDA -> MPS (Apple Silicon) -> CPU, or override with `ROUTEWISE_EMBED_DEVICE`

The same model and the same `SituationDoc` narrative template are used at both **index time** and **query time** — this shared schema is what makes cosine similarity actually mean "this trip resembles this crash's situation." Most vector DB demos quietly get this wrong by embedding queries and documents through different pipelines.

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("models/all-MiniLM-L6-v2", device="cpu")
vectors = model.encode(texts, normalize_embeddings=True, batch_size=128)
```

---

## How the Data Flows

### Ingestion (one-time)

1. Normalize FDOT crash records + news articles into `SituationDoc` (shared Pydantic model)
2. Attach H3 cells (resolution 9, ~150m hexagons) and AADT traffic volumes
3. Render a deterministic English narrative via `render_narrative()`
4. Embed with MiniLM (384-d, L2-normalized)
5. Upsert into VectorAI DB with deterministic `uuid5` point IDs (idempotent retry on timeout)

### Query (per trip brief)

1. Fetch route alternates from local OSRM, weather from Open-Meteo
2. Build a conditions-only `SituationDoc`, embed once (shared across all alternates)
3. For each alternate: compute H3 cell corridor, retrieve matching crashes from VectorAI DB, score per-segment and per-route risk
4. Pick the recommended route: `argmin(duration_norm + 0.4 * risk_norm)`
5. For each hotspot: run three-channel hybrid retrieval against `routewise_coaching`, fuse with RRF, attach coaching line and real crash lesson
6. Dedupe insights across hotspot cards and the "Lessons from the road" sidebar

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Vector DB** | Actian VectorAI DB (Docker, gRPC on port 50051) |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` (384-d, bundled offline) |
| **Backend** | FastAPI + Uvicorn |
| **Frontend** | Next.js 15 + React 19 + TypeScript |
| **Maps** | Leaflet + protomaps-leaflet + local PMTiles (served by FastAPI) |
| **Routing** | Self-hosted OSRM (Docker, Florida road network) |
| **Weather** | Open-Meteo (free, no API key) |
| **Geo/Risk** | h3, shapely, geopandas, scikit-learn, pandas, numpy |

Everything except weather resolves to `localhost` — the entire stack runs offline.

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### 1. Clone and install

```bash
git clone <repo-url>
cd Actian-VectorAI
./install.sh
```

The install script:
- Starts the VectorAI DB and OSRM containers via `docker compose up -d`
- Installs the `actian_vectorai` client from the bundled wheel
- Downloads the embedding model (if not already present)
- Fetches a pre-built VDB snapshot so you don't have to re-embed ~140K crash records (~1hr on CPU)
- Installs Python and Node.js dependencies

### 2. Start the stack

```bash
docker compose up -d      # VectorAI DB (port 50051) + OSRM (port 5001)
```

Start the backend:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8080
```

Start the frontend:

```bash
cd routewise && npm run dev
```

### 3. Try it

Open `http://localhost:3000`, enter an origin and destination in Florida (e.g. Miami to Tampa), and get your pre-trip safety briefing.

---

## Environment Variables

All backend settings use the `ROUTEWISE_` prefix (via Pydantic Settings):

| Variable | Default | Description |
|---|---|---|
| `ROUTEWISE_VDB_HOST` | `localhost` | VectorAI DB host |
| `ROUTEWISE_VDB_PORT` | `50051` | VectorAI DB gRPC port |
| `ROUTEWISE_VDB_COLLECTION` | `routewise_crashes` | Crash corpus collection name |
| `ROUTEWISE_VDB_COACHING_COLLECTION` | `routewise_coaching` | Coaching lesson collection name |
| `ROUTEWISE_VDB_VECTOR_SIZE` | `384` | Embedding dimensionality |
| `ROUTEWISE_MODEL_DIR` | `models/all-MiniLM-L6-v2` | Path to bundled MiniLM weights |
| `ROUTEWISE_EMBED_DEVICE` | auto-detect | Force embedding device (`cuda`, `mps`, `cpu`, `dml`) |
| `ROUTEWISE_EMBED_BATCH_SIZE` | `128` | Embedding batch size |

---

## Project Structure

```
├── backend/
│   ├── main.py                          # FastAPI app + PMTiles tile server
│   ├── config.py                        # Pydantic Settings (ROUTEWISE_* env vars)
│   ├── embeddings.py                    # MiniLM wrapper (embed / embed_one)
│   ├── schemas.py                       # SituationDoc — shared index + query schema
│   ├── vdb.py                           # routewise_crashes collection wiring
│   ├── coaching_vdb.py                  # routewise_coaching collection wiring (multi-vector + sparse)
│   ├── routers/
│   │   └── trip.py                      # /trip/brief orchestration + route re-ranking
│   ├── services/
│   │   ├── scoring.py                   # VDB-driven per-segment and per-route risk
│   │   ├── coaching_retrieval.py        # Three-channel hybrid retrieval + RRF fusion
│   │   ├── crash_cache.py              # In-memory corpus cache (workaround for missing server-side indexes)
│   │   ├── routing.py                   # Local OSRM client
│   │   └── coaching.py                  # Rule-based coaching fallback
│   └── ingest/
│       ├── upsert.py                    # Batched embed + upsert with timeout retry
│       ├── situation_doc.py             # render_narrative() — shared between ingest + query
│       └── factor_vocab.py             # Sparse vocabulary + coarse-to-rich tag bridge
├── routewise/                           # Next.js 15 frontend
├── scripts/
│   ├── ingest_fdot_crash.py             # Crash corpus ingestion
│   ├── ingest_coaching.py               # Coaching collection ingestion (multi-vector + sparse)
│   ├── fetch_vdb_snapshot.py            # Pre-built snapshot downloader
│   └── download_model.py               # MiniLM model fetcher
├── models/all-MiniLM-L6-v2/            # Bundled embedding model weights
├── vectorai-db-beta/                    # Actian client wheel + examples + data volume
├── docker-compose.yml                   # VectorAI DB + OSRM containers
├── install.sh                           # One-command setup
└── requirements.txt                     # Python dependencies
```

---

## Operational Design Decisions

**Deterministic point IDs.** All ingest scripts use `uuid5(namespace, source + case_id)`. Resumed ingests are idempotent — duplicate writes are harmless.

**Batched upsert with retry.** The VDB server occasionally pauses 30-60s for index flushing under sustained write pressure. Upserts retry with linear backoff on `DEADLINE_EXCEEDED`, and idempotent IDs mean retries are safe.

**Server capability probing.** We don't trust the server's self-reported sparse support. The coaching collection setup does a real round-trip upsert of a probe point and only treats sparse as available when the point actually survives. If the server lies, we recreate dense-only.

**Graceful degradation.** Every VDB retrieval is wrapped in try/except. If the VDB is down: scoring collapses to 0, coaching returns empty, and the chosen route falls back to fastest. The UI renders neutral — it never fakes a result.

**Pre-built snapshot.** Rebuilding the crash corpus from raw data is ~1hr of CPU embedding. We ship a snapshot artifact so new contributors pull pre-embedded data and skip the wait.

**Coarse-to-rich vocabulary bridge.** The segment scorer emits coarse factors (`rear_end`, `wet`). The LLM-enriched coaching corpus uses richer tags (`following_too_close`, `impaired_alcohol`). A frozen bridge map keeps query and index vocabularies aligned so sparse retrieval actually fires.

---

## Demo Corridors

Three pre-verified Florida routes that showcase different retrieval patterns:

- **Miami -> Tampa** via I-75 / Alligator Alley (~280 mi, ~4h) — urban to rural interstate, afternoon thunderstorm corridor
- **Jacksonville -> Pensacola** via I-10 (~360 mi, ~5.5h) — long rural interstate, high fatigue signature, limited services
- **Orlando <-> Tampa** via I-4 (~85 mi, ~1.5h) — "Florida's deadliest interstate" verification demo

---

## License

Built for the Actian Build Challenge hackathon, April 2026.

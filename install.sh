#!/usr/bin/env bash
# RouteWise install script (bash / Git Bash / WSL / macOS / Linux).
#
# Goal: a fresh `git pull` + `cp .env.example .env` + `./install.sh` should
# leave the user able to run `./start.sh` and hit a fully populated trip
# planner. Idempotent — re-run any time, expensive steps are skipped if
# already done.
set -euo pipefail

cd "$(dirname "$0")"

section() { printf "\n\033[36m=== %s ===\033[0m\n" "$1"; }
info()    { printf "\033[2m[install] %s\033[0m\n" "$1"; }
warn()    { printf "\033[33m[install] %s\033[0m\n" "$1"; }
die()     { printf "\033[31m[install] %s\033[0m\n" "$1" >&2; exit 1; }

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    die "missing dependency: $1 — $2"
  fi
}

# ---------------------------------------------------------------------------
section "Checking prerequisites"
# ---------------------------------------------------------------------------
need python3  "Install Python 3.11+ (https://www.python.org/downloads/)"
need docker  "Install Docker Desktop (https://www.docker.com/products/docker-desktop/)"
need node    "Install Node.js 20+ (https://nodejs.org/)"
need npm     "Comes with Node.js"

if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    cp .env.example .env
    info "created .env from .env.example (placeholder ORS key)."
    info "  edit .env and drop in a real OPEN_ROUTE_SERVICE_API_KEY for"
    info "  multi-alternate routing — without it the backend falls back"
    info "  to OSRM single-route and you only see one route option."
  else
    warn ".env missing and no .env.example to copy from. Routing will fall back to OSRM."
  fi
fi

# ---------------------------------------------------------------------------
section "Python venv (.venv)"
# ---------------------------------------------------------------------------
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  info "created .venv"
else
  info ".venv already exists"
fi

# Pick the right venv python depending on platform (Windows uses Scripts/, *nix bin/).
if [ -x ".venv/Scripts/python.exe" ]; then
  VENV_PY=".venv/Scripts/python.exe"
else
  VENV_PY=".venv/bin/python"
fi

"$VENV_PY" -m pip install --upgrade pip wheel >/dev/null
"$VENV_PY" -m pip install -r requirements.txt

# ---------------------------------------------------------------------------
section "Actian VectorAI DB python client"
# ---------------------------------------------------------------------------
WHEEL="$(ls vectorai-db-beta/actian_vectorai-*.whl 2>/dev/null | head -n1 || true)"
if [ -n "$WHEEL" ]; then
  "$VENV_PY" -m pip install --upgrade "$WHEEL"
else
  die "no actian_vectorai wheel found in vectorai-db-beta/ — the VDB client is required."
fi

# ---------------------------------------------------------------------------
section "Embedding model (all-MiniLM-L6-v2)"
# ---------------------------------------------------------------------------
"$VENV_PY" scripts/download_model.py

# Prewarm the embedder so the 5-10s transitive-import cost of
# sentence_transformers + transformers + huggingface_hub + requests +
# charset_normalizer happens here (visibly, in its own install step)
# rather than silently during the first batch of the ingest. On CPU
# that scary "it's frozen" moment is what tempts people to Ctrl+C
# mid-embed; doing it up-front also warms the .pyc cache for the
# subsequent ingest subprocesses.
info "Warming MiniLM (first import is ~5-10s; subsequent Python processes reuse the .pyc cache)..."
"$VENV_PY" -c "from backend.embeddings import embed; _ = embed(['warmup'])" \
  || warn "MiniLM warmup failed — ingest will still try to load it lazily."

# ---------------------------------------------------------------------------
section "Frontend (routewise/)"
# ---------------------------------------------------------------------------
( cd routewise && npm install )

# Frontend env: the only required value is BACKEND_URL, which already has
# a sane default in src/env.js. Still drop a .env file so Next stops
# warning about missing env on first boot.
if [ ! -f "routewise/.env" ]; then
  cp routewise/.env.example routewise/.env
  info "created routewise/.env from .env.example"
fi

# ---------------------------------------------------------------------------
section "Pulling Actian VectorAI DB Docker image"
# ---------------------------------------------------------------------------
docker pull williamimoh/actian-vectorai-db:latest >/dev/null
info "image ready"

# ---------------------------------------------------------------------------
section "Local map stack (OSRM routing + PMTiles basemap)"
# ---------------------------------------------------------------------------
# scripts/setup_local_map.sh is fully idempotent:
#   * OSRM: skipped if osrm-data/florida-latest.osrm already exists.
#   * PMTiles: skipped if tiles-data/florida.pmtiles already exists.
#   * pmtiles CLI: auto-installed into .bin/ on first run, reused after.
#
# First-run cost on a cold box is ~5 min for OSRM preprocessing + ~2 min
# for the PMTiles extract. Both run against real network + Docker, so
# we surface any failure as a hard error — without these assets the
# start.sh precheck will refuse to bring the services up.
bash scripts/setup_local_map.sh \
  || die "local map setup failed — see output above. Re-run ./install.sh once the issue is resolved."

# ---------------------------------------------------------------------------
section "Fetching pre-built VDB snapshot (optional fast-path)"
# ---------------------------------------------------------------------------
# Maintainers publish a gzipped dump of the fully-embedded collection as a
# GitHub Release asset (see scripts/dump_vdb_snapshot.py). If the URL in
# vdb_snapshot.manifest.json is set, teammates download + extract it here
# and skip the ~20-minute local FDOT+news ingest entirely (the fetch script
# writes the ingest marker so the seeding section below no-ops).
#
# Must run BEFORE the VDB container boots: vectorai-db-beta indexes are
# memory-mapped *.btr files, and extracting over a live collection silently
# corrupts whatever segment is currently paged in. We defensively stop any
# already-running container so re-running install.sh mid-update is safe.
# The normal `compose up -d` below restarts it.
if docker compose ps -q 2>/dev/null | grep -q .; then
  info "stopping running VDB container before extracting snapshot..."
  docker compose stop vectoraidb >/dev/null 2>&1 || true
fi

set +e
"$VENV_PY" scripts/fetch_vdb_snapshot.py
SNAPSHOT_RC=$?
set -e
case "$SNAPSHOT_RC" in
  0) info "snapshot applied — seeding section will skip the local ingest." ;;
  1) info "no snapshot applied — continuing with the normal ingest flow." ;;
  2) die  "VDB snapshot download was corrupt. Delete vdb_snapshot.tar.gz and re-run install.sh, or set ROUTEWISE_SKIP_VDB_SNAPSHOT=1 to fall back to a local ingest." ;;
  *) warn "fetch_vdb_snapshot.py returned unexpected code $SNAPSHOT_RC — continuing with ingest." ;;
esac

# ---------------------------------------------------------------------------
section "Booting Actian VectorAI DB (one-time, for seeding)"
# ---------------------------------------------------------------------------
# We need the container running to seed it. Bring it up here, leave it up
# afterwards — start.sh will reuse the same container (compose up -d is a
# no-op if it's already running).
docker compose up -d vectoraidb
"$VENV_PY" scripts/wait_vdb.py --timeout 90 \
  || die "VectorAI DB never came up. Check 'docker compose logs vectoraidb'."

# ---------------------------------------------------------------------------
section "Building processed data tables"
# ---------------------------------------------------------------------------
# These are tiny (<1s each) and feed the segment / hotspot scoring logic.
mkdir -p data/processed
"$VENV_PY" scripts/build_baselines.py     || warn "build_baselines failed — non-fatal, falls back to a constant FL average."
"$VENV_PY" scripts/load_aadt_table.py     || warn "load_aadt_table failed — non-fatal, AADT shapefile spatial join still works."
"$VENV_PY" scripts/load_night_segments.py || warn "load_night_segments failed — non-fatal, night-skew tag will be off."

# ---------------------------------------------------------------------------
section "Fetching FDOT crash chunks (if missing)"
# ---------------------------------------------------------------------------
# data/raw/crash{1000..150000}.json is committed to git, but a thin clone
# (sparse-checkout, partial clone, or anyone trimming the ~213 MB raw/
# tree to keep their fork small) won't have them. Auto-pull whatever's
# missing from the FDOT ArcGIS REST API. Existing files are skipped, so
# this is cheap on a normal full clone (a couple of seconds).
EXPECTED_CHUNKS=150
HAVE_CHUNKS="$(ls data/raw/crash*.json 2>/dev/null | wc -l | tr -d ' ')"
if [ "${HAVE_CHUNKS:-0}" -lt "$EXPECTED_CHUNKS" ]; then
  info "have $HAVE_CHUNKS / $EXPECTED_CHUNKS FDOT crash chunks — fetching the rest from FDOT (~213 MB total, ~5-10 min on a fresh box)."
  "$VENV_PY" scripts/fetch_fdot_crashes.py --start 1 --end "$EXPECTED_CHUNKS" \
    || warn "FDOT fetch returned non-zero — some chunks may be missing. Re-run install.sh to retry."
else
  info "all $HAVE_CHUNKS FDOT crash chunks already present."
fi

# ---------------------------------------------------------------------------
section "Seeding VectorAI DB (real FDOT crashes + news articles)"
# ---------------------------------------------------------------------------
# Two real-data sources land in the same routewise_crashes collection:
#   1. data/raw/crash*.json          — ~150 FDOT ArcGIS chunks (~140K crashes
#                                      after we drop rows with missing
#                                      CRASH_TIME).
#   2. data/raw/semantic_crashes.json — scraped news articles semantically
#                                      matched to FDOT crashes; each article
#                                      becomes a source="NEWS" SituationDoc
#                                      whose h3_cell / hour_bucket / weather
#                                      are inherited from the linked crash,
#                                      so news surfaces through the same
#                                      H3 + conditions retrieval path.
#
# --- Embedding is CPU-bound, so the corpus is downsampled ---
# MiniLM on CPU is the bottleneck (all full 150K rows takes 8-17 min on
# a laptop). The hotspot / intensity_ratio pipeline is density-based,
# so a uniform Bernoulli sample of ~FDOT_SAMPLE rows produces the same
# hotspots in the same places, just with fewer example crashes each.
# I-75 / I-4 / I-10 are still saturated. Bump FDOT_SAMPLE if you
# demo on a rural corridor and want more statistical power per cell,
# or set it to "" to ingest the whole corpus. Override with the
# ROUTEWISE_FDOT_SAMPLE env var for a one-off run.
#
# About GPUs: sentence-transformers will auto-use CUDA (NVIDIA) or
# Apple MPS if available. CUDA is NVIDIA-only — AMD Radeon on Windows
# does NOT get a "pip install torch" GPU path. If you want DirectML
# on AMD/Intel Windows, `pip install torch-directml` and set
# ROUTEWISE_EMBED_DEVICE=dml. Otherwise CPU with a batch_size=128
# (the default in backend/embeddings.py) is the realistic speed
# ceiling for this project.
# Ingestion freshness is tracked with a marker file. If it's missing — or
# the collection has fewer points than a healthy ingest produces — we
# re-run both ingesters. Bump INGEST_VERSION when normalize.py /
# situation_doc.py / schemas.py change in a way that would alter what
# gets indexed, or when stale junk needs evicting:
#   v2 → v3: dropped the ~500 synthetic SYN-###### anchor crashes.
#   v3 → v4: switched from full-corpus to Bernoulli sample (FDOT_SAMPLE).
INGEST_VERSION="4"
INGEST_MARKER="data/processed/.fdot_ingest_v${INGEST_VERSION}"

# --- FDOT sample size, interactive prompt ---
# Respect a pre-set env var (CI, power users, non-interactive re-runs)
# and fall back to an interactive menu otherwise. Skipped entirely if
# stdin isn't a TTY (piped install / automated provisioner) or if the
# ingest marker already looks healthy — no point asking about a size
# we aren't about to use.
_prompt_fdot_sample() {
  # IMPORTANT: this function is called via $(...) command substitution,
  # so anything on stdout becomes the function's return value. The menu
  # and the read prompt must therefore be written to /dev/tty, and only
  # the final numeric answer is echoed to stdout. Writing the menu to
  # stdout (as I did on the first pass) capture-poisons FDOT_SAMPLE
  # with the menu text, and the later arithmetic $(( FDOT_SAMPLE ... ))
  # explodes under `set -u` because bash tries to resolve each word in
  # the multi-line string as a variable name.
  cat >/dev/tty <<'EOF'

  FDOT corpus size
  ----------------
  MiniLM on CPU embeds ~30 texts/s on a laptop; pick how much of the
  ~140K FDOT crash corpus to ingest. All ~500 scraped news articles
  are always fully embedded on top of this (they're small and every
  one carries unique narrative context that crash rows don't).
  Hotspots look the same from ~20K onward because retrieval is
  density-based, so 20K is usually enough.

    1)   5,000   ~ 30 sec      fastest, good enough for UI smoke test
    2)  20,000   ~ 2 min       default, full interstate hotspot coverage
    3)  50,000   ~ 5 min       more signal for rural / secondary roads
    4) 140,000   ~15 min       full corpus (skip the sampler entirely)

EOF
  local choice=""
  # Prompt AND response both on /dev/tty so users still get a usable
  # prompt when stdin/stdout are redirected by a wrapper script.
  printf '  Choice [1-4, default 2]: ' >/dev/tty
  read -r choice </dev/tty || choice=""
  case "${choice:-2}" in
    1|5k|5K|5000) echo 5000 ;;
    2|20k|20K|20000|"") echo 20000 ;;
    3|50k|50K|50000) echo 50000 ;;
    4|140k|140K|140000|full|all) echo "" ;;  # "" = ingest full corpus
    *)
      warn "unrecognised choice '$choice' — falling back to 20,000." >&2
      echo 20000
      ;;
  esac
}

if [ -n "${ROUTEWISE_FDOT_SAMPLE+x}" ]; then
  # env var set (possibly empty-string → full corpus); honour it as-is
  FDOT_SAMPLE="$ROUTEWISE_FDOT_SAMPLE"
  info "using ROUTEWISE_FDOT_SAMPLE=${FDOT_SAMPLE:-<full corpus>}"
elif [ ! -t 0 ] && [ ! -e /dev/tty ]; then
  # non-interactive shell, can't prompt — take the safe default
  FDOT_SAMPLE="20000"
  info "non-interactive shell detected — defaulting FDOT_SAMPLE=20000"
elif [ -f "$INGEST_MARKER" ]; then
  # marker present → we might skip seeding entirely. Don't prompt yet;
  # pick the default so the marker-check below can decide.
  FDOT_SAMPLE="20000"
else
  FDOT_SAMPLE="$(_prompt_fdot_sample)"
  info "FDOT_SAMPLE=${FDOT_SAMPLE:-<full corpus>}"
fi

# Defense-in-depth: FDOT_SAMPLE must be empty OR all-digits. Anything
# else indicates a capture-poisoning bug (menu text leaked into the
# $() result). Fail fast with a clear message instead of exploding
# cryptically inside the arithmetic expansion below.
case "$FDOT_SAMPLE" in
  ""|*[!0-9]*)
    if [ -n "$FDOT_SAMPLE" ]; then
      die "FDOT_SAMPLE is non-numeric (got: $(printf '%q' "$FDOT_SAMPLE")) — prompt logic bug."
    fi
    ;;
esac

# Floor for "seeding worked". Scales with FDOT_SAMPLE (we expect
# ~94% of sampled rows to survive normalisation after the
# missing-CRASH_TIME drop), plus a handful of news docs. Empty
# FDOT_SAMPLE means "ingest the whole corpus", so fall back to the
# old 100K floor.
if [ -n "$FDOT_SAMPLE" ]; then
  HEALTHY_MIN="$(( FDOT_SAMPLE * 80 / 100 ))"
else
  HEALTHY_MIN=100000
fi

if [ -f "$INGEST_MARKER" ] \
   && "$VENV_PY" scripts/vdb_count.py --min "$HEALTHY_MIN" >/dev/null 2>&1; then
  EXISTING="$("$VENV_PY" scripts/vdb_count.py)"
  info "VDB already populated ($EXISTING points, ingest v${INGEST_VERSION}) — skipping reseed."
  info "  to force a fresh ingest: rm $INGEST_MARKER  (and re-run install.sh)"
else
  if [ -f "$INGEST_MARKER" ]; then
    info "marker present but VDB has fewer than $HEALTHY_MIN points — re-running ingest."
  else
    info "no v${INGEST_VERSION} ingest marker — running fresh ingest."
  fi

  # Any previous-version marker (e.g. the old v2 that seeded synthetic
  # SYN-###### anchor crashes) means the collection carries stale docs
  # that a plain re-ingest won't overwrite — point IDs are uuid5(source,
  # case_id), so synthetic case_ids persist forever unless dropped. Wipe
  # the collection on version bumps so re-ingest lands on a clean slate.
  STALE_MARKER="$(ls data/processed/.fdot_ingest_v* 2>/dev/null | grep -v "v${INGEST_VERSION}\$" | head -n1 || true)"
  if [ -n "$STALE_MARKER" ]; then
    info "detected older ingest marker ($STALE_MARKER) — wiping VDB collection to drop stale (incl. synthetic) records."
    "$VENV_PY" scripts/_wipe_collection.py
    rm -f "$STALE_MARKER"
  fi

  CRASH_FILES="$(ls data/raw/crash*.json 2>/dev/null | wc -l | tr -d ' ')"
  if [ "$CRASH_FILES" -gt 0 ]; then
    if [ -n "$FDOT_SAMPLE" ]; then
      info "Ingesting $CRASH_FILES FDOT crash chunks, uniform-sampling ~${FDOT_SAMPLE} rows (CPU-bound embedding; set ROUTEWISE_FDOT_SAMPLE='' to ingest the full ~140K corpus)..."
      "$VENV_PY" scripts/ingest_fdot_crash.py --sample "$FDOT_SAMPLE"
    else
      info "Ingesting $CRASH_FILES FDOT crash chunks (~140K rows; ~5-10 min on first run, mostly embedding)..."
      "$VENV_PY" scripts/ingest_fdot_crash.py
    fi
  else
    warn "no data/raw/crash*.json files found — skipping FDOT ingest. Re-run install.sh once the FDOT fetch step succeeds."
  fi

  # Scraped news articles linked to FDOT crashes (spec.md). The script
  # globs data/raw/semantic_crashes*.json + *news*.json by default.
  NEWS_FILES="$(ls data/raw/semantic_crashes*.json data/raw/*news*.json 2>/dev/null | wc -l | tr -d ' ')"
  if [ "$NEWS_FILES" -gt 0 ]; then
    info "Ingesting $NEWS_FILES news article file(s) (semantic-embedding each article alongside its linked crash)..."
    "$VENV_PY" scripts/ingest_news.py \
      || warn "news ingest returned non-zero — some articles may be missing."
  else
    info "no news article JSON files found in data/raw/ — skipping news ingest."
  fi

  # Only write the marker if at least one real-data ingest ran. That
  # way a box with no crash chunks *and* no news files doesn't silently
  # convince future install.sh runs that seeding is done.
  if [ "${CRASH_FILES:-0}" -gt 0 ] || [ "${NEWS_FILES:-0}" -gt 0 ]; then
    mkdir -p data/processed
    : > "$INGEST_MARKER"
    info "wrote ingest marker $INGEST_MARKER"
  fi

  FINAL="$("$VENV_PY" scripts/vdb_count.py)"
  info "VDB now contains $FINAL points."
fi

# ---------------------------------------------------------------------------
section "Done"
# ---------------------------------------------------------------------------
cat <<'EOF'
Install complete. Next:

  ./start.sh              # boots VDB (docker), backend (:8080), frontend (:3000)

Notes for first run:
  * The backend warms an in-memory crash cache on startup (size =
    whatever FDOT_SAMPLE you ingested, plus news docs). It runs on a
    daemon thread so the API binds immediately; start.sh waits for
    the warm-up before opening the frontend.
  * To ingest the full ~140K-row FDOT corpus instead of the default
    20K sample, set ROUTEWISE_FDOT_SAMPLE='' (empty) before install.sh.
    Only worth it if you have an NVIDIA GPU or patience — MiniLM is
    the bottleneck, not the VDB upsert.
  * AMD Radeon on Windows = CPU-only by default. See the "GPU" note
    in the seeding section of install.sh for the DirectML escape hatch.
  * The trip planner needs an OPEN_ROUTE_SERVICE_API_KEY in .env to
    return alternate routes. Without it you only see one route.
EOF

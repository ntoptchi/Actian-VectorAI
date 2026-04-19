#!/usr/bin/env bash
# RouteWise start script.
#
# Boots: Actian VectorAI DB (docker), FastAPI backend (:8080), Next.js dev
# server (:3000). Ctrl-C cleanly stops the backend; the VDB container is
# left running so the next start is instant.
set -euo pipefail

cd "$(dirname "$0")"

section() { printf "\n\033[36m=== %s ===\033[0m\n" "$1"; }
info()    { printf "\033[2m[start] %s\033[0m\n" "$1"; }
warn()    { printf "\033[33m[start] %s\033[0m\n" "$1"; }
die()     { printf "\033[31m[start] %s\033[0m\n" "$1" >&2; exit 1; }

# Best-effort PID lookup for whoever is bound to a TCP port. Tries the
# usual unix tools first; on Git Bash / Cygwin (no lsof) it falls back to
# Windows' netstat. Returns the PID(s) on stdout, empty if free.
port_owner() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null || true
  elif command -v ss >/dev/null 2>&1; then
    ss -ltnp 2>/dev/null | awk -v p=":$port" '$4 ~ p {print $0}' \
      | grep -oE 'pid=[0-9]+' | cut -d= -f2 || true
  elif command -v netstat >/dev/null 2>&1; then
    # Windows netstat (Git Bash inherits PATH from cmd's). Columns:
    #   1=Proto  2=LocalAddr  3=ForeignAddr  4=State  5=PID
    # Match Local Address that ends in :PORT and is in LISTENING state.
    # We exclude the IPv6 wildcard form ([::]:PORT) only to avoid printing
    # the same PID twice when uvicorn binds dual-stack.
    netstat -ano 2>/dev/null \
      | awk -v p=":$port" '$1=="TCP" && $2 ~ p"$" && $4=="LISTENING" && $2 !~ /^\[::\]/ {print $NF}'
  fi
}

# Cross-platform "kill this PID". Bash's own `kill` doesn't accept
# Windows-native PIDs from netstat under Git Bash (different PID
# namespace), and MSYS aggressively rewrites slash-args, mangling
# `taskkill //F //PID` so the command silently no-ops. Routing through
# Python sidesteps both problems: argv is passed verbatim, os.kill goes
# straight to TerminateProcess on Windows and SIGTERM on unix.
kill_pid() {
  local pid="$1"
  if [ -z "$pid" ]; then return; fi
  if [ -n "${VENV_PY:-}" ] && [ -x "$VENV_PY" ]; then
    "$VENV_PY" -c '
import os, signal, subprocess, sys
pid = int(sys.argv[1])
try:
    os.kill(pid, signal.SIGTERM)
except (OSError, ProcessLookupError):
    # On Windows os.kill maps to TerminateProcess; on unix this is a
    # graceful SIGTERM. If that fails (race with already-exited proc,
    # or insufficient privilege) fall back to taskkill on Windows.
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                       capture_output=True, check=False)
' "$pid" >/dev/null 2>&1 || true
  else
    kill -9 "$pid" 2>/dev/null || true
  fi
}

# Pick the right venv python depending on platform.
if [ -x ".venv/Scripts/python.exe" ]; then
  VENV_PY=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
  VENV_PY=".venv/bin/python"
else
  die ".venv missing — run ./install.sh first."
fi

# ---------------------------------------------------------------------------
section "Starting Actian VectorAI DB"
# ---------------------------------------------------------------------------
docker compose -f vectorai-db-beta/docker-compose.yml up -d
"$VENV_PY" scripts/wait_vdb.py --timeout 60 \
  || die "VectorAI DB never came up. Check 'docker compose -f vectorai-db-beta/docker-compose.yml logs'."

# Sanity check: warn loudly if the collection is empty. Most "the trip
# page is broken" reports trace back to nobody having run install.sh.
COUNT="$("$VENV_PY" scripts/vdb_count.py 2>/dev/null || echo 0)"
if [ "${COUNT:-0}" -lt 100 ]; then
  warn "VDB is empty (only $COUNT points). The frontend will load but every"
  warn "      hotspot/segment will read as zero risk. Run ./install.sh to seed."
else
  info "VDB has $COUNT crash records."
fi

# ---------------------------------------------------------------------------
section "Starting FastAPI backend on :8080"
# ---------------------------------------------------------------------------
# Detect a stale uvicorn (most common cause: previous start.sh killed by
# something other than Ctrl-C, e.g. the IDE closing the terminal). Without
# this, uvicorn just dies with WinError 10013 / EADDRINUSE and the user
# gets no hint about what to do.
EXISTING="$(port_owner 8080 | head -n1 | tr -d '[:space:]')"
if [ -n "$EXISTING" ]; then
  warn "port 8080 already in use (pid $EXISTING) — assuming it's a stale uvicorn from a prior run, killing it."
  kill_pid "$EXISTING"
  sleep 3
  STILL="$(port_owner 8080 | head -n1 | tr -d '[:space:]')"
  if [ -n "$STILL" ]; then
    die "port 8080 is still held by pid $STILL after kill attempt. Stop it manually and re-run."
  fi
fi

BACKEND_PID=""
cleanup() {
  if [ -n "$BACKEND_PID" ]; then
    info "stopping backend (pid $BACKEND_PID)"
    # uvicorn's --reload spawns a child worker; kill the whole tree to
    # avoid orphans on the next start.
    kill_pid "$BACKEND_PID"
    OWNER="$(port_owner 8080 | head -n1 | tr -d '[:space:]')"
    [ -n "$OWNER" ] && kill_pid "$OWNER"
  fi
}
trap cleanup EXIT INT TERM

[ -f "backend/main.py" ] || die "backend/main.py not found"
"$VENV_PY" -m uvicorn backend.main:app --reload --port 8080 &
BACKEND_PID=$!
info "backend pid=$BACKEND_PID"

# Wait for /health to come back 200, then wait for crash_cache.loaded.
# Without this the frontend opens before the in-memory crash corpus
# is ready and the user's first /trip/brief blocks 30-45s on the
# background warm-up. We poll cheaply via Python (no curl dependency
# on stock Windows).
info "waiting for backend /health to respond..."
"$VENV_PY" - <<'PY' || warn "backend /health didn't come up cleanly — continuing anyway."
import json, sys, time
from urllib.request import urlopen
from urllib.error import URLError

URL = "http://127.0.0.1:8080/health"
DEADLINE = time.time() + 20  # 20s to bind uvicorn
while time.time() < DEADLINE:
    try:
        with urlopen(URL, timeout=2) as r:
            json.loads(r.read())
            sys.exit(0)
    except (URLError, OSError, json.JSONDecodeError):
        time.sleep(0.5)
sys.exit(1)
PY

info "waiting for crash cache to finish warming (one-time, ~30-45s on first boot)..."
"$VENV_PY" - <<'PY' || warn "crash cache didn't finish warming in 90s — first /trip/brief may block on the load."
import json, sys, time
from urllib.request import urlopen

URL = "http://127.0.0.1:8080/health"
DEADLINE = time.time() + 90
while time.time() < DEADLINE:
    try:
        with urlopen(URL, timeout=2) as r:
            body = json.loads(r.read())
        cache = body.get("crash_cache") or {}
        if cache.get("loaded"):
            print(f"  crash cache ready: {cache.get('size'):,} crashes")
            sys.exit(0)
    except Exception:
        pass
    time.sleep(1.0)
sys.exit(1)
PY

# ---------------------------------------------------------------------------
section "Starting frontend (routewise/) on :3000"
# ---------------------------------------------------------------------------
( cd routewise && npm run dev )

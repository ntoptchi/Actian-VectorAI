"""Download + extract the published VDB snapshot so teammates skip the ~20-minute embed.

Called by install.sh before the VDB container is booted. If the fetch + extract
succeeds, install.sh skips the FDOT / news ingest steps entirely (the existing
marker-check logic picks up the ingest marker we write here and the post-boot
health check confirms the collection is populated).

Exit codes::

    0  snapshot applied (or already present) — install.sh should skip ingest.
    1  skipped for a benign reason (no manifest, no URL, env override) — install.sh
       should run the normal ingest path.
    2  hard failure (download succeeded but was corrupted) — install.sh aborts.

Override knobs (env vars)::

    ROUTEWISE_SKIP_VDB_SNAPSHOT=1   force the slow ingest path, skip the download.
    ROUTEWISE_VDB_SNAPSHOT_URL=...  override the manifest URL (useful for testing
                                    against a local file:// URL or a staging mirror).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tarfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO / "vdb_snapshot.manifest.json"
DATA_DIR = REPO / "vectorai-db-beta" / "data"
# Biggest known file in a healthy dump (the payload btree); its presence at a
# reasonable size is a cheap "already populated" sentinel. Avoids re-downloading
# a 400 MB tarball every install.sh run once the snapshot is extracted.
SENTINEL = DATA_DIR / "routewise_crashes" / "segment_0" / "payloads" / "payloads.btr"
SENTINEL_MIN_BYTES = 10 * 1024 * 1024  # 10 MB — any real snapshot is >> this.

# The fetch script writes this marker file on success so the seeding section of
# install.sh picks it up and skips. Keep in sync with install.sh's INGEST_MARKER.
INGEST_MARKER_DIR = REPO / "data" / "processed"


def _log(msg: str) -> None:
    print(f"[fetch-snapshot] {msg}", flush=True)


def _human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _already_populated() -> bool:
    return SENTINEL.exists() and SENTINEL.stat().st_size >= SENTINEL_MIN_BYTES


def _download(url: str, dest: Path) -> None:
    """Stream a URL to ``dest`` with 5 %-step progress logging.

    ``httpx`` is a required dep (used by the backend) so we don't pull a new
    library. Uses an extended read timeout because the release-asset redirect
    sometimes stalls a few seconds on the first chunk.
    """
    import httpx

    _log(f"downloading {url}")
    _log(f"        -> {dest}")
    timeout = httpx.Timeout(30.0, read=300.0)
    with httpx.stream("GET", url, follow_redirects=True, timeout=timeout) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", "0") or 0)
        seen = 0
        last_pct = -5
        t0 = time.perf_counter()
        with open(dest, "wb") as f:
            for chunk in r.iter_bytes(chunk_size=1 << 20):
                f.write(chunk)
                seen += len(chunk)
                if total:
                    pct = 100 * seen // total
                    if pct >= last_pct + 5:
                        last_pct = pct
                        rate = seen / max(time.perf_counter() - t0, 1e-3)
                        _log(
                            f"  {pct:3d}%  {_human_bytes(seen)} / {_human_bytes(total)}  "
                            f"({_human_bytes(rate)}/s)"
                        )
    _log(f"downloaded {_human_bytes(dest.stat().st_size)}")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_extract(tarball: Path, target_root: Path) -> None:
    """Extract with path-traversal guard (CVE-2007-4559 / PEP 706).

    Python 3.12 adds ``filter="data"`` which enforces this natively; we use it
    when available and fall back to a manual check for older interpreters.
    """
    with tarfile.open(tarball, "r:gz") as tar:
        try:
            tar.extractall(target_root, filter="data")  # Python 3.12+
        except TypeError:
            for member in tar.getmembers():
                resolved = (target_root / member.name).resolve()
                if not str(resolved).startswith(str(target_root.resolve())):
                    raise RuntimeError(f"unsafe path in tarball: {member.name}")
            tar.extractall(target_root)


def _write_marker(ingest_version: str) -> None:
    INGEST_MARKER_DIR.mkdir(parents=True, exist_ok=True)
    marker = INGEST_MARKER_DIR / f".fdot_ingest_v{ingest_version}"
    marker.touch()
    _log(f"wrote ingest marker {marker.relative_to(REPO)}")


def main() -> int:
    if os.environ.get("ROUTEWISE_SKIP_VDB_SNAPSHOT"):
        _log("ROUTEWISE_SKIP_VDB_SNAPSHOT is set — skipping; install.sh will ingest from scratch")
        return 1

    if not MANIFEST_PATH.exists():
        _log(f"no manifest at {MANIFEST_PATH.relative_to(REPO)} — skipping")
        return 1

    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _log(f"manifest is not valid JSON: {exc}")
        return 1

    url = (os.environ.get("ROUTEWISE_VDB_SNAPSHOT_URL") or manifest.get("url") or "").strip()
    expected_sha = (manifest.get("sha256") or "").strip().lower()
    expected_bytes = int(manifest.get("bytes") or 0)
    ingest_version = str(manifest.get("ingest_version") or "").strip()

    # Skip the download only if BOTH the data is on disk AND a matching-version
    # ingest marker is present. Checking just the sentinel is a version-skew
    # trap: when maintainers bump `ingest_version` in the manifest they're
    # saying the data schema changed, and stale-but-populated *.btr files
    # should be re-downloaded (or at least re-ingested via the fallback path),
    # not silently accepted.
    current_marker = (
        INGEST_MARKER_DIR / f".fdot_ingest_v{ingest_version}" if ingest_version else None
    )
    if _already_populated() and current_marker is not None and current_marker.exists():
        _log(
            f"VDB data dir already populated at ingest v{ingest_version} "
            f"({_human_bytes(SENTINEL.stat().st_size)} payload btree) — skipping download"
        )
        return 0

    if not url:
        _log(
            "manifest has no URL — no snapshot published yet; install.sh will ingest from scratch.\n"
            "                 (To publish one, see scripts/dump_vdb_snapshot.py.)"
        )
        return 1

    tarball = REPO / "vdb_snapshot.tar.gz"
    try:
        _download(url, tarball)
    except Exception as exc:  # noqa: BLE001
        _log(f"download failed: {exc}")
        tarball.unlink(missing_ok=True)
        return 1

    if expected_bytes and tarball.stat().st_size != expected_bytes:
        _log(
            f"size mismatch: expected {expected_bytes:,} bytes, "
            f"got {tarball.stat().st_size:,} — treating as corrupt"
        )
        tarball.unlink(missing_ok=True)
        return 2

    if expected_sha:
        _log("verifying sha256...")
        got = _sha256(tarball)
        if got != expected_sha:
            _log(f"sha256 mismatch: expected {expected_sha}, got {got}")
            tarball.unlink(missing_ok=True)
            return 2
        _log("sha256 ok")

    _log(f"extracting to {REPO}")
    try:
        _safe_extract(tarball, REPO)
    except Exception as exc:  # noqa: BLE001
        _log(f"extraction failed: {exc}")
        tarball.unlink(missing_ok=True)
        return 2
    tarball.unlink(missing_ok=True)

    if not _already_populated():
        _log("extraction completed but expected payload file is missing — snapshot may be malformed")
        return 2

    if ingest_version:
        _write_marker(ingest_version)

    _log("snapshot applied successfully — install.sh will skip the FDOT/news ingest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

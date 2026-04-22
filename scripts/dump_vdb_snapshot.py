"""Create a gzipped tarball of the VDB data dir for publishing as a GitHub Release asset.

Run this on the authoritative machine after a fresh, healthy ingest. The resulting
``vdb_snapshot.tar.gz`` gets uploaded as a release asset; teammates then download +
extract it via ``scripts/fetch_vdb_snapshot.py`` (called automatically by install.sh)
instead of re-embedding the whole corpus from scratch (~20 min on CPU).

Stop the VDB container before running this. ``vectorai-db-beta`` uses memory-mapped
``*.btr`` files; snapshotting them while the server is mid-write produces a corrupt
archive that boots but silently misses the tail of the last segment.

Usage::

    docker compose -f vectorai-db-beta/docker-compose.yml stop
    python scripts/dump_vdb_snapshot.py
    docker compose -f vectorai-db-beta/docker-compose.yml start

Then upload the printed file to a GitHub Release and copy the printed url / sha256 /
bytes into ``vdb_snapshot.manifest.json`` and commit the manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA_DIR = REPO / "vectorai-db-beta" / "data"
MANIFEST_PATH = REPO / "vdb_snapshot.manifest.json"


def _human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _container_running() -> bool:
    """Best-effort check. Returns True if the actian-vectorai container is up."""
    import shutil
    import subprocess

    if not shutil.which("docker"):
        return False
    try:
        r = subprocess.run(
            ["docker", "ps", "--filter", "ancestor=williamimoh/actian-vectorai-db:latest", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=5,
        )
        return bool(r.stdout.strip())
    except Exception:  # noqa: BLE001
        return False


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default=str(REPO / "vdb_snapshot.tar.gz"),
                   help="Output tarball path (default: repo-root/vdb_snapshot.tar.gz)")
    p.add_argument("--force", action="store_true",
                   help="Skip the 'container is running' safety check.")
    args = p.parse_args(argv)

    if not DATA_DIR.exists():
        print(f"[dump] VDB data dir missing: {DATA_DIR}", file=sys.stderr)
        return 1

    if _container_running() and not args.force:
        print(
            "[dump] VDB container appears to be running. Running mid-snapshot can\n"
            "       capture a partially-written page and produce a silently-corrupt\n"
            "       archive. Stop it first:\n\n"
            "         docker compose -f vectorai-db-beta/docker-compose.yml stop\n\n"
            "       (or pass --force to bypass this check if you're sure nothing is\n"
            "       writing to the collection right now).",
            file=sys.stderr,
        )
        return 1

    out = Path(args.out)
    print(f"[dump] source:  {DATA_DIR}")
    print(f"[dump] target:  {out}")
    t0 = time.perf_counter()
    with tarfile.open(out, "w:gz", compresslevel=6) as tar:
        tar.add(DATA_DIR, arcname="vectorai-db-beta/data")
    elapsed = time.perf_counter() - t0

    size = out.stat().st_size
    print(f"[dump] wrote {_human_bytes(size)} in {elapsed:.1f}s; hashing...")
    digest = _sha256(out)
    print(f"[dump] sha256: {digest}")
    print()

    manifest = {}
    if MANIFEST_PATH.exists():
        try:
            manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    print("Next steps:")
    print(f"  1. Upload '{out.name}' to a GitHub Release (e.g. tag: {manifest.get('version', 'v4.1')})")
    print("     - Releases page: https://github.com/<org>/routewise/releases/new")
    print(f"  2. Update vdb_snapshot.manifest.json with:")
    print(f'       "url":    "<release asset download URL>"')
    print(f'       "sha256": "{digest}"')
    print(f'       "bytes":  {size}')
    print(f"  3. Bump 'version' (currently {manifest.get('version', '<unset>')!r}) if the ingest")
    print(f"     pipeline changed in a way that invalidates older snapshots.")
    print(f"  4. Commit the updated manifest and push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

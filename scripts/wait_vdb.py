"""Block until the Actian VectorAI DB at vdb_host:vdb_port is reachable.

Used by install.sh and start.sh between `docker compose up -d` and the
seed step. The compose container needs ~10-15s on a cold boot before the
gRPC listener accepts connections.

Exits 0 when the client's ``health_check`` succeeds, or 1 after the
deadline.

Usage::

    python scripts/wait_vdb.py            # default 60s timeout
    python scripts/wait_vdb.py --timeout 120
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--interval", type=float, default=1.5)
    args = p.parse_args(argv)

    try:
        # Defer imports so a missing actian_vectorai wheel raises a clean error.
        from backend.config import get_settings
        from backend.vdb import get_client
    except Exception as exc:
        print(f"[wait_vdb] backend import failed: {exc}", file=sys.stderr)
        return 1

    addr = get_settings().vdb_address
    deadline = time.time() + args.timeout
    last_err: Exception | None = None
    attempts = 0
    while time.time() < deadline:
        attempts += 1
        try:
            # Drop the cached client between attempts — `connect()` is sticky
            # on the singleton, so a stale client from before the container
            # was up will keep failing.
            get_client.cache_clear()  # type: ignore[attr-defined]
            client = get_client()
            client.health_check()
            print(f"[wait_vdb] VDB ready at {addr} after {attempts} attempt(s)")
            return 0
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(args.interval)

    print(
        f"[wait_vdb] VDB at {addr} not reachable after {args.timeout:.0f}s "
        f"({attempts} attempts). Last error: {last_err}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

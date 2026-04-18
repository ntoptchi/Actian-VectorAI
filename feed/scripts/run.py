"""Dev entry point: ``python scripts/run.py``."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn


if __name__ == "__main__":
    uvicorn.run("feed.server:app", host="0.0.0.0", port=8100, reload=False)

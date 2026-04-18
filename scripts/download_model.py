"""Ensure the MiniLM sentence-transformer is present under models/all-MiniLM-L6-v2/.

Idempotent: if model.safetensors already exists, this is a no-op. Otherwise it
fetches `sentence-transformers/all-MiniLM-L6-v2` from the Hugging Face Hub and
saves it locally so the rest of the pipeline can run offline.

Run via the install scripts; can also be invoked directly:
    python scripts/download_model.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = REPO_ROOT / "models" / "all-MiniLM-L6-v2"
HF_SLUG = "sentence-transformers/all-MiniLM-L6-v2"


def main() -> int:
    weights = MODEL_DIR / "model.safetensors"
    if weights.exists():
        print(f"[download_model] model already present at {MODEL_DIR}")
        return 0

    print(f"[download_model] fetching {HF_SLUG} -> {MODEL_DIR}")
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print(
            "[download_model] sentence-transformers is not installed yet. "
            "Run the install script first, or `pip install -r requirements.txt`.",
            file=sys.stderr,
        )
        return 1

    MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)
    model = SentenceTransformer(HF_SLUG)
    model.save(str(MODEL_DIR))
    print(f"[download_model] saved to {MODEL_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

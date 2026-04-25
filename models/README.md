# Bundled models

## `all-MiniLM-L6-v2/`

Sentence-Transformer checkpoint for `sentence-transformers/all-MiniLM-L6-v2`
(384-dim, ~87 MB on disk). Bundled in-repo so `install.sh` doesn't need a HF
download at setup time and the pipeline runs fully offline.

Produced with:

```python
from sentence_transformers import SentenceTransformer
SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2").save("models/all-MiniLM-L6-v2")
```

`backend/config.py` defaults `ROUTEWISE_MODEL_DIR` to this directory when
it exists; override via the `ROUTEWISE_MODEL_DIR` environment variable to
point at a different checkpoint or the HF Hub slug.

The loader sets `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1` automatically
when the path resolves to a local directory, suppressing the HF
"unauthenticated requests" warning that would otherwise appear on every
process start.

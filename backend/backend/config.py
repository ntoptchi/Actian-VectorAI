"""RigSense settings.

All knobs live here so subagents and seed scripts agree on the exact same
collection names, sensor order, and embedding dimension. Override any of them
through environment variables (see ``.env.example``).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Repo-local path to the bundled MiniLM model.
# ``backend/backend/config.py`` -> repo root is parents[2].
_BUNDLED_MODEL_DIR = (
    Path(__file__).resolve().parents[2] / "models" / "all-MiniLM-L6-v2"
)


def _default_embedding_model() -> str:
    """Prefer the repo-local model if present, fall back to the HF Hub slug."""
    if _BUNDLED_MODEL_DIR.exists() and (_BUNDLED_MODEL_DIR / "config.json").exists():
        return str(_BUNDLED_MODEL_DIR)
    return "sentence-transformers/all-MiniLM-L6-v2"


SENSOR_ORDER: tuple[str, ...] = (
    "vibration",
    "bearing_temp",
    "pressure",
    "rpm",
    "lubricant_pressure",
    "humidity",
)


class Settings(BaseSettings):
    """Runtime configuration loaded from env / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    vectorai_host: str = "localhost:50051"

    embedding_model: str = Field(default_factory=_default_embedding_model)
    embedding_dim: int = 384
    use_mock_embeddings: bool = False

    sensor_readings_collection: str = "rigsense_sensor_readings"
    past_incidents_collection: str = "rigsense_past_incidents"
    manuals_collection: str = "rigsense_manuals"
    manual_chunks_collection: str = "rigsense_manual_chunks"

    z_threshold: float = Field(default=3.0, ge=0.0)
    incident_top_k: int = Field(default=3, ge=1)
    manual_top_k: int = Field(default=3, ge=1)
    chunk_top_k: int = Field(default=2, ge=1)

    text_weight: float = Field(default=0.7, ge=0.0, le=1.0)

    @property
    def numeric_weight(self) -> float:
        """Complement of ``text_weight`` for the hybrid classifier."""
        return 1.0 - self.text_weight

    @property
    def sensor_dim(self) -> int:
        return len(SENSOR_ORDER)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton settings accessor."""
    return Settings()

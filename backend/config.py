"""Runtime configuration for the RouteWise backend.

Single ``Settings`` object loaded from environment variables (with sensible
defaults for local dev). Mirrors the RigSense ``pydantic-settings`` pattern
referenced in ROUTEWISE.md s7.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[1]

# Push every key in .env into os.environ so legacy consumers that read
# straight from the environment (e.g. ors_client._api_key()) pick up
# unprefixed secrets like OPEN_ROUTE_SERVICE_API_KEY. Pydantic-settings
# only binds ROUTEWISE_-prefixed values onto Settings; without this
# load_dotenv() pass, anything else in .env would be invisible to the
# rest of the backend, which is exactly the silent-fallback bug we hit
# in QA (ORS quietly degraded to OSRM single-route).
load_dotenv(REPO_ROOT / ".env", override=False)


class Settings(BaseSettings):
    """All runtime configuration for the RouteWise API."""

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_prefix="ROUTEWISE_",
        extra="ignore",
    )

    # --- VectorAI DB ---
    vdb_host: str = "localhost"
    vdb_port: int = 50051
    vdb_collection: str = "routewise_crashes"
    vdb_vector_size: int = 384

    # --- Embedding model (offline MiniLM) ---
    model_dir: Path = REPO_ROOT / "models" / "all-MiniLM-L6-v2"

    # --- External services ---
    osrm_base_url: str = "https://router.project-osrm.org"
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"
    open_meteo_archive_url: str = "https://archive-api.open-meteo.com/v1"

    # --- Data dirs ---
    data_dir: Path = REPO_ROOT / "data"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def vdb_address(self) -> str:
        return f"{self.vdb_host}:{self.vdb_port}"

    # --- API ---
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton accessor."""
    return Settings()

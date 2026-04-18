"""Feed service settings loaded from env / process start."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    csv_path: str = str(
        _ROOT / "data" / "industrial_pump" / "Large_Industrial_Pump_Maintenance_Dataset.csv"
    )
    backend_url: str = "http://localhost:8000"
    tick_seconds: float = 2.0
    rig_id: str = "rig-north-atlas-07"


# Map CSV Pump_ID -> existing dashboard asset_id. Pumps not in this map are
# skipped (the CSV has many; we only animate the 5 that are visible on the rig).
ASSET_MAP: dict[int, str] = {
    1: "compressor-03",
    2: "pump-07",
    3: "valve-12",
    4: "heat-exchanger-2",
    5: "tank-04",
}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

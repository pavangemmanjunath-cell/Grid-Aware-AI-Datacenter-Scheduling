"""Runtime configuration (12-factor: every setting can be overridden by an env var)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QH2DC_", env_file=".env", extra="ignore")

    app_name: str = "QH2DC AI Data Centre Simulator API"
    version: str = "1.0.0"
    data_dir: Path = Field(default=REPO_ROOT / "data", description="Folder holding the benchmark CSV files")
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    max_workers: int = Field(default=2, ge=1, le=16, description="Concurrent what-if simulations")
    max_jobs_retained: int = Field(default=100, ge=10, le=10_000)
    # Language-model assistant: disabled until a provider is configured (see app/assistant).
    llm_provider: str = "none"


@lru_cache
def get_settings() -> Settings:
    return Settings()

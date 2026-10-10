"""
Central application configuration.

All configuration is sourced from environment variables (see .env.example
at the repo root). Nothing here is hard-coded to a secret value - every
credential-shaped field defaults to empty string / None and the system
falls back to DEMO behaviour when it is absent.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    APP_NAME: str = "GhostNet Marine Debris Intelligence Platform"

    # DATA_MODE controls whether the system uses deterministic synthetic
    # data (demo) or attempts to reach real external providers (live).
    DATA_MODE: Literal["demo", "live"] = "demo"

    # Database. Defaults to a local SQLite file so the whole platform can
    # run with zero external services. Point this at a
    # postgresql+psycopg://... PostGIS instance for production use -
    # every model/query in this codebase is written in a
    # database-agnostic way (geometry stored as GeoJSON text + plain
    # lat/lon columns, spatial operations done in Python via Shapely) so
    # no code changes are required to move from SQLite to Postgres/PostGIS.
    DATABASE_URL: str = "sqlite:///./ghostnet_demo.db"

    # Redis / background jobs. When REDIS_URL is unset the job system
    # transparently falls back to an in-process synchronous queue
    # (see app/jobs/queue.py) so `docker compose up` is not required to
    # exercise the full pipeline.
    REDIS_URL: str | None = None
    JOB_BACKEND: Literal["inline", "redis"] = "inline"

    # Detection provider: "mock" (default, always works) or "sentinel2"
    # (requires a real trained model - see README "Model integration").
    MODEL_PROVIDER: Literal["mock", "sentinel2"] = "mock"
    MODEL_CHECKPOINT_PATH: str = "segmentation_best.pth"
    EE_PROJECT_ID: str = "balmy-ocean-509105-v8"

    # Ocean forcing provider for the drift engine.
    OCEAN_DATA_PROVIDER: Literal["demo", "cmems", "era5", "gfs"] = "demo"

    # RAG configuration.
    VECTOR_STORE: Literal["memory", "faiss"] = "memory"
    EMBEDDING_PROVIDER: Literal["hashing", "openai"] = "hashing"

    # LLM provider for report narration. "mock" produces deterministic
    # template-driven text and requires no API key.
    LLM_PROVIDER: Literal["mock", "openai", "anthropic"] = "mock"
    LLM_API_KEY: str | None = None
    LLM_MODEL: str | None = None

    # Frontend map style.
    MAP_STYLE_URL: str = (
        "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
    )

    # Uploads.
    MAX_UPLOAD_MB: int = 200
    ALLOWED_UPLOAD_EXTENSIONS: tuple[str, ...] = (".tif", ".tiff")

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    RISK_CONFIG_PATH: str = "configs/risk.yaml"
    SYSTEM_CONFIG_PATH: str = "configs/system.yaml"

    @property
    def is_demo(self) -> bool:
        return self.DATA_MODE == "demo"


@lru_cache
def get_settings() -> Settings:
    return Settings()

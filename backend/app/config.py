"""Application settings, loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenAI
    openai_api_key: str = ""
    openai_engine_model: str = "gpt-4o"
    openai_intel_model: str = "gpt-4o-mini"

    # Database
    database_url: str = "postgresql+psycopg://limelight:limelight@localhost:5432/limelight"
    database_url_direct: str = ""

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # API
    cors_origins: str = "http://localhost:5173"
    # Shared secret gating write endpoints (seed, trigger run). If empty, writes
    # are disabled (503). Sent by the client as the X-Admin-Token header.
    admin_token: str = ""

    @property
    def alembic_url(self) -> str:
        """Direct (non-pooled) URL for migrations; falls back to the app URL."""
        return self.database_url_direct or self.database_url

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

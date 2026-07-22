"""Application configuration via Pydantic Settings.

Loaded from environment variables and/or .env file.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATABASE_URL: str = "sqlite+aiosqlite:///./contentforge.db"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o"
    LLM_PROVIDER: str = "openai"
    LLM_BASE_URL: str | None = None
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "*"
    SECRET_KEY: str = "change-me-in-production"
    HEALTH_CHECK_LLM: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings: Settings | None = None


def get_settings() -> Settings:
    """Return the cached application settings singleton.

    Uses a module-level cache so the .env file is only read once.
    """
    global settings  # noqa: PLW0603
    if settings is None:
        settings = Settings()
    return settings

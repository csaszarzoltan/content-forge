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

    # JWT authentication settings
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Social media publishing settings
    ENCRYPTION_KEY: str = ""
    TWITTER_API_KEY: str = ""
    TWITTER_API_SECRET: str = ""
    TWITTER_ACCESS_TOKEN: str = ""
    TWITTER_ACCESS_TOKEN_SECRET: str = ""
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""

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

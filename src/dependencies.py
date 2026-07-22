"""FastAPI dependency injection helpers.

Reusable dependencies for route handlers: settings access,
database session, authentication stubs, etc.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
from src.database import get_db as _get_db


async def get_db(request: Request) -> AsyncGenerator[AsyncSession]:
    """Yield a database session, rolled back / closed on error."""
    async for session in _get_db():
        yield session


async def get_settings_dep(request: Request) -> Settings:
    """Return the cached application settings."""
    return get_settings()


async def get_current_user(
    settings: Settings = Depends(get_settings_dep),
) -> str | None:
    """Stub authentication — return user ID or raise 401.

    Replace with real auth (JWT, API key, etc.) in production.
    """
    # Stub: always returns None (no auth configured yet)
    return None

"""FastAPI dependency injection helpers.

Reusable dependencies for route handlers: settings access,
database session, authentication, and user-scoped query helpers.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
from src.database import get_db as _get_db

if TYPE_CHECKING:
    from src.models.user import User

# OAuth2 scheme — tells FastAPI to expect Bearer tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_db(request: Request) -> AsyncGenerator[AsyncSession]:
    """Yield a database session, rolled back / closed on error."""
    async for session in _get_db():
        yield session


async def get_settings_dep(request: Request) -> Settings:
    """Return the cached application settings."""
    return get_settings()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> User:
    """Decode JWT, fetch the authenticated user from DB, or raise 401."""
    from src.services.auth_service import decode_token, get_user_by_id

    payload = decode_token(token, settings)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_optional_current_user(
    token: str | None = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> User | None:
    """Optional auth — return the User or None if no valid token provided."""
    if token is None:
        return None

    from src.services.auth_service import decode_token, get_user_by_id

    payload = decode_token(token, settings)
    if payload is None:
        return None

    user_id: str | None = payload.get("sub")
    if user_id is None:
        return None

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        return None
    return user


async def scope_query_by_user(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> AsyncSession:
    """Yield a DB session with the current user context for query scoping.

    Injects ``current_user`` into the session's info dict so that CRUD
    operations can filter by ``user_id`` automatically.
    """
    db.info["current_user_id"] = current_user.id
    return db

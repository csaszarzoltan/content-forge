"""SQLAlchemy 2.0 async engine, session factory, and declarative base.

Provides the DatabaseManager class for lifecycle management and
a ``get_db`` async generator for FastAPI dependency injection.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class DatabaseManager:
    """Manages the SQLAlchemy async engine and session factory lifecycle."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def _create_engine(self) -> AsyncEngine:
        """Create the async engine (lazy initialization)."""
        if self._engine is None:
            self._engine = create_async_engine(
                self._database_url,
                echo=False,
                pool_pre_ping=True,
            )
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._engine

    async def get_session(self) -> AsyncSession:
        """Create a new async session."""
        self._create_engine()
        assert self._session_factory is not None  # noqa: S101
        return self._session_factory()

    async def close(self) -> None:
        """Dispose of the engine and release connections."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency: yield an async session and close it on teardown."""
    from src.config import get_settings

    settings = get_settings()
    manager = DatabaseManager(settings.DATABASE_URL)
    session = await manager.get_session()
    try:
        yield session
    finally:
        await session.close()
        await manager.close()

"""Interface and behavioral tests for src.database module.

Interface tests  — verify imports, class signatures (should PASS).
Behavioral tests — verify NotImplementedError for stubs.
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncGenerator

import pytest

from src.database import Base, DatabaseManager, get_db


# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestDatabaseInterface:
    """Verify the database module interface."""

    def test_base_importable(self):
        assert Base is not None

    def test_base_is_declarative(self):
        from sqlalchemy.orm import DeclarativeBase
        assert issubclass(Base, DeclarativeBase)

    def test_database_manager_importable(self):
        assert DatabaseManager is not None

    def test_database_manager_is_class(self):
        assert inspect.isclass(DatabaseManager)

    def test_database_manager_init_signature(self):
        sig = inspect.signature(DatabaseManager.__init__)
        assert "database_url" in sig.parameters

    def test_database_manager_has_get_session(self):
        assert hasattr(DatabaseManager, "get_session")
        assert callable(DatabaseManager.get_session)

    def test_database_manager_get_session_return_annotation(self):
        sig = inspect.signature(DatabaseManager.get_session)
        ann = sig.return_annotation
        assert ann is not inspect.Parameter.empty

    def test_database_manager_has_close(self):
        assert hasattr(DatabaseManager, "close")
        assert callable(DatabaseManager.close)

    def test_get_db_importable(self):
        assert get_db is not None

    def test_get_db_is_async_generator(self):
        import inspect
        assert inspect.isasyncgenfunction(get_db)

    def test_get_db_return_annotation(self):
        sig = inspect.signature(get_db)
        ann = sig.return_annotation
        assert ann is not inspect.Parameter.empty


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (verify real implementation)
# ============================================================================


class TestDatabaseBehavioral:
    """Behavioral tests for database — verify real implementation."""

    def test_database_manager_init_works(self):
        """DatabaseManager() should construct with a database URL."""
        mgr = DatabaseManager(database_url="sqlite+aiosqlite:///./test.db")
        assert mgr is not None
        assert mgr._database_url == "sqlite+aiosqlite:///./test.db"

    def test_get_db_is_async_generator(self):
        """get_db() should return an async generator."""
        import inspect
        assert inspect.isasyncgenfunction(get_db)

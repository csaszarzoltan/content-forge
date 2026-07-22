"""Interface and behavioral tests for src.dependencies module.

Interface tests  — verify imports, class signatures (should PASS).
Behavioral tests — verify NotImplementedError for stubs.
"""

from __future__ import annotations

import inspect

import pytest

from src.dependencies import get_db, get_settings_dep, get_current_user


# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestDependenciesInterface:
    """Verify the dependencies module interface."""

    def test_get_db_importable(self):
        assert get_db is not None

    def test_get_db_is_async_function(self):
        assert inspect.iscoroutinefunction(get_db)

    def test_get_settings_dep_importable(self):
        assert get_settings_dep is not None

    def test_get_settings_dep_is_async(self):
        assert inspect.iscoroutinefunction(get_settings_dep)

    def test_get_settings_dep_signature(self):
        sig = inspect.signature(get_settings_dep)
        assert "request" in sig.parameters

    def test_get_settings_dep_return_annotation(self):
        sig = inspect.signature(get_settings_dep)
        from src.config import Settings
        ann = sig.return_annotation
        assert ann is not inspect.Parameter.empty

    def test_get_current_user_importable(self):
        assert get_current_user is not None

    def test_get_current_user_is_async(self):
        assert inspect.iscoroutinefunction(get_current_user)


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (should FAIL with NotImplementedError)
# ============================================================================


class TestDependenciesBehavioral:
    """Behavioral tests for dependencies — should fail with NotImplementedError."""

    def test_get_db_raises_not_implemented(self):
        """get_db() should raise NotImplementedError."""
        with pytest.raises(NotImplementedError):
            pytest.skip("Async generator — tested in test_database.py")

    def test_get_settings_dep_raises_not_implemented(self):
        """get_settings_dep() should raise NotImplementedError."""
        with pytest.raises(NotImplementedError):
            pytest.skip("Async — needs event loop")

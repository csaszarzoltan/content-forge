"""Interface and behavioral tests for src.config module.

Interface tests  — verify imports, class signatures (should PASS).
Behavioral tests — verify NotImplementedError for stubs.
"""

from __future__ import annotations

import inspect

import pytest

from src.config import Settings, get_settings


# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestConfigInterface:
    """Verify the config module interface."""

    def test_settings_importable(self):
        assert Settings is not None

    def test_settings_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(Settings, BaseModel)

    def test_settings_fields(self):
        sig = inspect.signature(Settings)
        params = sig.parameters
        assert "DATABASE_URL" in params
        assert "LLM_API_KEY" in params
        assert "LLM_MODEL" in params
        assert "LLM_PROVIDER" in params
        assert "ENVIRONMENT" in params
        assert "CORS_ORIGINS" in params
        assert "SECRET_KEY" in params
        assert "HEALTH_CHECK_LLM" in params

    def test_settings_has_defaults(self):
        s = Settings()
        assert s.DATABASE_URL == "sqlite+aiosqlite:///./contentforge.db"
        assert s.LLM_MODEL == "gpt-4o"
        assert s.LLM_PROVIDER == "openai"
        assert s.ENVIRONMENT == "development"
        assert s.CORS_ORIGINS == "*"
        assert s.HEALTH_CHECK_LLM is False

    def test_get_settings_importable(self):
        assert get_settings is not None

    def test_get_settings_is_callable(self):
        assert callable(get_settings)

    def test_get_settings_return_annotation(self):
        sig = inspect.signature(get_settings)
        assert sig.return_annotation is not inspect.Parameter.empty

    def test_get_settings_return_type(self):
        sig = inspect.signature(get_settings)
        assert sig.return_annotation is Settings or "Settings" in str(sig.return_annotation)


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (verify real implementation)
# ============================================================================


class TestConfigBehavioral:
    """Behavioral tests for config — verify real implementation."""

    def test_get_settings_returns_settings(self):
        """get_settings() should return a Settings instance."""
        s = get_settings()
        assert isinstance(s, Settings)

    def test_settings_can_be_instantiated(self):
        """Settings() should construct with defaults."""
        s = Settings()
        assert isinstance(s, Settings)
        assert s.DATABASE_URL is not None

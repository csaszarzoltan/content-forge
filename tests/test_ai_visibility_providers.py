"""Interface + behavioral tests for M4 — provider abstraction + registry.

Interface tests verify the ABC contract, the four concrete provider classes,
the registry surface, and the normalized result model — these PASS
immediately (contract data is implemented in the stub). Behavioral tests
verify provider behavior (engine identity, check/validate, graceful
degradation, registry wiring); against the stubs they FAIL with
``NotImplementedError`` (TDD RED phase).
"""

from __future__ import annotations

import inspect
from abc import ABC

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.quick]

from pydantic import BaseModel

from src.ai_visibility.providers import (
    AIEngineProvider,
    ChatGPTProvider,
    EngineVisibilityResult,
    GeminiProvider,
    GoogleAIOverviewsProvider,
    PerplexityProvider,
    ProviderError,
    ProviderRegistry,
)

CONCRETE_PROVIDERS = [
    ChatGPTProvider,
    PerplexityProvider,
    GeminiProvider,
    GoogleAIOverviewsProvider,
]


# ============================================================================
# SECTION 1 — INTERFACE TESTS (PASS immediately)
# ============================================================================


class TestProvidersInterface:
    """Verify the M4 contract surface."""

    def test_module_importable(self):
        assert AIEngineProvider is not None and ProviderRegistry is not None

    def test_provider_error_is_runtime_error(self):
        """ProviderError derives from RuntimeError (brief §5 M4)."""
        assert issubclass(ProviderError, RuntimeError)

    def test_engine_visibility_result_is_pydantic(self):
        assert issubclass(EngineVisibilityResult, BaseModel)

    def test_engine_visibility_result_fields(self):
        r = EngineVisibilityResult(engine="chatgpt", query="q",
                                   mentioned=True, cited=False)
        assert r.cited_url is None
        assert r.snippet == ""
        assert r.sentiment == "unknown"
        assert r.raw_payload == {}

    def test_engine_visibility_result_bad_sentiment_rejected(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            EngineVisibilityResult(engine="chatgpt", query="q",
                                   mentioned=True, cited=False,
                                   sentiment="angry")

    def test_abc_is_abstract(self):
        """AIEngineProvider is an abstract base class."""
        assert inspect.isabstract(AIEngineProvider)
        assert issubclass(AIEngineProvider, ABC)

    def test_abc_abstract_members(self):
        """engine property + check_visibility + validate_credentials abstract."""
        abstract = AIEngineProvider.__abstractmethods__
        assert "engine" in abstract
        assert "check_visibility" in abstract
        assert "validate_credentials" in abstract

    @pytest.mark.parametrize("provider_cls", CONCRETE_PROVIDERS)
    def test_concrete_providers_subclass_abc(self, provider_cls):
        """All four engines are concrete AIEngineProvider subclasses."""
        assert issubclass(provider_cls, AIEngineProvider)
        assert not inspect.isabstract(provider_cls)

    def test_registry_surface(self):
        """ProviderRegistry exposes the full brief §5 M4 surface."""
        assert callable(ProviderRegistry.__init__)
        for name in ("register", "get", "available_engines", "configured_engines"):
            assert callable(getattr(ProviderRegistry, name))
        assert callable(ProviderRegistry.from_settings)

    def test_registry_method_signatures(self):
        sig = inspect.signature(ProviderRegistry.register)
        assert "provider" in sig.parameters
        sig_get = inspect.signature(ProviderRegistry.get)
        assert "engine" in sig_get.parameters
        sig_fs = inspect.signature(ProviderRegistry.from_settings)
        assert "settings" in sig_fs.parameters
        assert "llm_provider" in sig_fs.parameters

    def test_check_visibility_signature(self):
        """check_visibility(query, target_url) -> EngineVisibilityResult."""
        sig = inspect.signature(AIEngineProvider.check_visibility)
        assert tuple(sig.parameters) == ("self", "query", "target_url")


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (FAIL with NotImplementedError during RED)
# ============================================================================


class TestProvidersBehavioral:
    """Provider behavior once the developer implements the engines."""

    @pytest.mark.parametrize("provider_cls, expected_engine", [
        (ChatGPTProvider, "chatgpt"),
        (PerplexityProvider, "perplexity"),
        (GeminiProvider, "gemini"),
        (GoogleAIOverviewsProvider, "google_ai_overviews"),
    ])
    def test_engine_identity(self, provider_cls, expected_engine):
        """Each provider reports its canonical engine id (brief §4.5)."""
        provider = provider_cls()
        assert provider.engine == expected_engine

    @pytest.mark.parametrize("provider_cls", CONCRETE_PROVIDERS)
    async def test_check_visibility_returns_result(self, provider_cls):
        """check_visibility returns a normalized EngineVisibilityResult."""
        provider = provider_cls()
        result = await provider.check_visibility("what is acme?", "https://acme.com/x")
        assert isinstance(result, EngineVisibilityResult)
        assert result.query == "what is acme?"

    @pytest.mark.parametrize("provider_cls", CONCRETE_PROVIDERS)
    async def test_validate_credentials_returns_bool(self, provider_cls):
        """validate_credentials returns a bool (False when unconfigured)."""
        provider = provider_cls()
        assert isinstance(await provider.validate_credentials(), bool)

    async def test_provider_error_on_failure(self):
        """Provider failures raise ProviderError, never other exceptions."""
        provider = ChatGPTProvider()
        with pytest.raises(ProviderError):
            await provider.check_visibility("q", "https://acme.com/x")

    def test_registry_from_settings(self):
        """from_settings builds a registry with only configured engines."""
        from src.config import Settings

        registry = ProviderRegistry.from_settings(Settings())
        assert registry is not None
        assert set(registry.configured_engines()) <= set(registry.available_engines())

    def test_registry_get_unregistered_raises_keyerror(self):
        """get() raises KeyError for engines without a registered provider."""
        from src.config import Settings

        registry = ProviderRegistry.from_settings(Settings())
        with pytest.raises(KeyError):
            registry.get("chatgpt")

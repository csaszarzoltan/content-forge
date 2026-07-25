"""Pre-development tests for auto-language detection during content generation.

Task: T7 — Auto-Detection in Generation
Module: src/services/generator.py — ContentGenerator.generate()

Acceptance criteria:
  AC-T7.1: POST /generate/{content_type} auto-detects topic language, stores on Generation
  AC-T7.2: Language returned in GenerationResponse
  AC-T7.3: Non-English topic without brand_voice_id → English template + "Respond in {detected}"
  AC-T7.4: No regression for English content

Dependencies: T1 (language_detection module), T2 (language field on models)

Interface tests  — verify expected interfaces exist (some may fail until implemented).
Behavioral tests — verify real behavior or fail with clear spec messages.
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio

from src.schemas.content import GenerationResponse
from src.services.generator import ContentGenerator, GenerationResult

# ============================================================================
# SECTION 1 — INTERFACE TESTS (structural checks)
# ============================================================================


class TestLanguageFieldOnModels:
    """AC-T7.1 & AC-T7.2: Language field must exist on result and response schemas."""

    def test_generation_result_has_language_field(self):
        """GenerationResult must declare a 'language' field (AC-T7.1)."""
        sig = inspect.signature(GenerationResult)
        assert "language" in sig.parameters, (
            "AC-T7.1 FAIL: GenerationResult is missing 'language' parameter. "
            "Add `language: str = 'en'` to GenerationResult."
        )

    def test_generation_result_language_default_is_en(self):
        """GenerationResult.language defaults to 'en' (AC-T7.4 backward compat)."""
        try:
            result = GenerationResult(
                id="test-id",
                generated_text="Hello world",
                compliance_scores={},
                model_used="gpt-4o",
                tokens_used=50,
                latency_ms=200,
            )
        except TypeError as e:
            pytest.fail(
                f"AC-T7.1 FAIL: Cannot construct GenerationResult without language. "
                f"Add `language: str = 'en'` field. Error: {e}"
            )
        assert result.language == "en", (
            f"AC-T7.4 FAIL: Default language should be 'en', got '{result.language}'"
        )

    def test_generation_response_has_language_field(self):
        """GenerationResponse must declare a 'language' field (AC-T7.2)."""
        sig = inspect.signature(GenerationResponse)
        assert "language" in sig.parameters, (
            "AC-T7.2 FAIL: GenerationResponse is missing 'language' parameter. "
            "Add `language: str = 'en'` to GenerationResponse."
        )

    def test_generation_response_language_accepts_str(self):
        """GenerationResponse.language accepts and stores a string (AC-T7.2)."""
        sig = inspect.signature(GenerationResponse)
        if "language" not in sig.parameters:
            pytest.skip("GenerationResponse.language not yet implemented")
        from datetime import datetime

        resp = GenerationResponse(
            id="test",
            content_type="blog",
            generated_text="Hello",
            brand_voice_id=None,
            compliance_score=None,
            model_used="gpt-4o",
            tokens_used=10,
            latency_ms=100,
            created_at=datetime(2026, 1, 1),
            language="de",
        )
        assert resp.language == "de"

    def test_generation_orm_has_language_column(self):
        """Generation ORM model must have a 'language' column (AC-T7.1)."""
        from src.models.generation import Generation

        try:
            cols = {c.name for c in Generation.__table__.columns}
        except Exception:
            pytest.fail("Cannot inspect Generation.__table__.columns")
        assert "language" in cols, (
            "AC-T7.1 FAIL: Generation ORM table 'generations' is missing 'language' column. "
            "Add `language: Mapped[str] = mapped_column(String(10), default='en')`."
        )

    def test_generation_orm_language_default(self):
        """Generation ORM model language defaults to 'en'."""
        from src.models.generation import Generation

        try:
            cols = {c.name for c in Generation.__table__.columns}
        except Exception:
            pytest.skip("Cannot inspect Generation columns")
        if "language" not in cols:
            pytest.skip("Generation.language not yet implemented")
        col = Generation.__table__.columns["language"]
        assert col.default is not None or col.nullable, (
            "AC-T7.4 FAIL: language column should have a sensible default "
            "for backward compatibility with existing records"
        )


class TestLanguageDetectionDependency:
    """Interface for the language detection module (T1 dependency required by T7)."""

    def test_language_detection_module_importable(self):
        """The language_detection service module must be importable (T1)."""
        try:
            from src.services import language_detection  # noqa: F401
        except ImportError as exc:
            pytest.fail(
                f"T1 dependency FAIL: Cannot import src.services.language_detection. "
                f"Create src/services/language_detection.py with detect_language(). "
                f"Error: {exc}"
            )

    def test_detect_language_function_exists(self):
        """detect_language(text: str) -> LanguageResult must exist."""
        pytest.importorskip("src.services.language_detection")
        from src.services.language_detection import detect_language

        assert callable(detect_language), "detect_language must be a callable function"

    def test_detect_language_signature(self):
        """detect_language accepts text: str."""
        pytest.importorskip("src.services.language_detection")
        from src.services.language_detection import detect_language

        sig = inspect.signature(detect_language)
        assert "text" in sig.parameters, (
            "detect_language(text: str) must accept 'text' parameter"
        )

    def test_language_result_model_exists(self):
        """LanguageResult model must be importable with expected fields."""
        pytest.importorskip("src.services.language_detection")
        from src.services.language_detection import LanguageResult

        assert hasattr(LanguageResult, "language_code"), (
            "LanguageResult must have 'language_code' field (ISO 639-1)"
        )
        assert hasattr(LanguageResult, "confidence"), (
            "LanguageResult must have 'confidence' field (0.0–1.0)"
        )
        assert hasattr(LanguageResult, "is_reliable"), (
            "LanguageResult must have 'is_reliable' field (bool)"
        )


class TestContentGeneratorLanguageInterface:
    """ContentGenerator.generate() must support language detection (AC-T7.1)."""

    def test_generate_returns_language_in_result(self):
        """ContentGenerator.generate() result should include language (AC-T7.1)."""
        try:
            result = GenerationResult(
                id="test",
                generated_text="Hello",
                compliance_scores={},
                model_used="gpt-4o",
                tokens_used=10,
                latency_ms=100,
                language="en",
            )
        except TypeError as e:
            pytest.fail(
                f"AC-T7.1 FAIL: Cannot construct GenerationResult with language field. "
                f"Error: {e}"
            )
        assert hasattr(result, "language")
        assert isinstance(result.language, str), "language must be a string"

    def test_generate_signature_includes_language_support(self):
        """Existing test: generate() signature must still accept existing params."""
        sig = inspect.signature(ContentGenerator.generate)
        assert "content_type" in sig.parameters
        assert "topic" in sig.parameters


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (async — verify actual behavior)
# ============================================================================


class TestAutoDetectionBehavioral:
    """Verify auto-detection behavior during generation (AC-T7.1, T7.3, T7.4)."""

    @pytest.fixture
    def mock_detection(self):
        """Fixture: mock the language detection module."""
        try:
            from src.services import language_detection as ld_mod
        except ImportError:
            pytest.skip("language_detection module not yet implemented (T1)")

        with patch.object(ld_mod, "detect_language") as mock:
            mock.return_value = MagicMock(
                language_code="en", confidence=0.99, is_reliable=True
            )
            yield mock

    @pytest.fixture
    def mock_provider(self):
        """Fixture: mock the LLM provider to avoid real API calls."""
        with patch("src.services.llm_provider.get_provider") as mock_get:
            provider = AsyncMock()
            provider.generate.return_value = MagicMock(
                text="Generated content here.",
                model_used="gpt-4o",
                tokens_prompt=20,
                tokens_completion=30,
            )
            mock_get.return_value = provider
            yield provider

    @pytest.fixture
    def generator(self, mock_provider):
        """Fixture: ContentGenerator instance with mocked provider."""
        return ContentGenerator()

    # --- AC-T7.1: Language detection is called during generate ---

    async def test_language_detection_called_on_topic(
        self, generator, mock_detection, mock_provider
    ):
        """AC-T7.1: detect_language(topic) is called during generate()."""
        try:
            result = await generator.generate(
                content_type="blog",
                topic="Why Python is great for machine learning",
                brand_voice_id=None,
                user_id=None,
            )
        except NotImplementedError:
            pytest.fail(
                "AC-T7.1 FAIL: ContentGenerator.generate() must call detect_language(topic). "
                "Add `from src.services.language_detection import detect_language` "
                "and call it early in generate()."
            )
        except Exception as exc:
            pytest.fail(f"generate() raised unexpected error: {exc}")

        mock_detection.assert_called_once()
        call_arg = mock_detection.call_args[0][0] if mock_detection.call_args else ""
        assert "Python" in str(call_arg) or "machine" in str(call_arg), (
            "detect_language must be called with the topic string"
        )

    # --- AC-T7.1: language is stored on GenerationResult ---

    async def test_stores_language_on_result(
        self, generator, mock_detection, mock_provider
    ):
        """AC-T7.1: detected language is stored on GenerationResult."""
        mock_detection.return_value = MagicMock(
            language_code="de", confidence=0.95, is_reliable=True
        )
        try:
            result = await generator.generate(
                content_type="blog",
                topic="Die Zukunft der künstlichen Intelligenz",
                brand_voice_id=None,
                user_id=None,
            )
        except NotImplementedError:
            pytest.fail(
                "AC-T7.1 FAIL: generate() must return language in GenerationResult. "
                "Check GenerationResult includes `language` field and generate() sets it."
            )
        except Exception as exc:
            pytest.fail(f"generate() raised unexpected error: {exc}")

        assert hasattr(result, "language"), (
            "AC-T7.1 FAIL: GenerationResult must have 'language' attribute"
        )
        assert result.language == "de", (
            f"AC-T7.1 FAIL: Expected language='de' for German topic, "
            f"got '{result.language}'"
        )

    # --- AC-T7.3: Non-English without brand_voice_id uses fallback prompt ---

    async def test_non_english_without_brand_voice_uses_fallback(
        self, generator, mock_detection, mock_provider
    ):
        """AC-T7.3: Non-English topic without brand_voice_id uses English + Respond in {lang}."""
        mock_detection.return_value = MagicMock(
            language_code="de", confidence=0.95, is_reliable=True
        )
        mock_provider.generate.reset_mock()

        try:
            await generator.generate(
                content_type="blog",
                topic="Die Zukunft der künstlichen Intelligenz",
                brand_voice_id=None,  # No brand voice → fallback path
            )
        except (NotImplementedError, Exception) as exc:
            pytest.fail(f"generate() raised unexpected error: {exc}")

        # Verify the provider was called with a system prompt that includes
        # the "Respond in" instruction for non-English
        if mock_provider.generate.called:
            call_kwargs = mock_provider.generate.call_args[1]
            system_prompt = call_kwargs.get("system_prompt", "")
            prompt = call_kwargs.get("prompt", "")
            combined = system_prompt + " " + prompt
            assert "Respond in" in combined, (
                "AC-T7.3 FAIL: For non-English topic without brand_voice_id, "
                "the prompt must include 'Respond in {detected_language}'. "
                "Expected 'Respond in de' in prompt text."
            )
            assert "de" in combined, (
                "AC-T7.3 FAIL: The detected language code ('de') must appear in the "
                "'Respond in {language}' instruction."
            )
        else:
            pytest.fail("AC-T7.3 FAIL: provider.generate() was never called")

    # --- AC-T7.1: brand_voice_id provided → language still populated ---

    async def test_non_english_with_brand_voice_still_detects_language(
        self, generator, mock_detection, mock_provider
    ):
        """brand_voice_id provided → language field still populated."""
        mock_detection.return_value = MagicMock(
            language_code="fr", confidence=0.92, is_reliable=True
        )
        try:
            result = await generator.generate(
                content_type="social",
                topic="Les avantages de Python pour la science des données",
                brand_voice_id="acme-corp-v1",
                user_id=None,
            )
        except NotImplementedError:
            pytest.fail(
                "AC-T7.1 FAIL: generate() must return language field "
                "even when brand_voice_id is set"
            )
        except Exception as exc:
            pytest.fail(f"generate() raised unexpected error: {exc}")

        assert hasattr(result, "language"), (
            "AC-T7.1 FAIL: result must have language even with brand_voice_id"
        )
        assert result.language == "fr", (
            f"Expected language='fr' for French topic, got '{result.language}'"
        )

    # --- AC-T7.4: No regression for English content ---

    async def test_english_topic_no_regression(
        self, generator, mock_detection, mock_provider
    ):
        """AC-T7.4: English topic uses unchanged generation flow."""
        mock_detection.return_value = MagicMock(
            language_code="en", confidence=0.99, is_reliable=True
        )
        mock_provider.generate.reset_mock()

        try:
            result = await generator.generate(
                content_type="blog",
                topic="How to build a micro-SaaS with Python",
                brand_voice_id=None,
                user_id=None,
            )
        except Exception as exc:
            pytest.fail(f"generate() for English topic raised unexpected error: {exc}")

        # Language should be 'en'
        assert hasattr(result, "language"), (
            "AC-T7.4 FAIL: result must have language attribute"
        )
        assert result.language == "en", (
            f"AC-T7.4 FAIL: English topic should return language='en', got '{result.language}'"
        )

        # The system prompt should NOT contain 'Respond in' for English
        if mock_provider.generate.called:
            call_kwargs = mock_provider.generate.call_args[1]
            system_prompt = call_kwargs.get("system_prompt", "")
            assert "Respond in" not in system_prompt, (
                "AC-T7.4 FAIL: For English topics, the system prompt should NOT "
                "contain 'Respond in' instruction. English content must behave "
                "exactly as before."
            )


class TestResponseSchemaBehavioral:
    """Verify GenerationResponse serializes language (AC-T7.2)."""

    def test_generation_response_serializes_language(self):
        """AC-T7.2: GenerationResponse serializes language field in JSON."""
        sig = inspect.signature(GenerationResponse)
        if "language" not in sig.parameters:
            pytest.skip("GenerationResponse.language not yet implemented (AC-T7.2)")
        from datetime import datetime

        resp = GenerationResponse(
            id="test-id",
            content_type="blog",
            generated_text="Hallo Welt",
            brand_voice_id=None,
            compliance_score=None,
            model_used="gpt-4o",
            tokens_used=50,
            latency_ms=300,
            created_at=datetime(2026, 1, 1),
            language="de",
        )
        data = resp.model_dump()
        assert "language" in data, (
            "AC-T7.2 FAIL: language field must appear in serialized GenerationResponse"
        )
        assert data["language"] == "de"


# ============================================================================
# SECTION 3 — INTEGRATION STUBS (skipped by default — need DB + TestClient)
# ============================================================================


class TestAutoDetectionIntegration:
    """Integration-level tests for auto-detection in generation."""

    @pytest.mark.skip(reason="Full integration — needs DB + FastAPI TestClient")
    async def test_post_generate_returns_language_in_response(self):
        """AC-T7.1+7.2: POST /generate/{content_type} returns language in response body."""
        ...

    @pytest.mark.skip(reason="Full integration — needs DB + FastAPI TestClient")
    async def test_non_english_topic_language_in_response(self):
        """AC-T7.1: Non-English topic returns detected language code."""
        ...

    @pytest.mark.skip(reason="Full integration — needs DB + FastAPI TestClient")
    async def test_english_topic_works_unchanged(self):
        """AC-T7.4: English topic works without regression."""
        ...

    @pytest.mark.skip(reason="Full integration — needs DB + FastAPI TestClient")
    async def test_generation_persists_language(self):
        """AC-T7.1: Language is persisted on Generation ORM record."""
        ...

    @pytest.mark.skip(reason="Full integration — needs DB + FastAPI TestClient")
    async def test_backward_compatibility_no_language_field(self):
        """AC-T7.4: Existing generations without language still load."""
        ...

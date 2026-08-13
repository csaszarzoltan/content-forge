"""Interface and behavioral tests for TranslationService (AC-T4.3–AC-T4.9).

Interface tests  — verify imports, class hierarchies, method signatures (PASS).
Behavioral tests — verify NotImplementedError until implemented (FAIL).
"""

from __future__ import annotations

import inspect

import pytest

# Mark as quick (unit tests)
pytestmark = pytest.mark.quick

from src.schemas.translation import TranslateRequest
from src.services.translation import TranslationService

# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestTranslationServiceInterface:
    """Verify TranslationService class and method signatures."""

    def test_class_importable(self):
        assert TranslationService is not None

    def test_is_class(self):
        assert inspect.isclass(TranslationService)

    def test_init_signature(self):
        sig = inspect.signature(TranslationService.__init__)
        assert "self" in sig.parameters

    def test_translate_method_exists(self):
        assert hasattr(TranslationService, "translate")
        assert callable(TranslationService.translate)

    def test_translate_is_async(self):
        assert inspect.iscoroutinefunction(TranslationService.translate)

    def test_translate_signature(self):
        """translate() should accept a TranslateRequest and an optional user_id."""
        sig = inspect.signature(TranslationService.translate)
        assert "request" in sig.parameters
        assert "user_id" in sig.parameters

    def test_translate_returns_translate_response(self):
        """translate() return annotation should be TranslateResponse."""
        ann = TranslationService.translate.__annotations__
        assert "return" in ann
        return_hint = ann["return"]
        return_str = str(return_hint)
        assert "TranslateResponse" in return_str

    def test_select_mode_exists(self):
        assert hasattr(TranslationService, "_select_mode")
        assert callable(TranslationService._select_mode)

    def test_translate_via_llm_exists(self):
        assert hasattr(TranslationService, "_translate_via_llm")
        assert inspect.iscoroutinefunction(TranslationService._translate_via_llm)

    def test_translate_via_nmt_exists(self):
        assert hasattr(TranslationService, "_translate_via_nmt")
        assert inspect.iscoroutinefunction(TranslationService._translate_via_nmt)

    def test_detect_language_exists(self):
        assert hasattr(TranslationService, "_detect_language")
        assert inspect.iscoroutinefunction(TranslationService._detect_language)

    def test_chunk_content_exists(self):
        assert hasattr(TranslationService, "_chunk_content")
        assert callable(TranslationService._chunk_content)

    def test_score_translation_exists(self):
        assert hasattr(TranslationService, "_score_translation")
        assert callable(TranslationService._score_translation)

    def test_validate_language_pair_exists(self):
        assert hasattr(TranslationService, "_validate_language_pair")
        assert callable(TranslationService._validate_language_pair)


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (fail with NotImplementedError until impl)
# ============================================================================


class TestTranslationServiceInit:
    """TranslationService.__init__ works."""

    def test_init_succeeds(self):
        """TranslationService.__init__ creates an instance."""
        svc = TranslationService()
        assert svc is not None
        assert hasattr(svc, "_supported_pairs")


class TestTranslationServiceAutoMode:
    """AC-T4.3 — auto mode selection."""

    def test_auto_mode_llm_for_blog(self):
        """auto mode selects LLM for blog content_type."""
        svc = TranslationService()
        assert svc._select_mode("blog", "auto") == "llm"

    def test_auto_mode_llm_for_social(self):
        """auto mode selects LLM for social content_type."""
        svc = TranslationService()
        assert svc._select_mode("social", "auto") == "llm"

    def test_auto_mode_nmt_for_email(self):
        """auto mode selects NMT for email content_type."""
        svc = TranslationService()
        assert svc._select_mode("email", "auto") == "nmt"

    def test_explicit_llm_mode(self):
        """Explicit 'llm' mode overrides auto selection."""
        svc = TranslationService()
        assert svc._select_mode("email", "llm") == "llm"

    def test_explicit_nmt_mode(self):
        """Explicit 'nmt' mode overrides auto selection."""
        svc = TranslationService()
        assert svc._select_mode("blog", "nmt") == "nmt"


class TestTranslationServiceBrandVoice:
    """AC-T4.4 — Brand voice injection in LLM translation mode."""

    @pytest.mark.skip(reason="Needs LLM provider")
    @pytest.mark.asyncio
    async def test_llm_translation_with_brand_voice(self):
        """When brand_voice_id is provided in LLM mode, profile is injected."""
        svc = TranslationService()
        await svc._translate_via_llm(
            text="Hello world",
            source_language="en",
            target_language="de",
            content_type="blog",
            brand_voice_id="acme-corp-v1",
        )

    @pytest.mark.skip(reason="Needs LLM provider")
    @pytest.mark.asyncio
    async def test_llm_translation_without_brand_voice(self):
        """LLM translation works without brand_voice_id."""
        svc = TranslationService()
        await svc._translate_via_llm(
            text="Hello world",
            source_language="en",
            target_language="de",
            content_type="blog",
            brand_voice_id=None,
        )


class TestTranslationServiceAutoDetection:
    """AC-T4.5 — Auto source language detection."""

    @pytest.mark.asyncio
    async def test_detect_language_english(self):
        """Detect English text."""
        svc = TranslationService()
        result = await svc._detect_language("Hello, how are you today?")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_detect_language_german(self):
        """Detect German text."""
        svc = TranslationService()
        result = await svc._detect_language("Hallo, wie geht es Ihnen heute?")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_detect_language_short_input(self):
        """Short/invalid input returns 'und'."""
        svc = TranslationService()
        result = await svc._detect_language("Hi")
        assert result == "und"

    @pytest.mark.asyncio
    async def test_detect_language_empty(self):
        """Empty string returns 'und'."""
        svc = TranslationService()
        result = await svc._detect_language("")
        assert result == "und"


class TestTranslationServiceQualityScoring:
    """AC-T4.6 — Quality scoring integration (BLEU + chrF)."""

    def test_score_with_reference(self):
        """Scoring with reference returns BLEU + chrF."""
        svc = TranslationService()
        result = svc._score_translation(
            source="Hello world",
            translation="Hallo Welt",
            reference="Hallo Welt",
        )
        assert isinstance(result, dict)
        assert "bleu" in result
        assert "chrf" in result

    def test_score_without_reference(self):
        """Scoring without reference returns scores dict."""
        svc = TranslationService()
        result = svc._score_translation(
            source="Hello world",
            translation="Hallo Welt",
            reference=None,
        )
        assert isinstance(result, dict)
        assert "bleu" in result
        assert "chrf" in result

    def test_score_identical_strings(self):
        """Identical source and translation yield perfect scores."""
        svc = TranslationService()
        result = svc._score_translation(
            source="Test",
            translation="Test",
            reference="Test",
        )
        assert isinstance(result, dict)
        assert result["bleu"] == 100.0
        assert result["chrf"] == 100.0


class TestTranslationServiceLanguagePairValidation:
    """AC-T4.7 — Validate supported language pairs."""

    def test_validate_supported_pair(self):
        """Valid language pair (en->de) passes."""
        svc = TranslationService()
        svc._validate_language_pair("en", "de")  # should not raise

    def test_validate_same_language_raises(self):
        """Same source and target language raises ValueError."""
        svc = TranslationService()
        with pytest.raises(ValueError):
            svc._validate_language_pair("en", "en")

    def test_validate_unsupported_pair_raises(self):
        """Unsupported language pair raises ValueError."""
        svc = TranslationService()
        with pytest.raises(ValueError):
            svc._validate_language_pair("en", "xx")


class TestTranslationServiceContentChunking:
    """AC-T4.8 — Content chunking for large inputs."""

    def test_short_content_not_chunked(self):
        """Content under 4000 chars returns single chunk."""
        svc = TranslationService()
        chunks = svc._chunk_content("Short text", max_chars=4000)
        assert isinstance(chunks, list)
        assert len(chunks) == 1
        assert chunks[0] == "Short text"

    def test_long_content_chunked(self):
        """Content over 4000 chars is split into chunks."""
        long_text = "A" * 5000
        svc = TranslationService()
        chunks = svc._chunk_content(long_text, max_chars=4000)
        assert isinstance(chunks, list)
        assert len(chunks) >= 2

    def test_chunk_boundary(self):
        """Content exactly at 4000 chars returns single chunk."""
        text = "A" * 4000
        svc = TranslationService()
        chunks = svc._chunk_content(text, max_chars=4000)
        assert isinstance(chunks, list)
        assert len(chunks) == 1
        assert len(chunks[0]) == 4000

    def test_empty_content(self):
        """Empty string returns empty list."""
        svc = TranslationService()
        chunks = svc._chunk_content("", max_chars=4000)
        assert isinstance(chunks, list)
        assert len(chunks) == 0


class TestTranslationServiceDeepLFallback:
    """AC-T4.9 — Graceful fallback when deepl not installed."""

    @pytest.mark.asyncio
    async def test_nmt_raises_when_deepl_missing(self):
        """NMT path raises RuntimeError if deepl package is not installed."""
        with pytest.raises(RuntimeError):
            svc = TranslationService()
            await svc._translate_via_nmt(
                text="Hello world",
                source_language="en",
                target_language="de",
            )


class TestTranslationServiceFullTranslate:
    """Integration-level translate() method."""

    @pytest.mark.asyncio
    async def test_translate_raises_for_unsupported_pair(self):
        """Top-level translate() raises ValueError for unsupported language pair."""
        with pytest.raises(ValueError):
            svc = TranslationService()
            req = TranslateRequest(text="Hello", target_language="de")
            await svc.translate(req)

"""Interface tests for translation Pydantic schemas (AC-T4.1, AC-T4.2).

Interface tests verify imports, model subclasses, field signatures, and
defaults — they should PASS immediately after schemas are defined.
"""

from __future__ import annotations

import inspect
import typing

import pytest


# Mark as quick (unit tests)
pytestmark = pytest.mark.quick

from src.schemas.translation import (
    TranslateRequest,
    TranslateResponse,
    TranslationMode,
)

# ============================================================================
# SECTION 1 — TRANSLATION SCHEMA INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestTranslateRequestInterface:
    """Verify TranslateRequest schema (AC-T4.1)."""

    def test_importable(self):
        assert TranslateRequest is not None

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(TranslateRequest, BaseModel)

    def test_text_field_exists(self):
        sig = inspect.signature(TranslateRequest)
        assert "text" in sig.parameters

    def test_source_language_field_exists(self):
        sig = inspect.signature(TranslateRequest)
        assert "source_language" in sig.parameters

    def test_target_language_field_exists(self):
        sig = inspect.signature(TranslateRequest)
        assert "target_language" in sig.parameters

    def test_content_type_field_exists(self):
        sig = inspect.signature(TranslateRequest)
        assert "content_type" in sig.parameters

    def test_brand_voice_id_field_exists(self):
        sig = inspect.signature(TranslateRequest)
        assert "brand_voice_id" in sig.parameters

    def test_mode_field_exists(self):
        sig = inspect.signature(TranslateRequest)
        assert "mode" in sig.parameters

    def test_scoring_field_exists(self):
        sig = inspect.signature(TranslateRequest)
        assert "scoring" in sig.parameters

    def test_default_source_language_is_auto(self):
        req = TranslateRequest(text="Hello", target_language="de")
        assert req.source_language == "auto"

    def test_default_mode_is_auto(self):
        req = TranslateRequest(text="Hello", target_language="de")
        assert req.mode == "auto"

    def test_default_scoring_is_false(self):
        req = TranslateRequest(text="Hello", target_language="de")
        assert req.scoring is False

    def test_default_content_type_is_general(self):
        req = TranslateRequest(text="Hello", target_language="de")
        assert req.content_type == "general"

    def test_brand_voice_id_optional(self):
        req = TranslateRequest(text="Hello", target_language="de")
        assert req.brand_voice_id is None

    def test_text_min_length_enforced(self):
        """Empty text should fail validation."""
        with pytest.raises(Exception):
            TranslateRequest(text="", target_language="de")

    def test_target_language_required(self):
        """target_language has no default — must be provided."""
        with pytest.raises(Exception):
            TranslateRequest(text="Hello")

    def test_mode_literal_llm(self):
        """'llm' is a valid mode."""
        req = TranslateRequest(text="Hi", target_language="fr", mode="llm")
        assert req.mode == "llm"

    def test_mode_literal_nmt(self):
        """'nmt' is a valid mode."""
        req = TranslateRequest(text="Hi", target_language="fr", mode="nmt")
        assert req.mode == "nmt"

    def test_mode_literal_auto(self):
        """'auto' is a valid mode."""
        req = TranslateRequest(text="Hi", target_language="fr", mode="auto")
        assert req.mode == "auto"

    def test_mode_invalid_rejected(self):
        """Invalid mode string should fail validation."""
        with pytest.raises(Exception):
            TranslateRequest(text="Hi", target_language="fr", mode="invalid")


class TestTranslateResponseInterface:
    """Verify TranslateResponse schema (AC-T4.2)."""

    def test_importable(self):
        assert TranslateResponse is not None

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(TranslateResponse, BaseModel)

    def test_translated_text_field_exists(self):
        sig = inspect.signature(TranslateResponse)
        assert "translated_text" in sig.parameters

    def test_detected_source_language_field_exists(self):
        sig = inspect.signature(TranslateResponse)
        assert "detected_source_language" in sig.parameters

    def test_target_language_field_exists(self):
        sig = inspect.signature(TranslateResponse)
        assert "target_language" in sig.parameters

    def test_mode_used_field_exists(self):
        sig = inspect.signature(TranslateResponse)
        assert "mode_used" in sig.parameters

    def test_quality_scores_field_exists(self):
        sig = inspect.signature(TranslateResponse)
        assert "quality_scores" in sig.parameters

    def test_tokens_used_field_exists(self):
        sig = inspect.signature(TranslateResponse)
        assert "tokens_used" in sig.parameters

    def test_latency_ms_field_exists(self):
        sig = inspect.signature(TranslateResponse)
        assert "latency_ms" in sig.parameters

    def test_default_quality_scores_is_none(self):
        resp = TranslateResponse(
            translated_text="Hallo",
            detected_source_language="en",
            target_language="de",
            mode_used="llm",
        )
        assert resp.quality_scores is None

    def test_default_tokens_used_zero(self):
        resp = TranslateResponse(
            translated_text="Hallo",
            detected_source_language="en",
            target_language="de",
            mode_used="llm",
        )
        assert resp.tokens_used == 0

    def test_default_latency_ms_zero(self):
        resp = TranslateResponse(
            translated_text="Hallo",
            detected_source_language="en",
            target_language="de",
            mode_used="llm",
        )
        assert resp.latency_ms == 0

    def test_minimal_response_creates(self):
        """Translated text, languages, and mode_used are required."""
        resp = TranslateResponse(
            translated_text="Bonjour",
            detected_source_language="en",
            target_language="fr",
            mode_used="nmt",
        )
        assert resp.translated_text == "Bonjour"
        assert resp.detected_source_language == "en"
        assert resp.target_language == "fr"
        assert resp.mode_used == "nmt"


class TestTranslationModeLiteral:
    """Verify TranslationMode type alias."""

    def test_translation_mode_importable(self):
        assert TranslationMode is not None

    def test_translation_mode_accepts_valid_values(self):
        """Verify the type hint permits the three valid mode strings."""
        args = typing.get_args(TranslationMode)
        assert "llm" in args
        assert "nmt" in args
        assert "auto" in args
        assert len(args) == 3

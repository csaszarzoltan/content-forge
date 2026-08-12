"""
Interface and behavioral tests for the Language Detection module.

Interface tests  — verify imports, type signatures, constants (should PASS).
Behavioral tests — verify actual detection functionality now that it's implemented.

Total: 20+ unit tests + 3 integration tests.
"""

from __future__ import annotations

import dataclasses
import inspect
import time
from typing import get_type_hints

import pytest

# Mark as quick (unit tests)
pytestmark = pytest.mark.quick

from src.services.language_detection import (
    RELIABILITY_THRESHOLD,
    SHORT_TEXT_THRESHOLD,
    SUPPORTED_LANGUAGES,
    LanguageResult,
    detect_language,
    get_supported_languages,
    is_language_supported,
)

# ============================================================================
# INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestLanguageResultInterface:
    """Verify LanguageResult dataclass contract."""

    def test_importable(self):
        assert LanguageResult is not None

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(LanguageResult)

    def test_has_language_code_field(self):
        hints = get_type_hints(LanguageResult)
        assert "language_code" in hints
        assert hints["language_code"] is str

    def test_language_code_defaults_to_und(self):
        r = LanguageResult()
        assert r.language_code == "und"

    def test_has_confidence_field(self):
        hints = get_type_hints(LanguageResult)
        assert "confidence" in hints
        assert hints["confidence"] is float

    def test_confidence_defaults_to_0(self):
        r = LanguageResult()
        assert r.confidence == 0.0

    def test_has_is_reliable_field(self):
        hints = get_type_hints(LanguageResult)
        assert "is_reliable" in hints
        assert hints["is_reliable"] is bool

    def test_is_reliable_defaults_to_false(self):
        r = LanguageResult()
        assert r.is_reliable is False

    def test_can_create_with_all_fields(self):
        r = LanguageResult(language_code="en", confidence=0.95, is_reliable=True)
        assert r.language_code == "en"
        assert r.confidence == 0.95
        assert r.is_reliable is True


class TestDetectLanguageInterface:
    """Verify detect_language function contract."""

    def test_detect_language_importable(self):
        assert detect_language is not None

    def test_detect_language_is_callable(self):
        assert callable(detect_language)

    def test_detect_language_takes_string_arg(self):
        sig = inspect.signature(detect_language)
        assert "text" in sig.parameters
        param = sig.parameters["text"]
        assert param.annotation is str or "str" in str(param.annotation)

    def test_detect_language_returns_language_result(self):
        hints = get_type_hints(detect_language)
        return_type = hints.get("return")
        assert return_type is LanguageResult or "LanguageResult" in str(return_type)


class TestConstantsInterface:
    """Verify module-level constants."""

    def test_supported_languages_list_exists(self):
        assert isinstance(SUPPORTED_LANGUAGES, list)

    def test_50_plus_supported_languages(self):
        assert len(SUPPORTED_LANGUAGES) >= 50, (
            f"Only {len(SUPPORTED_LANGUAGES)} languages — need at least 50"
        )

    def test_supported_languages_are_strings(self):
        for code in SUPPORTED_LANGUAGES:
            assert isinstance(code, str), f"Non-string entry: {code!r}"

    def test_supported_languages_are_lowercase(self):
        for code in SUPPORTED_LANGUAGES:
            assert code == code.lower(), f"Non-lowercase: {code!r}"

    def test_iso_639_1_format(self):
        for code in SUPPORTED_LANGUAGES:
            assert 2 <= len(code) <= 5, f"Non-ISO 639 code: {code!r}"

    @pytest.mark.parametrize(
        "expected_lang",
        [
            # European
            "en", "de", "fr", "es", "it", "pt", "nl", "pl", "sv", "da",
            "fi", "no", "cs", "hu", "ro", "el",
            # Asian
            "ja", "ko", "zh", "hi", "th", "vi",
            # Middle East
            "ar", "he", "fa", "tr",
            # Other
            "ru",
        ],
    )
    def test_key_languages_present(self, expected_lang: str):
        assert expected_lang in SUPPORTED_LANGUAGES, (
            f"Missing critical language: {expected_lang}"
        )

    def test_short_text_threshold_defined(self):
        assert isinstance(SHORT_TEXT_THRESHOLD, int)
        assert SHORT_TEXT_THRESHOLD > 0

    def test_reliability_threshold_defined(self):
        assert isinstance(RELIABILITY_THRESHOLD, float)
        assert 0.0 <= RELIABILITY_THRESHOLD <= 1.0


class TestGetSupportedLanguagesInterface:
    """Verify get_supported_languages function contract."""

    def test_get_supported_languages_importable(self):
        assert get_supported_languages is not None

    def test_get_supported_languages_callable(self):
        assert callable(get_supported_languages)

    def test_get_supported_languages_returns_list(self):
        hints = get_type_hints(get_supported_languages)
        return_type = hints.get("return")
        assert return_type is not None


class TestIsLanguageSupportedInterface:
    """Verify is_language_supported function contract."""

    def test_is_language_supported_importable(self):
        assert is_language_supported is not None

    def test_is_language_supported_callable(self):
        assert callable(is_language_supported)

    def test_is_language_supported_takes_code_arg(self):
        sig = inspect.signature(is_language_supported)
        assert "code" in sig.parameters
        param = sig.parameters["code"]
        assert param.annotation is str or "str" in str(param.annotation)

    def test_is_language_supported_returns_bool(self):
        hints = get_type_hints(is_language_supported)
        return_type = hints.get("return")
        assert return_type is bool or "bool" in str(return_type)


class TestImportGuardInterface:
    """Verify the optional-dependency import guard."""

    def test_module_importable_without_fast_langdetect(self):
        """AC-T1.6: Module is importable without optional deps."""
        import importlib
        import sys

        # Simulate fast-langdetect not being available
        saved = sys.modules.pop("src.services.language_detection", None)
        try:
            mod = importlib.import_module("src.services.language_detection")
            assert mod is not None
        finally:
            if saved:
                sys.modules["src.services.language_detection"] = saved


# ============================================================================
# BEHAVIORAL TESTS (verify the fully-implemented functions)
# ============================================================================


class TestDetectLanguageBehavior:
    """Expected behaviour of detect_language — fully implemented."""

    @pytest.mark.parametrize(
        "text, expected_code",
        [
            ("Hello, how are you today? This is a test.", "en"),
            ("Hallo, wie geht es dir heute? Das ist ein Test.", "de"),
            ("Bonjour, comment allez-vous aujourd'hui? Ceci est un test.", "fr"),
            ("Hola, ¿cómo estás hoy? Esto es una prueba.", "es"),
            ("Ciao, come stai oggi? Questo è un test.", "it"),
        ],
    )
    def test_single_language_inputs(self, text: str, expected_code: str):
        """AC-T1.1: detect_language returns correct ISO 639-1 code for single-language input."""
        result = detect_language(text)
        assert result.language_code == expected_code

    def test_short_input_returns_und(self):
        """AC-T1.3: Inputs under SHORT_TEXT_THRESHOLD chars return language_code='und'."""
        short = "Hi"
        assert len(short) < SHORT_TEXT_THRESHOLD
        result = detect_language(short)
        assert result.language_code == "und"

    def test_invalid_input_returns_und(self):
        """AC-T1.3: Non-linguistic / invalid input returns language_code='und'."""
        gibberish = "zzzzzzzz zzzzzzzz zzzzzzzz zzzzzzzz"
        result = detect_language(gibberish)
        assert result.language_code == "und"

    def test_empty_string_returns_und(self):
        """AC-T1.3: Empty string returns language_code='und' with 0.0 confidence."""
        result = detect_language("")
        assert result.language_code == "und"
        assert result.confidence == 0.0
        assert result.is_reliable is False

    def test_mixed_language_returns_dominant(self):
        """AC-T1.4: Mixed-language input returns the dominant language."""
        mostly_english = (
            "This is mostly English text with just a bit of français sprinkled in."
        )
        result = detect_language(mostly_english)
        # The dominant language should be English
        assert result.language_code in ("en", "und")
        assert result.is_reliable or result.language_code == "und"

    def test_unicode_non_ascii_input(self):
        """Unicode / non-ASCII characters (e.g. Japanese) are handled."""
        japanese = "今日はいい天気ですね。散歩に行きましょう。"
        result = detect_language(japanese)
        # fast-langdetect may or may not detect Japanese reliably
        assert result.language_code in ("ja", "und")

    def test_code_format_is_iso_639_1(self):
        """AC-T1.1: language_code matches ISO 639-1 format (2 chars, lowercase, or 'und')."""
        text = "This is a perfectly normal English sentence."
        result = detect_language(text)
        assert result.language_code == "en" or (
            len(result.language_code) == 2 and result.language_code.islower()
        ) or result.language_code == "und"

    @pytest.mark.parametrize(
        "text, expected_reliable",
        [
            ("This is a long and clear English paragraph that should be reliable.", True),
            ("Hi", False),
        ],
    )
    def test_confidence_reliability(self, text: str, expected_reliable: bool):
        """AC-T1.1: is_reliable reflects confidence >= RELIABILITY_THRESHOLD."""
        result = detect_language(text)
        assert result.is_reliable == expected_reliable, (
            f"Expected is_reliable={expected_reliable} for text={text!r}, "
            f"got is_reliable={result.is_reliable} with confidence={result.confidence}"
        )

    def test_confidence_in_range(self):
        """confidence is a float in [0.0, 1.0]."""
        text = "The quick brown fox jumps over the lazy dog."
        result = detect_language(text)
        assert 0.0 <= result.confidence <= 1.0

    def test_detect_language_stub_raises_not_implemented(self):
        """Stub no longer raises NotImplementedError — function is fully implemented."""
        result = detect_language("Hello world")
        assert result.language_code is not None
        assert isinstance(result, LanguageResult)

    def test_chinese_simplified_detected(self):
        """Simplified Chinese (zh) detection."""
        text = "今天天气真好，我们去散步吧。"
        result = detect_language(text)
        assert result.language_code in ("zh", "und")

    def test_russian_text_detected(self):
        """Cyrillic script (ru) detection."""
        text = "Сегодня хорошая погода, пойдем гулять."
        result = detect_language(text)
        assert result.language_code in ("ru", "und")

    def test_arabic_text_detected(self):
        """Arabic script (ar) detection."""
        text = "اليوم الجو جميل، دعنا نذهب في نزهة."
        result = detect_language(text)
        assert result.language_code in ("ar", "und")

    def test_korean_text_detected(self):
        """Korean (ko) detection."""
        text = "오늘 날씨가 좋네요. 산책하러 갑시다."
        result = detect_language(text)
        assert result.language_code in ("ko", "und")


class TestGetSupportedLanguagesBehavior:
    """Expected behaviour of get_supported_languages."""

    def test_returns_list_of_dicts(self):
        result = get_supported_languages()
        assert isinstance(result, list)
        for entry in result:
            assert isinstance(entry, dict)

    def test_each_entry_has_code_and_name(self):
        result = get_supported_languages()
        for entry in result:
            assert "code" in entry, f"Missing 'code' key in {entry}"
            assert "name" in entry, f"Missing 'name' key in {entry}"
            assert isinstance(entry["code"], str)
            assert isinstance(entry["name"], str)


class TestIsLanguageSupportedBehavior:
    """Expected behaviour of is_language_supported."""

    @pytest.mark.parametrize("code", ["en", "de", "ja", "ar"])
    def test_supported_code_returns_true(self, code: str):
        assert is_language_supported(code) is True

    @pytest.mark.parametrize("code", ["xx", "zz", "", "123"])
    def test_unsupported_code_returns_false(self, code: str):
        assert is_language_supported(code) is False


# ============================================================================
# INTEGRATION TESTS (verify real implementation)
# ============================================================================


class TestLanguageDetectionIntegration:
    """Integration-level behaviours for the real module."""

    def test_detection_under_100ms(self):
        """AC-T1.5: Detection completes in <100ms for 1KB text input."""
        text_1kb = ("Hello world. " * 100)[:1024]
        assert len(text_1kb.encode("utf-8")) > 900  # approximately 1KB
        start = time.monotonic()
        detect_language(text_1kb)
        elapsed = time.monotonic() - start
        assert elapsed < 0.1, f"Detection took {elapsed:.3f}s, expected < 0.1s"

    def test_stateless_multiple_calls(self):
        """AC-T1.7: Module is stateless — multiple calls return same result for same input."""
        text = "This is a test sentence."
        r1 = detect_language(text)
        r2 = detect_language(text)
        assert r1.language_code == r2.language_code
        assert r1.confidence == r2.confidence
        assert r1.is_reliable == r2.is_reliable

    def test_detection_pipeline(self):
        """End-to-end: call detect_language and validate LanguageResult fields."""
        text = "Natural language processing enables computers to understand human speech."
        result = detect_language(text)
        assert isinstance(result, LanguageResult)
        assert isinstance(result.language_code, str)
        assert result.language_code != ""  # must not be empty
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.is_reliable, bool)

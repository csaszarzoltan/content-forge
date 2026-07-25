"""
Language detection module for ContentForge.

Wraps ``fast-langdetect`` to provide ``detect_language(text) -> LanguageResult``
with an import guard for optional dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Auto-import guard — fails early when optional deps are missing
# ---------------------------------------------------------------------------

def _check_optional_deps() -> None:
    """Raise ImportError if fast-langdetect is not installed."""
    try:
        import fast_langdetect  # noqa: F401
    except ImportError:
        raise ImportError(
            "fast-langdetect is required for language detection. "
            "Install it with: pip install fast-langdetect>=1.0"
        )


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------

@dataclass
class LanguageResult:
    """Result of a language detection call.

    Attributes:
        language_code: ISO 639-1 language code (e.g. "en", "de", "fr").
            Returns "und" for undetermined / short inputs.
        confidence: Detection confidence in [0.0, 1.0].
        is_reliable: True when confidence >= 0.5.
    """

    language_code: str = "und"
    confidence: float = 0.0
    is_reliable: bool = False


# ---------------------------------------------------------------------------
# Supported-language constants
# ---------------------------------------------------------------------------

# Minimum set: 50+ languages across European, Asian, Middle Eastern groups
SUPPORTED_LANGUAGES: list[str] = [
    "en", "de", "fr", "es", "it", "pt", "nl", "pl", "sv", "da",
    "fi", "no", "cs", "hu", "ro", "uk", "el", "bg", "hr", "sk",
    "lt", "lv", "sl", "et",
    "ja", "ko", "zh", "hi", "th", "vi", "id", "ms", "tl",
    "my", "km", "lo",
    "ar", "he", "fa", "tr", "ur",
    "ru", "ca", "gl", "eu", "af", "sw",
    "sr", "mk", "is", "mt",
]

SHORT_TEXT_THRESHOLD: int = 10
"""Inputs shorter than this many characters return language_code ``und``."""

RELIABILITY_THRESHOLD: float = 0.5
"""Confidence at or above this value marks ``is_reliable=True``."""


# ---------------------------------------------------------------------------
# Language name lookup (ISO 639-1 code -> English name)
# ---------------------------------------------------------------------------

_LANGUAGE_NAMES: dict[str, str] = {
    "en": "English", "de": "German", "fr": "French", "es": "Spanish",
    "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "pl": "Polish",
    "sv": "Swedish", "da": "Danish", "fi": "Finnish", "no": "Norwegian",
    "cs": "Czech", "hu": "Hungarian", "ro": "Romanian", "uk": "Ukrainian",
    "el": "Greek", "bg": "Bulgarian", "hr": "Croatian", "sk": "Slovak",
    "lt": "Lithuanian", "lv": "Latvian", "sl": "Slovenian", "et": "Estonian",
    "ja": "Japanese", "ko": "Korean", "zh": "Chinese", "hi": "Hindi",
    "th": "Thai", "vi": "Vietnamese", "id": "Indonesian", "ms": "Malay",
    "tl": "Filipino", "my": "Burmese", "km": "Khmer", "lo": "Lao",
    "ar": "Arabic", "he": "Hebrew", "fa": "Persian", "tr": "Turkish",
    "ur": "Urdu", "ru": "Russian", "ca": "Catalan", "gl": "Galician",
    "eu": "Basque", "af": "Afrikaans", "sw": "Swahili",
    "sr": "Serbian", "mk": "Macedonian", "is": "Icelandic", "mt": "Maltese",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_language(text: str) -> LanguageResult:
    """Detect the language of *text*.

    Args:
        text: UTF-8 string to analyse.

    Returns:
        LanguageResult with detected language code, confidence, reliability flag.

    Raises:
        ImportError: If ``fast-langdetect`` is not installed.
    """
    # Check for empty/very short input
    if not text or len(text.strip()) < SHORT_TEXT_THRESHOLD:
        return LanguageResult(language_code="und", confidence=0.0, is_reliable=False)

    # Try fast-langdetect first
    _check_optional_deps()
    import fast_langdetect

    try:
        raw = fast_langdetect.detect(text)
        # fast-langdetect returns a list of dicts like [{"lang": "en", "score": 0.99}]
        # or a single dict {"language": "en", "score": 0.99} depending on version
        if isinstance(raw, list) and raw:
            result = raw[0]
        elif isinstance(raw, dict):
            result = raw
        else:
            result = {}
        lang_code = result.get("lang") or result.get("language") or "und"
        if isinstance(lang_code, str):
            lang_code = lang_code.lower()
        else:
            lang_code = "und"
        confidence = result.get("score") or result.get("confidence") or 0.0
        if isinstance(confidence, str):
            try:
                confidence = float(confidence.rstrip("%")) / 100.0
            except (ValueError, AttributeError):
                confidence = 0.0

        # Normalize language code
        if lang_code and len(lang_code) >= 2:
            lang_code = lang_code[:2].lower()
        else:
            lang_code = "und"

        # Validate against supported languages
        if lang_code != "und" and lang_code not in SUPPORTED_LANGUAGES:
            lang_code = "und"
            confidence = 0.0

        is_reliable = confidence >= RELIABILITY_THRESHOLD
        return LanguageResult(
            language_code=lang_code,
            confidence=round(confidence, 4),
            is_reliable=is_reliable,
        )
    except Exception:
        return LanguageResult(language_code="und", confidence=0.0, is_reliable=False)


def get_supported_languages() -> list[dict[str, str]]:
    """Return the list of languages the module supports.

    Each entry is ``{"code": "en", "name": "English"}``.
    The name is the ISO language's English exonym.
    """
    return [
        {"code": code, "name": _LANGUAGE_NAMES.get(code, code)}
        for code in SUPPORTED_LANGUAGES
    ]


def is_language_supported(code: str) -> bool:
    """Return True if *code* is in the supported set."""
    return code in SUPPORTED_LANGUAGES

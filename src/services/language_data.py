"""Language data service — static/config-driven supported languages.

This service provides the list of languages supported by ContentForge.
The data is static / config-driven (not persisted in the database).
"""

from __future__ import annotations

from src.schemas.languages import LanguageInfo, LanguageResponse

# ---------------------------------------------------------------------------
# Static language data: ISO 639-1 codes with metadata
# ---------------------------------------------------------------------------
# Each entry: code, native_name, english_name, status, supports_translation, supports_detection

_LANGUAGE_DATA: list[dict] = [
    # Active languages (full support)
    {"code": "en", "name": "English", "english_name": "English", "status": "active", "supports_translation": True, "supports_detection": True},
    {"code": "de", "name": "Deutsch", "english_name": "German", "status": "active", "supports_translation": True, "supports_detection": True},
    {"code": "fr", "name": "Français", "english_name": "French", "status": "active", "supports_translation": True, "supports_detection": True},
    {"code": "es", "name": "Español", "english_name": "Spanish", "status": "active", "supports_translation": True, "supports_detection": True},
    {"code": "it", "name": "Italiano", "english_name": "Italian", "status": "active", "supports_translation": True, "supports_detection": True},
    {"code": "pt", "name": "Português", "english_name": "Portuguese", "status": "active", "supports_translation": True, "supports_detection": True},
    {"code": "nl", "name": "Nederlands", "english_name": "Dutch", "status": "active", "supports_translation": True, "supports_detection": True},
    {"code": "pl", "name": "Polski", "english_name": "Polish", "status": "active", "supports_translation": True, "supports_detection": True},
    {"code": "ja", "name": "日本語", "english_name": "Japanese", "status": "active", "supports_translation": True, "supports_detection": True},
    {"code": "zh", "name": "中文", "english_name": "Chinese", "status": "active", "supports_translation": True, "supports_detection": True},
    # Beta languages (experimental support)
    {"code": "sv", "name": "Svenska", "english_name": "Swedish", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "da", "name": "Dansk", "english_name": "Danish", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "fi", "name": "Suomi", "english_name": "Finnish", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "no", "name": "Norsk", "english_name": "Norwegian", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "cs", "name": "Čeština", "english_name": "Czech", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "hu", "name": "Magyar", "english_name": "Hungarian", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "ro", "name": "Română", "english_name": "Romanian", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "uk", "name": "Українська", "english_name": "Ukrainian", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "el", "name": "Ελληνικά", "english_name": "Greek", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "bg", "name": "Български", "english_name": "Bulgarian", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "hr", "name": "Hrvatski", "english_name": "Croatian", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "sk", "name": "Slovenčina", "english_name": "Slovak", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "lt", "name": "Lietuvių", "english_name": "Lithuanian", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "lv", "name": "Latviešu", "english_name": "Latvian", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "sl", "name": "Slovenščina", "english_name": "Slovenian", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "et", "name": "Eesti", "english_name": "Estonian", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "ko", "name": "한국어", "english_name": "Korean", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "hi", "name": "हिन्दी", "english_name": "Hindi", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "th", "name": "ไทย", "english_name": "Thai", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "vi", "name": "Tiếng Việt", "english_name": "Vietnamese", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "id", "name": "Bahasa Indonesia", "english_name": "Indonesian", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "ms", "name": "Bahasa Melayu", "english_name": "Malay", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "tl", "name": "Tagalog", "english_name": "Filipino", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "ar", "name": "العربية", "english_name": "Arabic", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "he", "name": "עברית", "english_name": "Hebrew", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "fa", "name": "فارسی", "english_name": "Persian", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "tr", "name": "Türkçe", "english_name": "Turkish", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "ur", "name": "اردو", "english_name": "Urdu", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "ru", "name": "Русский", "english_name": "Russian", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "ca", "name": "Català", "english_name": "Catalan", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "gl", "name": "Galego", "english_name": "Galician", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "eu", "name": "Euskara", "english_name": "Basque", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "af", "name": "Afrikaans", "english_name": "Afrikaans", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "sw", "name": "Kiswahili", "english_name": "Swahili", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "sr", "name": "Српски", "english_name": "Serbian", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "mk", "name": "Македонски", "english_name": "Macedonian", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "is", "name": "Íslenska", "english_name": "Icelandic", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "mt", "name": "Malti", "english_name": "Maltese", "status": "beta", "supports_translation": True, "supports_detection": True},
    {"code": "my", "name": "မြန်မာဘာသာ", "english_name": "Burmese", "status": "beta", "supports_translation": False, "supports_detection": True},
    {"code": "km", "name": "ភាសាខ្មែរ", "english_name": "Khmer", "status": "beta", "supports_translation": False, "supports_detection": True},
    {"code": "lo", "name": "ລາວ", "english_name": "Lao", "status": "beta", "supports_translation": False, "supports_detection": True},
]


class LanguageDataService:
    """Service that provides supported language metadata.

    Data is loaded from a static config and cached at service init time.
    The service is stateless after construction.
    """

    def __init__(self) -> None:
        """Initialize the language data service with static language data."""
        self._languages: dict[str, LanguageInfo] = {}

        for entry in _LANGUAGE_DATA:
            info = LanguageInfo(
                code=entry["code"],
                name=entry["name"],
                english_name=entry["english_name"],
                status=entry["status"],  # type: ignore[arg-type]
                supports_translation=entry["supports_translation"],
                supports_detection=entry["supports_detection"],
            )
            self._languages[entry["code"]] = info

        self._sorted_languages = sorted(self._languages.values(), key=lambda x: x.code)

    def get_languages(self) -> LanguageResponse:
        """Return the full list of supported languages with metadata.

        Returns:
            LanguageResponse with languages sorted alphabetically by code,
            active languages first, then beta languages.
        """
        active_first = sorted(
            [lang for lang in self._sorted_languages if lang.status == "active"],
            key=lambda x: x.code,
        )
        beta = sorted(
            [lang for lang in self._sorted_languages if lang.status == "beta"],
            key=lambda x: x.code,
        )
        ordered = active_first + beta
        return LanguageResponse(languages=ordered, total=len(ordered))

    def get_language_by_code(self, code: str) -> LanguageInfo | None:
        """Look up a single language by its ISO 639-1 code.

        Args:
            code: Two-letter ISO 639-1 language code (e.g. "en", "de").

        Returns:
            LanguageInfo if found, None if the code is not supported.
        """
        return self._languages.get(code)

    def get_active_languages(self) -> list[LanguageInfo]:
        """Return only languages with status == "active".

        Returns:
            List of active LanguageInfo entries, sorted by code.
        """
        return sorted(
            [lang for lang in self._languages.values() if lang.status == "active"],
            key=lambda x: x.code,
        )

    @property
    def total_count(self) -> int:
        """Total number of supported languages (active + beta)."""
        return len(self._languages)

    @property
    def active_count(self) -> int:
        """Number of languages with status "active"."""
        return len([lang for lang in self._languages.values() if lang.status == "active"])

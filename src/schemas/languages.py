"""Pydantic schemas for supported-languages endpoint.

GET /api/v1/languages returns LanguageResponse with a list of LanguageInfo.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LanguageInfo(BaseModel):
    """Information about a single supported language.

    Attributes:
        code: ISO 639-1 language code (e.g. "de", "fr", "ja").
        name: Native name of the language (e.g. "Deutsch", "Français").
        english_name: English name of the language (e.g. "German", "French").
        status: "active" for full support, "beta" for experimental support.
        supports_translation: Whether translation to/from this language is available.
        supports_detection: Whether auto-detection of this language is available.
    """

    code: str
    name: str
    english_name: str
    status: Literal["active", "beta"]
    supports_translation: bool
    supports_detection: bool


class LanguageResponse(BaseModel):
    """Response returned by GET /api/v1/languages.

    Attributes:
        languages: List of supported languages with metadata.
        total: Total number of languages in the list.
    """

    languages: list[LanguageInfo]
    total: int

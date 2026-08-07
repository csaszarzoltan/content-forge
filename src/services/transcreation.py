"""Transcreation & cultural adaptation service.

PROVISIONAL STUB — pre-development scaffold only. Every method raises
NotImplementedError until the developer implements the module
(US-001 .. US-005 acceptance criteria).
"""

from __future__ import annotations

from src.schemas.transcreation import (
    AdaptRequest,
    AdaptResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    PreflightRequest,
    PreflightResult,
)

# Confidence threshold below which segments are flagged for review (US-003).
CONFIDENCE_THRESHOLD = 0.7


class LocaleData:
    """Locale-specific formatting data (dates, currency, units, honorifics).

    US-002: locale data table consulted by the formatting converter.
    """

    def __init__(self) -> None:
        raise NotImplementedError("Transcreation stub — not implemented yet")

    def get_locale(self, locale: str) -> dict:
        raise NotImplementedError("Transcreation stub — not implemented yet")

    def supported_locales(self) -> list[str]:
        raise NotImplementedError("Transcreation stub — not implemented yet")


class LocaleFormatter:
    """Converts dates, currency, units and honorifics per target locale."""

    def __init__(self, data: LocaleData | None = None) -> None:
        raise NotImplementedError("Transcreation stub — not implemented yet")

    def convert_date(self, value: str, locale: str) -> str:
        raise NotImplementedError("Transcreation stub — not implemented yet")

    def convert_currency(self, value: str, locale: str) -> str:
        raise NotImplementedError("Transcreation stub — not implemented yet")

    def convert_units(self, value: str, locale: str) -> str:
        raise NotImplementedError("Transcreation stub — not implemented yet")

    def convert_honorifics(self, value: str, locale: str) -> str:
        raise NotImplementedError("Transcreation stub — not implemented yet")


class TranscreationService:
    """Orchestrates cultural-risk analysis, adaptation, and preflight."""

    def __init__(self) -> None:
        raise NotImplementedError("Transcreation stub — not implemented yet")

    async def analyze(
        self,
        text: str,
        target_locale: str,
        source_locale: str = "auto",
    ) -> AnalyzeResponse:
        """Detect cultural risk items (idioms, references, register, taboo)."""
        raise NotImplementedError("Transcreation stub — not implemented yet")

    async def adapt(
        self,
        text: str,
        target_locale: str,
        source_locale: str = "auto",
        accepted_ids: list[str] | None = None,
        rejected_ids: list[str] | None = None,
        edits: dict[str, str] | None = None,
    ) -> AdaptResponse:
        """Produce adapted text with per-segment changes and change log."""
        raise NotImplementedError("Transcreation stub — not implemented yet")

    async def preflight(
        self,
        asset_id: str,
        content: str,
        target_locale: str,
    ) -> PreflightResult:
        """Flag high-risk items and block publishing until resolved/overridden."""
        raise NotImplementedError("Transcreation stub — not implemented yet")

    async def export(self, asset_id: str) -> str:
        """Export accepted adaptations (blocked if unresolved flags exist)."""
        raise NotImplementedError("Transcreation stub — not implemented yet")

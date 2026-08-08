"""Transcreation service — cultural-risk analysis, locale formatting, and preflight.

Covers US-001 .. US-005 acceptance criteria:
  US-001  Cultural risk detection (idioms, references, register, taboo)
  US-002  Locale formatting conversion (dates, currency, units, honorifics)
  US-003  Low-confidence flagging
  US-004  Side-by-side review (per-segment accept/edit/reject)
  US-005  Pre-flight publish check

Dual-path design (mirrors ``src/services/translation.py``): risk analysis
uses the configured LLM provider when one is available; otherwise a
deterministic rule-based engine over a module-level cache of compiled risk
patterns is used. Any LLM outage is logged and the cached fallback is served
so the API keeps working (graceful degradation). Locale formatting is always
rule-based and driven by the locale data table (US-002).

Known limitation: currency conversion reformats the symbol and number for the
target locale but does NOT apply foreign-exchange rates (out of scope for the
formatting converter).
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from src.schemas.transcreation import (
    AdaptedSegment,
    AdaptResponse,
    AnalyzeResponse,
    FormatType,
    LocaleFormatItem,
    PreflightResult,
    RiskCategory,
    RiskItem,
    RiskLevel,
    SegmentDecision,
    TranscreationResult,
)

logger = logging.getLogger(__name__)

# Confidence threshold below which segments are flagged for review (US-003).
CONFIDENCE_THRESHOLD = 0.7


class TranscreationProviderError(RuntimeError):
    """LLM provider failure surfaced to the API layer (mapped to 502/503).

    The service normally degrades gracefully to the rule-based fallback and
    logs the outage instead of raising. This exception is only raised when a
    caller explicitly requires provider results (defensive path for the API).
    """


class TranscreationBlockedError(RuntimeError):
    """Publishing/export blocked by unresolved cultural-risk flags (US-003/005).

    Raised by ``export`` when no stored analysis exists or low-confidence
    segments are still unresolved. The API layer maps this to HTTP 409.
    """

# ── Cached risk patterns (US-001 rule-based fallback) ───────────────────────
# Compiled once at import time — this is the "cached risk patterns" cache.
# Each entry: compiled pattern, category, severity, confidence, description,
# and locale-aware suggested replacement (keyed by ISO 639-1 language).
_RISK_PATTERNS: list[dict[str, Any]] = [
    {
        "pattern": re.compile(r"raining cats and dogs", re.IGNORECASE),
        "category": RiskCategory.idiom,
        "risk_level": RiskLevel.medium,
        "confidence": 0.65,
        "description": "English idiom that does not translate literally.",
        "suggestion": {"de": "Es regnet in Strömen.", "en": "It is raining heavily."},
    },
    {
        "pattern": re.compile(r"whole nine yards", re.IGNORECASE),
        "category": RiskCategory.idiom,
        "risk_level": RiskLevel.medium,
        "confidence": 0.6,
        "description": "Idiomatic expression with no direct equivalent in most locales.",
        "suggestion": {"de": "das ganze Drum und Dran", "en": "the full treatment"},
    },
    {
        "pattern": re.compile(r"benedict arnold", re.IGNORECASE),
        "category": RiskCategory.cultural_reference,
        "risk_level": RiskLevel.medium,
        "confidence": 0.55,
        "description": "US-specific historical reference that is opaque outside the US.",
        "suggestion": {"de": "ein echter Verräter", "en": "a real traitor"},
    },
    {
        "pattern": re.compile(r"\bhey\s+guys\b", re.IGNORECASE),
        "category": RiskCategory.register,
        "risk_level": RiskLevel.low,
        "confidence": 0.8,
        "description": "Informal, gendered address that may mismatch formal target locales.",
        "suggestion": {"de": "Guten Tag, meine Damen und Herren", "en": "Hello everyone"},
    },
    {
        "pattern": re.compile(r"\bcrap\b|\bshit\b|\bdamn\b|\bfuck(?:ing)?\b", re.IGNORECASE),
        "category": RiskCategory.taboo,
        "risk_level": RiskLevel.high,
        "confidence": 0.95,
        "description": "Potentially offensive language that should be softened before publishing.",
        "suggestion": {"de": "Unsinn", "en": "nonsense"},
    },
]

# Literal / adapted phrase pairs used to build side-by-side segments (US-004).
# Keyed by (ISO 639-1 language, normalized source phrase).
_LITERAL_TABLE: dict[tuple[str, str], dict[str, str]] = {
    ("de", "It's raining cats and dogs"): {
        "literal": "Es regnet Katzen und Hunde.",
        "adapted": "Es regnet in Strömen.",
    },
    ("de", "He's a real Benedict Arnold"): {
        "literal": "Er ist ein echter Benedict Arnold.",
        "adapted": "Er ist ein echter Verräter.",
    },
    ("de", "Hey guys, what's up"): {
        "literal": "Hey Leute, was ist los?",
        "adapted": "Guten Tag, was kann ich für Sie tun?",
    },
    ("de", "That's a load of crap"): {
        "literal": "Das ist eine Ladung Mist.",
        "adapted": "Das ist völliger Unsinn.",
    },
    ("de", "The report is ready"): {
        "literal": "Der Bericht ist fertig.",
        "adapted": "Der Bericht ist fertig.",
    },
}

# ── Locale data table (US-002) ──────────────────────────────────────────────
# Each locale: date format, currency symbol/position, number separators,
# unit system, and honorific title mapping.
_LOCALES: dict[str, dict[str, Any]] = {
    "en-US": {
        "code": "en-US",
        "name": "English (US)",
        "date_format": "MM/DD/YYYY",
        "currency": {"symbol": "$", "position": "prefix", "code": "USD"},
        "thousands_sep": ",",
        "decimal_sep": ".",
        "units": "imperial",
        "honorifics": {
            "Mr.": {"replacement": "Mr.", "position": "prefix"},
            "Mrs.": {"replacement": "Mrs.", "position": "prefix"},
            "Ms.": {"replacement": "Ms.", "position": "prefix"},
            "Dr.": {"replacement": "Dr.", "position": "prefix"},
        },
    },
    "en-GB": {
        "code": "en-GB",
        "name": "English (UK)",
        "date_format": "DD/MM/YYYY",
        "currency": {"symbol": "£", "position": "prefix", "code": "GBP"},
        "thousands_sep": ",",
        "decimal_sep": ".",
        "units": "imperial",
        "honorifics": {
            "Mr.": {"replacement": "Mr", "position": "prefix"},
            "Mrs.": {"replacement": "Mrs", "position": "prefix"},
            "Ms.": {"replacement": "Ms", "position": "prefix"},
            "Dr.": {"replacement": "Dr", "position": "prefix"},
        },
    },
    "de-DE": {
        "code": "de-DE",
        "name": "German (Germany)",
        "date_format": "DD.MM.YYYY",
        "currency": {"symbol": "€", "position": "suffix", "code": "EUR"},
        "thousands_sep": ".",
        "decimal_sep": ",",
        "units": "metric",
        "honorifics": {
            "Mr.": {"replacement": "Herr", "position": "prefix"},
            "Mrs.": {"replacement": "Frau", "position": "prefix"},
            "Ms.": {"replacement": "Frau", "position": "prefix"},
            "Dr.": {"replacement": "Dr.", "position": "prefix"},
        },
    },
    "fr-FR": {
        "code": "fr-FR",
        "name": "French (France)",
        "date_format": "DD/MM/YYYY",
        "currency": {"symbol": "€", "position": "suffix", "code": "EUR"},
        "thousands_sep": " ",
        "decimal_sep": ",",
        "units": "metric",
        "honorifics": {
            "Mr.": {"replacement": "M.", "position": "prefix"},
            "Mrs.": {"replacement": "Mme", "position": "prefix"},
            "Ms.": {"replacement": "Mme", "position": "prefix"},
            "Dr.": {"replacement": "Dr", "position": "prefix"},
        },
    },
    "es-ES": {
        "code": "es-ES",
        "name": "Spanish (Spain)",
        "date_format": "DD/MM/YYYY",
        "currency": {"symbol": "€", "position": "suffix", "code": "EUR"},
        "thousands_sep": ".",
        "decimal_sep": ",",
        "units": "metric",
        "honorifics": {
            "Mr.": {"replacement": "Sr.", "position": "prefix"},
            "Mrs.": {"replacement": "Sra.", "position": "prefix"},
            "Ms.": {"replacement": "Sra.", "position": "prefix"},
            "Dr.": {"replacement": "Dr.", "position": "prefix"},
        },
    },
    "it-IT": {
        "code": "it-IT",
        "name": "Italian (Italy)",
        "date_format": "DD/MM/YYYY",
        "currency": {"symbol": "€", "position": "suffix", "code": "EUR"},
        "thousands_sep": ".",
        "decimal_sep": ",",
        "units": "metric",
        "honorifics": {
            "Mr.": {"replacement": "Sig.", "position": "prefix"},
            "Mrs.": {"replacement": "Sig.ra", "position": "prefix"},
            "Ms.": {"replacement": "Sig.ra", "position": "prefix"},
            "Dr.": {"replacement": "Dott.", "position": "prefix"},
        },
    },
    "pt-BR": {
        "code": "pt-BR",
        "name": "Portuguese (Brazil)",
        "date_format": "DD/MM/YYYY",
        "currency": {"symbol": "R$", "position": "prefix", "code": "BRL"},
        "thousands_sep": ".",
        "decimal_sep": ",",
        "units": "metric",
        "honorifics": {
            "Mr.": {"replacement": "Sr.", "position": "prefix"},
            "Mrs.": {"replacement": "Sra.", "position": "prefix"},
            "Ms.": {"replacement": "Sra.", "position": "prefix"},
            "Dr.": {"replacement": "Dr.", "position": "prefix"},
        },
    },
    "ja-JP": {
        "code": "ja-JP",
        "name": "Japanese (Japan)",
        "date_format": "YYYY/MM/DD",
        "currency": {"symbol": "￥", "position": "prefix", "code": "JPY"},
        "thousands_sep": ",",
        "decimal_sep": ".",
        "units": "metric",
        "honorifics": {
            "Mr.": {"replacement": "様", "position": "suffix"},
            "Mrs.": {"replacement": "様", "position": "suffix"},
            "Ms.": {"replacement": "様", "position": "suffix"},
            "Dr.": {"replacement": "先生", "position": "suffix"},
        },
    },
    "zh-CN": {
        "code": "zh-CN",
        "name": "Chinese (Simplified)",
        "date_format": "YYYY-MM-DD",
        "currency": {"symbol": "¥", "position": "prefix", "code": "CNY"},
        "thousands_sep": ",",
        "decimal_sep": ".",
        "units": "metric",
        "honorifics": {
            "Mr.": {"replacement": "先生", "position": "suffix"},
            "Mrs.": {"replacement": "女士", "position": "suffix"},
            "Ms.": {"replacement": "女士", "position": "suffix"},
            "Dr.": {"replacement": "博士", "position": "suffix"},
        },
    },
}

# Language prefix -> canonical locale (e.g. "de" -> "de-DE").
_LANGUAGE_ALIASES: dict[str, str] = {
    "en": "en-US",
    "de": "de-DE",
    "fr": "fr-FR",
    "es": "es-ES",
    "it": "it-IT",
    "pt": "pt-BR",
    "ja": "ja-JP",
    "zh": "zh-CN",
}

# ── Format detection patterns (US-002) ──────────────────────────────────────
_DATE_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_CURRENCY_RE = re.compile(r"\$\s?([\d,]+(?:\.\d{1,2})?)")
_UNIT_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(miles|mile|mi|fahrenheit|°\s*f|pounds|pound|lbs|lb|inches|inch|feet|foot|ft)\b",
    re.IGNORECASE,
)
_HONORIFIC_RE = re.compile(r"\b(Mr\.|Mrs\.|Ms\.|Dr\.)\s+([A-Z][a-zA-Z]+)\b")

# Imperial -> metric conversion factors (source unit -> (factor, target label)).
_UNIT_FACTORS: dict[str, tuple[float, str]] = {
    "miles": (1.60934, "km"),
    "mile": (1.60934, "km"),
    "mi": (1.60934, "km"),
    "fahrenheit": (None, "°C"),  # special formula, see convert_units
    "°f": (None, "°C"),
    "pounds": (0.453592, "kg"),
    "pound": (0.453592, "kg"),
    "lbs": (0.453592, "kg"),
    "lb": (0.453592, "kg"),
    "inches": (2.54, "cm"),
    "inch": (2.54, "cm"),
    "feet": (0.3048, "m"),
    "foot": (0.3048, "m"),
    "ft": (0.3048, "m"),
}


def _extract_json(text: str) -> Any:
    """Extract the first JSON value from an LLM response (tolerates fences)."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return json.loads(cleaned)


class LocaleData:
    """Locale-specific formatting data (dates, currency, units, honorifics).

    US-002: locale data table consulted by the formatting converter. Locale
    codes may be given in full form (``de-DE``) or as a language prefix
    (``de``); unknown locales raise ``KeyError``.
    """

    def __init__(self) -> None:
        self._locales: dict[str, dict[str, Any]] = {
            code: dict(entry) for code, entry in _LOCALES.items()
        }
        self._aliases: dict[str, str] = dict(_LANGUAGE_ALIASES)

    def get_locale(self, locale: str) -> dict:
        """Return the data table entry for a locale code.

        Args:
            locale: Full locale code (``de-DE``) or language prefix (``de``).

        Returns:
            The locale data dict (date format, currency, units, honorifics).

        Raises:
            KeyError: If the locale is not in the data table.
        """
        resolved = self._resolve(locale)
        if resolved is None:
            raise KeyError(locale)
        return self._locales[resolved]

    def _resolve(self, locale: str) -> str | None:
        """Resolve a locale code to a canonical table key."""
        if locale in self._locales:
            return locale
        lang = locale.split("-")[0].lower()
        alias = self._aliases.get(lang)
        if alias in self._locales:
            return alias
        for code in self._locales:
            if code.split("-")[0].lower() == lang:
                return code
        return None

    def supported_locales(self) -> list[str]:
        """Return the sorted list of supported locale codes."""
        return sorted(self._locales)


class LocaleFormatter:
    """Converts dates, currency, units and honorifics per target locale.

    Each converter returns the input unchanged when no conversion applies
    (unknown locale, no match, target uses the same convention).
    """

    def __init__(self, data: LocaleData | None = None) -> None:
        self._data = data or LocaleData()

    def convert_date(self, value: str, locale: str) -> str:
        """Convert a US-style ``MM/DD/YYYY`` date to the target locale format.

        Args:
            value: Date token, e.g. ``07/04/2026``.
            locale: Target locale code.

        Returns:
            The converted date string, or ``value`` unchanged when the input
            is not a parseable date or the locale is unknown.
        """
        return self._convert_date(value, locale, "auto")

    def _convert_date(self, value: str, locale: str, source_locale: str = "auto") -> str:
        """Convert a date with an explicit source convention.

        ``source_locale`` selects how the input is read: US-style month-first
        (default/``en-US``) or day-first (e.g. ``en-GB``).
        """
        match = _DATE_RE.match(value)
        if not match:
            return value
        try:
            data = self._data.get_locale(locale)
        except KeyError:
            return value
        first, second, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if source_locale not in ("", "auto") and source_locale.lower() not in ("en", "en-us"):
            day, month = first, second
        else:
            month, day = first, second
        if not (1 <= month <= 12 and 1 <= day <= 31):
            return value
        fmt = data["date_format"]
        if fmt == "DD.MM.YYYY":
            return f"{day:02d}.{month:02d}.{year}"
        if fmt == "DD/MM/YYYY":
            return f"{day:02d}/{month:02d}/{year}"
        if fmt == "YYYY/MM/DD":
            return f"{year}/{month:02d}/{day:02d}"
        if fmt == "YYYY-MM-DD":
            return f"{year}-{month:02d}-{day:02d}"
        return value

    def convert_currency(self, value: str, locale: str) -> str:
        """Convert a ``$`` amount to the target locale's symbol and number format.

        Args:
            value: Currency token, e.g. ``$1,000``.
            locale: Target locale code.

        Returns:
            The reformatted amount (e.g. ``1.000 €`` for de-DE), or ``value``
            unchanged when the input has no ``$`` or the locale is unknown.
        """
        match = _CURRENCY_RE.match(value)
        if not match:
            return value
        try:
            data = self._data.get_locale(locale)
        except KeyError:
            return value
        try:
            amount = float(match.group(1).replace(",", ""))
        except ValueError:
            return value
        formatted = self._format_number(amount, data)
        symbol = data["currency"]["symbol"]
        if data["currency"]["position"] == "suffix":
            return f"{formatted} {symbol}"
        return f"{symbol}{formatted}"

    def _format_number(self, amount: float, data: dict[str, Any]) -> str:
        """Format a number with the locale's thousands/decimal separators."""
        grouped = f"{amount:,.2f}".rstrip("0").rstrip(".") if amount % 1 else f"{amount:,.0f}"
        int_part, _, dec_part = grouped.partition(".")
        int_part = int_part.replace(",", data["thousands_sep"])
        if dec_part:
            return f"{int_part}{data['decimal_sep']}{dec_part}"
        return int_part

    def convert_units(self, value: str, locale: str) -> str:
        """Convert imperial units to metric for metric-system target locales.

        Args:
            value: Value + unit token, e.g. ``10 miles``.
            locale: Target locale code.

        Returns:
            The converted value (e.g. ``16 km``), or ``value`` unchanged when
            the target uses imperial units or the unit is unknown.
        """
        match = _UNIT_RE.match(value)
        if not match:
            return value
        try:
            data = self._data.get_locale(locale)
        except KeyError:
            return value
        if data["units"] != "metric":
            return value
        unit = match.group(2).lower()
        factor, label = _UNIT_FACTORS.get(unit, (None, ""))
        if factor is None:
            try:
                fahrenheit = float(match.group(1))
            except ValueError:
                return value
            converted = round((fahrenheit - 32) * 5 / 9)
            return f"{converted} {label}"
        try:
            amount = float(match.group(1))
        except ValueError:
            return value
        converted = round(amount * factor)
        return f"{converted} {label}"

    def convert_honorifics(self, value: str, locale: str) -> str:
        """Convert an English title (``Mr.``, ``Mrs.``, ``Ms.``, ``Dr.``) per locale.

        Args:
            value: Title + name token, e.g. ``Mr. Smith``.
            locale: Target locale code.

        Returns:
            The localized title form (e.g. ``Herr Smith`` for de-DE,
            ``Smith 様`` for ja-JP), or ``value`` unchanged when no mapping
            exists for the locale.
        """
        match = _HONORIFIC_RE.match(value)
        if not match:
            return value
        title, name = match.group(1), match.group(2)
        try:
            data = self._data.get_locale(locale)
        except KeyError:
            return value
        mapping = data["honorifics"].get(title)
        if not mapping:
            return value
        if mapping["position"] == "suffix":
            return f"{name} {mapping['replacement']}"
        return f"{mapping['replacement']} {name}"


class TranscreationService:
    """Orchestrates cultural-risk analysis, adaptation, and preflight."""

    def __init__(self, store: Any | None = None) -> None:
        """Initialize the service.

        Args:
            store: Optional ``TranscreationStore`` (product_ops pattern) used
                to persist/read per-asset results. When omitted the service
                keeps an in-memory per-asset map (unit-test friendly).
        """
        self._locale_data = LocaleData()
        self._formatter = LocaleFormatter(self._locale_data)
        self._store = store
        # In-memory per-asset state for preflight -> export flow (US-003/005).
        # The API layer persists the same data via the product_ops pattern.
        self._results: dict[str, TranscreationResult] = {}

    # ── Public API ──────────────────────────────────────────────────────────

    async def analyze(
        self,
        text: str,
        target_locale: str,
        source_locale: str = "auto",
    ) -> AnalyzeResponse:
        """Detect cultural risk items (idioms, references, register, taboo).

        Args:
            text: Content to analyze.
            target_locale: Target locale code (e.g. ``de-DE``).
            source_locale: Source locale or ``auto``.

        Returns:
            AnalyzeResponse with risk items, format items, and overall risk.

        Raises:
            ValueError: If the text is empty or the target locale is unsupported.
        """
        self._validate_input(text, target_locale)
        locale = self._locale_code(target_locale)
        risk_items = await self._detect_risks(text, locale, source_locale)
        format_items = self._detect_formats(text, locale, source_locale)
        return AnalyzeResponse(
            risk_items=risk_items,
            format_items=format_items,
            overall_risk=self._overall_risk(risk_items),
            locale=locale,
        )

    async def adapt(
        self,
        text: str,
        target_locale: str,
        source_locale: str = "auto",
        accepted_ids: list[str] | None = None,
        rejected_ids: list[str] | None = None,
        edits: dict[str, str] | None = None,
    ) -> AdaptResponse:
        """Produce adapted text with per-segment changes and change log.

        Reviewer decisions (US-004):
          - ``accepted_ids``: use the cultural adaptation and record accept.
          - ``rejected_ids``: fall back to the literal translation.
          - ``edits``: use the human-supplied text and clear any low-confidence
            flag (US-003 AC3).
        Format conversions (US-002) are applied unless their ``fmt-*`` id is
        in ``rejected_ids``.

        Args:
            text: Content to adapt.
            target_locale: Target locale code.
            source_locale: Source locale or ``auto``.
            accepted_ids: Segment ids whose adaptation is accepted.
            rejected_ids: Segment (or ``fmt-*``) ids whose change is rejected.
            edits: Segment id -> replacement text.

        Returns:
            AdaptResponse with the fully adapted text, segments, change log,
            and flagged low-confidence segment ids.

        Raises:
            ValueError: If the text is empty or the target locale is unsupported.
        """
        self._validate_input(text, target_locale)
        locale = self._locale_code(target_locale)
        accepted = set(accepted_ids or [])
        rejected = set(rejected_ids or [])
        edits = edits or {}

        sentences = self._sentences(text)
        risk_items = await self._detect_risks(text, locale, source_locale)
        risks_by_sentence: dict[str, list[RiskItem]] = {}
        for item in risk_items:
            risks_by_sentence.setdefault(item.segment, []).append(item)

        segments: list[AdaptedSegment] = []
        chosen_texts: list[str] = []
        for idx, sentence in enumerate(sentences, start=1):
            sid = f"seg-{idx}"
            risks = risks_by_sentence.get(sentence, [])
            literal = self._literal(sentence, locale)
            adapted = self._adapt_sentence(sentence, locale, risks)
            decision: SegmentDecision | None = None
            if sid in edits:
                decision = SegmentDecision.edit
                final_text = edits[sid]
            elif sid in accepted:
                decision = SegmentDecision.accept
                final_text = adapted
            elif sid in rejected:
                decision = SegmentDecision.reject
                final_text = literal
            else:
                final_text = adapted
            segments.append(
                AdaptedSegment(
                    id=sid,
                    original=sentence,
                    literal=literal,
                    adapted=adapted,
                    risk_item=risks[0] if risks else None,
                    decision=decision,
                )
            )
            chosen_texts.append(final_text)

        joined = " ".join(chosen_texts).strip()
        adapted_text = self._apply_format_conversions(joined, locale, source_locale, rejected)

        flagged = [
            seg.id
            for seg in segments
            if seg.risk_item is not None
            and seg.risk_item.confidence < CONFIDENCE_THRESHOLD
            and seg.decision is None
        ]
        changes_log = self._build_changes_log(segments, edits)
        return AdaptResponse(
            adapted_text=adapted_text,
            segments=segments,
            changes_log=changes_log,
            flagged_segments=flagged,
        )

    async def preflight(
        self,
        asset_id: str,
        content: str,
        target_locale: str,
    ) -> PreflightResult:
        """Flag high-risk items and block publishing until resolved/overridden.

        US-005: content with at least one ``high`` risk item is blocked. The
        analysis is recorded per asset so ``export`` can enforce the
        unresolved-flags rule (US-003 AC2).

        Args:
            asset_id: Asset identifier.
            content: Content to preflight-check.
            target_locale: Target locale code.

        Returns:
            PreflightResult with risk/format items, blocked flag, blocked
            reasons, audit status, and override availability.
        """
        analysis = await self.analyze(content, target_locale)
        high_risk = [item for item in analysis.risk_items if item.risk_level == RiskLevel.high]
        blocked = bool(high_risk)
        reasons = [f"{item.category.value}: {item.issue_description}" for item in high_risk]
        if blocked:
            audit_status: str = "fail"
        elif analysis.risk_items:
            audit_status = "review_needed"
        else:
            audit_status = "pass"
        result = PreflightResult(
            asset_id=asset_id,
            risk_items=analysis.risk_items,
            format_items=analysis.format_items,
            blocked=blocked,
            blocked_reasons=reasons,
            audit_status=audit_status,  # type: ignore[arg-type]
            override_available=True,
        )
        snapshot = TranscreationResult(
            id=f"tr-{uuid.uuid4().hex[:12]}",
            asset_id=asset_id,
            analysis=analysis,
            preflight=result,
        )
        self._results[asset_id] = snapshot
        if self._store is not None:
            self._store.save_result(snapshot)
        return result

    async def export(
        self,
        asset_id: str,
        accepted_ids: list[str] | None = None,
        rejected_ids: list[str] | None = None,
    ) -> str:
        """Export accepted adaptations (blocked if unresolved flags exist).

        US-003 AC2: export raises when the asset has unresolved low-confidence
        segments.  Decisions passed via *accepted_ids* / *rejected_ids* resolve
        the corresponding flags so export can proceed.

        Args:
            asset_id: Asset identifier.
            accepted_ids: Segment ids whose adaptation is accepted.
            rejected_ids: Segment ids whose adaptation is rejected.

        Returns:
            JSON string of accepted adaptations.

        Raises:
            TranscreationBlockedError: If the asset is unknown or has
                unresolved low-confidence flags.
        """
        result = self._results.get(asset_id)
        if result is None and self._store is not None:
            try:
                result = self._store.result(asset_id)
                self._results[asset_id] = result
            except KeyError:
                result = None
        if result is None or result.analysis is None:
            raise TranscreationBlockedError(
                "transcreation_export_unavailable: no analysis for asset"
            )
        # Determine which flagged segment IDs have been decided by the reviewer.
        decided_ids = set(accepted_ids or []) | set(rejected_ids or [])
        unresolved = [
            item
            for item in result.analysis.risk_items
            if item.confidence < CONFIDENCE_THRESHOLD and item.id not in decided_ids
        ]
        if unresolved:
            raise TranscreationBlockedError(
                "transcreation_export_blocked: unresolved low-confidence segments"
            )
        accepted = [
            {
                "segment": item.segment,
                "category": item.category.value,
                "replacement": item.suggested_replacement,
            }
            for item in result.analysis.risk_items
        ]
        return json.dumps(
            {"asset_id": asset_id, "accepted_adaptations": accepted}, ensure_ascii=False
        )

    # ── Risk detection ──────────────────────────────────────────────────────

    async def _detect_risks(self, text: str, locale: str, source_locale: str) -> list[RiskItem]:
        """Run LLM analysis when configured; fall back to the rule engine."""
        llm_items = await self._analyze_via_llm(text, locale, source_locale)
        if llm_items is not None:
            return llm_items
        return self._analyze_via_rules(text, locale)

    async def _analyze_via_llm(
        self, text: str, locale: str, source_locale: str
    ) -> list[RiskItem] | None:
        """Ask the LLM provider for cultural-risk items; None on any failure.

        The provider is only contacted when an API key is configured; any
        exception (missing key, network error, malformed JSON) is logged and
        returns None so the caller falls back to the cached rule engine.
        """
        try:
            from src.config import get_settings

            settings = get_settings()
            if not settings.LLM_API_KEY:
                return None
            from src.services.llm_provider import get_provider

            provider = get_provider(settings.LLM_PROVIDER)
            system_prompt = (
                "You are a transcreation QA specialist. Analyze the text for cultural "
                f"risks (idioms, cultural references, register mismatches, taboo terms) "
                f"when localizing into {locale}. Return ONLY a JSON array of objects with "
                "keys: segment, category (idiom|cultural_reference|register|taboo), "
                "original_text, issue_description, confidence (0-1), risk_level "
                "(low|medium|high), suggested_replacement."
            )
            response = await provider.generate(
                prompt=f"Source locale: {source_locale}\n\n{text}",
                system_prompt=system_prompt,
                model=settings.LLM_MODEL,
            )
            payload = _extract_json(response.text)
            if not isinstance(payload, list):
                return None
            items: list[RiskItem] = []
            for i, raw in enumerate(payload[:20], start=1):
                if not isinstance(raw, dict):
                    continue
                try:
                    items.append(
                        RiskItem(
                            id=f"risk-{i}",
                            segment=str(raw.get("segment") or text),
                            category=RiskCategory(str(raw["category"])),
                            original_text=str(raw.get("original_text") or ""),
                            issue_description=str(raw.get("issue_description") or "Cultural risk"),
                            confidence=float(raw["confidence"]),
                            risk_level=RiskLevel(str(raw["risk_level"])),
                            suggested_replacement=raw.get("suggested_replacement"),
                            locale=locale,
                        )
                    )
                except (KeyError, ValueError):
                    continue
            return items
        except Exception as exc:  # noqa: BLE001 — fallback path must never raise
            logger.warning(
                "transcreation LLM analysis unavailable (%s: %s) — using cached rule-based fallback",
                type(exc).__name__,
                exc,
            )
            return None

    def _analyze_via_rules(self, text: str, locale: str) -> list[RiskItem]:
        """Rule-based risk detection over the cached pattern table."""
        items: list[RiskItem] = []
        spans = self._build_span_map(text)  # O(n) once
        for pattern in _RISK_PATTERNS:
            for match in pattern["pattern"].finditer(text):
                items.append(
                    RiskItem(
                        id=f"risk-{len(items) + 1}",
                        segment=self._span_for_position(spans, match.start()) or text,
                        category=pattern["category"],
                        original_text=match.group(0),
                        issue_description=pattern["description"],
                        confidence=pattern["confidence"],
                        risk_level=pattern["risk_level"],
                        suggested_replacement=self._localize_suggestion(
                            pattern["suggestion"], locale
                        ),
                        locale=locale,
                    )
                )
        return items

    def _localize_suggestion(self, suggestions: dict[str, str], locale: str) -> str:
        """Pick the locale-appropriate suggestion (falls back to English)."""
        lang = locale.split("-")[0].lower()
        return suggestions.get(lang) or suggestions.get("en") or ""

    @staticmethod
    def _overall_risk(risk_items: list[RiskItem]) -> RiskLevel:
        """Highest risk level among items; ``low`` when no items exist."""
        if not risk_items:
            return RiskLevel.low
        order = {RiskLevel.low: 0, RiskLevel.medium: 1, RiskLevel.high: 2}
        return max((item.risk_level for item in risk_items), key=lambda level: order[level])

    # ── Format detection / conversion ───────────────────────────────────────

    def _detect_formats(self, text: str, locale: str, source_locale: str) -> list[LocaleFormatItem]:
        """Detect and convert locale-specific values in the text (US-002)."""
        items: list[LocaleFormatItem] = []
        counts: dict[str, int] = {"date": 0, "currency": 0, "unit": 0, "honorific": 0}
        formatter = self._formatter

        for match in _DATE_RE.finditer(text):
            original = match.group(0)
            converted = formatter._convert_date(original, locale, source_locale)
            if converted == original:
                continue
            counts["date"] += 1
            items.append(
                LocaleFormatItem(
                    id=f"fmt-date-{counts['date']}",
                    original=original,
                    converted=converted,
                    format_type=FormatType.date,
                    ambiguous=self._date_is_ambiguous(original, source_locale),
                    locale=locale,
                )
            )
        for match in _CURRENCY_RE.finditer(text):
            original = match.group(0)
            converted = formatter.convert_currency(original, locale)
            if converted == original:
                continue
            counts["currency"] += 1
            items.append(
                LocaleFormatItem(
                    id=f"fmt-currency-{counts['currency']}",
                    original=original,
                    converted=converted,
                    format_type=FormatType.currency,
                    locale=locale,
                )
            )
        for match in _UNIT_RE.finditer(text):
            original = match.group(0)
            converted = formatter.convert_units(original, locale)
            if converted == original:
                continue
            counts["unit"] += 1
            items.append(
                LocaleFormatItem(
                    id=f"fmt-unit-{counts['unit']}",
                    original=original,
                    converted=converted,
                    format_type=FormatType.unit,
                    locale=locale,
                )
            )
        for match in _HONORIFIC_RE.finditer(text):
            original = match.group(0)
            converted = formatter.convert_honorifics(original, locale)
            if converted == original:
                continue
            counts["honorific"] += 1
            items.append(
                LocaleFormatItem(
                    id=f"fmt-honorific-{counts['honorific']}",
                    original=original,
                    converted=converted,
                    format_type=FormatType.honorific,
                    locale=locale,
                )
            )
        return items

    def _apply_format_conversions(
        self, text: str, locale: str, source_locale: str, rejected: set[str]
    ) -> str:
        """Apply format conversions to a text, skipping rejected ``fmt-*`` ids."""
        counts: dict[str, int] = {"date": 0, "currency": 0, "unit": 0, "honorific": 0}
        formatter = self._formatter

        def make_replacer(ftype: str):
            def replacer(match: re.Match[str]) -> str:
                original = match.group(0)
                counts[ftype] += 1
                fid = f"fmt-{ftype}-{counts[ftype]}"
                if fid in rejected:
                    return original
                if ftype == "date":
                    return formatter._convert_date(original, locale, source_locale)
                if ftype == "currency":
                    return formatter.convert_currency(original, locale)
                if ftype == "unit":
                    return formatter.convert_units(original, locale)
                return formatter.convert_honorifics(original, locale)

            return replacer

        out = _DATE_RE.sub(make_replacer("date"), text)
        out = _CURRENCY_RE.sub(make_replacer("currency"), out)
        out = _UNIT_RE.sub(make_replacer("unit"), out)
        out = _HONORIFIC_RE.sub(make_replacer("honorific"), out)
        return out

    @staticmethod
    def _date_is_ambiguous(original: str, source_locale: str) -> bool:
        """A slash-formatted date is ambiguous when the source convention is unknown.

        US-002 AC2: ``07/04/2026`` could be July 4 (US) or 7 April (GB);
        without a known source convention the conversion is flagged for review.
        """
        if "/" not in original:
            return False
        return source_locale in ("", "auto") or source_locale.lower() in ("en", "en-us")

    # ── Segmentation / adaptation helpers ───────────────────────────────────

    @staticmethod
    def _sentences(text: str) -> list[str]:
        """Split text into sentences on ``. ! ?`` followed by whitespace."""
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        return [part for part in parts if part]

    @staticmethod
    def _build_span_map(text: str) -> list[tuple[int, int, str]]:
        """Build a list of (start, end, sentence) spans in a single O(n) pass.

        Used by ``_analyze_via_rules`` to resolve match positions to sentences
        without the O(n²) ``text.find(sentence)`` call per match.
        """
        spans: list[tuple[int, int, str]] = []
        idx = 0
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
            if not sentence:
                continue
            start = text.find(sentence, idx)
            if start == -1:
                start = text.find(sentence)
            end = start + len(sentence)
            spans.append((start, end, sentence))
            idx = end
        return spans

    @staticmethod
    def _span_for_position(spans: list[tuple[int, int, str]], position: int) -> str:
        """Return the sentence whose span contains *position*. O(n) scan over
        pre-sorted spans; total cost is O(n) across all calls in one rule pass.
        """
        for start, end, sentence in spans:
            if start <= position < end:
                return sentence
        return ""

    def _literal(self, sentence: str, locale: str) -> str:
        """Literal (word-for-word) translation of a sentence."""
        lang = locale.split("-")[0].lower()
        key = self._phrase_key(sentence)
        entry = _LITERAL_TABLE.get((lang, key)) or _LITERAL_TABLE.get(("en", key))
        return entry["literal"] if entry else sentence

    def _adapt_sentence(self, sentence: str, locale: str, risks: list[RiskItem]) -> str:
        """Culturally adapted form of a sentence (US-004 side-by-side view)."""
        lang = locale.split("-")[0].lower()
        key = self._phrase_key(sentence)
        entry = _LITERAL_TABLE.get((lang, key)) or _LITERAL_TABLE.get(("en", key))
        if entry and entry["adapted"]:
            return entry["adapted"]
        if risks:
            top = max(risks, key=lambda item: item.confidence)
            if top.category == RiskCategory.taboo and top.suggested_replacement:
                return re.sub(
                    re.escape(top.original_text),
                    top.suggested_replacement,
                    sentence,
                    flags=re.IGNORECASE,
                )
        return sentence

    @staticmethod
    def _phrase_key(sentence: str) -> str:
        """Normalize a sentence for the phrase-table lookup."""
        return sentence.strip().rstrip(".!?").strip()

    def _build_changes_log(
        self, segments: list[AdaptedSegment], edits: dict[str, str]
    ) -> list[dict]:
        """Build the review change log (US-004)."""
        log: list[dict] = []
        for seg in segments:
            if seg.decision is None:
                continue
            entry: dict[str, str] = {
                "segment_id": seg.id,
                "decision": seg.decision.value,
                "original": seg.original,
                "result": seg.literal if seg.decision == SegmentDecision.reject else seg.adapted,
            }
            if seg.decision == SegmentDecision.edit and seg.id in edits:
                entry["edited_text"] = edits[seg.id]
            log.append(entry)
        return log

    # ── Validation ──────────────────────────────────────────────────────────

    def _locale_code(self, locale: str) -> str:
        """Return the canonical locale code; raise ValueError if unsupported."""
        try:
            data = self._locale_data.get_locale(locale)
        except KeyError:
            raise ValueError(f"unsupported_locale: {locale}") from None
        return data["code"]

    @staticmethod
    def _validate_input(text: str, target_locale: str) -> None:
        """Reject empty text / locale up front (maps to HTTP 400 at the API)."""
        if not text or not text.strip():
            raise ValueError("empty_text")
        if not target_locale or not target_locale.strip():
            raise ValueError("empty_locale")

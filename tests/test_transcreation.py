"""Interface and behavioral pre-dev tests for the transcreation module.

Covers acceptance criteria US-001..US-005:
  US-001  Cultural risk detection (idioms, references, register, taboo)
  US-002  Locale formatting conversion (dates, currency, units, honorifics)
  US-003  Low-confidence flagging
  US-004  Side-by-side review (per-segment accept/edit/reject)
  US-005  Pre-flight publish check

Test policy (pre-dev contract):
  * INTERFACE tests — importability, class/field/signature existence.
    They PASS immediately once the module + schemas exist.
  * BEHAVIORAL tests — expected runtime behavior of the implemented
    TranscreationService. They FAIL during RED phase (stubs raise
    NotImplementedError) and must PASS after the developer implements.
  * NO inverse stub-guards: no test asserts NotImplementedError as the
    expected behavior (that pattern inverts the contract and forces the
    developer to delete tests when implementing).
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = pytest.mark.quick

# ── Schemas ─────────────────────────────────────────────────────────────────
# ── Router ──────────────────────────────────────────────────────────────────
from src.routers.transcreation import router as transcreation_router
from src.schemas.transcreation import (
    AdaptedSegment,
    AdaptRequest,
    AdaptResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    ConfidenceFlag,
    FlaggedSegment,
    FormatType,
    LocaleFormatItem,
    PreflightRequest,
    PreflightResult,
    RiskCategory,
    RiskItem,
    RiskLevel,
    SegmentDecision,
    TranscreationResult,
)

# ── Stub module (dev will replace with a real implementation) ───────────────
from src.services.transcreation import (
    CONFIDENCE_THRESHOLD,
    LocaleData,
    LocaleFormatter,
    TranscreationService,
)

# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestRiskItemInterface:
    """US-001 — RiskItem schema contract."""

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(RiskItem, BaseModel)

    def test_field_category(self):
        assert "category" in inspect.signature(RiskItem).parameters

    def test_field_original_text(self):
        assert "original_text" in inspect.signature(RiskItem).parameters

    def test_field_issue_description(self):
        assert "issue_description" in inspect.signature(RiskItem).parameters

    def test_field_confidence(self):
        assert "confidence" in inspect.signature(RiskItem).parameters

    def test_field_suggested_replacement(self):
        assert "suggested_replacement" in inspect.signature(RiskItem).parameters

    def test_risk_level_field(self):
        assert "risk_level" in inspect.signature(RiskItem).parameters

    def test_confidence_range_validated(self):
        with pytest.raises(Exception):
            RiskItem(
                id="r1",
                segment="x",
                category=RiskCategory.idiom,
                original_text="x",
                issue_description="y",
                confidence=1.5,
                risk_level=RiskLevel.high,
                locale="de-DE",
            )

    def test_confidence_negative_rejected(self):
        with pytest.raises(Exception):
            RiskItem(
                id="r1",
                segment="x",
                category=RiskCategory.idiom,
                original_text="x",
                issue_description="y",
                confidence=-0.1,
                risk_level=RiskLevel.high,
                locale="de-DE",
            )

    def test_confidence_bounds_ok(self):
        item = RiskItem(
            id="r1",
            segment="x",
            category=RiskCategory.idiom,
            original_text="x",
            issue_description="y",
            confidence=0.5,
            risk_level=RiskLevel.high,
            locale="de-DE",
        )
        assert 0.0 <= item.confidence <= 1.0

    def test_suggested_replacement_optional(self):
        item = RiskItem(
            id="r1",
            segment="x",
            category=RiskCategory.taboo,
            original_text="x",
            issue_description="y",
            confidence=0.9,
            risk_level=RiskLevel.high,
            locale="de-DE",
        )
        assert item.suggested_replacement is None


class TestRiskCategoriesInterface:
    """US-001 — the four mandated risk categories exist."""

    def test_idiom_category(self):
        assert RiskCategory.idiom.value == "idiom"

    def test_reference_category(self):
        assert RiskCategory.cultural_reference.value == "cultural_reference"

    def test_register_category(self):
        assert RiskCategory.register.value == "register"

    def test_taboo_category(self):
        assert RiskCategory.taboo.value == "taboo"

    def test_all_categories_enumerated(self):
        values = {c.value for c in RiskCategory}
        assert {"idiom", "cultural_reference", "register", "taboo"} <= values


class TestAnalyzeRequestInterface:
    """US-001 — AnalyzeRequest schema contract."""

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(AnalyzeRequest, BaseModel)

    def test_text_field_exists(self):
        assert "text" in inspect.signature(AnalyzeRequest).parameters

    def test_target_locale_field_exists(self):
        assert "target_locale" in inspect.signature(AnalyzeRequest).parameters

    def test_target_locale_required(self):
        with pytest.raises(Exception):
            AnalyzeRequest(text="Hello")

    def test_empty_text_rejected(self):
        with pytest.raises(Exception):
            AnalyzeRequest(text="", target_locale="de-DE")

    def test_source_locale_default_auto(self):
        req = AnalyzeRequest(text="Hello", target_locale="de-DE")
        assert req.source_locale == "auto"


class TestAnalyzeResponseInterface:
    """US-001 — AnalyzeResponse schema contract."""

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(AnalyzeResponse, BaseModel)

    def test_risk_items_field(self):
        assert "risk_items" in inspect.signature(AnalyzeResponse).parameters

    def test_format_items_field(self):
        assert "format_items" in inspect.signature(AnalyzeResponse).parameters

    def test_risk_items_default_empty_list(self):
        resp = AnalyzeResponse(locale="de-DE")
        assert resp.risk_items == []

    def test_locale_required(self):
        with pytest.raises(Exception):
            AnalyzeResponse()


class TestLocaleFormatItemInterface:
    """US-002 — LocaleFormatItem schema contract."""

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(LocaleFormatItem, BaseModel)

    def test_format_type_field(self):
        assert "format_type" in inspect.signature(LocaleFormatItem).parameters

    def test_ambiguous_field(self):
        assert "ambiguous" in inspect.signature(LocaleFormatItem).parameters

    def test_ambiguous_default_false(self):
        item = LocaleFormatItem(
            original="$1,000", converted="1.000 €", format_type=FormatType.currency, locale="de-DE"
        )
        assert item.ambiguous is False

    def test_format_types_enumerated(self):
        values = {f.value for f in FormatType}
        assert {"date", "currency", "unit", "honorific"} <= values


class TestAdaptRequestInterface:
    """US-001/US-004 — AdaptRequest schema contract."""

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(AdaptRequest, BaseModel)

    def test_text_field(self):
        assert "text" in inspect.signature(AdaptRequest).parameters

    def test_target_locale_field(self):
        assert "target_locale" in inspect.signature(AdaptRequest).parameters

    def test_accepted_ids_field(self):
        assert "accepted_ids" in inspect.signature(AdaptRequest).parameters

    def test_rejected_ids_field(self):
        assert "rejected_ids" in inspect.signature(AdaptRequest).parameters

    def test_edits_field(self):
        assert "edits" in inspect.signature(AdaptRequest).parameters

    def test_defaults(self):
        req = AdaptRequest(text="x", target_locale="de-DE")
        assert req.accepted_ids == []
        assert req.rejected_ids == []
        assert req.edits == {}


class TestAdaptResponseInterface:
    """US-004 — AdaptResponse schema contract."""

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(AdaptResponse, BaseModel)

    def test_adapted_text_field(self):
        assert "adapted_text" in inspect.signature(AdaptResponse).parameters

    def test_segments_field(self):
        assert "segments" in inspect.signature(AdaptResponse).parameters

    def test_changes_log_field(self):
        assert "changes_log" in inspect.signature(AdaptResponse).parameters

    def test_flagged_segments_field(self):
        assert "flagged_segments" in inspect.signature(AdaptResponse).parameters


class TestAdaptedSegmentInterface:
    """US-004 — side-by-side segment contract."""

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(AdaptedSegment, BaseModel)

    def test_original_literal_adapted_fields(self):
        sig = inspect.signature(AdaptedSegment).parameters
        assert {"original", "literal", "adapted"} <= set(sig)

    def test_decision_field(self):
        assert "decision" in inspect.signature(AdaptedSegment).parameters

    def test_decision_enum(self):
        values = {d.value for d in SegmentDecision}
        assert {"accept", "reject", "edit"} <= values


class TestConfidenceFlagInterface:
    """US-003 — low-confidence flagging contract."""

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(ConfidenceFlag, BaseModel)

    def test_flagged_field(self):
        assert "flagged" in inspect.signature(ConfidenceFlag).parameters

    def test_threshold_field(self):
        assert "threshold" in inspect.signature(ConfidenceFlag).parameters

    def test_threshold_default(self):
        flag = ConfidenceFlag()
        assert flag.threshold == 0.7

    def test_flagged_segment_has_rationale(self):
        assert "rationale" in inspect.signature(FlaggedSegment).parameters

    def test_flagged_segment_has_confidence(self):
        assert "confidence" in inspect.signature(FlaggedSegment).parameters


class TestPreflightInterface:
    """US-005 — preflight schema contract."""

    def test_request_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(PreflightRequest, BaseModel)

    def test_preflight_request_fields(self):
        sig = inspect.signature(PreflightRequest).parameters
        assert {"asset_id", "content", "target_locale"} <= set(sig)

    def test_result_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(PreflightResult, BaseModel)

    def test_preflight_result_fields(self):
        sig = inspect.signature(PreflightResult).parameters
        assert {"blocked", "blocked_reasons", "audit_status", "override_available"} <= set(sig)

    def test_blocked_default_false(self):
        result = PreflightResult(asset_id="a1")
        assert result.blocked is False

    def test_override_available_default_true(self):
        result = PreflightResult(asset_id="a1")
        assert result.override_available is True


class TestTranscreationResultInterface:
    """Persistence contract — analysis results stored per asset."""

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(TranscreationResult, BaseModel)

    def test_asset_id_field(self):
        assert "asset_id" in inspect.signature(TranscreationResult).parameters

    def test_analysis_field(self):
        assert "analysis" in inspect.signature(TranscreationResult).parameters

    def test_adaptation_field(self):
        assert "adaptation" in inspect.signature(TranscreationResult).parameters

    def test_preflight_field(self):
        assert "preflight" in inspect.signature(TranscreationResult).parameters

    def test_decisions_field(self):
        assert "decisions" in inspect.signature(TranscreationResult).parameters


class TestTranscreationServiceInterface:
    """US-001..US-005 — TranscreationService class + method contract."""

    def test_class_importable(self):
        assert TranscreationService is not None

    def test_is_class(self):
        assert inspect.isclass(TranscreationService)

    def test_analyze_method_exists(self):
        assert hasattr(TranscreationService, "analyze")
        assert callable(TranscreationService.analyze)

    def test_adapt_method_exists(self):
        assert hasattr(TranscreationService, "adapt")
        assert callable(TranscreationService.adapt)

    def test_preflight_method_exists(self):
        assert hasattr(TranscreationService, "preflight")
        assert callable(TranscreationService.preflight)

    def test_analyze_is_async(self):
        assert inspect.iscoroutinefunction(TranscreationService.analyze)

    def test_adapt_is_async(self):
        assert inspect.iscoroutinefunction(TranscreationService.adapt)

    def test_preflight_is_async(self):
        assert inspect.iscoroutinefunction(TranscreationService.preflight)

    def test_analyze_signature(self):
        sig = inspect.signature(TranscreationService.analyze)
        params = sig.parameters
        assert "text" in params
        assert "target_locale" in params
        assert params["source_locale"].default == "auto"

    def test_adapt_signature(self):
        sig = inspect.signature(TranscreationService.adapt)
        params = sig.parameters
        assert "text" in params
        assert "target_locale" in params
        assert "accepted_ids" in params
        assert "rejected_ids" in params
        assert "edits" in params

    def test_preflight_signature(self):
        sig = inspect.signature(TranscreationService.preflight)
        params = sig.parameters
        assert "asset_id" in params
        assert "content" in params
        assert "target_locale" in params

    def test_analyze_return_annotation(self):
        ann = TranscreationService.analyze.__annotations__.get("return")
        assert ann is not None
        assert "AnalyzeResponse" in str(ann)

    def test_adapt_return_annotation(self):
        ann = TranscreationService.adapt.__annotations__.get("return")
        assert ann is not None
        assert "AdaptResponse" in str(ann)

    def test_preflight_return_annotation(self):
        ann = TranscreationService.preflight.__annotations__.get("return")
        assert ann is not None
        assert "PreflightResult" in str(ann)

    def test_confidence_threshold_constant(self):
        assert isinstance(CONFIDENCE_THRESHOLD, float)
        assert 0.0 < CONFIDENCE_THRESHOLD < 1.0


class TestLocaleDataInterface:
    """US-002 — locale data table contract."""

    def test_class_importable(self):
        assert LocaleData is not None

    def test_get_locale_method(self):
        assert callable(LocaleData.get_locale)

    def test_supported_locales_method(self):
        assert callable(LocaleData.supported_locales)


class TestLocaleFormatterInterface:
    """US-002 — locale formatting converter contract."""

    def test_class_importable(self):
        assert LocaleFormatter is not None

    def test_convert_date_method(self):
        assert callable(LocaleFormatter.convert_date)

    def test_convert_currency_method(self):
        assert callable(LocaleFormatter.convert_currency)

    def test_convert_units_method(self):
        assert callable(LocaleFormatter.convert_units)

    def test_convert_honorifics_method(self):
        assert callable(LocaleFormatter.convert_honorifics)


class TestRouterInterface:
    """Router endpoints for the transcreation module."""

    def test_router_importable(self):
        assert transcreation_router is not None

    def test_router_prefix(self):
        assert transcreation_router.prefix == "/api/v1/transcreation"

    def test_analyze_endpoint_registered(self):
        routes = {(r.path, tuple(sorted(r.methods or []))) for r in transcreation_router.routes}
        assert ("/api/v1/transcreation/analyze", ("POST",)) in routes, (
            f"Expected POST /api/v1/transcreation/analyze. Found: {sorted(routes)}"
        )

    def test_adapt_endpoint_registered(self):
        routes = {(r.path, tuple(sorted(r.methods or []))) for r in transcreation_router.routes}
        assert ("/api/v1/transcreation/adapt", ("POST",)) in routes

    def test_preflight_endpoint_registered(self):
        routes = {(r.path, tuple(sorted(r.methods or []))) for r in transcreation_router.routes}
        assert ("/api/v1/transcreation/preflight", ("POST",)) in routes

    def test_analyze_handler_async(self):
        from src.routers.transcreation import analyze_transcreation

        assert inspect.iscoroutinefunction(analyze_transcreation)

    def test_adapt_handler_async(self):
        from src.routers.transcreation import adapt_transcreation

        assert inspect.iscoroutinefunction(adapt_transcreation)

    def test_preflight_handler_async(self):
        from src.routers.transcreation import preflight_transcreation

        assert inspect.iscoroutinefunction(preflight_transcreation)

    def test_analyze_handler_accepts_body(self):
        from src.routers.transcreation import analyze_transcreation

        assert "body" in inspect.signature(analyze_transcreation).parameters

    def test_analyze_handler_returns_analyze_response(self):
        from src.routers.transcreation import analyze_transcreation

        ann = analyze_transcreation.__annotations__
        assert "return" in ann
        assert "AnalyzeResponse" in str(ann["return"])

    def test_adapt_handler_returns_adapt_response(self):
        from src.routers.transcreation import adapt_transcreation

        ann = adapt_transcreation.__annotations__
        assert "return" in ann
        assert "AdaptResponse" in str(ann["return"])

    def test_preflight_handler_returns_preflight_result(self):
        from src.routers.transcreation import preflight_transcreation

        ann = preflight_transcreation.__annotations__
        assert "return" in ann
        assert "PreflightResult" in str(ann["return"])


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (RED phase: FAIL with NotImplementedError;
#              must PASS after implementation)
# ============================================================================

# ── Shared fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def service() -> TranscreationService:
    """Fresh service instance per test."""
    return TranscreationService()


# ── US-001 — Cultural risk detection ────────────────────────────────────────


class TestAnalyzeBehavior:
    """US-001 — analyze() detects cultural risks and returns structured results."""

    @pytest.mark.asyncio
    async def test_analyze_returns_analyze_response(self, service):
        result = await service.analyze("The whole nine yards.", "de-DE")
        assert isinstance(result, AnalyzeResponse)
        assert result.locale == "de-DE"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "text,category",
        [
            ("It's raining cats and dogs.", RiskCategory.idiom),
            ("He's a real Benedict Arnold.", RiskCategory.cultural_reference),
            ("Hey guys, what's up?", RiskCategory.register),
            ("That's a load of crap.", RiskCategory.taboo),
        ],
        ids=["idiom", "reference", "register", "taboo"],
    )
    async def test_analyze_detects_risk_categories(self, service, text, category):
        """Each category must be detectable and returned as a structured item."""
        result = await service.analyze(text, "de-DE")
        assert isinstance(result.risk_items, list)
        found = [item for item in result.risk_items if item.category == category]
        assert len(found) >= 1, (
            f"Expected at least one {category.value} risk item for {text!r}; got {result.risk_items}"
        )
        item = found[0]
        assert item.segment
        assert item.original_text
        assert item.issue_description
        assert 0.0 <= item.confidence <= 1.0
        assert item.risk_level in RiskLevel

    @pytest.mark.asyncio
    async def test_analyze_clean_text_no_risks(self, service):
        result = await service.analyze(
            "The quarterly report is now available for download.", "de-DE"
        )
        assert result.risk_items == []

    @pytest.mark.asyncio
    async def test_analyze_risk_item_has_suggestion(self, service):
        result = await service.analyze("It's raining cats and dogs.", "de-DE")
        assert result.risk_items
        assert result.risk_items[0].suggested_replacement

    @pytest.mark.asyncio
    async def test_analyze_overall_risk_level(self, service):
        result = await service.analyze("That's a load of crap.", "de-DE")
        assert result.overall_risk in RiskLevel

    @pytest.mark.asyncio
    async def test_analyze_sets_overall_risk_high_for_taboo(self, service):
        result = await service.analyze("That's a load of crap.", "de-DE")
        assert result.overall_risk in (RiskLevel.high, RiskLevel.medium)


# ── US-002 — Locale formatting conversion ───────────────────────────────────


class TestLocaleFormatBehavior:
    """US-002 — dates, currency, units, honorifics converted per target locale."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "text,locale,format_type",
        [
            ("Launching on 07/04/2026.", "de-DE", FormatType.date),
            ("The upgrade costs $1,000.", "de-DE", FormatType.currency),
            ("Drive 10 miles to the office.", "de-DE", FormatType.unit),
            ("Please ask Mr. Smith to join.", "ja-JP", FormatType.honorific),
        ],
        ids=["date", "currency", "unit", "honorific"],
    )
    async def test_analyze_detects_format_items(self, service, text, locale, format_type):
        result = await service.analyze(text, locale)
        assert isinstance(result.format_items, list)
        found = [item for item in result.format_items if item.format_type == format_type]
        assert len(found) >= 1, (
            f"Expected at least one {format_type.value} format item for {text!r} "
            f"-> {locale}; got {result.format_items}"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "text,locale,expected_fragment",
        [
            ("Launching on 07/04/2026.", "de-DE", "04.07.2026"),
            ("The upgrade costs $1,000.", "de-DE", "1.000"),
            ("Drive 10 miles to the office.", "de-DE", "16"),
        ],
        ids=["date-de", "currency-de", "units-de"],
    )
    async def test_analyze_converts_values(self, service, text, locale, expected_fragment):
        """Converted values appear in the format items."""
        result = await service.analyze(text, locale)
        assert result.format_items, f"Expected format items for {text!r} -> {locale}"
        assert any(
            expected_fragment in item.converted for item in result.format_items
        ), f"Expected {expected_fragment!r} in converted values: {result.format_items}"

    @pytest.mark.asyncio
    async def test_ambiguous_conversion_flagged(self, service):
        """US-002 AC2 — ambiguous conversions are flagged instead of auto-converted."""
        result = await service.analyze("Launching on 07/04/2026.", "en-GB")
        assert result.format_items
        ambiguous = [item for item in result.format_items if item.format_type == FormatType.date]
        assert ambiguous, "Expected a date conversion to be flagged as ambiguous"
        assert any(item.ambiguous for item in ambiguous)

    @pytest.mark.asyncio
    async def test_adapt_respects_disabled_conversion(self, service):
        """US-002 AC3 — a disabled conversion keeps the original form.

        The caller passes the rejected ids; the adapted text must retain the
        original value while other conversions are applied.
        """
        result = await service.adapt(
            "Launching on 07/04/2026. The upgrade costs $1,000.",
            "de-DE",
            rejected_ids=["fmt-date-1"],
        )
        assert isinstance(result, AdaptResponse)
        assert "07/04/2026" in result.adapted_text
        assert "1.000" in result.adapted_text


# ── US-003 — Low-confidence flagging ────────────────────────────────────────


class TestConfidenceFlagBehavior:
    """US-003 — low-confidence adaptations are flagged with score + rationale."""

    @pytest.mark.asyncio
    async def test_flagged_segments_with_confidence(self, service):
        result = await service.adapt("It's raining cats and dogs.", "de-DE")
        assert isinstance(result.flagged_segments, list)
        # Every flagged id must appear in the segments with a confidence score.
        for seg in result.segments:
            if seg.id in result.flagged_segments:
                assert seg.risk_item is not None
                assert seg.risk_item.confidence < CONFIDENCE_THRESHOLD

    @pytest.mark.asyncio
    async def test_low_confidence_has_rationale(self, service):
        """US-003 AC1 — flagged segment carries confidence score and rationale."""
        result = await service.adapt("He's a real Benedict Arnold.", "de-DE")
        assert result.flagged_segments, "Expected at least one low-confidence flag"
        flag_id = result.flagged_segments[0]
        seg = next(s for s in result.segments if s.id == flag_id)
        assert seg.risk_item is not None
        assert seg.risk_item.confidence < CONFIDENCE_THRESHOLD
        assert seg.risk_item.issue_description  # rationale present

    @pytest.mark.asyncio
    async def test_export_blocked_on_unresolved_flags(self, service):
        """US-003 AC2 — export is blocked while flagged segments are unresolved."""
        with pytest.raises(Exception):
            await service.export("asset-with-flags")


# ── US-004 — Side-by-side review ────────────────────────────────────────────


class TestReviewBehavior:
    """US-004 — per-segment accept/reject/edit semantics."""

    @pytest.mark.asyncio
    async def test_adapt_segments_show_three_versions(self, service):
        """US-004 AC1 — each segment shows original, literal, adapted in parallel."""
        result = await service.adapt(
            "It's raining cats and dogs. The report is ready.", "de-DE"
        )
        assert len(result.segments) >= 1
        for seg in result.segments:
            assert seg.original
            assert seg.literal
            assert seg.adapted

    @pytest.mark.asyncio
    async def test_rejected_segment_uses_literal(self, service):
        """US-004 AC2 — rejected segment falls back to the literal translation."""
        result = await service.adapt(
            "It's raining cats and dogs.",
            "de-DE",
            rejected_ids=["seg-1"],
        )
        assert result.segments
        rejected = next(s for s in result.segments if s.id == "seg-1")
        assert rejected.decision == SegmentDecision.reject
        assert rejected.literal in result.adapted_text

    @pytest.mark.asyncio
    async def test_accepted_segment_uses_adaptation(self, service):
        """US-004 AC3 — accepted adaptation is used and decision is recorded."""
        result = await service.adapt(
            "It's raining cats and dogs.",
            "de-DE",
            accepted_ids=["seg-1"],
        )
        accepted = next(s for s in result.segments if s.id == "seg-1")
        assert accepted.decision == SegmentDecision.accept
        assert accepted.adapted in result.adapted_text
        assert result.changes_log, "Accepted decisions must be recorded in the change log"
        assert any("seg-1" in str(entry) for entry in result.changes_log)

    @pytest.mark.asyncio
    async def test_edited_segment_uses_edit(self, service):
        """US-003 AC3 — edited flagged segment clears its flag and uses the edit."""
        result = await service.adapt(
            "He's a real Benedict Arnold.",
            "de-DE",
            edits={"seg-1": "He's a real traitor."},
        )
        edited = next(s for s in result.segments if s.id == "seg-1")
        assert edited.decision == SegmentDecision.edit
        assert "He's a real traitor." in result.adapted_text
        assert "seg-1" not in result.flagged_segments


# ── US-005 — Pre-flight publish check ───────────────────────────────────────


class TestPreflightBehavior:
    """US-005 — preflight flags high-risk items; blocks publish until resolved."""

    @pytest.mark.asyncio
    async def test_preflight_returns_result(self, service):
        result = await service.preflight(
            "asset-1", "That's a load of crap.", "de-DE"
        )
        assert isinstance(result, PreflightResult)
        assert result.asset_id == "asset-1"

    @pytest.mark.asyncio
    async def test_preflight_blocks_high_risk(self, service):
        """US-005 AC1 — high-risk items are flagged and blocked until adapted."""
        result = await service.preflight("asset-1", "That's a load of crap.", "de-DE")
        assert result.risk_items
        high = [item for item in result.risk_items if item.risk_level == RiskLevel.high]
        assert high, f"Expected at least one high-risk item: {result.risk_items}"
        assert result.blocked is True
        assert result.blocked_reasons

    @pytest.mark.asyncio
    async def test_preflight_passes_clean_content(self, service):
        """US-005 AC2 — passing content records the transcreation audit status."""
        result = await service.preflight(
            "asset-2", "The quarterly report is available for download.", "de-DE"
        )
        assert result.blocked is False
        assert result.audit_status == "pass"

    @pytest.mark.asyncio
    async def test_preflight_override_allows_publish(self, service):
        """US-005 — explicit override allows publishing despite high-risk items."""
        result = await service.preflight("asset-1", "That's a load of crap.", "de-DE")
        assert result.override_available is True

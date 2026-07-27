"""Interface and behavioral tests for the A/B testing framework.

Interface tests  — verify imports, class/function signatures (should PASS).
Behavioral tests — verify NotImplementedError from stubs.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ab_test import (
    AB_VALID_EVENT_TYPES,
    AB_VALID_STATUSES,
    AB_VALID_VARIANT_TYPES,
    ABEvent,
    ABTest,
    ABVariant,
)
from src.routers.ab_test import router as ab_router
from src.schemas.ab_test import (
    ABConcludeRequest,
    ABCreateRequest,
    ABDashboardResponse,
    ABResultsResponse,
    ABTestListResponse,
    ABTestResponse,
    ABTrackRequest,
    ABVariantResponse,
    ABVariantResult,
)
from src.services.ab_service import ABTestService
from src.services.ab_stats import AbStatsService, SignificanceResult

pytestmark = pytest.mark.asyncio


# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestABSchemasInterface:
    """Verify the A/B testing schema interfaces."""

    @pytest.mark.parametrize(
        "schema_cls",
        [
            ABCreateRequest,
            ABVariantResponse,
            ABTestResponse,
            ABTestListResponse,
            ABTrackRequest,
            ABResultsResponse,
            ABVariantResult,
            ABConcludeRequest,
            ABDashboardResponse,
        ],
    )
    def test_schema_importable(self, schema_cls):
        assert schema_cls is not None

    @pytest.mark.parametrize(
        "schema_cls",
        [
            ABCreateRequest,
            ABVariantResponse,
            ABTestResponse,
            ABTestListResponse,
            ABTrackRequest,
            ABResultsResponse,
            ABVariantResult,
            ABConcludeRequest,
            ABDashboardResponse,
        ],
    )
    def test_schema_is_pydantic(self, schema_cls):
        assert issubclass(schema_cls, BaseModel)

    # --- ABCreateRequest fields ---
    def test_ab_create_request_fields(self):
        sig = inspect.signature(ABCreateRequest)
        assert "name" in sig.parameters
        assert "content_type" in sig.parameters
        assert "topic" in sig.parameters
        assert "variant_count" in sig.parameters
        assert "variant_dimension" in sig.parameters

    # --- ABVariantResponse fields ---
    def test_ab_variant_response_fields(self):
        sig = inspect.signature(ABVariantResponse)
        assert "id" in sig.parameters
        assert "name" in sig.parameters
        assert "variant_type" in sig.parameters
        assert "impressions" in sig.parameters
        assert "conversions" in sig.parameters
        assert "conversion_rate" in sig.parameters
        assert "created_at" in sig.parameters

    # --- ABTestResponse fields ---
    def test_ab_test_response_fields(self):
        sig = inspect.signature(ABTestResponse)
        assert "id" in sig.parameters
        assert "name" in sig.parameters
        assert "content_type" in sig.parameters
        assert "status" in sig.parameters
        assert "variants" in sig.parameters
        assert "created_at" in sig.parameters

    # --- ABTestListResponse fields ---
    def test_ab_test_list_response_fields(self):
        sig = inspect.signature(ABTestListResponse)
        assert "items" in sig.parameters
        assert "total" in sig.parameters
        assert "limit" in sig.parameters
        assert "offset" in sig.parameters

    # --- ABTrackRequest fields ---
    def test_ab_track_request_fields(self):
        sig = inspect.signature(ABTrackRequest)
        assert "variant_id" in sig.parameters
        assert "event_type" in sig.parameters
        assert "user_identifier" in sig.parameters

    # --- ABResultsResponse fields ---
    def test_ab_results_response_fields(self):
        sig = inspect.signature(ABResultsResponse)
        assert "test" in sig.parameters
        assert "significance_level" in sig.parameters
        assert "confidence_level" in sig.parameters
        assert "winner_variant_id" in sig.parameters
        assert "insufficient_data" in sig.parameters
        assert "variants" in sig.parameters
        assert "method" in sig.parameters

    # --- ABVariantResult fields ---
    def test_ab_variant_result_fields(self):
        sig = inspect.signature(ABVariantResult)
        assert "id" in sig.parameters
        assert "name" in sig.parameters
        assert "impressions" in sig.parameters
        assert "conversions" in sig.parameters
        assert "conversion_rate" in sig.parameters
        assert "z_score" in sig.parameters
        assert "p_value" in sig.parameters
        assert "is_winner" in sig.parameters

    # --- ABConcludeRequest fields ---
    def test_ab_conclude_request_fields(self):
        sig = inspect.signature(ABConcludeRequest)
        assert "winner_variant_id" in sig.parameters
        assert "note" in sig.parameters

    # --- ABDashboardResponse fields ---
    def test_ab_dashboard_response_fields(self):
        sig = inspect.signature(ABDashboardResponse)
        assert "active_tests" in sig.parameters
        assert "concluded_tests" in sig.parameters
        assert "total_tests" in sig.parameters
        assert "active_count" in sig.parameters
        assert "concluded_count" in sig.parameters


class TestABModelsInterface:
    """Verify the A/B testing ORM model interfaces."""

    @pytest.mark.parametrize(
        "model_cls",
        [ABTest, ABVariant, ABEvent],
    )
    def test_model_importable(self, model_cls):
        assert model_cls is not None

    @pytest.mark.parametrize(
        "model_cls,expected_table",
        [
            (ABTest, "ab_tests"),
            (ABVariant, "ab_variants"),
            (ABEvent, "ab_events"),
        ],
    )
    def test_model_tablename(self, model_cls, expected_table):
        assert model_cls.__tablename__ == expected_table

    def test_ab_test_has_id_column(self):
        assert hasattr(ABTest, "id")
        assert hasattr(ABTest, "name")
        assert hasattr(ABTest, "status")
        assert hasattr(ABTest, "variants")

    def test_ab_variant_has_columns(self):
        assert hasattr(ABVariant, "id")
        assert hasattr(ABVariant, "ab_test_id")
        assert hasattr(ABVariant, "variant_type")
        assert hasattr(ABVariant, "impressions")
        assert hasattr(ABVariant, "conversions")

    def test_ab_event_has_columns(self):
        assert hasattr(ABEvent, "id")
        assert hasattr(ABEvent, "variant_id")
        assert hasattr(ABEvent, "ab_test_id")
        assert hasattr(ABEvent, "event_type")

    def test_ab_valid_statuses_defined(self):
        assert isinstance(AB_VALID_STATUSES, list)
        assert "draft" in AB_VALID_STATUSES
        assert "running" in AB_VALID_STATUSES
        assert "concluded" in AB_VALID_STATUSES
        assert "archived" in AB_VALID_STATUSES

    def test_ab_valid_event_types_defined(self):
        assert isinstance(AB_VALID_EVENT_TYPES, list)
        assert "impression" in AB_VALID_EVENT_TYPES
        assert "conversion" in AB_VALID_EVENT_TYPES

    def test_ab_valid_variant_types_defined(self):
        assert isinstance(AB_VALID_VARIANT_TYPES, list)
        assert "control" in AB_VALID_VARIANT_TYPES
        assert "treatment" in AB_VALID_VARIANT_TYPES


class TestABRouterInterface:
    """Verify the A/B testing router interface."""

    def test_router_importable(self):
        assert ab_router is not None
        assert ab_router.prefix == "/api/v1/ab"

    def test_router_has_create_endpoint(self):
        routes = [(r.path, r.methods) for r in ab_router.routes]
        assert any("/create" in path for path, _ in routes)

    def test_router_has_track_endpoint(self):
        routes = [(r.path, r.methods) for r in ab_router.routes]
        assert any("/track" in path for path, _ in routes)

    def test_router_has_results_endpoint(self):
        routes = [(r.path, r.methods) for r in ab_router.routes]
        assert any("/results" in path for path, _ in routes)

    def test_router_has_conclude_endpoint(self):
        routes = [(r.path, r.methods) for r in ab_router.routes]
        assert any("/conclude" in path for path, _ in routes)

    def test_router_has_list_endpoint(self):
        routes = [(r.path, r.methods) for r in ab_router.routes]
        assert any("/list" in path for path, _ in routes)

    def test_router_has_dashboard_endpoint(self):
        routes = [(r.path, r.methods) for r in ab_router.routes]
        assert any("/dashboard" in path for path, _ in routes)


class TestABStatsServiceInterface:
    """Verify the AbStatsService interface."""

    def test_ab_stats_service_importable(self):
        assert AbStatsService is not None

    def test_ab_stats_service_is_class(self):
        assert inspect.isclass(AbStatsService)

    def test_ab_stats_service_has_calculate_significance(self):
        assert hasattr(AbStatsService, "calculate_significance")
        assert callable(AbStatsService.calculate_significance)

    def test_ab_stats_service_calculate_significance_signature(self):
        sig = inspect.signature(AbStatsService.calculate_significance)
        assert "counts" in sig.parameters

    def test_ab_stats_service_has_needs_more_data(self):
        assert hasattr(AbStatsService, "needs_more_data")
        assert callable(AbStatsService.needs_more_data)

    def test_ab_stats_service_needs_more_data_signature(self):
        sig = inspect.signature(AbStatsService.needs_more_data)
        assert "counts" in sig.parameters
        assert "min_per_variant" in sig.parameters

    def test_ab_stats_service_has_format_confidence(self):
        assert hasattr(AbStatsService, "format_confidence")
        assert callable(AbStatsService.format_confidence)

    def test_ab_stats_service_format_confidence_signature(self):
        sig = inspect.signature(AbStatsService.format_confidence)
        assert "p_value" in sig.parameters

    def test_significance_result_importable(self):
        assert SignificanceResult is not None

    def test_significance_result_is_pydantic(self):
        assert issubclass(SignificanceResult, BaseModel)

    def test_significance_result_fields(self):
        sig = inspect.signature(SignificanceResult)
        assert "chi_square_statistic" in sig.parameters
        assert "p_value" in sig.parameters
        assert "dof" in sig.parameters
        assert "sufficient_data" in sig.parameters
        assert "method" in sig.parameters


class TestABServiceInterface:
    """Verify the ABTestService interface."""

    def test_ab_service_importable(self):
        assert ABTestService is not None

    def test_ab_service_is_class(self):
        assert inspect.isclass(ABTestService)

    @pytest.mark.parametrize(
        "method_name",
        [
            "create_test",
            "track_event",
            "get_results",
            "conclude_test",
            "get_dashboard",
            "list_tests",
        ],
    )
    def test_ab_service_has_method(self, method_name):
        assert hasattr(ABTestService, method_name)
        assert callable(getattr(ABTestService, method_name))

    @pytest.mark.parametrize(
        "method_name,expected_params",
        [
            ("create_test", ["self", "request", "db"]),
            ("track_event", ["self", "request", "db"]),
            ("get_results", ["self", "test_id", "db"]),
            ("conclude_test", ["self", "test_id", "request", "db"]),
            ("get_dashboard", ["self", "db"]),
            ("list_tests", ["self", "db"]),
        ],
    )
    def test_ab_service_method_signatures(self, method_name, expected_params):
        method = getattr(ABTestService, method_name)
        sig = inspect.signature(method)
        for param in expected_params:
            assert param in sig.parameters

    @pytest.mark.parametrize(
        "method_name",
        [
            "create_test",
            "track_event",
            "get_results",
            "conclude_test",
            "get_dashboard",
            "list_tests",
        ],
    )
    def test_ab_service_methods_are_async(self, method_name):
        method = getattr(ABTestService, method_name)
        assert inspect.iscoroutinefunction(method), (
            f"{method_name} should be async"
        )


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (verify real implementation)
# ============================================================================


class TestAbStatsServiceBehavioral:
    """Behavioral tests for AbStatsService — verify real statistical calculations."""

    def test_calculate_significance_returns_significance_result(self):
        """AbStatsService.calculate_significance should return a SignificanceResult."""
        result = AbStatsService.calculate_significance([(100, 10), (100, 15)])
        assert isinstance(result, SignificanceResult)
        assert result.chi_square_statistic > 0
        assert 0 <= result.p_value <= 1
        assert result.dof >= 1
        assert result.sufficient_data is True
        assert result.method == "chi-squared"

    def test_calculate_significance_different_rates_has_low_p(self):
        """Significantly different conversion rates should yield low p-value."""
        result = AbStatsService.calculate_significance([(1000, 100), (1000, 200)])
        assert result.p_value < 0.05
        assert result.z_score is not None

    def test_calculate_significance_similar_rates_has_high_p(self):
        """Similar conversion rates should yield high p-value."""
        result = AbStatsService.calculate_significance([(1000, 100), (1000, 105)])
        assert result.p_value > 0.05

    def test_needs_more_data_returns_bool(self):
        """needs_more_data should return True/False."""
        assert AbStatsService.needs_more_data([(100, 10), (100, 15)]) is False
        assert AbStatsService.needs_more_data([(10, 1), (10, 2)]) is True

    def test_needs_more_data_with_custom_threshold(self):
        """needs_more_data should respect custom min_per_variant."""
        assert AbStatsService.needs_more_data([(20, 1), (20, 2)], min_per_variant=30) is True
        assert AbStatsService.needs_more_data([(50, 1), (50, 2)], min_per_variant=30) is False

    def test_format_confidence_returns_string(self):
        """format_confidence should return a formatted string."""
        result = AbStatsService.format_confidence(0.05)
        assert isinstance(result, str)
        assert result == "95.0%"

    def test_format_confidence_highly_significant(self):
        """Very low p-values should show high confidence."""
        result = AbStatsService.format_confidence(0.001)
        assert result == "99.9%"

    def test_format_confidence_not_significant(self):
        """High p-values should indicate insufficient data."""
        result = AbStatsService.format_confidence(0.5)
        assert result == "Insufficient data"
        result = AbStatsService.format_confidence(0.2)
        assert result == "Insufficient data"

    def test_calculate_significance_with_single_variant(self):
        """Single variant should raise ValueError."""
        with pytest.raises(ValueError, match="At least 2 variants"):
            AbStatsService.calculate_significance([(100, 10)])

    def test_calculate_significance_with_zero_conversions(self):
        """Zero conversions should still produce valid results."""
        result = AbStatsService.calculate_significance([(100, 0), (100, 0)])
        assert result.p_value >= 0.0
        assert result.chi_square_statistic >= 0.0

    def test_calculate_significance_with_zero_impressions(self):
        """Zero impressions edge case should still work."""
        result = AbStatsService.calculate_significance([(0, 0), (100, 5)])
        assert isinstance(result, SignificanceResult)

    def test_calculate_significance_multiple_variants(self):
        """More than 2 variants should work correctly."""
        result = AbStatsService.calculate_significance(
            [(100, 10), (100, 15), (100, 12)]
        )
        assert result.dof == 2  # (3-1)*(2-1) = 2
        assert result.z_score is not None  # z-score for first two

    def test_format_confidence_with_edge_values(self):
        """Edge values for format_confidence."""
        assert AbStatsService.format_confidence(0.0) == "100.0%"
        assert AbStatsService.format_confidence(1.0) == "Insufficient data"
        assert AbStatsService.format_confidence(-0.1) == "Invalid p-value"


class TestABTestServiceBehavioral:
    """Behavioral tests for ABTestService — verify real implementation with DB."""

    async def _init_db(self) -> tuple[AsyncSession, Any]:
        """Create an in-memory SQLite database with tables for testing."""
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from src.database import Base

        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        session = session_factory()
        return session, engine

    @pytest.mark.asyncio
    async def test_create_test_creates_records(self):
        """ABTestService.create_test should create test and variant records."""
        svc = ABTestService()
        request = ABCreateRequest(
            name="Test headline variations",
            content_type="blog",
            topic="Benefits of AI in marketing",
            variant_count=3,
            variant_dimension="headline",
        )
        session, engine = await self._init_db()
        try:
            ab_test = await svc.create_test(request, session)
            assert ab_test.id is not None
            assert ab_test.name == "Test headline variations"
            assert ab_test.status == "draft"
            assert ab_test.content_type == "blog"

            # Verify variants were created
            await session.refresh(ab_test, ["variants"])
            assert len(ab_test.variants) == 3
            assert ab_test.variants[0].variant_type == "control"
            assert all(v.variant_type == "treatment" for v in ab_test.variants[1:])
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_create_test_with_default_variant_count(self):
        """Default variant_count=2 should create 1 control + 1 treatment."""
        svc = ABTestService()
        request = ABCreateRequest(
            name="Simple test",
            content_type="email",
            topic="test topic",
        )
        session, engine = await self._init_db()
        try:
            ab_test = await svc.create_test(request, session)
            await session.refresh(ab_test, ["variants"])
            assert len(ab_test.variants) == 2
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_track_event_increments_counters(self):
        """track_event should increment variant counters."""
        svc = ABTestService()
        session, engine = await self._init_db()
        try:
            # Create a test first
            request = ABCreateRequest(
                name="Test",
                content_type="blog",
                topic="AI testing",
            )
            ab_test = await svc.create_test(request, session)
            await session.refresh(ab_test, ["variants"])
            variant_id = ab_test.variants[0].id

            # Track an impression
            track_req = ABTrackRequest(variant_id=variant_id, event_type="impression")
            await svc.track_event(track_req, session)

            # Verify impression was counted
            await session.refresh(ab_test.variants[0])
            assert ab_test.variants[0].impressions == 1
            assert ab_test.variants[0].conversions == 0

            # Track a conversion
            track_req2 = ABTrackRequest(variant_id=variant_id, event_type="conversion")
            await svc.track_event(track_req2, session)

            await session.refresh(ab_test.variants[0])
            assert ab_test.variants[0].impressions == 1
            assert ab_test.variants[0].conversions == 1
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_get_results_returns_valid_response(self):
        """get_results should return ABResultsResponse with stats."""
        svc = ABTestService()
        session, engine = await self._init_db()
        try:
            # Create a test
            request = ABCreateRequest(
                name="Results test",
                content_type="social",
                topic="Testing results",
                variant_count=2,
            )
            ab_test = await svc.create_test(request, session)
            await session.refresh(ab_test, ["variants"])
            v1 = ab_test.variants[0]
            v2 = ab_test.variants[1]

            # Add some events to create difference
            for _ in range(50):
                tr = ABTrackRequest(variant_id=v1.id, event_type="impression")
                await svc.track_event(tr, session)
            for _ in range(10):
                tr = ABTrackRequest(variant_id=v1.id, event_type="conversion")
                await svc.track_event(tr, session)
            for _ in range(50):
                tr = ABTrackRequest(variant_id=v2.id, event_type="impression")
                await svc.track_event(tr, session)
            for _ in range(5):
                tr = ABTrackRequest(variant_id=v2.id, event_type="conversion")
                await svc.track_event(tr, session)

            results = await svc.get_results(ab_test.id, session)
            assert isinstance(results, ABResultsResponse)
            assert results.test.id == ab_test.id
            assert results.test.name == "Results test"
            assert len(results.variants) == 2
            assert results.method == "chi-squared"
            assert results.significance_level is not None
            assert results.confidence_level is not None
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_conclude_test_updates_status(self):
        """conclude_test should set status to concluded and record winner."""
        svc = ABTestService()
        session, engine = await self._init_db()
        try:
            request = ABCreateRequest(
                name="Conclude test",
                content_type="blog",
                topic="Testing conclusion",
            )
            ab_test = await svc.create_test(request, session)
            await session.refresh(ab_test, ["variants"])
            winner_id = ab_test.variants[0].id

            conclude_req = ABConcludeRequest(winner_variant_id=winner_id, note="Variant A wins")
            concluded = await svc.conclude_test(ab_test.id, conclude_req, session)
            assert concluded.status == "concluded"
            assert concluded.winner_variant_id == winner_id
            assert concluded.concluded_at is not None
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_get_dashboard_returns_summary(self):
        """get_dashboard should return grouped test summaries."""
        svc = ABTestService()
        session, engine = await self._init_db()
        try:
            request = ABCreateRequest(
                name="Dashboard test",
                content_type="blog",
                topic="Testing dashboard",
            )
            await svc.create_test(request, session)

            dashboard = await svc.get_dashboard(session)
            assert isinstance(dashboard, ABDashboardResponse)
            assert dashboard.total_tests >= 1
            assert dashboard.active_count >= 1
            assert dashboard.concluded_count == 0
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_list_tests_returns_paginated(self):
        """list_tests should return paginated results."""
        svc = ABTestService()
        session, engine = await self._init_db()
        try:
            for i in range(3):
                request = ABCreateRequest(
                    name=f"List test {i}",
                    content_type="blog",
                    topic=f"topic {i}",
                )
                await svc.create_test(request, session)

            result = await svc.list_tests(session, limit=2, offset=0)
            assert isinstance(result, ABTestListResponse)
            assert len(result.items) == 2
            assert result.total == 3
            assert result.limit == 2
            assert result.offset == 0
        finally:
            await session.close()
            await engine.dispose()


class TestABCreateRequestValidation:
    """Behavioral tests for ABCreateRequest schema validation."""

    def test_valid_create_request(self):
        """A valid ABCreateRequest should construct successfully."""
        req = ABCreateRequest(
            name="Test headline variations",
            content_type="blog",
            topic="Benefits of AI in marketing",
            variant_count=3,
            variant_dimension="headline",
        )
        assert req.name == "Test headline variations"
        assert req.content_type == "blog"
        assert req.variant_count == 3

    def test_name_min_length_validated(self):
        """name must have min_length=1."""
        with pytest.raises(ValidationError):
            ABCreateRequest(
                name="",
                content_type="blog",
                topic="test",
            )

    def test_variant_count_range_validated(self):
        """variant_count must be >= 2 and <= 5."""
        with pytest.raises(ValidationError):
            ABCreateRequest(
                name="Test",
                content_type="blog",
                topic="test",
                variant_count=1,
            )
        with pytest.raises(ValidationError):
            ABCreateRequest(
                name="Test",
                content_type="blog",
                topic="test",
                variant_count=6,
            )

    def test_content_type_literal_validated(self):
        """content_type must be one of blog, social, email."""
        with pytest.raises(ValidationError):
            ABCreateRequest(
                name="Test",
                content_type="video",
                topic="test",
            )

    def test_default_values(self):
        """Defaults should be applied correctly."""
        req = ABCreateRequest(
            name="Test",
            content_type="email",
            topic="test topic",
        )
        assert req.variant_count == 2
        assert req.variant_dimension == "tone"
        assert req.description == ""
        assert req.length == "medium"
        assert req.audience is None


class TestABTrackRequestValidation:
    """Behavioral tests for ABTrackRequest schema validation."""

    def test_valid_track_request(self):
        req = ABTrackRequest(
            variant_id="var_1",
            event_type="conversion",
        )
        assert req.variant_id == "var_1"
        assert req.event_type == "conversion"

    def test_event_type_must_be_valid_literal(self):
        with pytest.raises(ValidationError):
            ABTrackRequest(
                variant_id="var_1",
                event_type="click",
            )

    def test_user_identifier_optional(self):
        req = ABTrackRequest(
            variant_id="var_1",
            event_type="impression",
        )
        assert req.user_identifier is None
        assert req.metadata == {}


class TestABConcludeRequestValidation:
    """Behavioral tests for ABConcludeRequest schema validation."""

    def test_valid_conclude_request(self):
        req = ABConcludeRequest(winner_variant_id="var_1")
        assert req.winner_variant_id == "var_1"
        assert req.note == ""

    def test_conclude_request_with_note(self):
        req = ABConcludeRequest(winner_variant_id="var_1", note="Clear winner")
        assert req.note == "Clear winner"


class TestABVariantResponseBehavioral:
    """Behavioral tests for ABVariantResponse schema."""

    def test_default_conversion_rate_zero(self):
        resp = ABVariantResponse(
            id="var_1",
            name="Control",
            variant_type="control",
            impressions=0,
            conversions=0,
            created_at=datetime.now(UTC),
        )
        assert resp.conversion_rate == 0.0

    def test_computed_conversion_rate(self):
        """conversion_rate should be set explicitly (it's computed)."""
        resp = ABVariantResponse(
            id="var_1",
            name="Variant A",
            variant_type="treatment",
            impressions=100,
            conversions=15,
            conversion_rate=0.15,
            created_at=datetime.now(UTC),
        )
        assert resp.conversion_rate == 0.15

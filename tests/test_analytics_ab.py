"""Interface and behavioral tests for M6 — A/B results correlation.

Interface tests  — verify imports, signatures (should PASS).
Behavioral tests — verify expected behavior; against pre-dev stubs they FAIL
                   with NotImplementedError (TDD RED phase).
"""

from __future__ import annotations

import inspect

import pytest
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from tests.analytics_test_utils import (
    seed_event,
    seed_generation,
)
from src.models.ab_test import ABTest, ABVariant
from src.routers.analytics import get_ab_results as ab_results_endpoint
from src.routers.analytics import router as analytics_router
from src.schemas.analytics import ABResultsCorrelationResponse, VariantPerformance
from src.services.analytics import AnalyticsService

pytestmark = pytest.mark.asyncio


async def _seed_ab_test(
    session: AsyncSession,
    test_id: str = "test_1",
    winner_variant_id: str | None = None,
) -> None:
    session.add(
        ABTest(
            id=test_id,
            name="Headline A/B test",
            content_type="blog",
            topic="AI marketing",
            status="concluded",
            winner_variant_id=winner_variant_id,
        )
    )
    await session.commit()


async def _seed_variant(
    session: AsyncSession,
    variant_id: str,
    test_id: str,
    name: str,
    variant_type: str = "treatment",
    generation_id: str | None = None,
) -> None:
    session.add(
        ABVariant(
            id=variant_id,
            ab_test_id=test_id,
            name=name,
            variant_type=variant_type,
            generation_id=generation_id,
        )
    )
    await session.commit()


# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestABCorrelationSchemasInterface:
    """Verify the A/B correlation schemas (brief §5.3)."""

    def test_variant_performance_importable(self):
        assert VariantPerformance is not None

    def test_variant_performance_is_pydantic(self):
        assert issubclass(VariantPerformance, BaseModel)

    def test_ab_results_correlation_importable(self):
        assert ABResultsCorrelationResponse is not None

    def test_ab_results_correlation_is_pydantic(self):
        assert issubclass(ABResultsCorrelationResponse, BaseModel)

    def test_variant_performance_fields(self):
        sig = inspect.signature(VariantPerformance)
        for field in (
            "variant_id",
            "name",
            "variant_type",
            "generation_id",
            "impressions",
            "conversions",
            "conversion_rate",
            "engagement_rate",
            "is_winner",
        ):
            assert field in sig.parameters

    def test_ab_results_correlation_fields(self):
        sig = inspect.signature(ABResultsCorrelationResponse)
        for field in (
            "ab_test_id",
            "name",
            "status",
            "winner_variant_id",
            "variants",
            "correlation_note",
        ):
            assert field in sig.parameters


class TestABCorrelationServiceInterface:
    """Verify get_ab_correlation on the service (brief §5.1)."""

    def test_service_has_get_ab_correlation(self):
        assert hasattr(AnalyticsService, "get_ab_correlation")
        assert inspect.iscoroutinefunction(AnalyticsService.get_ab_correlation)

    def test_get_ab_correlation_signature(self):
        sig = inspect.signature(AnalyticsService.get_ab_correlation)
        assert "db" in sig.parameters
        assert "test_id" in sig.parameters
        assert sig.parameters["date_from"].default is None
        assert sig.parameters["date_to"].default is None

    def test_get_ab_correlation_return_annotation(self):
        annotation = inspect.signature(
            AnalyticsService.get_ab_correlation
        ).return_annotation
        assert "ABResultsCorrelationResponse" in str(annotation)


class TestABCorrelationRouterInterface:
    """Verify the /ab-results route (brief §5.4)."""

    def test_router_has_ab_results_endpoint(self):
        routes = [(r.path, sorted(r.methods or [])) for r in analytics_router.routes]
        assert ("/api/v1/analytics/ab-results", ["GET"]) in routes


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (FAIL with NotImplementedError during RED)
# ============================================================================


class TestABCorrelationBehavioral:
    """M6 — GET /api/v1/analytics/ab-results behavior (brief §4 T6)."""

    async def test_ab_results_unknown_test_raises(self, db_session):
        """Unknown test_id -> service ValueError (router maps to 404)."""
        svc = AnalyticsService()
        with pytest.raises(ValueError):
            await svc.get_ab_correlation(db_session, "does-not-exist")

    async def test_ab_results_unknown_test_404(self, db_session):
        """Handler maps unknown test_id to HTTP 404."""
        with pytest.raises(HTTPException) as exc_info:
            await ab_results_endpoint("does-not-exist", db=db_session)
        assert exc_info.value.status_code == 404

    async def test_ab_results_response_shape(self, db_session):
        """Response carries test metadata (§4 T6)."""
        await _seed_ab_test(db_session, test_id="test_1", winner_variant_id="var_a")
        await _seed_variant(db_session, "var_a", "test_1", "Variant A", "control")
        await _seed_variant(db_session, "var_b", "test_1", "Variant B", "treatment")

        svc = AnalyticsService()
        response = await svc.get_ab_correlation(db_session, "test_1")
        assert isinstance(response, ABResultsCorrelationResponse)
        assert response.ab_test_id == "test_1"
        assert response.name == "Headline A/B test"
        assert response.status == "concluded"
        assert response.winner_variant_id == "var_a"

    async def test_ab_variants_without_generation_zeroed(self, db_session):
        """Variants without generation_id are included with zeroed analytics (§4 T6)."""
        await _seed_ab_test(db_session, test_id="test_1")
        await _seed_variant(db_session, "var_a", "test_1", "Variant A", "control")
        await _seed_variant(db_session, "var_b", "test_1", "Variant B", "treatment")

        svc = AnalyticsService()
        response = await svc.get_ab_correlation(db_session, "test_1")
        assert len(response.variants) == 2
        for variant in response.variants:
            assert variant.generation_id is None
            assert variant.impressions == 0
            assert variant.conversions == 0
            assert variant.conversion_rate == 0.0
            assert variant.engagement_rate == 0.0

    async def test_ab_merges_analytics_events(self, db_session):
        """Variants with generation_id get analytics merged from events (§4 T6)."""
        await seed_generation(db_session, "gen_a")
        await seed_generation(db_session, "gen_b")
        await _seed_ab_test(db_session, test_id="test_1", winner_variant_id="var_a")
        await _seed_variant(
            db_session, "var_a", "test_1", "Variant A", "control", generation_id="gen_a"
        )
        await _seed_variant(
            db_session, "var_b", "test_1", "Variant B", "treatment", generation_id="gen_b"
        )
        for _ in range(100):
            await seed_event(db_session, "gen_a", "impression", "web")
        for _ in range(10):
            await seed_event(db_session, "gen_a", "conversion", "web")
        await seed_event(db_session, "gen_b", "impression", "web", value=80)

        svc = AnalyticsService()
        response = await svc.get_ab_correlation(db_session, "test_1")
        by_id = {v.variant_id: v for v in response.variants}
        assert by_id["var_a"].impressions == 100
        assert by_id["var_a"].conversions == 10
        assert by_id["var_a"].conversion_rate == pytest.approx(0.10)
        assert by_id["var_b"].impressions == 80
        assert by_id["var_b"].conversions == 0

    async def test_ab_winner_marked(self, db_session):
        """is_winner True for the test's winner_variant_id (§4 T6)."""
        await seed_generation(db_session, "gen_a")
        await _seed_ab_test(db_session, test_id="test_1", winner_variant_id="var_a")
        await _seed_variant(
            db_session, "var_a", "test_1", "Variant A", "control", generation_id="gen_a"
        )
        await _seed_variant(db_session, "var_b", "test_1", "Variant B", "treatment")

        svc = AnalyticsService()
        response = await svc.get_ab_correlation(db_session, "test_1")
        by_id = {v.variant_id: v for v in response.variants}
        assert by_id["var_a"].is_winner is True
        assert by_id["var_b"].is_winner is False

    async def test_ab_correlation_note_nonempty(self, db_session):
        """correlation_note present when significance is computable (§4 T6)."""
        await seed_generation(db_session, "gen_a")
        await seed_generation(db_session, "gen_b")
        await _seed_ab_test(db_session, test_id="test_1")
        await _seed_variant(
            db_session, "var_a", "test_1", "Variant A", "control", generation_id="gen_a"
        )
        await _seed_variant(
            db_session, "var_b", "test_1", "Variant B", "treatment", generation_id="gen_b"
        )
        for _ in range(1000):
            await seed_event(db_session, "gen_a", "impression", "web")
        for _ in range(100):
            await seed_event(db_session, "gen_a", "conversion", "web")
        for _ in range(1000):
            await seed_event(db_session, "gen_b", "impression", "web")
        for _ in range(150):
            await seed_event(db_session, "gen_b", "conversion", "web")

        svc = AnalyticsService()
        response = await svc.get_ab_correlation(db_session, "test_1")
        assert isinstance(response.correlation_note, str)
        assert response.correlation_note.strip() != ""

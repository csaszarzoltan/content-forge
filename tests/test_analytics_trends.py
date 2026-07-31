"""Interface and behavioral tests for M9 — trends + anomaly detection.

Interface tests  — verify imports, signatures (should PASS).
Behavioral tests — verify expected behavior; against pre-dev stubs they FAIL
                   with NotImplementedError (TDD RED phase).

Anomaly rule (brief §4 T9): |z| >= 2.0 on the daily series via stdlib
``statistics``, needs >= 7 daily points, direction spike/drop.
"""

from __future__ import annotations

import inspect

import pytest
from pydantic import BaseModel

from tests.analytics_test_utils import (
    seed_event,
    seed_generation,
)
from src.routers.analytics import router as analytics_router
from src.schemas.analytics import AnomalyItem, AnomalyResponse, TrendPoint, TrendResponse
from src.services.analytics import AnalyticsService

pytestmark = pytest.mark.asyncio


# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestTrendSchemasInterface:
    """Verify the trend/anomaly schemas (brief §5.3)."""

    def test_trend_point_importable(self):
        assert TrendPoint is not None

    def test_trend_point_is_pydantic(self):
        assert issubclass(TrendPoint, BaseModel)

    def test_trend_response_importable(self):
        assert TrendResponse is not None

    def test_trend_response_is_pydantic(self):
        assert issubclass(TrendResponse, BaseModel)

    def test_anomaly_item_importable(self):
        assert AnomalyItem is not None

    def test_anomaly_item_is_pydantic(self):
        assert issubclass(AnomalyItem, BaseModel)

    def test_anomaly_response_importable(self):
        assert AnomalyResponse is not None

    def test_anomaly_response_is_pydantic(self):
        assert issubclass(AnomalyResponse, BaseModel)

    def test_trend_point_fields(self):
        sig = inspect.signature(TrendPoint)
        for field in (
            "date",
            "impressions",
            "clicks",
            "shares",
            "comments",
            "conversions",
            "engagement_rate",
            "anomaly",
        ):
            assert field in sig.parameters

    def test_trend_response_fields(self):
        sig = inspect.signature(TrendResponse)
        for field in ("period", "metric", "points"):
            assert field in sig.parameters

    def test_anomaly_item_fields(self):
        sig = inspect.signature(AnomalyItem)
        for field in ("date", "metric", "value", "z_score", "direction"):
            assert field in sig.parameters

    def test_anomaly_response_fields(self):
        sig = inspect.signature(AnomalyResponse)
        for field in ("period", "metric", "anomalies"):
            assert field in sig.parameters


class TestTrendServiceInterface:
    """Verify get_trends / detect_anomalies on the service (brief §5.1)."""

    def test_service_has_get_trends(self):
        assert hasattr(AnalyticsService, "get_trends")
        assert inspect.iscoroutinefunction(AnalyticsService.get_trends)

    def test_service_has_detect_anomalies(self):
        assert hasattr(AnalyticsService, "detect_anomalies")
        assert inspect.iscoroutinefunction(AnalyticsService.detect_anomalies)

    def test_get_trends_signature(self):
        sig = inspect.signature(AnalyticsService.get_trends)
        assert sig.parameters["period"].default == "30d"
        assert sig.parameters["metric"].default == "impressions"
        assert sig.parameters["channel"].default is None

    def test_detect_anomalies_signature(self):
        sig = inspect.signature(AnalyticsService.detect_anomalies)
        assert sig.parameters["period"].default == "30d"
        assert sig.parameters["metric"].default == "impressions"

    def test_get_trends_return_annotation(self):
        annotation = inspect.signature(AnalyticsService.get_trends).return_annotation
        assert "TrendResponse" in str(annotation)

    def test_detect_anomalies_return_annotation(self):
        annotation = inspect.signature(
            AnalyticsService.detect_anomalies
        ).return_annotation
        assert "AnomalyResponse" in str(annotation)


class TestTrendRouterInterface:
    """Verify the /trends and /anomalies routes (brief §5.4)."""

    def test_router_has_trends_endpoint(self):
        routes = [(r.path, sorted(r.methods or [])) for r in analytics_router.routes]
        assert ("/api/v1/analytics/trends", ["GET"]) in routes

    def test_router_has_anomalies_endpoint(self):
        routes = [(r.path, sorted(r.methods or [])) for r in analytics_router.routes]
        assert ("/api/v1/analytics/anomalies", ["GET"]) in routes


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (FAIL with NotImplementedError during RED)
# ============================================================================


class TestTrendsBehavioral:
    """M9 — GET /api/v1/analytics/trends behavior (brief §4 T9)."""

    async def _seed_daily_series(
        self, db_session, days: int, values: list[int] | None = None
    ) -> None:
        await seed_generation(db_session, "gen_1")
        for day in range(days):
            value = values[day] if values else 100
            await seed_event(
                db_session, "gen_1", "impression", "web", value, days_ago=day
            )

    async def test_trends_returns_daily_series(self, db_session):
        """Daily series with per-point anomaly flags (brief §4 T9)."""
        await self._seed_daily_series(db_session, days=10)
        svc = AnalyticsService()
        response = await svc.get_trends(db_session, period="30d", metric="impressions")
        assert isinstance(response, TrendResponse)
        assert response.period == "30d"
        assert response.metric == "impressions"
        assert len(response.points) >= 7
        for point in response.points:
            assert isinstance(point, TrendPoint)
            assert isinstance(point.date, str)
            assert isinstance(point.anomaly, bool)

    async def test_trends_invalid_period_raises(self, db_session):
        """Invalid period -> 422 (service raises ValueError)."""
        svc = AnalyticsService()
        with pytest.raises(ValueError):
            await svc.get_trends(db_session, period="1y")

    async def test_trends_invalid_metric_raises(self, db_session):
        """Invalid metric -> 422 (service raises ValueError)."""
        svc = AnalyticsService()
        with pytest.raises(ValueError):
            await svc.get_trends(db_session, metric="likes")

    async def test_trends_channel_filter(self, db_session):
        """channel filter narrows the trend series."""
        await seed_generation(db_session, "gen_1")
        await seed_event(db_session, "gen_1", "impression", "twitter", 10, days_ago=1)
        await seed_event(db_session, "gen_1", "impression", "web", 99, days_ago=1)
        svc = AnalyticsService()
        response = await svc.get_trends(db_session, period="7d", channel="twitter")
        assert all(point.impressions == 10 for point in response.points)


class TestAnomaliesBehavioral:
    """M9 — GET /api/v1/analytics/anomalies behavior (brief §4 T9)."""

    async def test_anomalies_synthetic_spike_flagged(self, db_session):
        """A synthetic spike is flagged with |z| >= 2.0, direction spike."""
        await seed_generation(db_session, "gen_1")
        for day in range(9):
            await seed_event(
                db_session, "gen_1", "impression", "web", 100, days_ago=day
            )
        await seed_event(db_session, "gen_1", "impression", "web", 500, days_ago=9)

        svc = AnalyticsService()
        response = await svc.detect_anomalies(db_session, period="30d", metric="impressions")
        assert isinstance(response, AnomalyResponse)
        assert len(response.anomalies) >= 1
        for anomaly in response.anomalies:
            assert isinstance(anomaly, AnomalyItem)
            assert abs(anomaly.z_score) >= 2.0
            assert anomaly.direction in ("spike", "drop")

    async def test_anomalies_flat_series_none(self, db_session):
        """A flat series has no anomalies."""
        await seed_generation(db_session, "gen_1")
        for day in range(10):
            await seed_event(
                db_session, "gen_1", "impression", "web", 100, days_ago=day
            )
        svc = AnalyticsService()
        response = await svc.detect_anomalies(db_session, period="30d")
        assert response.anomalies == []

    async def test_anomalies_fewer_than_7_points_empty(self, db_session):
        """Fewer than 7 daily points -> no anomalies (rule needs >= 7)."""
        await seed_generation(db_session, "gen_1")
        for day in range(5):
            await seed_event(
                db_session, "gen_1", "impression", "web", 100, days_ago=day
            )
        svc = AnalyticsService()
        response = await svc.detect_anomalies(db_session, period="30d")
        assert response.anomalies == []

    async def test_anomalies_invalid_period_raises(self, db_session):
        """Invalid period -> 422 (service raises ValueError)."""
        svc = AnalyticsService()
        with pytest.raises(ValueError):
            await svc.detect_anomalies(db_session, period="1y")

    async def test_anomalies_response_metadata(self, db_session):
        """Response echoes period + metric."""
        await seed_generation(db_session, "gen_1")
        await seed_event(db_session, "gen_1", "impression", "web", 100)
        svc = AnalyticsService()
        response = await svc.detect_anomalies(db_session, period="30d", metric="clicks")
        assert response.period == "30d"
        assert response.metric == "clicks"

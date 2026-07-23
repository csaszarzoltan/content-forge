"""Interface and behavioral tests for analytics endpoints, schemas, and services.

Interface tests  — verify imports, class signatures (should PASS).
Behavioral tests — verify NotImplementedError for stubs.
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = pytest.mark.asyncio

from src.schemas.analytics import (
    ComplianceData,
    PerformanceData,
    ContentAnalyticsResponse,
    AnalyticsSummary,
)
from src.routers.analytics import router as analytics_router
from src.services.analytics import AnalyticsService


# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestAnalyticsSchemasInterface:
    """Verify the analytics schema interfaces."""

    def test_compliance_data_importable(self):
        assert ComplianceData is not None

    def test_compliance_data_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(ComplianceData, BaseModel)

    def test_compliance_data_fields(self):
        sig = inspect.signature(ComplianceData)
        assert "overall" in sig.parameters
        assert "vocabulary" in sig.parameters
        assert "readability" in sig.parameters
        assert "tone" in sig.parameters
        assert "violations" in sig.parameters

    def test_performance_data_importable(self):
        assert PerformanceData is not None

    def test_performance_data_fields(self):
        sig = inspect.signature(PerformanceData)
        assert "views" in sig.parameters
        assert "engagement_rate" in sig.parameters
        assert "shares" in sig.parameters
        assert "comments" in sig.parameters
        assert "avg_read_time_seconds" in sig.parameters

    def test_content_analytics_response_importable(self):
        assert ContentAnalyticsResponse is not None

    def test_content_analytics_response_fields(self):
        sig = inspect.signature(ContentAnalyticsResponse)
        assert "generation_id" in sig.parameters
        assert "content_type" in sig.parameters
        assert "compliance" in sig.parameters
        assert "performance" in sig.parameters

    def test_analytics_summary_importable(self):
        assert AnalyticsSummary is not None

    def test_analytics_summary_fields(self):
        sig = inspect.signature(AnalyticsSummary)
        assert "total_generations" in sig.parameters
        assert "avg_compliance" in sig.parameters
        assert "content_type_breakdown" in sig.parameters
        assert "total_views" in sig.parameters


class TestAnalyticsRouterInterface:
    """Verify the analytics router interface."""

    def test_router_importable(self):
        assert analytics_router is not None
        assert analytics_router.prefix == "/analytics"

    def test_router_has_content_endpoint(self):
        routes = [(r.path, r.methods) for r in analytics_router.routes]
        assert any("/content/{generation_id}" in path for path, _ in routes)

    def test_router_has_summary_endpoint(self):
        routes = [(r.path, r.methods) for r in analytics_router.routes]
        assert any("summary" in path for path, _ in routes)


class TestAnalyticsServiceInterface:
    """Verify the AnalyticsService interface."""

    def test_analytics_service_importable(self):
        assert AnalyticsService is not None

    def test_analytics_service_is_class(self):
        assert inspect.isclass(AnalyticsService)

    def test_analytics_service_has_get_content_analytics(self):
        assert hasattr(AnalyticsService, "get_content_analytics")
        assert inspect.iscoroutinefunction(AnalyticsService.get_content_analytics)

    def test_analytics_service_get_content_analytics_signature(self):
        sig = inspect.signature(AnalyticsService.get_content_analytics)
        assert "generation_id" in sig.parameters

    def test_analytics_service_has_get_summary(self):
        assert hasattr(AnalyticsService, "get_summary")
        assert inspect.iscoroutinefunction(AnalyticsService.get_summary)

    def test_analytics_service_has_update_performance_metrics(self):
        assert hasattr(AnalyticsService, "update_performance_metrics")
        assert inspect.iscoroutinefunction(AnalyticsService.update_performance_metrics)


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (verify real implementation)
# ============================================================================


class TestAnalyticsEndpointsBehavioral:
    """Behavioral tests for analytics endpoints — verify real implementation."""

    def test_content_analytics_endpoint_is_callable(self):
        """GET /analytics/content/{id} handler exists."""
        from src.routers.analytics import get_content_analytics
        assert callable(get_content_analytics)

    def test_summary_endpoint_is_callable(self):
        """GET /analytics/summary handler exists."""
        from src.routers.analytics import get_analytics_summary
        assert callable(get_analytics_summary)


class TestAnalyticsServiceBehavioral:
    """Behavioral tests for AnalyticsService — verify real implementation."""

    def test_analytics_service_init_works(self):
        """AnalyticsService() should construct successfully."""
        svc = AnalyticsService()
        assert svc is not None

    async def test_get_content_analytics_returns_data(self):
        """get_content_analytics() should return a dict."""
        svc = AnalyticsService()
        result = await svc.get_content_analytics("gen_1")
        assert isinstance(result, dict)
        assert "generation_id" in result

    async def test_get_summary_returns_data(self):
        """get_summary() should return a dict."""
        svc = AnalyticsService()
        result = await svc.get_summary()
        assert isinstance(result, dict)
        assert "total_generations" in result

    async def test_update_performance_metrics_works(self):
        """update_performance_metrics() should not raise."""
        svc = AnalyticsService()
        await svc.update_performance_metrics("gen_1", {"views": 100})

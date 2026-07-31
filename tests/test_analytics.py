"""Interface and behavioral tests for analytics modules M1-M5 (v0.9.0).

Interface tests  — verify imports, class/function signatures (should PASS).
Behavioral tests — verify expected behavior; against the pre-dev stubs they
                   FAIL with NotImplementedError (TDD RED phase).

Router prefix migrated to ``/api/v1/analytics`` (analysis brief §5.5); the
legacy ``get_content_analytics`` / ``get_summary`` stubs are superseded by
``get_content_performance`` / ``get_dashboard``.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta

import pytest

# Mark as quick (unit tests)
pytestmark = [pytest.mark.asyncio, pytest.mark.quick]

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select

from tests.analytics_test_utils import (
    seed_event,
    seed_generation,
)
from src.models.analytics import (
    ANALYTICS_CHANNELS,
    ANALYTICS_EVENT_TYPES,
    AnalyticsEvent,
)
from src.routers.analytics import (
    get_content_performance as content_endpoint,
    track_event as track_endpoint,
    router as analytics_router,
)
from src.schemas.analytics import (
    ABResultsCorrelationResponse,
    AnalyticsSummary,
    AnomalyItem,
    AnomalyResponse,
    ChannelComparisonResponse,
    ChannelMetrics,
    ComplianceData,
    ContentAnalyticsResponse,
    ContentPerformanceResponse,
    ContentScoreResponse,
    DashboardResponse,
    ExportResponse,
    MetricSummary,
    PerformanceData,
    ScoreBreakdown,
    TimeSeriesPoint,
    TopContentItem,
    TrackEventRequest,
    TrackEventResponse,
    TrendPoint,
    TrendResponse,
    VariantPerformance,
)
from src.services.analytics import AnalyticsService


NEW_SCHEMAS = [
    TrackEventRequest,
    TrackEventResponse,
    MetricSummary,
    ContentPerformanceResponse,
    TopContentItem,
    TimeSeriesPoint,
    DashboardResponse,
    ChannelMetrics,
    ChannelComparisonResponse,
    VariantPerformance,
    ABResultsCorrelationResponse,
    ScoreBreakdown,
    ContentScoreResponse,
    TrendPoint,
    TrendResponse,
    AnomalyItem,
    AnomalyResponse,
    ExportResponse,
]


# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestLegacySchemasInterface:
    """Verify the pre-existing analytics schema interfaces (unchanged)."""

    def test_compliance_data_importable(self):
        assert ComplianceData is not None

    def test_compliance_data_is_pydantic(self):
        assert issubclass(ComplianceData, BaseModel)

    def test_compliance_data_fields(self):
        sig = inspect.signature(ComplianceData)
        for field in ("overall", "vocabulary", "readability", "tone", "violations"):
            assert field in sig.parameters

    def test_performance_data_fields(self):
        sig = inspect.signature(PerformanceData)
        for field in (
            "views",
            "engagement_rate",
            "shares",
            "comments",
            "avg_read_time_seconds",
        ):
            assert field in sig.parameters

    def test_content_analytics_response_fields(self):
        sig = inspect.signature(ContentAnalyticsResponse)
        for field in (
            "generation_id",
            "content_type",
            "compliance",
            "performance",
        ):
            assert field in sig.parameters

    def test_analytics_summary_fields(self):
        sig = inspect.signature(AnalyticsSummary)
        for field in (
            "total_generations",
            "avg_compliance",
            "content_type_breakdown",
            "total_views",
        ):
            assert field in sig.parameters


class TestAnalyticsModelsInterface:
    """Verify the AnalyticsEvent ORM model + constants (brief §3.2)."""

    def test_analytics_event_importable(self):
        assert AnalyticsEvent is not None

    def test_analytics_event_tablename(self):
        assert AnalyticsEvent.__tablename__ == "analytics_events"

    def test_analytics_event_columns(self):
        cols = {c.name for c in AnalyticsEvent.__table__.columns}
        assert {"id", "generation_id", "channel", "event_type", "value"}.issubset(cols)
        assert "user_identifier" in cols
        assert "metadata" in cols  # DB column name per spec §3.2
        assert "occurred_at" in cols

    def test_analytics_event_has_indexes(self):
        cols = AnalyticsEvent.__table__.columns
        assert cols.generation_id.index is True
        assert cols.channel.index is True
        assert cols.occurred_at.index is True

    def test_event_types_constant_exact(self):
        assert ANALYTICS_EVENT_TYPES == [
            "impression",
            "click",
            "share",
            "comment",
            "conversion",
            "read_time",
        ]

    def test_channels_constant_exact(self):
        assert ANALYTICS_CHANNELS == [
            "twitter",
            "linkedin",
            "medium",
            "blog",
            "email",
            "web",
            "other",
        ]


class TestNewSchemasInterface:
    """Verify the 18 new v0.9.0 schemas (brief §5.3)."""

    @pytest.mark.parametrize("schema_cls", NEW_SCHEMAS)
    def test_schema_importable(self, schema_cls):
        assert schema_cls is not None

    @pytest.mark.parametrize("schema_cls", NEW_SCHEMAS)
    def test_schema_is_pydantic(self, schema_cls):
        assert issubclass(schema_cls, BaseModel)

    def test_track_event_request_fields(self):
        sig = inspect.signature(TrackEventRequest)
        for field in (
            "generation_id",
            "channel",
            "event_type",
            "value",
            "user_identifier",
            "metadata",
            "occurred_at",
        ):
            assert field in sig.parameters

    def test_track_event_request_defaults(self):
        sig = inspect.signature(TrackEventRequest)
        assert sig.parameters["channel"].default == "web"
        assert sig.parameters["value"].default == 1
        assert sig.parameters["user_identifier"].default is None
        assert sig.parameters["occurred_at"].default is None

    def test_track_event_response_fields(self):
        sig = inspect.signature(TrackEventResponse)
        assert "status" in sig.parameters
        assert "event_id" in sig.parameters

    def test_metric_summary_fields(self):
        sig = inspect.signature(MetricSummary)
        for field in (
            "impressions",
            "clicks",
            "shares",
            "comments",
            "conversions",
            "read_time_seconds",
            "engagement_rate",
        ):
            assert field in sig.parameters

    def test_content_performance_response_fields(self):
        sig = inspect.signature(ContentPerformanceResponse)
        for field in (
            "generation_id",
            "content_type",
            "brand_voice_id",
            "topic",
            "model_used",
            "tokens_used",
            "compliance",
            "performance",
            "channel_breakdown",
            "score",
            "created_at",
            "updated_at",
        ):
            assert field in sig.parameters

    def test_top_content_item_fields(self):
        sig = inspect.signature(TopContentItem)
        for field in (
            "generation_id",
            "topic",
            "content_type",
            "impressions",
            "engagement_rate",
        ):
            assert field in sig.parameters

    def test_time_series_point_fields(self):
        sig = inspect.signature(TimeSeriesPoint)
        for field in (
            "date",
            "impressions",
            "clicks",
            "shares",
            "comments",
            "conversions",
            "engagement_rate",
        ):
            assert field in sig.parameters

    def test_dashboard_response_fields(self):
        sig = inspect.signature(DashboardResponse)
        for field in (
            "date_from",
            "date_to",
            "totals",
            "content_type_breakdown",
            "channel_breakdown",
            "top_content",
            "time_series",
        ):
            assert field in sig.parameters

    def test_channel_metrics_fields(self):
        sig = inspect.signature(ChannelMetrics)
        for field in (
            "channel",
            "impressions",
            "clicks",
            "shares",
            "comments",
            "conversions",
            "engagement_rate",
        ):
            assert field in sig.parameters

    def test_channel_comparison_response_fields(self):
        sig = inspect.signature(ChannelComparisonResponse)
        for field in ("date_from", "date_to", "channels", "best_channel", "total_impressions"):
            assert field in sig.parameters

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

    def test_score_breakdown_fields(self):
        sig = inspect.signature(ScoreBreakdown)
        for field in ("engagement", "seo", "readability", "compliance"):
            assert field in sig.parameters

    def test_content_score_response_fields(self):
        sig = inspect.signature(ContentScoreResponse)
        for field in ("generation_id", "score", "grade", "breakdown"):
            assert field in sig.parameters

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

    def test_export_response_fields(self):
        sig = inspect.signature(ExportResponse)
        for field in ("format", "filename", "content_type", "data"):
            assert field in sig.parameters


class TestAnalyticsRouterInterface:
    """Verify the migrated router interface (brief §5.4, §5.5)."""

    def test_router_prefix_migrated(self):
        """Prefix MUST be /api/v1/analytics after the §1.5 #1 migration."""
        assert analytics_router.prefix == "/api/v1/analytics"

    def test_router_has_track_endpoint(self):
        routes = [(r.path, sorted(r.methods or [])) for r in analytics_router.routes]
        assert ("/api/v1/analytics/track", ["POST"]) in routes

    def test_router_has_dashboard_endpoint(self):
        routes = [(r.path, sorted(r.methods or [])) for r in analytics_router.routes]
        assert ("/api/v1/analytics/dashboard", ["GET"]) in routes

    def test_router_has_content_endpoint(self):
        routes = [(r.path, sorted(r.methods or [])) for r in analytics_router.routes]
        assert ("/api/v1/analytics/content/{generation_id}", ["GET"]) in routes

    def test_router_has_channels_endpoint(self):
        routes = [(r.path, sorted(r.methods or [])) for r in analytics_router.routes]
        assert ("/api/v1/analytics/channels", ["GET"]) in routes

    def test_router_has_ab_results_endpoint(self):
        routes = [(r.path, sorted(r.methods or [])) for r in analytics_router.routes]
        assert ("/api/v1/analytics/ab-results", ["GET"]) in routes

    def test_router_has_export_endpoint(self):
        routes = [(r.path, sorted(r.methods or [])) for r in analytics_router.routes]
        assert ("/api/v1/analytics/export", ["GET"]) in routes

    def test_router_has_score_endpoint(self):
        routes = [(r.path, sorted(r.methods or [])) for r in analytics_router.routes]
        assert ("/api/v1/analytics/score/{generation_id}", ["GET"]) in routes

    def test_router_has_trends_endpoint(self):
        routes = [(r.path, sorted(r.methods or [])) for r in analytics_router.routes]
        assert ("/api/v1/analytics/trends", ["GET"]) in routes

    def test_router_has_anomalies_endpoint(self):
        routes = [(r.path, sorted(r.methods or [])) for r in analytics_router.routes]
        assert ("/api/v1/analytics/anomalies", ["GET"]) in routes

    def test_router_summary_endpoint_superseded(self):
        """Legacy GET /analytics/summary is replaced by /dashboard (§3.3)."""
        paths = [r.path for r in analytics_router.routes]
        assert not any(path.endswith("/summary") for path in paths)

    def test_router_handlers_are_callable(self):
        from src.routers.analytics import (
            export_data,
            get_ab_results,
            get_anomalies,
            get_channel_comparison,
            get_content_performance,
            get_content_score,
            get_dashboard,
            get_trends,
            track_event,
        )

        for handler in (
            track_event,
            get_dashboard,
            get_content_performance,
            get_channel_comparison,
            get_ab_results,
            export_data,
            get_content_score,
            get_trends,
            get_anomalies,
        ):
            assert callable(handler)


class TestAnalyticsServiceInterface:
    """Verify the AnalyticsService interface (brief §5.1)."""

    def test_analytics_service_importable(self):
        assert AnalyticsService is not None

    def test_analytics_service_is_class(self):
        assert inspect.isclass(AnalyticsService)

    @pytest.mark.parametrize(
        "method_name",
        [
            "track_event",
            "get_dashboard",
            "get_content_performance",
            "get_channel_comparison",
            "get_ab_correlation",
            "export_data",
            "get_trends",
            "detect_anomalies",
        ],
    )
    def test_service_has_new_method(self, method_name):
        assert hasattr(AnalyticsService, method_name)
        assert callable(getattr(AnalyticsService, method_name))

    @pytest.mark.parametrize(
        "method_name",
        [
            "track_event",
            "get_dashboard",
            "get_content_performance",
            "get_channel_comparison",
            "get_ab_correlation",
            "export_data",
            "get_trends",
            "detect_anomalies",
        ],
    )
    def test_service_methods_are_async(self, method_name):
        method = getattr(AnalyticsService, method_name)
        assert inspect.iscoroutinefunction(method), f"{method_name} should be async"

    def test_track_event_signature(self):
        sig = inspect.signature(AnalyticsService.track_event)
        assert "db" in sig.parameters
        assert "request" in sig.parameters

    def test_get_dashboard_signature(self):
        sig = inspect.signature(AnalyticsService.get_dashboard)
        assert "db" in sig.parameters
        assert sig.parameters["date_from"].default is None
        assert sig.parameters["date_to"].default is None
        assert sig.parameters["channel"].default is None
        assert sig.parameters["content_type"].default is None

    def test_get_content_performance_signature(self):
        sig = inspect.signature(AnalyticsService.get_content_performance)
        assert "generation_id" in sig.parameters
        assert sig.parameters["date_from"].default is None
        assert sig.parameters["date_to"].default is None

    def test_get_channel_comparison_signature(self):
        sig = inspect.signature(AnalyticsService.get_channel_comparison)
        assert sig.parameters["metric"].default == "impressions"

    def test_get_ab_correlation_signature(self):
        sig = inspect.signature(AnalyticsService.get_ab_correlation)
        assert "test_id" in sig.parameters
        assert sig.parameters["date_from"].default is None

    def test_export_data_signature(self):
        sig = inspect.signature(AnalyticsService.export_data)
        assert sig.parameters["format"].default == "json"
        assert sig.parameters["date_from"].default is None
        assert sig.parameters["channel"].default is None
        assert sig.parameters["content_type"].default is None

    def test_get_trends_signature(self):
        sig = inspect.signature(AnalyticsService.get_trends)
        assert sig.parameters["period"].default == "30d"
        assert sig.parameters["metric"].default == "impressions"
        assert sig.parameters["channel"].default is None

    def test_detect_anomalies_signature(self):
        sig = inspect.signature(AnalyticsService.detect_anomalies)
        assert sig.parameters["period"].default == "30d"
        assert sig.parameters["metric"].default == "impressions"

    @pytest.mark.parametrize(
        "method_name,expected_annotation",
        [
            ("track_event", "TrackEventResponse"),
            ("get_dashboard", "DashboardResponse"),
            ("get_content_performance", "ContentPerformanceResponse"),
            ("get_channel_comparison", "ChannelComparisonResponse"),
            ("get_ab_correlation", "ABResultsCorrelationResponse"),
            ("export_data", "ExportResponse"),
            ("get_trends", "TrendResponse"),
            ("detect_anomalies", "AnomalyResponse"),
        ],
    )
    def test_service_return_annotations(self, method_name, expected_annotation):
        """Type hints on all public functions (feature AC)."""
        annotation = inspect.signature(
            getattr(AnalyticsService, method_name)
        ).return_annotation
        assert expected_annotation in str(annotation)

    def test_service_keeps_update_performance_metrics(self):
        assert hasattr(AnalyticsService, "update_performance_metrics")
        assert inspect.iscoroutinefunction(AnalyticsService.update_performance_metrics)

    def test_service_init_works(self):
        svc = AnalyticsService()
        assert svc is not None


# ============================================================================
# SECTION 1b — SCHEMA CONTRACT TESTS (declarative; PASS immediately)
# ============================================================================


class TestTrackEventRequestValidation:
    """Pydantic declarative contract — these pass because schemas are stubs."""

    def test_valid_request_defaults(self):
        req = TrackEventRequest(generation_id="gen_1", event_type="click")
        assert req.generation_id == "gen_1"
        assert req.channel == "web"
        assert req.value == 1
        assert req.user_identifier is None
        assert req.metadata == {}
        assert req.occurred_at is None

    @pytest.mark.parametrize("bad_type", ["view", "like", "impresssion", "CLICK"])
    def test_invalid_event_type_rejected(self, bad_type):
        with pytest.raises(ValidationError):
            TrackEventRequest(generation_id="gen_1", event_type=bad_type)

    @pytest.mark.parametrize("bad_value", [-1, 1_000_001])
    def test_value_bounds_enforced(self, bad_value):
        with pytest.raises(ValidationError):
            TrackEventRequest(generation_id="gen_1", event_type="click", value=bad_value)

    def test_boundary_values_accepted(self):
        assert TrackEventRequest(
            generation_id="g", event_type="click", value=0
        ).value == 0
        assert TrackEventRequest(
            generation_id="g", event_type="click", value=1_000_000
        ).value == 1_000_000

    def test_metadata_defaults_to_empty_dict(self):
        req = TrackEventRequest(generation_id="g", event_type="impression")
        assert req.metadata == {}

    def test_metadata_accepted(self):
        req = TrackEventRequest(
            generation_id="g", event_type="click", metadata={"source": "newsletter"}
        )
        assert req.metadata == {"source": "newsletter"}


class TestResponseSchemaContracts:
    """Declarative response schema contract checks (PASS immediately)."""

    def test_track_response_status_literal(self):
        with pytest.raises(ValidationError):
            TrackEventResponse(status="error", event_id="e1")

    def test_content_score_grade_literal(self):
        for grade in ["A", "B", "C", "D", "F"]:
            assert (
                ContentScoreResponse(
                    generation_id="g", score=80.0, grade=grade,  # type: ignore[arg-type]
                    breakdown=ScoreBreakdown(),
                ).grade
                == grade
            )
        with pytest.raises(ValidationError):
            ContentScoreResponse(
                generation_id="g", score=80.0, grade="E",  # type: ignore[arg-type]
                breakdown=ScoreBreakdown(),
            )

    def test_anomaly_direction_literal(self):
        with pytest.raises(ValidationError):
            AnomalyItem(date="2026-01-01", metric="impressions", value=1.0, z_score=2.0, direction="flat")  # type: ignore[arg-type]

    def test_metric_summary_defaults(self):
        summary = MetricSummary()
        assert summary.impressions == 0
        assert summary.engagement_rate == 0.0
        assert summary.read_time_seconds == 0

    def test_dashboard_response_requires_dates(self):
        with pytest.raises(ValidationError):
            DashboardResponse(totals=MetricSummary())  # type: ignore[call-arg]


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (FAIL with NotImplementedError during RED)
# ============================================================================


class TestTrackEventBehavioral:
    """M2 — POST /api/v1/analytics/track behavior (brief §4 T2)."""

    async def test_track_event_returns_response(self, db_session):
        """track_event returns TrackEventResponse with status ok + event_id."""
        await seed_generation(db_session, "gen_1")
        svc = AnalyticsService()
        request = TrackEventRequest(
            generation_id="gen_1", channel="twitter", event_type="click", value=3
        )
        response = await svc.track_event(db_session, request)
        assert isinstance(response, TrackEventResponse)
        assert response.status == "ok"
        assert response.event_id

    async def test_track_event_unknown_generation_raises(self, db_session):
        """Unknown generation -> service ValueError (router maps to 404)."""
        svc = AnalyticsService()
        request = TrackEventRequest(generation_id="does-not-exist", event_type="click")
        with pytest.raises(ValueError):
            await svc.track_event(db_session, request)

    async def test_track_event_unknown_generation_404(self, db_session):
        """Handler maps unknown generation to HTTP 404 'Generation not found'."""
        request = TrackEventRequest(generation_id="does-not-exist", event_type="click")
        with pytest.raises(HTTPException) as exc_info:
            await track_endpoint(request, db=db_session)
        assert exc_info.value.status_code == 404

    async def test_track_event_invalid_channel_raises(self, db_session):
        """Channel outside ANALYTICS_CHANNELS -> ValueError (endpoint 422)."""
        await seed_generation(db_session, "gen_1")
        svc = AnalyticsService()
        request = TrackEventRequest(
            generation_id="gen_1", channel="myspace", event_type="click"
        )
        with pytest.raises(ValueError):
            await svc.track_event(db_session, request)

    async def test_track_event_invalid_channel_422(self, db_session):
        """Handler maps invalid channel to HTTP 422 (brief §4 T2)."""
        await seed_generation(db_session, "gen_1")
        request = TrackEventRequest(
            generation_id="gen_1", channel="myspace", event_type="click"
        )
        with pytest.raises(HTTPException) as exc_info:
            await track_endpoint(request, db=db_session)
        assert exc_info.value.status_code == 422

    async def test_track_event_future_occurred_at_422(self, db_session):
        """Handler maps occurred_at >24h in future to HTTP 422 (brief §4 T2)."""
        await seed_generation(db_session, "gen_1")
        request = TrackEventRequest(
            generation_id="gen_1",
            channel="twitter",
            event_type="click",
            occurred_at=datetime.now(UTC) + timedelta(hours=25),
        )
        with pytest.raises(HTTPException) as exc_info:
            await track_endpoint(request, db=db_session)
        assert exc_info.value.status_code == 422

    async def test_track_event_invalid_event_type_rejected(self, db_session):
        """event_type outside ANALYTICS_EVENT_TYPES -> 422 (schema Literal)."""
        with pytest.raises(ValidationError):
            TrackEventRequest(generation_id="gen_1", event_type="purchase")

    async def test_track_event_no_upsert(self, db_session):
        """Two events for same generation+channel+day are BOTH stored (§4 T2)."""
        await seed_generation(db_session, "gen_1")
        svc = AnalyticsService()
        request = TrackEventRequest(
            generation_id="gen_1", channel="web", event_type="impression"
        )
        await svc.track_event(db_session, request)
        await svc.track_event(db_session, request)
        count = (
            await db_session.execute(select(func.count()).select_from(AnalyticsEvent))
        ).scalar_one()
        assert count == 2

    async def test_track_event_persists_fields(self, db_session):
        """Event persisted with correct field values (§4 T2)."""
        await seed_generation(db_session, "gen_1")
        occurred = datetime.now(UTC) - timedelta(days=2)
        svc = AnalyticsService()
        response = await svc.track_event(
            db_session,
            TrackEventRequest(
                generation_id="gen_1",
                channel="linkedin",
                event_type="read_time",
                value=120,
                user_identifier="user-42",
                occurred_at=occurred,
            ),
        )
        row = (
            await db_session.execute(
                select(AnalyticsEvent).where(AnalyticsEvent.id == response.event_id)
            )
        ).scalar_one()
        assert row.generation_id == "gen_1"
        assert row.channel == "linkedin"
        assert row.event_type == "read_time"
        assert row.value == 120
        assert row.user_identifier == "user-42"
        assert row.occurred_at is not None


class TestDashboardBehavioral:
    """M3 — GET /api/v1/analytics/dashboard behavior (brief §4 T3)."""

    async def test_dashboard_empty_returns_zeroed(self, db_session):
        """Empty data -> zeroed response, NOT an error (§4 T3)."""
        svc = AnalyticsService()
        response = await svc.get_dashboard(db_session)
        assert isinstance(response, DashboardResponse)
        assert response.totals.impressions == 0
        assert response.totals.clicks == 0
        assert response.totals.engagement_rate == 0.0
        assert response.content_type_breakdown == {}
        assert response.channel_breakdown == {}
        assert response.top_content == []
        assert response.time_series == []

    async def test_dashboard_default_window_last_30d(self, db_session):
        """Default window is the last 30 days (§4 T3)."""
        svc = AnalyticsService()
        response = await svc.get_dashboard(db_session)
        assert response.date_to - response.date_from <= timedelta(days=31)
        assert response.date_from <= datetime.now(UTC)
        assert response.date_to <= datetime.now(UTC) + timedelta(days=1)

    async def test_dashboard_from_after_to_raises(self, db_session):
        """from > to -> 422 (service raises ValueError)."""
        svc = AnalyticsService()
        later = datetime.now(UTC)
        earlier = later - timedelta(days=10)
        with pytest.raises(ValueError):
            await svc.get_dashboard(db_session, date_from=later, date_to=earlier)

    async def test_dashboard_aggregates_seeded_events(self, db_session):
        """3 generations x 2 channels x 3 days produce correct totals/rates."""
        gens = ["gen_a", "gen_b", "gen_c"]
        for gen_id in gens:
            await seed_generation(db_session, gen_id, content_type="blog")
        for gen_id in gens:
            for channel in ("twitter", "linkedin"):
                await seed_event(db_session, gen_id, "impression", channel, 10, 1)
        await seed_event(db_session, "gen_a", "click", "twitter", 4, 1)
        await seed_event(db_session, "gen_a", "share", "twitter", 2, 1)
        await seed_event(db_session, "gen_a", "conversion", "linkedin", 1, 2)
        await seed_event(db_session, "gen_b", "read_time", "web", 300, 3)

        svc = AnalyticsService()
        response = await svc.get_dashboard(db_session)

        # impressions = 3 gens * 2 channels * 10 = 60
        assert response.totals.impressions == 60
        assert response.totals.clicks == 4
        assert response.totals.shares == 2
        assert response.totals.conversions == 1
        assert response.totals.read_time_seconds == 300
        # engagement_rate = (4+2+0+1)/60, clamped [0,1]
        assert response.totals.engagement_rate == pytest.approx(7 / 60)
        assert response.channel_breakdown["twitter"].impressions == 30
        assert response.channel_breakdown["linkedin"].impressions == 30
        assert response.content_type_breakdown["blog"] == 3

    async def test_dashboard_top_content_top5(self, db_session):
        """top_content holds top 5 pieces by impressions (§4 T3)."""
        for i in range(6):
            gen_id = f"gen_{i}"
            await seed_generation(db_session, gen_id)
            await seed_event(db_session, gen_id, "impression", "web", value=(i + 1) * 10)
        svc = AnalyticsService()
        response = await svc.get_dashboard(db_session)
        assert len(response.top_content) <= 5
        assert response.top_content[0].generation_id == "gen_5"  # 60 impressions
        assert response.top_content[0].impressions == 60

    async def test_dashboard_date_filtering_respected(self, db_session):
        """Events outside the requested window are excluded (§4 T3)."""
        await seed_generation(db_session, "gen_1")
        await seed_event(db_session, "gen_1", "impression", "web", 5, days_ago=1)
        await seed_event(db_session, "gen_1", "impression", "web", 7, days_ago=40)
        svc = AnalyticsService()
        now = datetime.now(UTC)
        response = await svc.get_dashboard(
            db_session,
            date_from=now - timedelta(days=7),
            date_to=now,
        )
        assert response.totals.impressions == 5

    async def test_dashboard_channel_filter(self, db_session):
        """channel filter limits the breakdown to that channel."""
        await seed_generation(db_session, "gen_1")
        await seed_event(db_session, "gen_1", "impression", "twitter", 5)
        await seed_event(db_session, "gen_1", "impression", "web", 9)
        svc = AnalyticsService()
        response = await svc.get_dashboard(db_session, channel="twitter")
        assert response.totals.impressions == 5
        assert "twitter" in response.channel_breakdown


class TestContentPerformanceBehavioral:
    """M4 — GET /api/v1/analytics/content/{generation_id} (brief §4 T4)."""

    async def test_content_unknown_generation_404(self, db_session):
        """Unknown generation -> HTTP 404 via handler."""
        with pytest.raises(HTTPException) as exc_info:
            await content_endpoint("does-not-exist", db=db_session)
        assert exc_info.value.status_code == 404

    async def test_content_unknown_generation_service_raises(self, db_session):
        svc = AnalyticsService()
        with pytest.raises(ValueError):
            await svc.get_content_performance(db_session, "does-not-exist")

    async def test_content_no_events_zeroed(self, db_session):
        """No events -> zeroed performance + empty channel_breakdown (§4 T4)."""
        await seed_generation(
            db_session,
            "gen_1",
            content_type="email",
            topic="Hello world",
            model_used="claude-3",
            tokens_used=500,
        )
        svc = AnalyticsService()
        response = await svc.get_content_performance(db_session, "gen_1")
        assert isinstance(response, ContentPerformanceResponse)
        assert response.generation_id == "gen_1"
        assert response.content_type == "email"
        assert response.topic == "Hello world"
        assert response.model_used == "claude-3"
        assert response.tokens_used == 500
        assert response.performance.views == 0
        assert response.channel_breakdown == {}
        assert response.score is None

    async def test_content_aggregates_events(self, db_session):
        """Channel breakdown only includes channels with events (§4 T4)."""
        await seed_generation(db_session, "gen_1")
        await seed_event(db_session, "gen_1", "impression", "twitter", 10)
        await seed_event(db_session, "gen_1", "impression", "linkedin", 5)
        await seed_event(db_session, "gen_1", "click", "twitter", 2)
        svc = AnalyticsService()
        response = await svc.get_content_performance(db_session, "gen_1")
        assert response.channel_breakdown["twitter"].impressions == 10
        assert response.channel_breakdown["linkedin"].impressions == 5
        assert set(response.channel_breakdown.keys()) == {"twitter", "linkedin"}

    async def test_content_engagement_rate(self, db_session):
        """engagement_rate computed from event aggregates (brief §3.2)."""
        await seed_generation(db_session, "gen_1")
        await seed_event(db_session, "gen_1", "impression", "web", 100)
        await seed_event(db_session, "gen_1", "click", "web", 10)
        await seed_event(db_session, "gen_1", "share", "web", 5)
        svc = AnalyticsService()
        response = await svc.get_content_performance(db_session, "gen_1")
        assert response.performance.engagement_rate == pytest.approx(0.15)


class TestChannelComparisonBehavioral:
    """M5 — GET /api/v1/analytics/channels behavior (brief §4 T5)."""

    async def test_channels_empty(self, db_session):
        """No events -> empty channels, best_channel None (§4 T5)."""
        svc = AnalyticsService()
        response = await svc.get_channel_comparison(db_session)
        assert isinstance(response, ChannelComparisonResponse)
        assert response.channels == []
        assert response.best_channel is None
        assert response.total_impressions == 0

    async def test_channels_invalid_metric_raises(self, db_session):
        """Invalid metric -> 422 (service raises ValueError)."""
        svc = AnalyticsService()
        with pytest.raises(ValueError):
            await svc.get_channel_comparison(db_session, metric="likes")

    async def test_channels_per_channel_totals(self, db_session):
        """Seeded multi-channel data yields correct per-channel totals."""
        await seed_generation(db_session, "gen_1")
        await seed_event(db_session, "gen_1", "impression", "twitter", 20)
        await seed_event(db_session, "gen_1", "impression", "linkedin", 30)
        await seed_event(db_session, "gen_1", "click", "twitter", 5)
        svc = AnalyticsService()
        response = await svc.get_channel_comparison(db_session)
        by_channel = {c.channel: c for c in response.channels}
        assert by_channel["twitter"].impressions == 20
        assert by_channel["linkedin"].impressions == 30
        assert response.total_impressions == 50
        assert response.best_channel == "linkedin"

    async def test_channels_sorted_by_metric(self, db_session):
        """Channels sorted by the chosen metric (default impressions)."""
        await seed_generation(db_session, "gen_1")
        await seed_event(db_session, "gen_1", "impression", "twitter", 5)
        await seed_event(db_session, "gen_1", "impression", "web", 15)
        await seed_event(db_session, "gen_1", "impression", "blog", 10)
        svc = AnalyticsService()
        response = await svc.get_channel_comparison(db_session)
        impressions = [c.impressions for c in response.channels]
        assert impressions == sorted(impressions, reverse=True)

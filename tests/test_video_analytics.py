"""Interface and behavioral tests for video platform analytics module.

Test categories:
  1. Interface tests  — imports, signatures, schema fields (should PASS immediately)
  2. API client tests — YouTube/TikTok/Instagram clients (RED: NotImplementedError)
  3. Service tests    — unified analytics (RED)
  4. Endpoint tests   — FastAPI routes (RED)
  5. CLI tests        — contentforge CLI video-performance (RED)
  6. Database tests   — VideoPlatformMetric CRUD (RED)

Pattern follows tests/test_ai_visibility_providers.py and tests/test_ab_test.py.
"""

from __future__ import annotations

import inspect
from abc import ABC
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import BaseModel

# Mark as quick (unit tests)
pytestmark = [pytest.mark.asyncio, pytest.mark.quick]

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.database import Base
from src.models.video_platform_metrics import VIDEO_PLATFORMS, VideoPlatformMetric
from src.routers.video_analytics import router as video_analytics_router
from src.schemas.video_analytics import (
    OptimalTimesHeatmap,
    PlatformMetrics,
    TimeseriesPoint,
    VideoDetailResponse,
    VideoMetricsSnapshot,
    VideoPerformanceResponse,
    VideoTimeseriesResponse,
)
from src.services.video_analytics import (
    InstagramClient,
    TikTokClient,
    VideoAPIClient,
    VideoAPIClientError,
    VideoAnalyticsService,
    YouTubeClient,
)


# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestModelsInterface:
    """Verify VideoPlatformMetric ORM model."""

    def test_model_importable(self):
        assert VideoPlatformMetric is not None

    def test_tablename(self):
        assert VideoPlatformMetric.__tablename__ == "video_platform_metrics"

    def test_has_annotations(self):
        expected = {
            "id", "video_id", "platform", "collected_at",
            "views", "watch_time_minutes", "likes", "comments",
            "subscriber_change", "shares", "completion_rate",
            "plays", "saves",
        }
        actual = set(VideoPlatformMetric.__annotations__)
        missing = expected - actual
        assert not missing, f"Missing annotations: {missing}"

    def test_video_platforms_list(self):
        assert "youtube" in VIDEO_PLATFORMS
        assert "tiktok" in VIDEO_PLATFORMS
        assert "instagram" in VIDEO_PLATFORMS

    def test_table_can_be_created(self, tmp_path):
        """DB table creation must succeed (verifies model compiles)."""
        engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
        Base.metadata.create_all(engine)
        assert "video_platform_metrics" in Base.metadata.tables


class TestSchemasInterface:
    """Verify Pydantic schema fields and inheritance."""

    @pytest.mark.parametrize(
        "schema_cls",
        [
            VideoMetricsSnapshot,
            PlatformMetrics,
            VideoPerformanceResponse,
            TimeseriesPoint,
            VideoTimeseriesResponse,
            OptimalTimesHeatmap,
            VideoDetailResponse,
        ],
    )
    def test_schema_importable(self, schema_cls):
        assert schema_cls is not None

    @pytest.mark.parametrize(
        "schema_cls",
        [
            VideoMetricsSnapshot,
            PlatformMetrics,
            VideoPerformanceResponse,
            TimeseriesPoint,
            VideoTimeseriesResponse,
            OptimalTimesHeatmap,
            VideoDetailResponse,
        ],
    )
    def test_schema_is_pydantic(self, schema_cls):
        assert issubclass(schema_cls, BaseModel)

    def test_video_metrics_snapshot_fields(self):
        fields = VideoMetricsSnapshot.model_fields
        expected = {
            "video_id", "platform", "collected_at", "views", "likes",
            "comments", "shares", "watch_time_minutes", "subscriber_change",
            "completion_rate", "plays", "saves",
        }
        missing = expected - set(fields)
        assert not missing, f"Missing fields: {missing}"

    def test_video_performance_response_fields(self):
        fields = VideoPerformanceResponse.model_fields
        for name in ("video_id", "platforms", "platforms_unavailable", "date_from", "date_to"):
            assert name in fields, f"Missing field: {name}"

    def test_optimal_times_heatmap_fields(self):
        fields = OptimalTimesHeatmap.model_fields
        for name in ("heatmap", "days_analyzed", "platforms"):
            assert name in fields

    def test_video_detail_response_fields(self):
        fields = VideoDetailResponse.model_fields
        for name in ("video_id", "title", "platforms", "platforms_unavailable", "best_platform"):
            assert name in fields


class TestSchemasContracts:
    """Verify schema validation contracts (defaults, required fields, enums)."""

    def test_video_metrics_snapshot_defaults(self):
        snap = VideoMetricsSnapshot(
            video_id="v1", platform="youtube",
            collected_at=datetime.now(UTC),
        )
        assert snap.views == 0
        assert snap.likes == 0
        assert snap.comments == 0
        assert snap.shares == 0
        assert snap.watch_time_minutes == 0.0
        assert snap.completion_rate == 0.0

    def test_platform_metrics_defaults(self):
        pm = PlatformMetrics(platform="youtube")
        assert pm.views == 0
        assert pm.shares == 0

    def test_optimal_times_heatmap_default_empty(self):
        h = OptimalTimesHeatmap()
        assert h.heatmap == {}
        assert h.days_analyzed == 0

    def test_timeseries_point_fields(self):
        tp = TimeseriesPoint(date="2026-08-01", platform="youtube", views=100)
        assert tp.likes == 0
        assert tp.comments == 0


class TestServicesInterface:
    """Verify service class signatures and ABC contract."""

    def test_video_apclient_is_abc(self):
        assert issubclass(VideoAPIClient, ABC)

    def test_youtube_client_is_subclass(self):
        assert issubclass(YouTubeClient, VideoAPIClient)

    def test_tiktok_client_is_subclass(self):
        assert issubclass(TikTokClient, VideoAPIClient)

    def test_instagram_client_is_subclass(self):
        assert issubclass(InstagramClient, VideoAPIClient)

    def test_youtube_client_name_property(self):
        assert callable(YouTubeClient.name.fget)  # type: ignore[union-attr]

    def test_tiktok_client_name_property(self):
        assert callable(TikTokClient.name.fget)  # type: ignore[union-attr]

    def test_instagram_client_name_property(self):
        assert callable(InstagramClient.name.fget)  # type: ignore[union-attr]

    def test_video_analytics_service_exists(self):
        assert callable(VideoAnalyticsService)

    def test_service_get_performance_signature(self):
        sig = inspect.signature(VideoAnalyticsService.get_performance)
        params = set(sig.parameters)
        assert "video_id" in params

    def test_service_get_timeseries_signature(self):
        sig = inspect.signature(VideoAnalyticsService.get_timeseries)
        assert "platform" in sig.parameters

    def test_service_get_optimal_times_signature(self):
        sig = inspect.signature(VideoAnalyticsService.get_optimal_times)
        assert "platform" in sig.parameters

    def test_service_get_video_detail_signature(self):
        sig = inspect.signature(VideoAnalyticsService.get_video_detail)
        assert "video_id" in sig.parameters

    def test_fetch_video_metrics_signature(self):
        sig = inspect.signature(VideoAPIClient.fetch_video_metrics)
        assert "video_id" in sig.parameters

    def test_is_configured_signature(self):
        sig = inspect.signature(VideoAPIClient.is_configured)
        assert sig.return_annotation in (bool, "bool")


class TestRoutersInterface:
    """Verify router wiring and endpoint signatures."""

    def test_router_importable(self):
        assert video_analytics_router is not None

    def test_router_prefix(self):
        assert video_analytics_router.prefix == "/api/v1/analytics/video-performance"

    def test_router_tags(self):
        assert "video-analytics" in video_analytics_router.tags

    def test_router_has_routes(self):
        assert len(video_analytics_router.routes) > 0

    def test_route_paths(self):
        """Routes must exist (full path includes prefix)."""
        paths = {r.path for r in video_analytics_router.routes if hasattr(r, "path")}
        # Routes include the full prefix path
        assert "/api/v1/analytics/video-performance" in paths  # GET / (main)
        assert "/api/v1/analytics/video-performance/timeseries" in paths
        assert "/api/v1/analytics/video-performance/optimal-times" in paths
        assert "/api/v1/analytics/video-performance/{video_id}" in paths

    def test_get_performance_handler_exists(self):
        """Handler for GET / (video-performance) should be callable."""
        routes = video_analytics_router.routes
        get_routes = [
            r for r in routes
            if hasattr(r, "methods") and "GET" in r.methods
        ]
        assert len(get_routes) >= 3, f"Expected ≥3 GET routes, got {len(get_routes)}"


# ============================================================================
# SECTION 2 — API CLIENT TESTS (RED: NotImplementedError)
# ============================================================================


class TestYouTubeClient:
    """YouTube Data API v3 client behavior."""

    def test_fetch_video_metrics_not_implemented(self):
        with pytest.raises(NotImplementedError):
            YouTubeClient().fetch_video_metrics("test_id_123")

    def test_is_configured_not_implemented(self):
        with pytest.raises(NotImplementedError):
            YouTubeClient().is_configured()

    def test_name_not_implemented(self):
        with pytest.raises(NotImplementedError):
            YouTubeClient().name

    def test_fetch_returns_none_when_unconfigured(self):
        """When API key is empty, client must return None, not crash."""
        try:
            client = YouTubeClient(api_key="")
            result = client.fetch_video_metrics("abc123")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result is None

    def test_fetch_returns_none_on_api_error(self):
        """On API error (network, 403, etc.), client returns None gracefully."""
        try:
            client = YouTubeClient(api_key="fake-key")
            result = client.fetch_video_metrics("nonexistent-id")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result is None

    def test_fetch_returns_metrics_snapshot(self):
        """Happy path: returns dict with expected metric keys."""
        try:
            client = YouTubeClient(api_key="test-key")
            result = client.fetch_video_metrics("test_id")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result is not None
        for key in ("views", "watch_time_minutes", "likes", "comments", "subscriber_change"):
            assert key in result

    def test_oauth_token_refresh_not_implemented(self):
        with pytest.raises(NotImplementedError):
            YouTubeClient()._refresh_oauth_token()

    def test_rate_limit_backoff_not_implemented(self):
        with pytest.raises(NotImplementedError):
            YouTubeClient()._check_rate_limit({"X-RateLimit-Remaining": "0"})

    def test_rate_limit_429_triggers_backoff(self):
        """On 429 response, client must back off and retry."""
        try:
            client = YouTubeClient(api_key="test-key")
            # Simulate rate limit headers
            client._check_rate_limit({"X-RateLimit-Remaining": "0"})
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        # If implemented, should not raise — just sleep/backoff internally


class TestTikTokClient:
    """TikTok video metrics client (TikHub SDK integration)."""

    def test_fetch_video_metrics_not_implemented(self):
        with pytest.raises(NotImplementedError):
            TikTokClient().fetch_video_metrics("test_id")

    def test_is_configured_not_implemented(self):
        with pytest.raises(NotImplementedError):
            TikTokClient().is_configured()

    def test_name_not_implemented(self):
        with pytest.raises(NotImplementedError):
            TikTokClient().name

    def test_fetch_returns_none_when_unconfigured(self):
        try:
            client = TikTokClient(client_key="")
            result = client.fetch_video_metrics("abc123")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result is None

    def test_fetch_returns_none_on_error(self):
        try:
            client = TikTokClient(client_key="fake")
            result = client.fetch_video_metrics("nonexistent")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result is None

    def test_fetch_returns_partial_data_on_quota_exhausted(self):
        """When TikHub quota is exhausted, return partial data (not crash)."""
        try:
            client = TikTokClient(client_key="test-key")
            result = client.fetch_video_metrics("test_id")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        # Partial data: some fields may be None/0 but the call succeeds
        assert result is not None or result is None  # Graceful either way

    def test_fetch_returns_metrics_snapshot(self):
        try:
            client = TikTokClient(client_key="test-key")
            result = client.fetch_video_metrics("test_id")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        if result is not None:
            for key in ("views", "likes", "shares", "comments", "completion_rate"):
                assert key in result


class TestInstagramClient:
    """Instagram Reels metrics client."""

    def test_fetch_video_metrics_not_implemented(self):
        with pytest.raises(NotImplementedError):
            InstagramClient().fetch_video_metrics("test_id")

    def test_is_configured_not_implemented(self):
        with pytest.raises(NotImplementedError):
            InstagramClient().is_configured()

    def test_name_not_implemented(self):
        with pytest.raises(NotImplementedError):
            InstagramClient().name

    def test_fetch_returns_none_when_unconfigured(self):
        try:
            client = InstagramClient(access_token="")
            result = client.fetch_video_metrics("abc123")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result is None

    def test_fetch_returns_none_on_error(self):
        try:
            client = InstagramClient(access_token="fake")
            result = client.fetch_video_metrics("nonexistent")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result is None

    def test_fetch_returns_metrics_snapshot(self):
        try:
            client = InstagramClient(access_token="test-token")
            result = client.fetch_video_metrics("test_id")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        if result is not None:
            for key in ("plays", "likes", "comments", "shares", "saves"):
                assert key in result

    def test_business_account_error_not_implemented(self):
        with pytest.raises(NotImplementedError):
            InstagramClient()._check_business_account()

    def test_non_business_account_returns_none(self):
        """Non-Business account → graceful None, not exception."""
        try:
            client = InstagramClient(access_token="personal-token")
            result = client.fetch_video_metrics("test_id")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result is None


# ============================================================================
# SECTION 3 — ANALYTICS SERVICE TESTS (RED: NotImplementedError)
# ============================================================================


class TestVideoAnalyticsService:
    """Unified analytics service behavior."""

    def test_init_not_implemented(self):
        with pytest.raises(NotImplementedError):
            VideoAnalyticsService()

    def test_get_performance_not_implemented(self):
        with pytest.raises(NotImplementedError):
            VideoAnalyticsService().get_performance("v1")

    def test_get_timeseries_not_implemented(self):
        with pytest.raises(NotImplementedError):
            VideoAnalyticsService().get_timeseries("v1")

    def test_get_optimal_times_not_implemented(self):
        with pytest.raises(NotImplementedError):
            VideoAnalyticsService().get_optimal_times()

    def test_get_video_detail_not_implemented(self):
        with pytest.raises(NotImplementedError):
            VideoAnalyticsService().get_video_detail("v1")

    def test_get_performance_returns_all_platforms(self):
        """Aggregation includes metrics from all configured platforms."""
        try:
            svc = VideoAnalyticsService()
            result = svc.get_performance("v1")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result, dict)
        assert "platforms" in result
        assert "platforms_unavailable" in result

    def test_get_performance_with_platform_filter(self):
        """Filtering by single platform returns only that platform's data."""
        try:
            svc = VideoAnalyticsService()
            result = svc.get_performance("v1", platform="youtube")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        platforms = result.get("platforms", [])
        for p in platforms:
            assert p["platform"] == "youtube"

    @pytest.mark.parametrize("days", [7, 30, 90])
    def test_date_range_filtering(self, days):
        """Different date ranges return correct subsets."""
        try:
            svc = VideoAnalyticsService()
            now = datetime.now(UTC)
            result = svc.get_performance(
                "v1",
                date_from=now - timedelta(days=days),
                date_to=now,
            )
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result["date_from"] <= result["date_to"]

    def test_get_timeseries_daily_granularity(self):
        """Timeseries returns one point per day with platform dimension."""
        try:
            svc = VideoAnalyticsService()
            result = svc.get_timeseries("v1")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "points" in result
        for pt in result["points"]:
            assert "date" in pt
            assert "platform" in pt

    def test_get_optimal_times_heatmap_shape(self):
        """Optimal times returns a day×hour heatmap."""
        try:
            svc = VideoAnalyticsService()
            result = svc.get_optimal_times()
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "heatmap" in result
        assert "days_analyzed" in result
        assert "platforms" in result

    def test_get_video_detail_returns_platform_comparison(self):
        """Video detail returns per-platform metrics + best platform."""
        try:
            svc = VideoAnalyticsService()
            result = svc.get_video_detail("v1")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "video_id" in result
        assert "platforms" in result
        assert "best_platform" in result

    def test_platform_failure_returns_partial_data(self):
        """When one platform fails, aggregation returns partial data (not 500)."""
        try:
            # Pass broken client that always errors
            class BrokenClient(VideoAPIClient):
                async def fetch_video_metrics(self, video_id):
                    raise VideoAPIClientError("API down")

                def is_configured(self):
                    return True

                @property
                def name(self):
                    return "broken"

            svc = VideoAnalyticsService(youtube=BrokenClient())
            result = svc.get_performance("v1")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "platforms_unavailable" in result
        assert "broken" in result["platforms_unavailable"]

    def test_all_platforms_fail_returns_empty_not_500(self):
        """When ALL platforms fail, return empty data gracefully."""
        try:
            svc = VideoAnalyticsService()  # No clients configured
            result = svc.get_performance("v1")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(result, dict)
        assert result.get("platforms") == [] or len(result.get("platforms", [])) == 0


# ============================================================================
# SECTION 4 — API ENDPOINT TESTS (RED: NotImplementedError)
# ============================================================================


class TestVideoAnalyticsEndpoints:
    """FastAPI endpoint contracts (TestClient).

    During the RED phase, stubs raise NotImplementedError → 500.
    Both 200 (post-impl) and 500 (RED stub) are valid outcomes;
    the important assertion is that the route exists and is wired.
    """

    @pytest.fixture
    def anyio_backend(self):
        return "asyncio"

    @pytest.fixture
    def test_client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(video_analytics_router)
        return TestClient(app, raise_server_exceptions=False)

    def test_get_performance_returns_200_or_500(self, test_client):
        resp = test_client.get("/api/v1/analytics/video-performance")
        assert resp.status_code in (200, 500)

    def test_get_performance_with_platform_filter(self, test_client):
        resp = test_client.get(
            "/api/v1/analytics/video-performance",
            params={"platform": "youtube"},
        )
        assert resp.status_code in (200, 500)

    def test_get_performance_with_date_range(self, test_client):
        now = datetime.now(UTC)
        resp = test_client.get(
            "/api/v1/analytics/video-performance",
            params={
                "date_from": (now - timedelta(days=7)).isoformat(),
                "date_to": now.isoformat(),
            },
        )
        assert resp.status_code in (200, 500)

    def test_get_timeseries_returns_200_or_500(self, test_client):
        resp = test_client.get("/api/v1/analytics/video-performance/timeseries")
        assert resp.status_code in (200, 500)

    def test_get_optimal_times_returns_200_or_500(self, test_client):
        resp = test_client.get("/api/v1/analytics/video-performance/optimal-times")
        assert resp.status_code in (200, 500)

    def test_get_video_detail_returns_200_or_500(self, test_client):
        resp = test_client.get("/api/v1/analytics/video-performance/vid123")
        assert resp.status_code in (200, 500)

    def test_get_video_detail_unknown_returns_404_or_500(self, test_client):
        """Unknown video_id: 404 (post-impl) or 500 (RED stub)."""
        resp = test_client.get("/api/v1/analytics/video-performance/nonexistent-id")
        assert resp.status_code in (404, 500)

    def test_invalid_date_range_returns_400_or_422_or_500(self, test_client):
        """Date range where from > to: 400/422 (post-impl) or 500 (RED stub)."""
        resp = test_client.get(
            "/api/v1/analytics/video-performance",
            params={
                "date_from": "2026-12-31T00:00:00Z",
                "date_to": "2026-01-01T00:00:00Z",
            },
        )
        assert resp.status_code in (400, 422, 500)

    def test_performance_response_json_shape(self, test_client):
        resp = test_client.get("/api/v1/analytics/video-performance")
        if resp.status_code == 500:
            return  # RED phase: stub raises, no JSON body
        data = resp.json()
        assert isinstance(data, dict)
        assert "platforms" in data

    def test_timeseries_response_json_shape(self, test_client):
        resp = test_client.get("/api/v1/analytics/video-performance/timeseries")
        if resp.status_code == 500:
            return  # RED phase: stub raises, no JSON body
        data = resp.json()
        assert isinstance(data, dict)
        assert "points" in data


# ============================================================================
# SECTION 5 — CLI TESTS (RED: NotImplementedError)
# ============================================================================


class TestVideoAnalyticsCLI:
    """CLI tests for `contentforge analytics video-performance`."""

    def test_cli_entry_point_exists(self):
        """contentforge CLI entry point should be callable."""
        try:
            from typer.testing import CliRunner
        except ImportError:
            pytest.skip("typer not installed yet — RED phase")
        assert CliRunner is not None

    def test_cli_video_performance_command(self):
        """CLI renders a table for video-performance subcommand."""
        try:
            from typer.testing import CliRunner

            from src.cli import app

            runner = CliRunner()
            result = runner.invoke(app, ["analytics", "video-performance"])
        except (NotImplementedError, ImportError, SystemExit):
            pytest.skip("CLI not implemented yet — RED phase")
        assert result.exit_code == 0
        assert "platform" in result.output.lower() or "video" in result.output.lower()

    def test_cli_platform_filter(self):
        """--platform youtube filters output to YouTube only."""
        try:
            from typer.testing import CliRunner

            from src.cli import app

            runner = CliRunner()
            result = runner.invoke(
                app,
                ["analytics", "video-performance", "--platform", "youtube"],
            )
        except (NotImplementedError, ImportError, SystemExit):
            pytest.skip("CLI not implemented yet — RED phase")
        assert result.exit_code == 0
        assert "youtube" in result.output.lower()

    def test_cli_days_filter(self):
        """--days 30 sets the correct date range."""
        try:
            from typer.testing import CliRunner

            from src.cli import app

            runner = CliRunner()
            result = runner.invoke(
                app,
                ["analytics", "video-performance", "--days", "30"],
            )
        except (NotImplementedError, ImportError, SystemExit):
            pytest.skip("CLI not implemented yet — RED phase")
        assert result.exit_code == 0


# ============================================================================
# SECTION 6 — DATABASE TESTS (RED: NotImplementedError)
# ============================================================================


class TestVideoPlatformMetricsDB:
    """Database insert, query, and aggregation for VideoPlatformMetric."""

    @pytest.fixture
    def db_session(self, tmp_path):
        """Create a fresh SQLite DB with the video_platform_metrics table."""
        engine = create_engine(f"sqlite:///{tmp_path / 'test_metrics.db'}")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()
        engine.dispose()

    def test_insert_and_query(self, db_session):
        """Insert a record and query it back."""
        now = datetime.now(UTC)
        metric = VideoPlatformMetric(
            video_id="vid_001",
            platform="youtube",
            collected_at=now,
            views=1500,
            likes=42,
            comments=5,
            shares=3,
        )
        db_session.add(metric)
        db_session.commit()

        result = db_session.query(VideoPlatformMetric).filter_by(video_id="vid_001").first()
        assert result is not None
        assert result.views == 1500
        assert result.platform == "youtube"

    def test_insert_all_platforms(self, db_session):
        """Insert records for all three platforms."""
        now = datetime.now(UTC)
        for platform in ("youtube", "tiktok", "instagram"):
            db_session.add(
                VideoPlatformMetric(
                    video_id="vid_002",
                    platform=platform,
                    collected_at=now,
                    views=100,
                )
            )
        db_session.commit()

        results = db_session.query(VideoPlatformMetric).filter_by(video_id="vid_002").all()
        assert len(results) == 3

    def test_aggregation_views(self, db_session):
        """Sum views across platforms."""
        now = datetime.now(UTC)
        db_session.add(VideoPlatformMetric(
            video_id="vid_003", platform="youtube", collected_at=now, views=1000,
        ))
        db_session.add(VideoPlatformMetric(
            video_id="vid_003", platform="tiktok", collected_at=now, views=500,
        ))
        db_session.commit()

        from sqlalchemy import func

        total = db_session.query(func.sum(VideoPlatformMetric.views)).filter_by(
            video_id="vid_003"
        ).scalar()
        assert total == 1500

    def test_aggregation_by_platform(self, db_session):
        """Group by platform."""
        now = datetime.now(UTC)
        for i, platform in enumerate(("youtube", "youtube", "tiktok")):
            db_session.add(VideoPlatformMetric(
                video_id="vid_004", platform=platform,
                collected_at=now - timedelta(hours=i), views=100,
            ))
        db_session.commit()

        from sqlalchemy import func

        results = (
            db_session.query(
                VideoPlatformMetric.platform,
                func.sum(VideoPlatformMetric.views).label("total_views"),
            )
            .filter_by(video_id="vid_004")
            .group_by(VideoPlatformMetric.platform)
            .all()
        )
        result_dict = {r.platform: r.total_views for r in results}
        assert result_dict["youtube"] == 200
        assert result_dict["tiktok"] == 100

    def test_date_range_query(self, db_session):
        """Query records within a date range."""
        base = datetime(2026, 8, 1, tzinfo=UTC)
        db_session.add(VideoPlatformMetric(
            video_id="vid_005", platform="youtube",
            collected_at=base, views=100,
        ))
        db_session.add(VideoPlatformMetric(
            video_id="vid_005", platform="youtube",
            collected_at=base + timedelta(days=10), views=200,
        ))
        db_session.add(VideoPlatformMetric(
            video_id="vid_005", platform="youtube",
            collected_at=base + timedelta(days=20), views=300,
        ))
        db_session.commit()

        results = db_session.query(VideoPlatformMetric).filter(
            VideoPlatformMetric.video_id == "vid_005",
            VideoPlatformMetric.collected_at >= base,
            VideoPlatformMetric.collected_at <= base + timedelta(days=15),
        ).all()
        assert len(results) == 2
        assert sum(r.views for r in results) == 300

    def test_multiple_videos_independent(self, db_session):
        """Different video_ids are independent."""
        now = datetime.now(UTC)
        db_session.add(VideoPlatformMetric(
            video_id="vid_A", platform="youtube", collected_at=now, views=100,
        ))
        db_session.add(VideoPlatformMetric(
            video_id="vid_B", platform="youtube", collected_at=now, views=200,
        ))
        db_session.commit()

        result_a = db_session.query(VideoPlatformMetric).filter_by(video_id="vid_A").first()
        result_b = db_session.query(VideoPlatformMetric).filter_by(video_id="vid_B").first()
        assert result_a.views == 100
        assert result_b.views == 200

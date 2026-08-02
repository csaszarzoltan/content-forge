"""Interface + behavioral tests for M5 — AiVisibilityService.

Interface tests verify the class exists with the six public async methods and
exact signatures from brief §5 M5 — these PASS immediately. Behavioral tests
verify persistence, upsert aggregation, trend rollups, and query contracts;
against the stubs they FAIL with ``NotImplementedError`` (TDD RED phase) and
go green after the developer implements the service.
"""

from __future__ import annotations

import inspect
from datetime import date

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.quick]

from src.ai_visibility.providers import EngineVisibilityResult
from src.ai_visibility.schemas import (
    AIVisibilityTrendsResponse,
    ContentVisibilityResponse,
)
from src.ai_visibility.service import AiVisibilityService

EXPECTED_METHODS = [
    "record_mentions",
    "record_referral",
    "compute_engine_metrics",
    "rebuild_trend_aggregates",
    "get_content_visibility",
    "get_trends",
]


def _sample_results(engine: str = "chatgpt", cited: bool = False) -> list[EngineVisibilityResult]:
    return [
        EngineVisibilityResult(
            engine=engine,
            query=f"q{i}",
            mentioned=True,
            cited=cited,
            cited_url="https://acme.com/x" if cited else None,
            snippet="snippet",
            sentiment="neutral",
        )
        for i in range(3)
    ]


# ============================================================================
# SECTION 1 — INTERFACE TESTS (PASS immediately)
# ============================================================================


class TestServiceInterface:
    """Verify the M5 public surface."""

    def test_service_class_exists(self):
        assert AiVisibilityService is not None

    def test_public_methods_present(self):
        for name in EXPECTED_METHODS:
            assert callable(getattr(AiVisibilityService, name))

    def test_record_mentions_signature(self):
        sig = inspect.signature(AiVisibilityService.record_mentions)
        assert tuple(sig.parameters) == (
            "self", "db", "generation_id", "engine", "results",
        )

    def test_record_referral_signature(self):
        sig = inspect.signature(AiVisibilityService.record_referral)
        params = sig.parameters
        assert tuple(params) == (
            "self", "db", "generation_id", "engine", "referrer_url",
            "landing_path", "converted", "conversion_value", "occurred_at",
        )
        assert params["landing_path"].default == "/"
        assert params["converted"].default is False
        assert params["conversion_value"].default == 0.0
        assert params["occurred_at"].default is None

    def test_compute_engine_metrics_signature(self):
        sig = inspect.signature(AiVisibilityService.compute_engine_metrics)
        assert tuple(sig.parameters) == (
            "self", "db", "generation_id", "engine", "metric_date",
        )
        assert sig.parameters["metric_date"].default is None

    def test_rebuild_trend_aggregates_signature(self):
        sig = inspect.signature(AiVisibilityService.rebuild_trend_aggregates)
        assert tuple(sig.parameters) == ("self", "db", "metric_date")
        assert sig.parameters["metric_date"].default is None

    def test_get_content_visibility_signature(self):
        sig = inspect.signature(AiVisibilityService.get_content_visibility)
        assert tuple(sig.parameters) == ("self", "db", "content_id", "days")
        assert sig.parameters["days"].default == 30

    def test_get_trends_signature(self):
        sig = inspect.signature(AiVisibilityService.get_trends)
        assert tuple(sig.parameters) == ("self", "db", "days", "engine", "metric")
        assert sig.parameters["days"].default == 30
        assert sig.parameters["engine"].default is None
        assert sig.parameters["metric"].default is None


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (FAIL with NotImplementedError during RED)
# ============================================================================


class TestRecordMentionsBehavioral:
    """M5 — record_mentions persists raw mention rows."""

    async def test_records_mentions_returns_count(self, db_session):
        from tests.ai_visibility_test_utils import seed_generation

        await seed_generation(db_session, "gen_m")
        svc = AiVisibilityService()
        rows = await svc.record_mentions(db_session, "gen_m", "chatgpt",
                                         _sample_results())
        assert rows == 3

    async def test_unknown_generation_raises_value_error(self, db_session):
        svc = AiVisibilityService()
        with pytest.raises(ValueError):
            await svc.record_mentions(db_session, "missing", "chatgpt",
                                      _sample_results())

    async def test_unknown_engine_raises_value_error(self, db_session):
        from tests.ai_visibility_test_utils import seed_generation

        await seed_generation(db_session, "gen_e")
        svc = AiVisibilityService()
        with pytest.raises(ValueError):
            await svc.record_mentions(db_session, "gen_e", "claude",
                                      _sample_results(engine="claude"))


class TestRecordReferralBehavioral:
    """M5 — record_referral persists one referral row."""

    async def test_records_referral_returns_id(self, db_session):
        from tests.ai_visibility_test_utils import seed_generation

        await seed_generation(db_session, "gen_r")
        svc = AiVisibilityService()
        referral_id = await svc.record_referral(
            db_session, "gen_r", "chatgpt", "https://chatgpt.com/c/1"
        )
        assert isinstance(referral_id, str) and referral_id

    async def test_records_referral_with_conversion(self, db_session):
        from tests.ai_visibility_test_utils import seed_generation

        await seed_generation(db_session, "gen_r2")
        svc = AiVisibilityService()
        referral_id = await svc.record_referral(
            db_session, "gen_r2", "perplexity",
            "https://www.perplexity.ai/s/1", landing_path="/pricing",
            converted=True, conversion_value=49.0,
        )
        assert referral_id


class TestEngineMetricsBehavioral:
    """M5 — compute_engine_metrics aggregates + upserts per (gen, engine, day)."""

    async def test_compute_engine_metrics(self, db_session):
        from tests.ai_visibility_test_utils import seed_generation

        await seed_generation(db_session, "gen_cm")
        svc = AiVisibilityService()
        await svc.record_mentions(db_session, "gen_cm", "gemini",
                                  _sample_results(cited=True))
        metrics = await svc.compute_engine_metrics(
            db_session, "gen_cm", "gemini", metric_date=date(2026, 8, 1)
        )
        assert metrics.generation_id == "gen_cm"
        assert metrics.engine == "gemini"
        assert metrics.mentions == 3
        assert metrics.citations == 3
        assert metrics.citation_rate == pytest.approx(1.0)
        assert metrics.samples == 3

    async def test_compute_engine_metrics_upserts(self, db_session):
        """Calling twice for the same (gen, engine, day) upserts, no dupes."""
        from sqlalchemy import func, select

        from src.ai_visibility.models import AIEngineMetrics
        from tests.ai_visibility_test_utils import seed_generation

        await seed_generation(db_session, "gen_up")
        svc = AiVisibilityService()
        await svc.record_mentions(db_session, "gen_up", "chatgpt",
                                  _sample_results())
        await svc.compute_engine_metrics(db_session, "gen_up", "chatgpt",
                                         metric_date=date(2026, 8, 1))
        await svc.compute_engine_metrics(db_session, "gen_up", "chatgpt",
                                         metric_date=date(2026, 8, 1))
        count = (
            await db_session.execute(
                select(func.count()).select_from(AIEngineMetrics)
            )
        ).scalar_one()
        assert count == 1


class TestTrendAggregatesBehavioral:
    """M5 — rebuild_trend_aggregates rolls up cross-content daily values."""

    async def test_rebuild_trend_aggregates(self, db_session):
        from tests.ai_visibility_test_utils import seed_generation

        await seed_generation(db_session, "gen_t")
        svc = AiVisibilityService()
        await svc.record_mentions(db_session, "gen_t", "chatgpt",
                                  _sample_results(cited=True))
        await svc.compute_engine_metrics(db_session, "gen_t", "chatgpt",
                                         metric_date=date(2026, 8, 1))
        rows = await svc.rebuild_trend_aggregates(
            db_session, metric_date=date(2026, 8, 1)
        )
        assert rows >= 1


class TestGetContentVisibilityBehavioral:
    """M5 — per-content snapshot contract (404 via ValueError)."""

    async def test_unknown_content_raises_value_error(self, db_session):
        svc = AiVisibilityService()
        with pytest.raises(ValueError):
            await svc.get_content_visibility(db_session, "missing", days=30)

    async def test_empty_content_zero_filled_four_engines(self, db_session):
        from tests.ai_visibility_test_utils import seed_generation

        await seed_generation(db_session, "gen_v")
        svc = AiVisibilityService()
        resp = await svc.get_content_visibility(db_session, "gen_v", days=30)
        assert isinstance(resp, ContentVisibilityResponse)
        assert resp.content_id == "gen_v"
        assert [e.engine for e in resp.engines] == [
            "chatgpt", "perplexity", "gemini", "google_ai_overviews",
        ]
        assert all(e.citation_rate == 0.0 for e in resp.engines)


class TestGetTrendsBehavioral:
    """M5 — Chart.js trend contract (7d/30d/90d; ValueError on invalid)."""

    @pytest.mark.parametrize("days, period", [
        (7, "7d"), (30, "30d"), (90, "90d"),
    ])
    async def test_trends_periods(self, db_session, days, period):
        svc = AiVisibilityService()
        resp = await svc.get_trends(db_session, days=days)
        assert isinstance(resp, AIVisibilityTrendsResponse)
        assert resp.days == days
        assert resp.period == period

    async def test_invalid_days_raises_value_error(self, db_session):
        svc = AiVisibilityService()
        with pytest.raises(ValueError):
            await svc.get_trends(db_session, days=5)

    async def test_invalid_engine_raises_value_error(self, db_session):
        svc = AiVisibilityService()
        with pytest.raises(ValueError):
            await svc.get_trends(db_session, days=30, engine="claude")

    async def test_invalid_metric_raises_value_error(self, db_session):
        svc = AiVisibilityService()
        with pytest.raises(ValueError):
            await svc.get_trends(db_session, days=30, metric="bogus")

    async def test_trends_totals_shape(self, db_session):
        svc = AiVisibilityService()
        resp = await svc.get_trends(db_session, days=30)
        assert set(resp.totals) == {
            "citation_rate", "share_of_voice", "mention_rate",
            "ai_referral_traffic",
        }

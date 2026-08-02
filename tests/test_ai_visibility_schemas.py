"""Contract tests for M2 — Pydantic schemas (analysis brief §5 M2).

The schemas are pure declarative wire contracts with zero behavior to
implement, so they are shipped implemented in the pre-dev stub. These tests
pin the field names, defaults, types, and validation rules byte-for-byte —
ALL PASS immediately and stay green after the developer's work.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.quick]

from pydantic import BaseModel, ValidationError

from src.ai_visibility.schemas import (
    AIVisibilityTrendsResponse,
    ContentVisibilityResponse,
    EngineSentiment,
    EngineVisibilityMetrics,
    PollResult,
    ReferralIngestRequest,
    ReferralIngestResponse,
    TrendSeries,
    VisibilitySummary,
    VisibilityTimePoint,
)

SCHEMAS = [
    EngineSentiment,
    EngineVisibilityMetrics,
    VisibilitySummary,
    VisibilityTimePoint,
    ContentVisibilityResponse,
    TrendSeries,
    AIVisibilityTrendsResponse,
    ReferralIngestRequest,
    ReferralIngestResponse,
    PollResult,
]


# ============================================================================
# SECTION 1 — INTERFACE / CONTRACT TESTS (PASS immediately)
# ============================================================================


class TestSchemasContract:
    """Verify every schema is a Pydantic v2 model with the expected fields."""

    def test_module_importable(self):
        assert all(s is not None for s in SCHEMAS)

    @pytest.mark.parametrize("schema", SCHEMAS)
    def test_is_pydantic_model(self, schema):
        assert issubclass(schema, BaseModel)

    def test_engine_sentiment_fields(self):
        s = EngineSentiment()
        assert s.positive == 0 and s.neutral == 0 and s.negative == 0
        assert s.avg == 0.0

    def test_engine_visibility_metrics_fields(self):
        m = EngineVisibilityMetrics(engine="chatgpt")
        assert m.engine == "chatgpt"
        assert m.mentions == 0 and m.citations == 0
        assert m.citation_rate == 0.0 and m.share_of_voice == 0.0
        assert m.mention_rate == 0.0
        assert m.sentiment == EngineSentiment()
        assert m.ai_referral_traffic == 0
        assert m.ai_referral_conversions == 0
        assert m.ai_referral_conversion_rate == 0.0

    def test_visibility_summary_fields(self):
        s = VisibilitySummary()
        assert s.total_mentions == 0 and s.total_citations == 0
        assert s.overall_citation_rate == 0.0
        assert s.avg_share_of_voice == 0.0 and s.avg_mention_rate == 0.0
        assert s.ai_referral_traffic == 0 and s.ai_referral_conversions == 0
        assert s.ai_referral_conversion_rate == 0.0

    def test_visibility_time_point_fields(self):
        t = VisibilityTimePoint(date="2026-08-01")
        assert t.date == "2026-08-01"
        assert t.citation_rate == 0.0 and t.share_of_voice == 0.0
        assert t.mention_rate == 0.0 and t.ai_referral_traffic == 0

    def test_content_visibility_response_required(self):
        """content_id/date_from/date_to/summary are required; lists default
        empty (brief §5 M2: summary has no default)."""
        with pytest.raises(ValidationError):
            ContentVisibilityResponse()
        resp = ContentVisibilityResponse(
            content_id="g1", date_from="2026-07-01", date_to="2026-08-01",
            summary=VisibilitySummary(),
        )
        assert resp.topic == "" and resp.content_type == ""
        assert resp.engines == [] and resp.time_series == []

    def test_trend_series_fields(self):
        t = TrendSeries(engine="perplexity", metric="citation_rate")
        assert t.data == []

    def test_trends_response_fields(self):
        r = AIVisibilityTrendsResponse(
            period="30d", days=30, date_from="2026-07-03", date_to="2026-08-02"
        )
        assert r.dates == [] and r.series == [] and r.totals == {}

    def test_referral_ingest_request_defaults(self):
        r = ReferralIngestRequest(
            generation_id="g1", engine="gemini", referrer_url="https://gemini.example.com/x"
        )
        assert r.landing_path == "/"
        assert r.converted is False
        assert r.conversion_value == 0.0
        assert r.occurred_at is None

    def test_referral_ingest_response(self):
        r = ReferralIngestResponse(status="ok", referral_id="ref_1")
        assert r.status == "ok" and r.referral_id == "ref_1"

    def test_poll_result_defaults(self):
        from datetime import UTC, datetime

        p = PollResult(started_at=datetime.now(UTC), finished_at=datetime.now(UTC))
        assert p.engines_polled == [] and p.queries_run == 0
        assert p.mentions_recorded == 0 and p.errors == []


# ============================================================================
# SECTION 2 — VALIDATION TESTS (PASS immediately: pure Pydantic behavior)
# ============================================================================


class TestSchemasValidation:
    """Wire-contract validation rules (brief §5 M2)."""

    def test_referral_bad_engine_rejected(self):
        """engine outside the four AI_ENGINES -> ValidationError (422)."""
        with pytest.raises(ValidationError):
            ReferralIngestRequest(
                generation_id="g1", engine="claude", referrer_url="https://x.com/a"
            )

    def test_referral_negative_conversion_value_rejected(self):
        """conversion_value must be >= 0.0 (Field ge=0.0)."""
        with pytest.raises(ValidationError):
            ReferralIngestRequest(
                generation_id="g1", engine="chatgpt",
                referrer_url="https://chatgpt.com/c/1", conversion_value=-1.0,
            )

    def test_referral_missing_url_rejected(self):
        """referrer_url is required (max_length=512)."""
        with pytest.raises(ValidationError):
            ReferralIngestRequest(generation_id="g1", engine="chatgpt")

    def test_content_visibility_response_serializes(self):
        """Response model round-trips to the wire shape (JSON keys)."""
        from src.ai_visibility.schemas import EngineVisibilityMetrics

        resp = ContentVisibilityResponse(
            content_id="g1", date_from="2026-07-01", date_to="2026-08-01",
            summary=VisibilitySummary(),
            engines=[EngineVisibilityMetrics(engine="chatgpt")],
        )
        data = resp.model_dump()
        assert set(data) == {
            "content_id", "topic", "content_type", "date_from", "date_to",
            "summary", "engines", "time_series",
        }
        assert data["engines"][0]["engine"] == "chatgpt"

    def test_trends_response_serializes_chartjs_shape(self):
        """The trends feed exposes Chart.js labels + datasets keys."""
        resp = AIVisibilityTrendsResponse(
            period="30d", days=30, date_from="2026-07-03", date_to="2026-08-02",
            dates=["2026-07-04"], series=[TrendSeries(engine="chatgpt",
                                                      metric="citation_rate",
                                                      data=[0.12])],
            totals={"citation_rate": 0.12},
        )
        data = resp.model_dump()
        assert data["dates"] == ["2026-07-04"]
        assert data["series"][0]["data"] == [0.12]
        assert data["totals"]["citation_rate"] == 0.12

"""Interface + behavioral tests for M1 — ai_visibility ORM models & constants.

Interface tests verify imports, ``__tablename__`` values, expected column
names (via ``cls.__annotations__``, which holds for both the plain stub
classes and the real ``Mapped[...]`` declarative models the developer writes)
and the module constants — these PASS immediately.

Behavioral tests verify schema behavior (construction, unique constraints,
FK cascade). Against the stubs they FAIL with ``NotImplementedError`` (TDD RED
phase) and go green after the developer implements the real ORM models.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.quick]

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.ai_visibility.models import (
    AI_ENGINES,
    AI_ENGINE_REFERRER_DOMAINS,
    AI_METRICS,
    AI_SENTIMENTS,
    AI_TREND_PERIODS,
    AIEngineMetrics,
    AIRawMention,
    AIReferralTraffic,
    AITrendAggregate,
)
from tests.analytics_test_utils import seed_generation

# (class, expected __tablename__, expected column names)
MODEL_TABLES = [
    (AIRawMention, "ai_raw_mentions"),
    (AIEngineMetrics, "ai_engine_metrics"),
    (AIReferralTraffic, "ai_referral_traffic"),
    (AITrendAggregate, "ai_trend_aggregates"),
]

MODEL_COLUMNS = {
    AIRawMention: {
        "id", "generation_id", "engine", "query", "brand_or_topic",
        "mention_type", "cited_url", "snippet", "sentiment",
        "sentiment_score", "mentioned_at", "raw_payload",
    },
    AIEngineMetrics: {
        "id", "generation_id", "engine", "metric_date", "mentions",
        "citations", "citation_rate", "mention_rate", "share_of_voice",
        "sentiment_positive", "sentiment_neutral", "sentiment_negative",
        "sentiment_avg", "samples",
    },
    AIReferralTraffic: {
        "id", "generation_id", "engine", "referrer_url", "landing_path",
        "converted", "conversion_value", "referred_at",
    },
    AITrendAggregate: {
        "id", "metric_date", "engine", "metric", "value", "sample_size",
    },
}


# ============================================================================
# SECTION 1 — INTERFACE TESTS (PASS immediately)
# ============================================================================


class TestModelsInterface:
    """Verify imports, table names, columns, and constants exist."""

    def test_module_importable(self):
        """All four model classes and constants import cleanly."""
        assert all(cls is not None for cls in (AIRawMention, AIEngineMetrics,
                                               AIReferralTraffic, AITrendAggregate))

    @pytest.mark.parametrize("model_cls, expected", MODEL_TABLES)
    def test_tablename(self, model_cls, expected):
        """Each model declares the exact table name from brief §4."""
        assert model_cls.__tablename__ == expected

    @pytest.mark.parametrize("model_cls", list(MODEL_COLUMNS))
    def test_column_names_present(self, model_cls):
        """Expected columns are declared as class annotations."""
        expected = MODEL_COLUMNS[model_cls]
        assert expected <= set(model_cls.__annotations__)

    def test_ai_engines_constant(self):
        """AI_ENGINES lists the four canonical engines in order."""
        assert AI_ENGINES == ("chatgpt", "perplexity", "gemini", "google_ai_overviews")

    def test_engine_referrer_domains(self):
        """AI_ENGINE_REFERRER_DOMAINS maps every engine to its domain."""
        assert AI_ENGINE_REFERRER_DOMAINS == {
            "chatgpt": "chatgpt.com",
            "perplexity": "perplexity.ai",
            "gemini": "gemini.google.com",
            "google_ai_overviews": "google.com",
        }

    def test_ai_metrics_constant(self):
        """AI_METRICS lists the four tracked metrics in order."""
        assert AI_METRICS == (
            "citation_rate", "share_of_voice", "mention_rate", "ai_referral_traffic",
        )

    def test_ai_sentiments_constant(self):
        """AI_SENTIMENTS lists the four sentiment labels."""
        assert AI_SENTIMENTS == ("positive", "neutral", "negative", "unknown")

    def test_ai_trend_periods_constant(self):
        """AI_TREND_PERIODS accepts exactly 7/30/90 day windows."""
        assert AI_TREND_PERIODS == {7: 7, 30: 30, 90: 90}


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (FAIL with NotImplementedError during RED)
# ============================================================================


class TestModelsBehavioral:
    """Verify schema behavior once the real ORM models land."""

    @pytest.mark.parametrize(
        "model_cls, kwargs, attr, expected",
        [
            (AIRawMention, {"generation_id": "g1", "engine": "chatgpt",
                            "query": "q", "mention_type": "citation",
                            "sentiment": "positive"},
             "engine", "chatgpt"),
            (AIEngineMetrics, {"generation_id": "g1", "engine": "perplexity",
                               "metric_date": None, "mentions": 3,
                               "citations": 2, "citation_rate": 0.5},
             "citation_rate", 0.5),
            (AIReferralTraffic, {"generation_id": "g1", "engine": "gemini",
                                 "referrer_url": "https://gemini.example.com/",
                                 "converted": True, "conversion_value": 12.5},
             "converted", True),
            (AITrendAggregate, {"metric_date": None, "engine": "chatgpt",
                                "metric": "citation_rate", "value": 0.42,
                                "sample_size": 3},
             "value", 0.42),
        ],
    )
    def test_construction_sets_fields(self, model_cls, kwargs, attr, expected):
        """Constructing a model with required fields stores the values."""
        instance = model_cls(**kwargs)
        assert getattr(instance, attr) == expected

    async def test_engine_metrics_unique_per_day(self, db_session):
        """(generation_id, engine, metric_date) is unique — second insert
        violates the constraint (brief §4.2)."""
        await seed_generation(db_session, "gen_u")
        first = AIEngineMetrics(
            generation_id="gen_u", engine="chatgpt", metric_date=None,
            mentions=1, citations=0,
        )
        db_session.add(first)
        await db_session.commit()
        duplicate = AIEngineMetrics(
            generation_id="gen_u", engine="chatgpt", metric_date=None,
            mentions=2, citations=1,
        )
        db_session.add(duplicate)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_trend_aggregate_unique_per_day(self, db_session):
        """(metric_date, engine, metric) is unique — second insert violates
        the constraint (brief §4.4)."""
        first = AITrendAggregate(
            metric_date=None, engine="chatgpt", metric="citation_rate",
            value=0.1, sample_size=1,
        )
        db_session.add(first)
        await db_session.commit()
        duplicate = AITrendAggregate(
            metric_date=None, engine="chatgpt", metric="citation_rate",
            value=0.9, sample_size=2,
        )
        db_session.add(duplicate)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_raw_mention_fk_cascade(self, db_session):
        """Deleting the generation cascades to its raw mentions (brief §4.1)."""
        await seed_generation(db_session, "gen_c")
        mention = AIRawMention(
            generation_id="gen_c", engine="gemini", query="q",
            brand_or_topic="acme", mention_type="mention",
            sentiment="neutral",
        )
        db_session.add(mention)
        await db_session.commit()

        from src.models.generation import Generation

        gen = (
            await db_session.execute(
                select(Generation).where(Generation.id == "gen_c")
            )
        ).scalar_one()
        await db_session.delete(gen)
        await db_session.commit()

        rows = (
            await db_session.execute(
                select(AIRawMention).where(AIRawMention.generation_id == "gen_c")
            )
        ).scalars().all()
        assert rows == []

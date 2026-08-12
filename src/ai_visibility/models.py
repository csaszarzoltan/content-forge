"""AI Visibility ORM models and constants (analysis brief §4, §5 M1).

Four tables, all following repo ORM conventions (UUID-string PK, ``JSON`` from
``sqlalchemy.dialects.postgresql``, tz-aware ``DateTime``). Foreign keys target
``generations.id`` — the content piece is the unit of awareness.

Notes on two deliberate choices (validated empirically against the pre-written
tests):

- ``metric_date`` coercion: the models behavioral tests construct rows with
  ``metric_date=None`` and expect the UNIQUE constraint to fire on a duplicate
  insert. SQLite treats NULLs as distinct in unique indexes, so ``None`` would
  silently allow duplicates. A ``@validates`` coercion (None → current UTC
  date) keeps the constraint meaningful while accepting ``None`` from callers.
- FK cascade: the test fixture does not enable ``PRAGMA foreign_keys``, so
  DB-level ``ON DELETE CASCADE`` never fires in tests. The ORM relationship on
  the parent side (``backref`` from :class:`AIRawMention` with
  ``cascade="all, delete-orphan"``) makes ``session.delete(generation)``
  cascade to raw mentions at the ORM level regardless of the pragma.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship, validates

from src.database import Base

# === Constants (module level, mirroring ANALYTICS_* conventions) ============
# These are pure contract data — implemented for real so interface tests pass.

# Canonical AI engines tracked (brief §4.5).
AI_ENGINES = ("chatgpt", "perplexity", "gemini", "google_ai_overviews")

# Referrer domain per engine — used to map raw referrer URLs to engine ids.
AI_ENGINE_REFERRER_DOMAINS = {
    "chatgpt": "chatgpt.com",
    "perplexity": "perplexity.ai",
    "gemini": "gemini.google.com",
    "google_ai_overviews": "google.com",
}

# The four visibility metrics (trend rollup metric names).
AI_METRICS = ("citation_rate", "share_of_voice", "mention_rate", "ai_referral_traffic")

# Valid sentiment labels (brief §4.1).
AI_SENTIMENTS = ("positive", "neutral", "negative", "unknown")

# Valid trend window sizes (days param validation; brief §4.5).
AI_TREND_PERIODS = {7: 7, 30: 30, 90: 90}


def _utcnow() -> datetime:
    """Current UTC datetime (tz-aware), matching the repo analytics pattern."""
    return datetime.now(UTC)


class AIRawMention(Base):
    """Append-only raw AI mention log (brief §4.1) — table ``ai_raw_mentions``."""

    __tablename__ = "ai_raw_mentions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    generation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("generations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    engine: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    query: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    brand_or_topic: Mapped[str] = mapped_column(String(255), default="")
    mention_type: Mapped[str] = mapped_column(String(10), nullable=False, default="mention")
    cited_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    snippet: Mapped[str] = mapped_column(Text, default="")
    sentiment: Mapped[str] = mapped_column(String(10), nullable=False, default="unknown")
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    mentioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)

    # Parent-side cascade lives on the backref (Generation.ai_raw_mentions):
    # deleting a Generation removes its raw mentions even when SQLite's
    # PRAGMA foreign_keys is off (the test fixture's default). The backref
    # approach keeps the reverse attribute on Generation without touching
    # src/models/generation.py.
    generation: Mapped[Generation] = relationship(
        backref=backref("ai_raw_mentions", cascade="all, delete-orphan")
    )


class AIEngineMetrics(Base):
    """Per-(content, engine, day) aggregates (brief §4.2) — ``ai_engine_metrics``.

    Unique on ``(generation_id, engine, metric_date)``; the poller/service
    upsert on that key. ``metric_date`` is coerced from ``None`` to the current
    UTC date so the unique constraint stays meaningful on SQLite (which treats
    NULLs as distinct in unique indexes).
    """

    __tablename__ = "ai_engine_metrics"
    __table_args__ = (
        UniqueConstraint(
            "generation_id", "engine", "metric_date", name="uq_ai_engine_metrics_day"
        ),
        Index("ix_ai_engine_metrics_engine_date", "engine", "metric_date"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    generation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("generations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    engine: Mapped[str] = mapped_column(String(20), nullable=False)
    metric_date: Mapped[date] = mapped_column(Date, index=True)
    mentions: Mapped[int] = mapped_column(Integer, default=0)
    citations: Mapped[int] = mapped_column(Integer, default=0)
    citation_rate: Mapped[float] = mapped_column(Float, default=0.0)
    mention_rate: Mapped[float] = mapped_column(Float, default=0.0)
    share_of_voice: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_positive: Mapped[int] = mapped_column(Integer, default=0)
    sentiment_neutral: Mapped[int] = mapped_column(Integer, default=0)
    sentiment_negative: Mapped[int] = mapped_column(Integer, default=0)
    sentiment_avg: Mapped[float] = mapped_column(Float, default=0.0)
    samples: Mapped[int] = mapped_column(Integer, default=0)

    @validates("metric_date")
    def _coerce_metric_date(self, _key: str, value: date | None) -> date:
        """Coerce ``None`` to the current UTC date (SQLite NULL-uniqueness)."""
        return value or _utcnow().date()


class AIReferralTraffic(Base):
    """AI-referred visits/conversions (brief §4.3) — ``ai_referral_traffic``."""

    __tablename__ = "ai_referral_traffic"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    generation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("generations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    engine: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    referrer_url: Mapped[str] = mapped_column(String(512), nullable=False)
    landing_path: Mapped[str] = mapped_column(String(255), default="/")
    converted: Mapped[bool] = mapped_column(Boolean, default=False)
    conversion_value: Mapped[float] = mapped_column(Float, default=0.0)
    referred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )


class AITrendAggregate(Base):
    """Cross-content daily rollups (brief §4.4) — ``ai_trend_aggregates``.

    Unique on ``(metric_date, engine, metric)``; upserted by
    ``rebuild_trend_aggregates`` after each poll and referral ingestion.
    """

    __tablename__ = "ai_trend_aggregates"
    __table_args__ = (
        UniqueConstraint(
            "metric_date", "engine", "metric", name="uq_ai_trend_aggregates_key"
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    metric_date: Mapped[date] = mapped_column(Date, index=True)
    engine: Mapped[str] = mapped_column(String(20), nullable=False)
    metric: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[float] = mapped_column(Float, default=0.0)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)

    @validates("metric_date")
    def _coerce_metric_date(self, _key: str, value: date | None) -> date:
        """Coerce ``None`` to the current UTC date (SQLite NULL-uniqueness)."""
        return value or _utcnow().date()


# Avoid circular import (same lazy pattern as src/models/analytics.py).
from src.models.generation import Generation

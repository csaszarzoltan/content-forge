"""Analytics ORM models: ContentAnalytics (existing) + AnalyticsEvent (new).

AnalyticsEvent is the append-only event log introduced in v0.9.0 — the
canonical source for all performance metrics (see analysis brief §3.2).
ContentAnalytics remains the compliance / external-sync snapshot.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

# Valid event types for the analytics event log (mirrors AB_VALID_* convention).
ANALYTICS_EVENT_TYPES = [
    "impression",
    "click",
    "share",
    "comment",
    "conversion",
    "read_time",
]

# Valid channels for analytics events (mirrors AB_VALID_* convention).
ANALYTICS_CHANNELS = ["twitter", "linkedin", "medium", "blog", "email", "web", "other"]


class AnalyticsEvent(Base):
    """Append-only analytics event log — single source of truth for performance.

    Pre-development stub: columns per analysis brief §3.2. Note that the DB
    column is named ``metadata`` (per spec) but the mapped attribute is
    ``event_metadata`` because ``metadata`` is reserved by the Declarative API.
    """

    __tablename__ = "analytics_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    generation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("generations.id", ondelete="CASCADE"), index=True,
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(30), default="web", index=True)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[int] = mapped_column(Integer, default=1)
    user_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )


class ContentAnalytics(Base):
    """Performance and compliance data for a single generation."""

    __tablename__ = "content_analytics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    generation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("generations.id"), unique=True, nullable=False
    )
    views: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    avg_read_time_seconds: Mapped[int] = mapped_column(Integer, default=0)
    compliance_overall: Mapped[float | None] = mapped_column(Float, nullable=True)
    compliance_vocabulary: Mapped[float | None] = mapped_column(Float, nullable=True)
    compliance_readability: Mapped[float | None] = mapped_column(Float, nullable=True)
    compliance_tone: Mapped[float | None] = mapped_column(Float, nullable=True)
    violations: Mapped[dict] = mapped_column(JSON, default=list)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    generation: Mapped[Generation | None] = relationship()


# Avoid circular import
from src.models.generation import Generation  # noqa: E402

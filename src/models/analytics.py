"""ContentAnalytics ORM model.

Holds performance metrics and compliance data for generated content.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


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

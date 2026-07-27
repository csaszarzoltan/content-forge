"""SQLAlchemy ORM models for the A/B testing framework.

ABTest, ABVariant, ABEvent — three normalized models implementing
the chosen Option B from the analysis brief.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class ABTest(Base):
    """An A/B test comparing multiple content variants."""

    __tablename__ = "ab_tests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    brand_voice_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("brand_voices.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )
    winner_variant_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    concluded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationship to variants
    variants = relationship(
        "ABVariant", back_populates="ab_test", cascade="all, delete-orphan"
    )


class ABVariant(Base):
    """A single variant within an A/B test."""

    __tablename__ = "ab_variants"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    ab_test_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ab_tests.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    variant_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="treatment"
    )
    generation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("generations.id", ondelete="SET NULL"), nullable=True
    )
    variant_params: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    ab_test = relationship("ABTest", back_populates="variants")


class ABEvent(Base):
    """An individual interaction event recorded for an A/B test variant."""

    __tablename__ = "ab_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    variant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ab_variants.id", ondelete="CASCADE"), nullable=False
    )
    ab_test_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ab_tests.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    user_identifier: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    event_data: Mapped[dict] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


# Constants for validation
AB_VALID_STATUSES: list[str] = ["draft", "running", "concluded", "archived"]
AB_VALID_EVENT_TYPES: list[str] = ["impression", "conversion"]
AB_VALID_VARIANT_TYPES: list[str] = ["control", "treatment"]

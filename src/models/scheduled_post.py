"""ScheduledPost ORM model.

Represents a future-dated content publish job managed by APScheduler.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class ScheduledPost(Base):
    """A content piece scheduled for future publishing."""

    __tablename__ = "scheduled_posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    generation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("generations.id"), nullable=False
    )
    publish_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    platform: Mapped[str] = mapped_column(String(30), nullable=False)  # twitter, linkedin, email, blog
    platform_config: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending, publishing, published, failed
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    generation: Mapped[Generation | None] = relationship()


# Avoid circular import
from src.models.generation import Generation  # noqa: E402

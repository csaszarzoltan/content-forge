"""Video platform metrics ORM model.

Stores per-video metrics fetched from YouTube, TikTok, and Instagram.
Pre-development stub — columns per task spec t_6ffc403c.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base

# Valid video platforms for the analytics module.
# Extends the constraints Platform type with YouTube (not in social constraints).
VIDEO_PLATFORMS = ["youtube", "tiktok", "instagram"]


class VideoPlatformMetric(Base):
    """Per-video metrics snapshot from a single platform at a point in time.

    Table: video_platform_metrics
    Unique: (video_id, platform, collected_at)
    Index:  (platform, video_id, collected_at DESC)
    """

    __tablename__ = "video_platform_metrics"

    __table_args__ = (
        UniqueConstraint(
            "video_id", "platform", "collected_at",
            name="uq_video_platform_metrics_video_platform_time",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    video_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
    )

    # YouTube metrics
    views: Mapped[int] = mapped_column(Integer, default=0)
    watch_time_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    subscriber_change: Mapped[int] = mapped_column(Integer, default=0)

    # TikTok metrics
    shares: Mapped[int] = mapped_column(Integer, default=0)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # Instagram Reels metrics
    plays: Mapped[int] = mapped_column(Integer, default=0)
    saves: Mapped[int] = mapped_column(Integer, default=0)

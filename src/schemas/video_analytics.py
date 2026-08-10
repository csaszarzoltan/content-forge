"""Pydantic schemas for video platform analytics.

Pre-development stub — field contracts per task spec t_6ffc403c.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class VideoMetricsSnapshot(BaseModel):
    """Normalized metrics from any video platform adapter."""

    video_id: str
    platform: str
    collected_at: datetime
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    watch_time_minutes: float = 0.0
    subscriber_change: int = 0
    completion_rate: float = 0.0
    plays: int = 0
    saves: int = 0


class PlatformMetrics(BaseModel):
    """Aggregated metrics for a single platform in the response."""

    platform: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    watch_time_minutes: float = 0.0
    subscriber_change: int = 0
    completion_rate: float = 0.0
    plays: int = 0
    saves: int = 0


class VideoPerformanceResponse(BaseModel):
    """Unified performance response across all platforms."""

    video_id: str
    platforms: list[PlatformMetrics] = Field(default_factory=list)
    platforms_unavailable: list[str] = Field(default_factory=list)
    date_from: datetime
    date_to: datetime


class TimeseriesPoint(BaseModel):
    """Single point in a daily timeseries."""

    date: str
    platform: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0


class VideoTimeseriesResponse(BaseModel):
    """Daily timeseries with platform dimension."""

    video_id: str | None = None
    points: list[TimeseriesPoint] = Field(default_factory=list)


class OptimalTimesHeatmap(BaseModel):
    """Day × hour heatmap of optimal posting times."""

    # day_of_week (0=Mon) → hour (0-23) → engagement score
    heatmap: dict[int, dict[int, float]] = Field(default_factory=dict)
    days_analyzed: int = 0
    platforms: list[str] = Field(default_factory=list)


class VideoDetailResponse(BaseModel):
    """Per-video metrics with platform comparison."""

    video_id: str
    title: str = ""
    platforms: list[PlatformMetrics] = Field(default_factory=list)
    platforms_unavailable: list[str] = Field(default_factory=list)
    best_platform: str | None = None

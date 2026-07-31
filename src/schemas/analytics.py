"""Pydantic schemas for analytics endpoints.

Pre-development scaffolding: existing compliance/performance schemas plus the
v0.9.0 request/response schemas specified in analysis brief §5.3.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ComplianceData(BaseModel):
    """Compliance data stored at generation time."""

    overall: float = 0.0
    vocabulary: float = 0.0
    readability: float = 0.0
    tone: float = 0.0
    violations: list[str] = Field(default_factory=list)


class PerformanceData(BaseModel):
    """Content performance metrics updated externally."""

    views: int = 0
    engagement_rate: float = 0.0
    shares: int = 0
    comments: int = 0
    avg_read_time_seconds: int = 0


class ContentAnalyticsResponse(BaseModel):
    """Response body for GET /analytics/content/{id}."""

    generation_id: str
    content_type: str
    brand_voice_id: str | None
    compliance: ComplianceData
    performance: PerformanceData
    model_used: str
    tokens_used: int
    created_at: datetime
    updated_at: datetime | None = None


class AnalyticsSummary(BaseModel):
    """Response body for GET /analytics/summary."""

    total_generations: int = 0
    avg_compliance: float = 0.0
    content_type_breakdown: dict[str, int] = Field(default_factory=dict)
    total_views: int = 0
    avg_engagement_rate: float = 0.0


# ============================================================================
# v0.9.0 Content Performance Analytics Dashboard schemas (analysis brief §5.3)
# ============================================================================

EventType = Literal[
    "impression", "click", "share", "comment", "conversion", "read_time"
]


class TrackEventRequest(BaseModel):
    """Body for POST /api/v1/analytics/track."""

    generation_id: str
    channel: str = "web"
    event_type: EventType
    value: int = Field(1, ge=0, le=1_000_000)
    user_identifier: str | None = None
    metadata: dict = Field(default_factory=dict)
    occurred_at: datetime | None = None


class TrackEventResponse(BaseModel):
    """Response body for POST /api/v1/analytics/track."""

    status: Literal["ok"]
    event_id: str


class MetricSummary(BaseModel):
    """Aggregated event metrics for a content piece / channel / window."""

    impressions: int = 0
    clicks: int = 0
    shares: int = 0
    comments: int = 0
    conversions: int = 0
    read_time_seconds: int = 0
    engagement_rate: float = 0.0


class ContentPerformanceResponse(BaseModel):
    """Response body for GET /api/v1/analytics/content/{generation_id}."""

    generation_id: str
    content_type: str
    brand_voice_id: str | None = None
    topic: str = ""
    model_used: str = ""
    tokens_used: int = 0
    compliance: ComplianceData
    performance: PerformanceData
    channel_breakdown: dict[str, MetricSummary] = Field(default_factory=dict)
    score: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TopContentItem(BaseModel):
    """A single entry in the dashboard top-content list."""

    generation_id: str
    topic: str
    content_type: str
    impressions: int = 0
    engagement_rate: float = 0.0


class TimeSeriesPoint(BaseModel):
    """One daily aggregate point in the dashboard time series."""

    date: str  # ISO yyyy-mm-dd
    impressions: int = 0
    clicks: int = 0
    shares: int = 0
    comments: int = 0
    conversions: int = 0
    engagement_rate: float = 0.0


class DashboardResponse(BaseModel):
    """Response body for GET /api/v1/analytics/dashboard."""

    date_from: datetime
    date_to: datetime
    totals: MetricSummary
    content_type_breakdown: dict[str, int] = Field(default_factory=dict)
    channel_breakdown: dict[str, MetricSummary] = Field(default_factory=dict)
    top_content: list[TopContentItem] = Field(default_factory=list)
    time_series: list[TimeSeriesPoint] = Field(default_factory=list)


class ChannelMetrics(BaseModel):
    """Per-channel metrics row in the channel comparison response."""

    channel: str
    impressions: int = 0
    clicks: int = 0
    shares: int = 0
    comments: int = 0
    conversions: int = 0
    engagement_rate: float = 0.0


class ChannelComparisonResponse(BaseModel):
    """Response body for GET /api/v1/analytics/channels."""

    date_from: datetime
    date_to: datetime
    channels: list[ChannelMetrics] = Field(default_factory=list)
    best_channel: str | None = None
    total_impressions: int = 0


class VariantPerformance(BaseModel):
    """A/B variant with analytics metrics merged from the event log."""

    variant_id: str
    name: str
    variant_type: str
    generation_id: str | None = None
    impressions: int = 0
    conversions: int = 0
    conversion_rate: float = 0.0
    engagement_rate: float = 0.0
    is_winner: bool = False


class ABResultsCorrelationResponse(BaseModel):
    """Response body for GET /api/v1/analytics/ab-results."""

    ab_test_id: str
    name: str
    status: str
    winner_variant_id: str | None = None
    variants: list[VariantPerformance] = Field(default_factory=list)
    correlation_note: str = ""


class ScoreBreakdown(BaseModel):
    """The four normalized (0-100) sub-scores of the content score."""

    engagement: float = 0.0
    seo: float = 0.0
    readability: float = 0.0
    compliance: float = 0.0


class ContentScoreResponse(BaseModel):
    """Response body for GET /api/v1/analytics/score/{generation_id}."""

    generation_id: str
    score: float  # 0-100
    grade: Literal["A", "B", "C", "D", "F"]
    breakdown: ScoreBreakdown


class TrendPoint(BaseModel):
    """One daily point in a trend series, with anomaly flag."""

    date: str
    impressions: int = 0
    clicks: int = 0
    shares: int = 0
    comments: int = 0
    conversions: int = 0
    engagement_rate: float = 0.0
    anomaly: bool = False


class TrendResponse(BaseModel):
    """Response body for GET /api/v1/analytics/trends."""

    period: str
    metric: str
    points: list[TrendPoint] = Field(default_factory=list)


class AnomalyItem(BaseModel):
    """A single flagged anomaly in the anomaly response."""

    date: str
    metric: str
    value: float
    z_score: float
    direction: Literal["spike", "drop"]


class AnomalyResponse(BaseModel):
    """Response body for GET /api/v1/analytics/anomalies."""

    period: str
    metric: str
    anomalies: list[AnomalyItem] = Field(default_factory=list)


class ExportResponse(BaseModel):
    """Response body for GET /api/v1/analytics/export."""

    format: str
    filename: str
    content_type: str
    data: str  # CSV text or JSON array text

"""Pydantic schemas for analytics endpoints."""

from __future__ import annotations

from datetime import datetime

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

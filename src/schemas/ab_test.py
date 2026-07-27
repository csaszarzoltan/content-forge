"""Pydantic schemas for the A/B testing framework.

ABCreateRequest, ABVariantResponse, ABTestResponse, ABTestListResponse,
ABTrackRequest, ABResultsResponse, ABVariantResult, ABConcludeRequest,
ABDashboardResponse.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ABCreateRequest(BaseModel):
    """Request schema for creating an A/B test."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    content_type: Literal["blog", "social", "email"]
    topic: str = Field(..., min_length=1)
    brand_voice_id: str | None = None
    variant_count: int = Field(default=2, ge=2, le=5)
    variant_dimension: Literal["tone", "cta", "headline", "structure", "mixed"] = "tone"
    audience: str | None = None
    length: Literal["short", "medium", "long"] = "medium"


class ABVariantResponse(BaseModel):
    """Response schema for a single variant in an A/B test."""

    id: str
    name: str
    variant_type: str
    generation_id: str | None = None
    variant_params: dict = {}
    impressions: int = 0
    conversions: int = 0
    conversion_rate: float = 0.0
    created_at: datetime


class ABTestResponse(BaseModel):
    """Response schema for a full A/B test with its variants."""

    id: str
    name: str
    description: str
    content_type: str
    topic: str
    brand_voice_id: str | None = None
    status: str
    variants: list[ABVariantResponse] = []
    winner_variant_id: str | None = None
    created_by: str | None = None
    created_at: datetime
    concluded_at: datetime | None = None


class ABTestListResponse(BaseModel):
    """Response schema for listing A/B tests with pagination."""

    items: list[ABTestResponse]
    total: int
    limit: int
    offset: int


class ABTrackRequest(BaseModel):
    """Request schema for tracking an A/B test event."""

    variant_id: str
    event_type: Literal["impression", "conversion"]
    user_identifier: str | None = None
    metadata: dict = {}


class ABVariantResult(BaseModel):
    """Per-variant statistical result in an A/B test results response."""

    id: str
    name: str
    variant_type: str
    impressions: int
    conversions: int
    conversion_rate: float
    z_score: float | None = None
    p_value: float | None = None
    is_winner: bool = False


class ABResultsResponse(BaseModel):
    """Response schema for A/B test results with statistical significance."""

    test: ABTestResponse
    significance_level: float | None = None
    confidence_level: float | None = None
    winner_variant_id: str | None = None
    insufficient_data: bool = False
    variants: list[ABVariantResult] = []
    method: str = "chi-squared"


class ABConcludeRequest(BaseModel):
    """Request schema for concluding an A/B test."""

    winner_variant_id: str
    note: str = ""


class ABDashboardResponse(BaseModel):
    """Response schema for the A/B testing dashboard view."""

    active_tests: list[ABTestResponse]
    concluded_tests: list[ABTestResponse]
    total_tests: int
    active_count: int
    concluded_count: int

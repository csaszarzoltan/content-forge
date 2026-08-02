"""Pydantic contracts for AI visibility endpoints (analysis brief §5 M2).

These are pure declarative wire contracts (field names, types, defaults,
validation) — there is no behavior for the developer to implement, so they are
written for real in the pre-development stub. The developer keeps them
byte-for-byte; interface/contract tests in ``test_ai_visibility_schemas.py``
pass immediately.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Canonical engine literal shared by request/response schemas (brief §4.5).
AIEngine = Literal["chatgpt", "perplexity", "gemini", "google_ai_overviews"]


class EngineSentiment(BaseModel):
    """Sentiment counts + average for one engine (brief §5 M2)."""

    positive: int = 0
    neutral: int = 0
    negative: int = 0
    avg: float = 0.0  # -1..1


class EngineVisibilityMetrics(BaseModel):
    """Per-engine visibility metrics in the content snapshot."""

    engine: str  # one of AI_ENGINES
    mentions: int = 0
    citations: int = 0
    citation_rate: float = 0.0  # 0..1
    share_of_voice: float = 0.0  # 0..100
    mention_rate: float = 0.0  # 0..1
    sentiment: EngineSentiment = Field(default_factory=EngineSentiment)
    ai_referral_traffic: int = 0
    ai_referral_conversions: int = 0
    ai_referral_conversion_rate: float = 0.0


class VisibilitySummary(BaseModel):
    """Rolled-up summary cards for the content snapshot."""

    total_mentions: int = 0
    total_citations: int = 0
    overall_citation_rate: float = 0.0
    avg_share_of_voice: float = 0.0
    avg_mention_rate: float = 0.0
    ai_referral_traffic: int = 0
    ai_referral_conversions: int = 0
    ai_referral_conversion_rate: float = 0.0


class VisibilityTimePoint(BaseModel):
    """One daily point in the content time series."""

    date: str  # ISO yyyy-mm-dd
    citation_rate: float = 0.0
    share_of_voice: float = 0.0
    mention_rate: float = 0.0
    ai_referral_traffic: int = 0


class ContentVisibilityResponse(BaseModel):
    """Response body for GET /api/v1/ai-visibility/{content_id}."""

    content_id: str
    topic: str = ""
    content_type: str = ""
    date_from: str  # ISO date
    date_to: str
    summary: VisibilitySummary
    engines: list[EngineVisibilityMetrics] = Field(default_factory=list)
    time_series: list[VisibilityTimePoint] = Field(default_factory=list)


class TrendSeries(BaseModel):
    """One Chart.js dataset (brief §5 M2)."""

    engine: str
    metric: str  # one of AI_METRICS
    data: list[float] = Field(default_factory=list)


class AIVisibilityTrendsResponse(BaseModel):
    """Response body for GET /api/v1/ai-visibility/trends (Chart.js feed)."""

    period: str  # "7d" | "30d" | "90d"
    days: int
    date_from: str
    date_to: str
    dates: list[str] = Field(default_factory=list)  # Chart.js labels
    series: list[TrendSeries] = Field(default_factory=list)
    totals: dict[str, float] = Field(default_factory=dict)


class ReferralIngestRequest(BaseModel):
    """Body for POST /api/v1/ai-visibility/referral (webhook-style)."""

    generation_id: str
    engine: AIEngine
    referrer_url: str = Field(..., max_length=512)
    landing_path: str = "/"
    converted: bool = False
    conversion_value: float = Field(0.0, ge=0.0)
    occurred_at: datetime | None = None


class ReferralIngestResponse(BaseModel):
    """Response body for POST /api/v1/ai-visibility/referral (201)."""

    status: Literal["ok"]
    referral_id: str


class PollResult(BaseModel):
    """Result of one poll cycle (M7) / on-demand refresh (M8)."""

    started_at: datetime
    finished_at: datetime
    engines_polled: list[str] = Field(default_factory=list)
    queries_run: int = 0
    mentions_recorded: int = 0
    errors: list[str] = Field(default_factory=list)

"""Analytics endpoints (v0.9.0 target state, analysis brief §5.4).

Router prefix migrated from the legacy bare ``/analytics`` to
``/api/v1/analytics`` (brief §1.5 #1). Endpoint map:

    POST   /track                              -> TrackEventResponse (201)
    GET    /dashboard                          -> DashboardResponse
    GET    /content/{generation_id}            -> ContentPerformanceResponse
    GET    /channels                           -> ChannelComparisonResponse
    GET    /ab-results                         -> ABResultsCorrelationResponse
    GET    /export                             -> ExportResponse
    GET    /score/{generation_id}              -> ContentScoreResponse
    GET    /trends                             -> TrendResponse
    GET    /anomalies                          -> AnomalyResponse

Legacy ``GET /analytics/summary`` is superseded by ``/dashboard``.
Handlers are thin; services raise ``NotImplementedError`` during the TDD RED
phase and are implemented by the developer task.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_optional_current_user
from src.schemas.analytics import (
    ABResultsCorrelationResponse,
    AnomalyResponse,
    ChannelComparisonResponse,
    ContentPerformanceResponse,
    ContentScoreResponse,
    DashboardResponse,
    ExportResponse,
    TrackEventRequest,
    TrackEventResponse,
    TrendResponse,
)
from src.services.analytics import AnalyticsService
from src.services.content_scoring import ContentScoringService

if TYPE_CHECKING:
    from src.models.user import User

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def _service() -> AnalyticsService:
    return AnalyticsService()


@router.post("/track", status_code=201)
async def track_event(
    request: TrackEventRequest,
    db: AsyncSession = Depends(get_db),
) -> TrackEventResponse:
    """Record an analytics event (unauthenticated, webhook-style)."""
    try:
        return await _service().track_event(db, request)
    except ValueError as exc:
        # Distinguish "generation not found" (404) from validation errors (422)
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: "User | None" = Depends(get_optional_current_user),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    channel: str | None = None,
    content_type: str | None = None,
) -> DashboardResponse:
    """Aggregate dashboard metrics (default window: last 30 days)."""
    try:
        return await _service().get_dashboard(db, date_from, date_to, channel, content_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/content/{generation_id}")
async def get_content_performance(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: "User | None" = Depends(get_optional_current_user),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> ContentPerformanceResponse:
    """Per-content performance analytics."""
    try:
        return await _service().get_content_performance(
            db, generation_id, date_from, date_to
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/channels")
async def get_channel_comparison(
    db: AsyncSession = Depends(get_db),
    current_user: "User | None" = Depends(get_optional_current_user),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    metric: str = "impressions",
) -> ChannelComparisonResponse:
    """Per-channel metrics comparison."""
    try:
        return await _service().get_channel_comparison(db, date_from, date_to, metric)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/ab-results")
async def get_ab_results(
    test_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: "User | None" = Depends(get_optional_current_user),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> ABResultsCorrelationResponse:
    """Correlate A/B test variants with analytics event data."""
    try:
        return await _service().get_ab_correlation(db, test_id, date_from, date_to)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/export")
async def export_data(
    db: AsyncSession = Depends(get_db),
    current_user: "User | None" = Depends(get_optional_current_user),
    format: str = "json",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    channel: str | None = None,
    content_type: str | None = None,
) -> ExportResponse:
    """Export daily aggregates as CSV or JSON (stdlib csv only, brief §3.3)."""
    try:
        return await _service().export_data(
            db, format, date_from, date_to, channel, content_type
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/score/{generation_id}")
async def get_content_score(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: "User | None" = Depends(get_optional_current_user),
) -> ContentScoreResponse:
    """Deterministic content quality score (engagement+SEO+readability+compliance)."""
    try:
        return await ContentScoringService().score(db, generation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/trends")
async def get_trends(
    db: AsyncSession = Depends(get_db),
    current_user: "User | None" = Depends(get_optional_current_user),
    period: str = "30d",
    metric: str = "impressions",
    channel: str | None = None,
) -> TrendResponse:
    """Historical daily trend series with per-point anomaly flags."""
    try:
        return await _service().get_trends(db, period, metric, channel)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/anomalies")
async def get_anomalies(
    db: AsyncSession = Depends(get_db),
    current_user: "User | None" = Depends(get_optional_current_user),
    period: str = "30d",
    metric: str = "impressions",
) -> AnomalyResponse:
    """Anomaly detection: |z| >= 2.0 on daily series with >= 7 points."""
    try:
        return await _service().detect_anomalies(db, period, metric)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

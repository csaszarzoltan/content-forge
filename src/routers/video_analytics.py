"""Video platform analytics endpoints.

Router prefix: /api/v1/analytics/video-performance
Implements aggregated performance, timeseries, optimal posting times,
and per-video drill-down endpoints with proper error handling.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from src.services.video_analytics import VideoAnalyticsService

router = APIRouter(
    prefix="/api/v1/analytics/video-performance",
    tags=["video-analytics"],
)


def _get_service() -> VideoAnalyticsService:
    """Create an analytics service with configured platform clients.

    Each client is initialized from environment settings. A missing
    key means that platform is skipped gracefully.
    """
    from src.config import get_settings

    settings = get_settings()
    from src.services.video_analytics import InstagramClient, TikTokClient, YouTubeClient

    youtube = YouTubeClient(
        api_key=settings.YOUTUBE_API_KEY,
        oauth_token=settings.YOUTUBE_OAUTH_TOKEN,
    )
    tiktok = TikTokClient(client_key=settings.TIKTOK_API_KEY)
    instagram = InstagramClient(access_token=settings.INSTAGRAM_ACCESS_TOKEN)

    return VideoAnalyticsService(youtube=youtube, tiktok=tiktok, instagram=instagram)


def _validate_date_range(
    date_from: datetime | None,
    date_to: datetime | None,
) -> None:
    """Raise 400 if date_from > date_to."""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=400,
            detail="date_from must be before or equal to date_to",
        )


@router.get("")
async def get_video_performance(
    video_id: str | None = None,
    platform: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    """Unified performance metrics across all video platforms.

    Aggregates views, watch time, likes, comments, and shares from
    YouTube, TikTok, and Instagram. Platforms that fail or are
    unconfigured are reported in ``platforms_unavailable``.
    """
    _validate_date_range(date_from, date_to)
    service = _get_service()

    try:
        result = service.get_performance(
            video_id=video_id or "",
            platform=platform,
            date_from=date_from,
            date_to=date_to,
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"video_analytics_error: {exc}",
        ) from exc


@router.get("/timeseries")
async def get_video_timeseries(
    video_id: str | None = None,
    platform: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    """Daily timeseries with platform dimension.

    Returns one data point per day per platform, suitable for
    Chart.js rendering.
    """
    _validate_date_range(date_from, date_to)
    service = _get_service()

    try:
        result = service.get_timeseries(
            video_id=video_id,
            platform=platform,
            date_from=date_from,
            date_to=date_to,
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"video_analytics_error: {exc}",
        ) from exc


@router.get("/optimal-times")
async def get_optimal_times(
    platform: str | None = None,
) -> dict[str, Any]:
    """Day × hour heatmap of optimal posting times.

    Aggregates engagement data across historical posts to find the
    best day-of-week and hour combinations for posting.
    """
    service = _get_service()

    try:
        result = service.get_optimal_times(platform=platform)
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"video_analytics_error: {exc}",
        ) from exc


@router.get("/{video_id}")
async def get_video_detail(video_id: str) -> dict[str, Any]:
    """Per-video metrics with platform comparison.

    Returns detailed metrics for a specific video across all
    configured platforms, plus the best-performing platform.
    """
    service = _get_service()

    try:
        result = service.get_video_detail(video_id)
        # When ALL platforms are unavailable (no API keys), we can't
        # determine if the video exists — return 502.
        if not result.get("platforms") and result.get("platforms_unavailable"):
            raise HTTPException(status_code=502, detail="all_platforms_unavailable")
        if not result.get("platforms") and not result.get("platforms_unavailable"):
            raise HTTPException(status_code=404, detail="video_not_found")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"video_analytics_error: {exc}",
        ) from exc

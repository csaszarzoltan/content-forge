"""Video platform analytics endpoints.

Router prefix: /api/v1/analytics/video-performance
Pre-development stub — all handlers raise NotImplementedError.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Query

if TYPE_CHECKING:
    pass

router = APIRouter(
    prefix="/api/v1/analytics/video-performance",
    tags=["video-analytics"],
)


@router.get("")
async def get_video_performance(
    video_id: str | None = None,
    platform: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict:
    """Unified performance metrics across all video platforms."""
    raise NotImplementedError


@router.get("/timeseries")
async def get_video_timeseries(
    video_id: str | None = None,
    platform: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict:
    """Daily timeseries with platform dimension."""
    raise NotImplementedError


@router.get("/optimal-times")
async def get_optimal_times(
    platform: str | None = None,
) -> dict:
    """Day × hour heatmap of optimal posting times."""
    raise NotImplementedError


@router.get("/{video_id}")
async def get_video_detail(video_id: str) -> dict:
    """Per-video metrics with platform comparison."""
    raise NotImplementedError

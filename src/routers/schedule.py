"""Content scheduling endpoints.

POST /schedule        — schedule content for publishing
GET  /schedule/{id}   — get schedule status
DELETE /schedule/{id} — cancel scheduled post
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.schemas.schedule import (
    ScheduleRequest,
    ScheduleResponse,
    ScheduleStatusResponse,
)
from src.services.scheduler import SchedulerService

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def schedule_content(
    body: ScheduleRequest,
    db: AsyncSession = Depends(get_db),
) -> ScheduleResponse:
    """Schedule content for automatic publishing at a future time."""
    if body.publish_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="publish_at must be in the future")

    scheduler = SchedulerService()
    schedule_id = await scheduler.schedule_post(
        generation_id=body.generation_id,
        publish_at=body.publish_at,
        platform=body.platform,
        platform_config=body.platform_config.model_dump(),
        max_retries=body.max_retries,
    )

    return ScheduleResponse(
        schedule_id=schedule_id,
        generation_id=body.generation_id,
        status="scheduled",
        publish_at=body.publish_at,
        platform=body.platform,
        created_at=datetime.now(timezone.utc),
    )


@router.get("/{schedule_id}")
async def get_schedule_status(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
) -> ScheduleStatusResponse:
    """Get the current status of a scheduled post."""
    scheduler = SchedulerService()
    status_data = await scheduler.get_post_status(schedule_id)

    # In production, fetch full details from DB
    return ScheduleStatusResponse(
        schedule_id=status_data.get("schedule_id", schedule_id),
        generation_id="",
        status=status_data.get("status", "pending"),
        publish_at=datetime.now(timezone.utc),
        platform="",
        retry_count=0,
        max_retries=3,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_scheduled_post(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Cancel a scheduled post."""
    scheduler = SchedulerService()
    await scheduler.cancel_post(schedule_id)

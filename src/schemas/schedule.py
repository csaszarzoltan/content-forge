"""Pydantic schemas for content scheduling endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Platform = Literal["twitter", "linkedin", "email", "blog"]


class PlatformConfig(BaseModel):
    """Platform-specific configuration for scheduling."""

    account_id: str | None = None
    channel_id: str | None = None


class ScheduleRequest(BaseModel):
    """Request body for POST /schedule."""

    generation_id: str = Field(..., description="ID of the content to publish")
    publish_at: datetime = Field(..., description="When to publish (ISO 8601)")
    platform: Platform = Field(..., description="Target platform")
    platform_config: PlatformConfig = Field(default_factory=PlatformConfig)
    retry_on_failure: bool = True
    max_retries: int = 3


class ScheduleResponse(BaseModel):
    """Response body for POST /schedule."""

    schedule_id: str
    generation_id: str
    status: str = "scheduled"
    publish_at: datetime
    platform: str
    created_at: datetime


class ScheduleStatusResponse(BaseModel):
    """Response body for GET /schedule/{id}."""

    schedule_id: str
    generation_id: str
    status: str
    publish_at: datetime
    platform: str
    retry_count: int
    max_retries: int
    created_at: datetime
    updated_at: datetime

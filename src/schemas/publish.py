"""Pydantic schemas for the social media publish API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Platform = Literal["twitter", "linkedin"]


class PublishRequest(BaseModel):
    """Request body for POST /api/v1/publish."""

    generation_id: str = Field(..., description="ID of the generated content to publish")
    platform: Platform = Field(..., description="Target social media platform")
    text: str = Field(default="", description="Content text to publish")
    platform_config: dict = Field(default_factory=dict, description="Platform-specific config")


class PublishResponse(BaseModel):
    """Response body for a successful publish operation."""

    publish_id: str = Field(..., description="Unique publish operation ID")
    generation_id: str = Field(..., description="ID of the published content")
    platform: str = Field(..., description="Platform published to")
    status: str = Field(default="published", description="Publish status")
    platform_url: str | None = Field(default=None, description="URL of the published post")
    created_at: datetime = Field(default_factory=lambda: datetime.now(), description="When the publish was created")


class PublishStatusResponse(BaseModel):
    """Response body for publish status lookup."""

    publish_id: str = Field(..., description="Unique publish operation ID")
    status: str = Field(..., description="Current publish status")
    retry_count: int = Field(default=0, description="Number of retries so far")
    error_message: str | None = Field(default=None, description="Error message if failed")

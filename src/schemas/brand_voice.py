"""Pydantic schemas for brand voice CRUD operations."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BrandVoiceCreate(BaseModel):
    """Request body for creating a new brand voice."""

    name: str = Field(..., min_length=1, description="Human-readable name")
    description: str = Field("", description="Brief description")
    brand_identity: dict[str, str] = Field(default_factory=lambda: {"who": "", "audience": "", "purpose": ""})
    attributes: list[dict] = Field(default_factory=list)
    vocabulary: dict | None = None
    scenarios: list[dict] = Field(default_factory=list)
    formatting: dict | None = None
    user_id: str | None = None


class BrandVoiceUpdate(BaseModel):
    """Request body for updating an existing brand voice (partial / PATCH semantics)."""

    name: str | None = None
    description: str | None = None
    brand_identity: dict[str, str] | None = None
    attributes: list[dict] | None = None
    vocabulary: dict | None = None
    scenarios: list[dict] | None = None
    formatting: dict | None = None


class BrandVoiceResponse(BaseModel):
    """Response body representing a single brand voice."""

    id: str
    name: str
    description: str
    brand_identity: dict[str, str]
    attributes: list[dict]
    vocabulary: dict
    scenarios: list[dict]
    formatting: dict
    metadata: dict
    version: int
    created_at: datetime
    updated_at: datetime


class BrandVoiceListResponse(BaseModel):
    """Response body for listing brand voices (paginated)."""

    items: list[BrandVoiceResponse]
    total: int
    limit: int = 20
    offset: int = 0

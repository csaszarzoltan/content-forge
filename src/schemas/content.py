"""Pydantic schemas for content generation endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ContentParameters(BaseModel):
    """Optional generation parameters."""

    audience: str | None = None
    length: Literal["short", "medium", "long"] | None = "medium"
    tone_override: str | None = None
    include_cta: bool = True
    custom_instructions: str | None = None


class GenerateRequest(BaseModel):
    """Request body for POST /generate/{content_type}."""

    topic: str = Field(..., min_length=1, description="Subject of the content")
    brand_voice_id: str | None = Field(None, description="Brand voice ID (falls back to active scope)")
    user_id: str | None = None
    project_id: str | None = None
    parameters: ContentParameters = Field(default_factory=ContentParameters)


class ComplianceScore(BaseModel):
    """Compliance scoring result attached to a generation."""

    overall: float = 0.0
    vocabulary: float = 0.0
    readability: float = 0.0
    tone: float = 0.0
    violations: list[str] = Field(default_factory=list)


class GenerationResponse(BaseModel):
    """Response body for POST /generate/{content_type}."""

    id: str
    content_type: str
    generated_text: str
    brand_voice_id: str | None
    compliance_score: ComplianceScore
    model_used: str
    tokens_used: int
    latency_ms: int
    created_at: datetime

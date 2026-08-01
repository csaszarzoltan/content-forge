"""Request/response schemas for constraint validation API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.constraints.models import Platform


class MediaAttachment(BaseModel):
    """A media attachment to validate."""

    type: Literal["image", "video", "gif"]
    filename: str
    size_bytes: int
    format: str
    width: int | None = None
    height: int | None = None
    duration_seconds: float | None = None


class ValidateRequest(BaseModel):
    """Request body for POST /api/v1/validate."""

    platforms: list[Platform]
    text: str = ""
    media: list[MediaAttachment] | None = None


class ValidationError(BaseModel):
    """A single validation error."""

    field: str
    rule: str
    message: str
    severity: Literal["error", "warning"] = "error"


class PlatformValidationResult(BaseModel):
    """Validation result for a single platform."""

    valid: bool
    errors: list[ValidationError] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    truncated_text: str | None = None
    media_acceptable: bool = True


class ValidateResponse(BaseModel):
    """Response body for POST /api/v1/validate."""

    valid: bool
    platforms: dict[str, PlatformValidationResult] = Field(default_factory=dict)


class CrossPlatformRequest(BaseModel):
    """Request for cross-platform compatibility check."""

    text: str = ""
    media: list[MediaAttachment] | None = None
    platforms: list[Platform]


class CrossPlatformResult(BaseModel):
    """Cross-platform compatibility result."""

    compatible_all: bool
    compatible_platforms: list[str] = Field(default_factory=list)
    needs_adaptation: list[str] = Field(default_factory=list)
    adaptations: dict[str, list[str]] = Field(default_factory=dict)


class PlatformSummary(BaseModel):
    """Summary of a platform's constraints."""

    platform: str
    display_name: str
    max_chars: int
    supported_image_formats: list[str]
    supported_video_formats: list[str]

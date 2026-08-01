"""Validation engine for social media content against platform constraints."""

from __future__ import annotations

from typing import Any

from src.constraints.registry import ConstraintRegistry
from src.schemas.constraints import (
    MediaAttachment,
    PlatformValidationResult,
    ValidateRequest,
    ValidateResponse,
)


class ConstraintValidator:
    """Orchestrates text + media validation across platforms."""

    def __init__(self, registry: ConstraintRegistry | None = None) -> None:
        self._registry = registry

    def validate(self, request: ValidateRequest) -> ValidateResponse:
        """Validate content against one or more platforms."""
        raise NotImplementedError

    def validate_text(
        self, platform: str, text: str, media_count: int = 0
    ) -> PlatformValidationResult:
        """Validate text content for a specific platform."""
        raise NotImplementedError

    def validate_media(
        self, platform: str, attachment: MediaAttachment
    ) -> PlatformValidationResult:
        """Validate a media attachment for a specific platform."""
        raise NotImplementedError

    def check_cross_platform(
        self, text: str, media: list[MediaAttachment] | None, platforms: list[str]
    ) -> dict[str, Any]:
        """Check which platforms accept the content as-is."""
        raise NotImplementedError

    def count_effective_chars(self, platform: str, text: str) -> int:
        """Count characters accounting for platform-specific URL wrapping."""
        raise NotImplementedError

    def preview(self, platform: str, text: str) -> dict[str, Any]:
        """Preview how content will render on a platform."""
        raise NotImplementedError

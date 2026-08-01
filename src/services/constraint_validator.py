"""Validation engine for social media content against platform constraints."""

from __future__ import annotations

import re
from typing import Any

from src.constraints.models import PlatformConstraints
from src.constraints.registry import ConstraintRegistry
from src.schemas.constraints import (
    MediaAttachment,
    PlatformValidationResult,
    ValidateRequest,
    ValidateResponse,
    ValidationError,
)

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


def _count_hashtags(text: str) -> int:
    """Count hashtags in text (words starting with #)."""
    return sum(1 for token in text.split() if token.startswith("#"))


def _count_mentions(text: str) -> int:
    """Count @mentions in text (words starting with @)."""
    return sum(1 for token in text.split() if token.startswith("@"))


class ConstraintValidator:
    """Orchestrates text + media validation across platforms."""

    def __init__(self, registry: ConstraintRegistry | None = None) -> None:
        self._registry = registry

    def _get_registry(self) -> ConstraintRegistry:
        """Get or create a default registry."""
        if self._registry is None:
            reg = ConstraintRegistry()
            reg.load()
            self._registry = reg
        return self._registry

    def _get_constraints(self, platform: str) -> PlatformConstraints:
        """Get PlatformConstraints for a platform."""
        return self._get_registry().get(platform)

    def validate(self, request: ValidateRequest) -> ValidateResponse:
        """Validate content against one or more platforms."""
        results: dict[str, PlatformValidationResult] = {}
        all_valid = True

        for platform in request.platforms:
            media_count = len(request.media) if request.media else 0
            text_result = self.validate_text(platform, request.text, media_count)

            media_acceptable = True
            if request.media:
                for attachment in request.media:
                    media_result = self.validate_media(platform, attachment)
                    if not media_result.media_acceptable:
                        media_acceptable = False
                        # Merge media errors into text result
                        text_result.errors.extend(media_result.errors)
                        text_result.warnings.extend(media_result.warnings)

            text_result.media_acceptable = media_acceptable
            if text_result.errors:
                all_valid = False
            if not media_acceptable:
                all_valid = False

            results[platform] = text_result

        return ValidateResponse(valid=all_valid, platforms=results)

    def validate_text(
        self, platform: str, text: str, media_count: int = 0
    ) -> PlatformValidationResult:
        """Validate text content for a specific platform."""
        constraints = self._get_constraints(platform)
        tc = constraints.text
        errors: list[ValidationError] = []
        warnings: list[str] = []
        truncated_text: str | None = None

        effective_len = self.count_effective_chars(platform, text)

        # Check character limit
        if effective_len > tc.max_chars:
            errors.append(
                ValidationError(
                    field="text",
                    rule="max_chars",
                    message=f"Text length {effective_len} exceeds limit of {tc.max_chars} characters",
                    severity="error",
                )
            )
            truncated_text = text[: tc.max_chars]

        # Check hashtag limit
        if tc.max_hashtags is not None:
            hashtag_count = _count_hashtags(text)
            if hashtag_count > tc.max_hashtags:
                errors.append(
                    ValidationError(
                        field="text.hashtags",
                        rule="max_hashtags",
                        message=f"Hashtag count {hashtag_count} exceeds limit of {tc.max_hashtags}",
                        severity="error",
                    )
                )

        # Check mention limit
        if tc.max_mentions is not None:
            mention_count = _count_mentions(text)
            if mention_count > tc.max_mentions:
                errors.append(
                    ValidationError(
                        field="text.mentions",
                        rule="max_mentions",
                        message=f"Mention count {mention_count} exceeds limit of {tc.max_mentions}",
                        severity="error",
                    )
                )

        return PlatformValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            truncated_text=truncated_text,
        )

    def validate_media(
        self, platform: str, attachment: MediaAttachment
    ) -> PlatformValidationResult:
        """Validate a media attachment for a specific platform."""
        constraints = self._get_constraints(platform)
        errors: list[ValidationError] = []
        warnings: list[str] = []

        if attachment.type == "image":
            ic = constraints.image

            # Check format rejection
            if attachment.format.lower() in [f.lower() for f in ic.rejected_formats]:
                errors.append(
                    ValidationError(
                        field="media.format",
                        rule="rejected_format",
                        message=f"Image format '{attachment.format}' is not supported on {platform}",
                        severity="error",
                    )
                )

            # Check format acceptance
            if (
                ic.formats
                and attachment.format.lower()
                not in [f.lower() for f in ic.formats]
            ):
                errors.append(
                    ValidationError(
                        field="media.format",
                        rule="unsupported_format",
                        message=f"Image format '{attachment.format}' is not in supported formats for {platform}",
                        severity="error",
                    )
                )

            # Check size
            if ic.max_size_bytes and attachment.size_bytes > ic.max_size_bytes:
                errors.append(
                    ValidationError(
                        field="media.size",
                        rule="max_size_bytes",
                        message=f"Image size {attachment.size_bytes} exceeds limit of {ic.max_size_bytes}",
                        severity="error",
                    )
                )

            # Check aspect ratio
            if (
                attachment.width is not None
                and attachment.height is not None
                and attachment.width > 0
                and attachment.height > 0
            ):
                ratio = attachment.width / attachment.height
                if ic.aspect_ratio_range:
                    for ar_str in ic.aspect_ratio_range:
                        parts = ar_str.split(":")
                        if len(parts) == 2:
                            try:
                                expected = int(parts[0]) / int(parts[1])
                                if abs(ratio - expected) < 0.01:
                                    break
                            except ValueError:
                                continue
                    else:
                        # Check if ratio is within any allowed range
                        valid_ratios = []
                        for ar_str in ic.aspect_ratios:
                            parts = ar_str.split(":")
                            if len(parts) == 2:
                                try:
                                    valid_ratios.append(int(parts[0]) / int(parts[1]))
                                except ValueError:
                                    pass
                        if valid_ratios and not any(
                            abs(ratio - vr) < 0.01 for vr in valid_ratios
                        ):
                            warnings.append(
                                f"Aspect ratio {ratio:.2f} may not be optimal for {platform}"
                            )

            # Check color space
            if ic.color_space and ic.color_space.lower() != "unknown":
                # We can't verify actual color space from metadata alone, but we note it
                pass

        elif attachment.type == "video":
            vc = constraints.video

            # Check duration
            if (
                vc.duration_min_seconds
                and attachment.duration_seconds is not None
                and attachment.duration_seconds < vc.duration_min_seconds
            ):
                errors.append(
                    ValidationError(
                        field="media.duration",
                        rule="duration_min",
                        message=f"Video duration {attachment.duration_seconds}s is below minimum of {vc.duration_min_seconds}s",
                        severity="error",
                    )
                )

            if vc.duration_max_seconds and attachment.duration_seconds is not None:
                max_dur = vc.duration_max_seconds
                if attachment.duration_seconds > max_dur:
                    errors.append(
                        ValidationError(
                            field="media.duration",
                            rule="duration_max",
                            message=f"Video duration {attachment.duration_seconds}s exceeds maximum of {max_dur}s",
                            severity="error",
                        )
                    )

            # Check size
            if vc.max_size_bytes and attachment.size_bytes > vc.max_size_bytes:
                errors.append(
                    ValidationError(
                        field="media.size",
                        rule="max_size_bytes",
                        message=f"Video size {attachment.size_bytes} exceeds limit of {vc.max_size_bytes}",
                        severity="error",
                    )
                )

        return PlatformValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            media_acceptable=len(errors) == 0,
        )

    def check_cross_platform(
        self, text: str, media: list[MediaAttachment] | None, platforms: list[str]
    ) -> dict[str, Any]:
        """Check which platforms accept the content as-is."""
        compatible: list[str] = []
        needs_adaptation: list[str] = []
        adaptations: dict[str, list[str]] = {}

        for platform in platforms:
            text_result = self.validate_text(platform, text)
            media_ok = True
            platform_adaptations: list[str] = []

            if media:
                for attachment in media:
                    media_result = self.validate_media(platform, attachment)
                    if not media_result.media_acceptable:
                        media_ok = False
                        for err in media_result.errors:
                            platform_adaptations.append(err.message)

            if text_result.valid and media_ok:
                compatible.append(platform)
            else:
                needs_adaptation.append(platform)
                for err in text_result.errors:
                    platform_adaptations.append(err.message)
                if platform_adaptations:
                    adaptations[platform] = platform_adaptations

        return {
            "compatible_all": len(needs_adaptation) == 0,
            "compatible_platforms": compatible,
            "needs_adaptation": needs_adaptation,
            "adaptations": adaptations,
        }

    def count_effective_chars(self, platform: str, text: str) -> int:
        """Count characters accounting for platform-specific URL wrapping."""
        constraints = self._get_constraints(platform)
        url_consumed = constraints.text.url_consumed_chars

        if url_consumed is None:
            # Platform doesn't consume URLs at a fixed length — count as-is
            return len(text)

        urls = _URL_RE.findall(text)
        if not urls:
            return len(text)

        # Replace each URL with its consumed length
        effective = text
        total_url_chars = 0
        for url in urls:
            total_url_chars += len(url)
        # Remove actual URLs, add consumed length per URL
        for url in urls:
            effective = effective.replace(url, "", 1)
        return len(effective) + len(urls) * url_consumed

    def preview(self, platform: str, text: str) -> dict[str, Any]:
        """Preview how content will render on a platform."""
        constraints = self._get_constraints(platform)
        tc = constraints.text

        effective_len = self.count_effective_chars(platform, text)
        truncated = effective_len > tc.max_chars
        display_text = text[: tc.max_chars] if truncated else text

        return {
            "platform": platform,
            "display_name": constraints.display_name,
            "text": display_text,
            "truncated": truncated,
            "char_count": effective_len,
            "max_chars": tc.max_chars,
            "hashtags": _count_hashtags(text),
            "mentions": _count_mentions(text),
        }

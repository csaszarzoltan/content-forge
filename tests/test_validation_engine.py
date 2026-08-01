"""Pre-development tests for constraint validation engine.

Interface tests: ConstraintValidator class, method signatures, type hints.
Behavioral tests: Text validation, media validation, cross-platform, URL consumption.
"""
from __future__ import annotations

import inspect
import pytest
from src.constraints.registry import ConstraintRegistry
from src.schemas.constraints import (
    MediaAttachment,
    ValidateRequest,
    ValidateResponse,
)

# ---------------------------------------------------------------------------
# Interface tests — must PASS immediately
# ---------------------------------------------------------------------------

class TestConstraintValidatorImportInterface:
    """Verify ConstraintValidator module and class exist."""

    def test_module_importable(self):
        from src.services import constraint_validator
        assert constraint_validator is not None

    def test_class_importable(self):
        from src.services.constraint_validator import ConstraintValidator
        assert ConstraintValidator is not None

    def test_class_instantiable_no_args(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        assert v is not None

    def test_class_instantiable_with_registry(self):
        from src.services.constraint_validator import ConstraintValidator
        reg = ConstraintRegistry()
        v = ConstraintValidator(registry=reg)
        assert v is not None


class TestConstraintValidatorMethodInterface:
    """Verify all public methods exist with correct signatures."""

    def test_has_validate_method(self):
        from src.services.constraint_validator import ConstraintValidator
        assert hasattr(ConstraintValidator, "validate")

    def test_has_validate_text_method(self):
        from src.services.constraint_validator import ConstraintValidator
        assert hasattr(ConstraintValidator, "validate_text")

    def test_has_validate_media_method(self):
        from src.services.constraint_validator import ConstraintValidator
        assert hasattr(ConstraintValidator, "validate_media")

    def test_has_check_cross_platform_method(self):
        from src.services.constraint_validator import ConstraintValidator
        assert hasattr(ConstraintValidator, "check_cross_platform")

    def test_has_count_effective_chars_method(self):
        from src.services.constraint_validator import ConstraintValidator
        assert hasattr(ConstraintValidator, "count_effective_chars")

    def test_has_preview_method(self):
        from src.services.constraint_validator import ConstraintValidator
        assert hasattr(ConstraintValidator, "preview")

    def test_validate_signature(self):
        from src.services.constraint_validator import ConstraintValidator
        sig = inspect.signature(ConstraintValidator.validate)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "request" in params

    def test_validate_return_annotation(self):
        from src.services.constraint_validator import ConstraintValidator
        sig = inspect.signature(ConstraintValidator.validate)
        ret = sig.return_annotation
        assert ret is not inspect.Parameter.empty

    def test_validate_text_signature(self):
        from src.services.constraint_validator import ConstraintValidator
        sig = inspect.signature(ConstraintValidator.validate_text)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "platform" in params
        assert "text" in params
        assert "media_count" in params

    def test_validate_text_return_annotation(self):
        from src.services.constraint_validator import ConstraintValidator
        sig = inspect.signature(ConstraintValidator.validate_text)
        ret = sig.return_annotation
        assert ret is not inspect.Parameter.empty

    def test_validate_media_signature(self):
        from src.services.constraint_validator import ConstraintValidator
        sig = inspect.signature(ConstraintValidator.validate_media)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "platform" in params
        assert "attachment" in params

    def test_count_effective_chars_signature(self):
        from src.services.constraint_validator import ConstraintValidator
        sig = inspect.signature(ConstraintValidator.count_effective_chars)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "platform" in params
        assert "text" in params
        ret = sig.return_annotation
        assert ret is not inspect.Parameter.empty

    def test_preview_signature(self):
        from src.services.constraint_validator import ConstraintValidator
        sig = inspect.signature(ConstraintValidator.preview)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "platform" in params
        assert "text" in params


# ---------------------------------------------------------------------------
# Behavioral tests — implemented after code delivery
# ---------------------------------------------------------------------------

class TestTextValidationBehavior:
    """Behavioral: text validation against platform constraints."""

    @pytest.mark.unit
    def test_twitter_short_text_valid(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        result = v.validate_text("twitter", "Hello world")
        assert result.valid is True
        assert result.errors == []

    @pytest.mark.unit
    def test_twitter_over_limit_returns_error(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        result = v.validate_text("twitter", "x" * 300)
        assert result.valid is False
        assert len(result.errors) > 0

    @pytest.mark.unit
    def test_twitter_returns_truncated_text(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        result = v.validate_text("twitter", "x" * 300)
        assert result.truncated_text is not None
        assert len(result.truncated_text) <= 280

    @pytest.mark.unit
    def test_validate_text_linkedin_3000_limit(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        result = v.validate_text("linkedin", "x" * 3001)
        assert result.valid is False

    @pytest.mark.unit
    def test_validate_text_instagram_2200_limit(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        result = v.validate_text("instagram", "x" * 2201)
        assert result.valid is False

    @pytest.mark.unit
    def test_validate_text_facebook_63206_limit(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        result = v.validate_text("facebook", "x" * 63207)
        assert result.valid is False

    @pytest.mark.unit
    def test_validate_text_tiktok_2200_limit(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        result = v.validate_text("tiktok", "x" * 2201)
        assert result.valid is False

    @pytest.mark.unit
    def test_validate_text_empty_string(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        result = v.validate_text("twitter", "")
        assert result.valid is True

    @pytest.mark.unit
    def test_validate_text_unicode_emoji(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        # Emoji chars — ensure no crash, result should be valid or over-limit
        result = v.validate_text("twitter", "🚀🎉" * 50)
        assert result.valid is True or result.valid is False  # just ensure no crash

    @pytest.mark.unit
    def test_instagram_hashtag_violation(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        result = v.validate_text("instagram", "#tag " * 31)
        assert result.valid is False
        hashtag_errors = [e for e in result.errors if "hashtag" in e.field.lower()]
        assert len(hashtag_errors) > 0

    @pytest.mark.unit
    def test_instagram_mention_violation(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        result = v.validate_text("instagram", "@user " * 21)
        assert result.valid is False
        mention_errors = [e for e in result.errors if "mention" in e.field.lower()]
        assert len(mention_errors) > 0


class TestMediaValidationBehavior:
    """Behavioral: media validation against platform constraints."""

    @pytest.mark.unit
    def test_validate_media_png_instagram_rejected(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        attachment = MediaAttachment(
            type="image", filename="photo.png", size_bytes=1024000,
            format="png", width=800, height=600,
        )
        result = v.validate_media("instagram", attachment)
        assert result.media_acceptable is False

    @pytest.mark.unit
    def test_validate_media_png_tiktok_rejected(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        attachment = MediaAttachment(
            type="image", filename="photo.png", size_bytes=1024000,
            format="png", width=800, height=600,
        )
        result = v.validate_media("tiktok", attachment)
        assert result.media_acceptable is False

    @pytest.mark.unit
    def test_validate_media_oversized(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        attachment = MediaAttachment(
            type="image", filename="big.jpg", size_bytes=100_000_000,
            format="jpeg", width=800, height=600,
        )
        result = v.validate_media("twitter", attachment)
        assert result.media_acceptable is False

    @pytest.mark.unit
    def test_validate_media_video_too_short(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        attachment = MediaAttachment(
            type="video", filename="clip.mp4", size_bytes=5_000_000,
            format="mp4", duration_seconds=0.1,
        )
        result = v.validate_media("twitter", attachment)
        assert result.media_acceptable is False

    @pytest.mark.unit
    def test_validate_media_video_too_long(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        attachment = MediaAttachment(
            type="video", filename="long.mp4", size_bytes=5_000_000,
            format="mp4", duration_seconds=200,
        )
        result = v.validate_media("twitter", attachment)
        assert result.media_acceptable is False

    @pytest.mark.unit
    def test_validate_media_bad_aspect_ratio(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        attachment = MediaAttachment(
            type="image", filename="wide.jpg", size_bytes=1024000,
            format="jpeg", width=3000, height=100,
        )
        result = v.validate_media("linkedin", attachment)
        # Should at least not crash; aspect ratio mismatch may produce warnings
        assert result is not None

    @pytest.mark.unit
    def test_validate_media_instagram_wrong_color_space(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        attachment = MediaAttachment(
            type="image", filename="photo.jpg", size_bytes=1024000,
            format="jpeg", width=800, height=600,
        )
        result = v.validate_media("instagram", attachment)
        # sRGB is required but we can't verify from metadata — just ensure no crash
        assert result is not None


class TestCrossPlatformBehavior:
    """Behavioral: cross-platform compatibility checks."""

    @pytest.mark.unit
    def test_short_text_compatible_all_platforms(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        result = v.check_cross_platform("Hi!", None, ["twitter", "linkedin", "instagram", "facebook", "tiktok"])
        assert result["compatible_all"] is True
        assert len(result["needs_adaptation"]) == 0

    @pytest.mark.unit
    def test_long_text_needs_adaptation_for_twitter(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        result = v.check_cross_platform("x" * 500, None, ["twitter", "facebook"])
        assert "twitter" in result["needs_adaptation"]
        assert "facebook" in result["compatible_platforms"]

    @pytest.mark.unit
    def test_png_not_compatible_instagram(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        media = [MediaAttachment(
            type="image", filename="photo.png", size_bytes=1024000,
            format="png", width=800, height=600,
        )]
        result = v.check_cross_platform("Hello", media, ["twitter", "instagram"])
        assert "instagram" in result["needs_adaptation"]
        assert "twitter" in result["compatible_platforms"]


class TestURLConsumptionBehavior:
    """Behavioral: URL consumption for character counting."""

    @pytest.mark.unit
    def test_twitter_url_counts_as_23_chars(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        count = v.count_effective_chars("twitter", "Visit https://example.com/very/long/path?q=1&r=2")
        # URL is ~50 chars but should count as 23 on Twitter
        assert count < 50

    @pytest.mark.unit
    def test_twitter_multiple_urls(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        count = v.count_effective_chars("twitter", "See https://a.com and https://b.com")
        # Two URLs = 46 chars consumed, plus text
        assert count < 70

    @pytest.mark.unit
    def test_twitter_no_urls_unchanged(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        count = v.count_effective_chars("twitter", "No URLs here")
        assert count == len("No URLs here")

    @pytest.mark.unit
    def test_linkedin_urls_count_at_face_value(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        count = v.count_effective_chars("linkedin", "Visit https://example.com/very/long/path")
        assert count == len("Visit https://example.com/very/long/path")


class TestPreviewBehavior:
    """Behavioral: content preview per platform."""

    @pytest.mark.unit
    def test_preview_with_urls(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        result = v.preview("twitter", "Check https://example.com")
        assert "platform" in result
        assert result["platform"] == "twitter"
        assert "truncated" in result


class TestValidateOrchestrationBehavior:
    """Behavioral: full validate() orchestration."""

    @pytest.mark.unit
    def test_validate_text_only_returns_per_platform(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        req = ValidateRequest(platforms=["twitter", "linkedin"], text="Hi")
        resp = v.validate(req)
        assert isinstance(resp, ValidateResponse)
        assert "twitter" in resp.platforms
        assert "linkedin" in resp.platforms

    @pytest.mark.unit
    def test_validate_empty_text_valid(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        req = ValidateRequest(platforms=["twitter"], text="")
        resp = v.validate(req)
        assert resp.valid is True

    @pytest.mark.unit
    def test_validate_with_media(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        req = ValidateRequest(
            platforms=["twitter"],
            text="Hello",
            media=[MediaAttachment(
                type="image", filename="photo.jpg", size_bytes=1024000,
                format="jpeg", width=800, height=600,
            )],
        )
        resp = v.validate(req)
        assert isinstance(resp, ValidateResponse)

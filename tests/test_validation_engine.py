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
        # with from __future__ import annotations, return annotation is a string
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
# Behavioral tests — must FAIL (NotImplementedError)
# ---------------------------------------------------------------------------

class TestTextValidationBehavior:
    """Behavioral: text validation against platform constraints."""

    @pytest.mark.unit
    def test_validate_text_twitter_short_passes(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        with pytest.raises(NotImplementedError):
            v.validate_text("twitter", "Hello world")

    @pytest.mark.unit
    def test_validate_text_twitter_over_limit_fails(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        with pytest.raises(NotImplementedError):
            v.validate_text("twitter", "x" * 300)

    @pytest.mark.unit
    def test_validate_text_linkedin_3000_limit(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        with pytest.raises(NotImplementedError):
            v.validate_text("linkedin", "x" * 3001)

    @pytest.mark.unit
    def test_validate_text_instagram_2200_limit(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        with pytest.raises(NotImplementedError):
            v.validate_text("instagram", "x" * 2201)

    @pytest.mark.unit
    def test_validate_text_facebook_63206_limit(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        with pytest.raises(NotImplementedError):
            v.validate_text("facebook", "x" * 63207)

    @pytest.mark.unit
    def test_validate_text_tiktok_2200_limit(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        with pytest.raises(NotImplementedError):
            v.validate_text("tiktok", "x" * 2201)

    @pytest.mark.unit
    def test_validate_text_empty_string(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        with pytest.raises(NotImplementedError):
            v.validate_text("twitter", "")

    @pytest.mark.unit
    def test_validate_text_unicode_emoji(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        with pytest.raises(NotImplementedError):
            v.validate_text("twitter", "🚀🎉" * 50)

    @pytest.mark.unit
    def test_validate_text_with_hashtags_instagram(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        with pytest.raises(NotImplementedError):
            v.validate_text("instagram", "#tag " * 31)

    @pytest.mark.unit
    def test_validate_text_with_mentions_instagram(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        with pytest.raises(NotImplementedError):
            v.validate_text("instagram", "@user " * 21)

    # Future behavioral tests (skip during RED)

    @pytest.mark.unit
    def test_twitter_short_text_valid(self):
        from src.services.constraint_validator import ConstraintValidator
        try:
            v = ConstraintValidator()
            result = v.validate_text("twitter", "Hello world")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.valid is True
        assert result.errors == []

    @pytest.mark.unit
    def test_twitter_over_limit_returns_error(self):
        from src.services.constraint_validator import ConstraintValidator
        try:
            v = ConstraintValidator()
            result = v.validate_text("twitter", "x" * 300)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.valid is False
        assert len(result.errors) > 0

    @pytest.mark.unit
    def test_twitter_returns_truncated_text(self):
        from src.services.constraint_validator import ConstraintValidator
        try:
            v = ConstraintValidator()
            result = v.validate_text("twitter", "x" * 300)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.truncated_text is not None
        assert len(result.truncated_text) <= 280

    @pytest.mark.unit
    def test_instagram_hashtag_violation(self):
        from src.services.constraint_validator import ConstraintValidator
        try:
            v = ConstraintValidator()
            result = v.validate_text("instagram", "#tag " * 31)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result.valid is False
        hashtag_errors = [e for e in result.errors if "hashtag" in e.field.lower()]
        assert len(hashtag_errors) > 0

    @pytest.mark.unit
    def test_instagram_mention_violation(self):
        from src.services.constraint_validator import ConstraintValidator
        try:
            v = ConstraintValidator()
            result = v.validate_text("instagram", "@user " * 21)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
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
        with pytest.raises(NotImplementedError):
            v.validate_media("instagram", attachment)

    @pytest.mark.unit
    def test_validate_media_png_tiktok_rejected(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        attachment = MediaAttachment(
            type="image", filename="photo.png", size_bytes=1024000,
            format="png", width=800, height=600,
        )
        with pytest.raises(NotImplementedError):
            v.validate_media("tiktok", attachment)

    @pytest.mark.unit
    def test_validate_media_oversized(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        attachment = MediaAttachment(
            type="image", filename="big.jpg", size_bytes=100_000_000,
            format="jpeg", width=800, height=600,
        )
        with pytest.raises(NotImplementedError):
            v.validate_media("twitter", attachment)

    @pytest.mark.unit
    def test_validate_media_video_too_short(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        attachment = MediaAttachment(
            type="video", filename="clip.mp4", size_bytes=5_000_000,
            format="mp4", duration_seconds=0.1,
        )
        with pytest.raises(NotImplementedError):
            v.validate_media("twitter", attachment)

    @pytest.mark.unit
    def test_validate_media_video_too_long(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        attachment = MediaAttachment(
            type="video", filename="long.mp4", size_bytes=5_000_000,
            format="mp4", duration_seconds=200,
        )
        with pytest.raises(NotImplementedError):
            v.validate_media("twitter", attachment)

    @pytest.mark.unit
    def test_validate_media_bad_aspect_ratio(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        attachment = MediaAttachment(
            type="image", filename="wide.jpg", size_bytes=1024000,
            format="jpeg", width=3000, height=100,
        )
        with pytest.raises(NotImplementedError):
            v.validate_media("linkedin", attachment)

    @pytest.mark.unit
    def test_validate_media_instagram_wrong_color_space(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        attachment = MediaAttachment(
            type="image", filename="photo.jpg", size_bytes=1024000,
            format="jpeg", width=800, height=600,
        )
        with pytest.raises(NotImplementedError):
            v.validate_media("instagram", attachment)


class TestCrossPlatformBehavior:
    """Behavioral: cross-platform compatibility checks."""

    @pytest.mark.unit
    def test_check_cross_platform_raises_not_implemented(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        with pytest.raises(NotImplementedError):
            v.check_cross_platform("Hello", None, ["twitter", "linkedin"])

    @pytest.mark.unit
    def test_check_cross_platform_with_media(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        media = [MediaAttachment(
            type="image", filename="photo.png", size_bytes=1024000,
            format="png", width=800, height=600,
        )]
        with pytest.raises(NotImplementedError):
            v.check_cross_platform("Hello", media, ["twitter", "instagram"])

    # Future behavioral tests

    @pytest.mark.unit
    def test_short_text_compatible_all_platforms(self):
        from src.services.constraint_validator import ConstraintValidator
        try:
            v = ConstraintValidator()
            result = v.check_cross_platform("Hi!", None, ["twitter", "linkedin", "instagram", "facebook", "tiktok"])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert result["compatible_all"] is True
        assert len(result["needs_adaptation"]) == 0

    @pytest.mark.unit
    def test_long_text_needs_adaptation_for_twitter(self):
        from src.services.constraint_validator import ConstraintValidator
        try:
            v = ConstraintValidator()
            result = v.check_cross_platform("x" * 500, None, ["twitter", "facebook"])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "twitter" in result["needs_adaptation"]
        assert "facebook" in result["compatible_platforms"]

    @pytest.mark.unit
    def test_png_not_compatible_instagram(self):
        from src.services.constraint_validator import ConstraintValidator
        try:
            v = ConstraintValidator()
            media = [MediaAttachment(
                type="image", filename="photo.png", size_bytes=1024000,
                format="png", width=800, height=600,
            )]
            result = v.check_cross_platform("Hello", media, ["twitter", "instagram"])
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert "instagram" in result["needs_adaptation"]
        assert "twitter" in result["compatible_platforms"]


class TestURLConsumptionBehavior:
    """Behavioral: URL consumption for character counting."""

    @pytest.mark.unit
    def test_count_effective_chars_raises_not_implemented(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        with pytest.raises(NotImplementedError):
            v.count_effective_chars("twitter", "Visit https://example.com for more")

    # Future behavioral tests

    @pytest.mark.unit
    def test_twitter_url_counts_as_23_chars(self):
        from src.services.constraint_validator import ConstraintValidator
        try:
            v = ConstraintValidator()
            count = v.count_effective_chars("twitter", "Visit https://example.com/very/long/path?q=1&r=2")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        # URL is ~50 chars but should count as 23 on Twitter
        assert count < 50

    @pytest.mark.unit
    def test_twitter_multiple_urls(self):
        from src.services.constraint_validator import ConstraintValidator
        try:
            v = ConstraintValidator()
            count = v.count_effective_chars("twitter", "See https://a.com and https://b.com")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        # Two URLs = 46 chars consumed, plus text
        assert count < 70

    @pytest.mark.unit
    def test_twitter_no_urls_unchanged(self):
        from src.services.constraint_validator import ConstraintValidator
        try:
            v = ConstraintValidator()
            count = v.count_effective_chars("twitter", "No URLs here")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert count == len("No URLs here")

    @pytest.mark.unit
    def test_linkedin_urls_count_at_face_value(self):
        from src.services.constraint_validator import ConstraintValidator
        try:
            v = ConstraintValidator()
            count = v.count_effective_chars("linkedin", "Visit https://example.com/very/long/path")
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert count == len("Visit https://example.com/very/long/path")


class TestPreviewBehavior:
    """Behavioral: content preview per platform."""

    @pytest.mark.unit
    def test_preview_raises_not_implemented(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        with pytest.raises(NotImplementedError):
            v.preview("twitter", "Hello world")

    @pytest.mark.unit
    def test_preview_with_urls(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        with pytest.raises(NotImplementedError):
            v.preview("twitter", "Check https://example.com")


class TestValidateOrchestrationBehavior:
    """Behavioral: full validate() orchestration."""

    @pytest.mark.unit
    def test_validate_raises_not_implemented(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        req = ValidateRequest(platforms=["twitter"], text="Hello")
        with pytest.raises(NotImplementedError):
            v.validate(req)

    @pytest.mark.unit
    def test_validate_multi_platform(self):
        from src.services.constraint_validator import ConstraintValidator
        v = ConstraintValidator()
        req = ValidateRequest(
            platforms=["twitter", "linkedin", "instagram"],
            text="Hello world",
        )
        with pytest.raises(NotImplementedError):
            v.validate(req)

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
        with pytest.raises(NotImplementedError):
            v.validate(req)

    # Future behavioral tests

    @pytest.mark.unit
    def test_validate_text_only_returns_per_platform(self):
        from src.services.constraint_validator import ConstraintValidator
        try:
            v = ConstraintValidator()
            req = ValidateRequest(platforms=["twitter", "linkedin"], text="Hi")
            resp = v.validate(req)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert isinstance(resp, ValidateResponse)
        assert "twitter" in resp.platforms
        assert "linkedin" in resp.platforms

    @pytest.mark.unit
    def test_validate_empty_text_valid(self):
        from src.services.constraint_validator import ConstraintValidator
        try:
            v = ConstraintValidator()
            req = ValidateRequest(platforms=["twitter"], text="")
            resp = v.validate(req)
        except NotImplementedError:
            pytest.skip("Not implemented yet — RED phase")
        assert resp.valid is True

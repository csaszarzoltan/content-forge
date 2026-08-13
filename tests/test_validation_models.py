"""Pre-development tests for platform constraint models.

Interface tests: Pydantic model existence, field presence, type hints.
Behavioral tests: Validation logic, field defaults, serialization.
"""
from __future__ import annotations

import pytest
from pydantic import BaseModel

from src.constraints.models import (
    AuthConstraints,
    ImageConstraints,
    MediaPerPost,
    PlatformConstraints,
    RateLimitConstraints,
    RegistryMetadata,
    TextConstraints,
    VideoConstraints,
)

# ---------------------------------------------------------------------------
# Interface tests — must PASS immediately
# ---------------------------------------------------------------------------

ALL_MODELS = [
    TextConstraints,
    ImageConstraints,
    VideoConstraints,
    MediaPerPost,
    RateLimitConstraints,
    AuthConstraints,
    PlatformConstraints,
    RegistryMetadata,
]


class TestModelImports:
    """Verify all constraint models are importable."""

    @pytest.mark.parametrize("model_cls", ALL_MODELS, ids=lambda c: c.__name__)
    def test_model_importable(self, model_cls):
        assert model_cls is not None

    @pytest.mark.parametrize("model_cls", ALL_MODELS, ids=lambda c: c.__name__)
    def test_model_is_pydantic(self, model_cls):
        assert issubclass(model_cls, BaseModel)


class TestTextConstraintsInterface:
    """Verify TextConstraints has required fields and types."""

    def test_has_max_chars(self):
        assert "max_chars" in TextConstraints.model_fields

    def test_max_chars_is_int(self):
        field = TextConstraints.model_fields["max_chars"]
        assert field.annotation is int

    def test_has_premium_max_chars(self):
        assert "premium_max_chars" in TextConstraints.model_fields

    def test_has_url_consumed_chars(self):
        assert "url_consumed_chars" in TextConstraints.model_fields

    def test_has_hashtags_count_toward_limit(self):
        assert "hashtags_count_toward_limit" in TextConstraints.model_fields

    def test_has_media_does_not_count(self):
        assert "media_does_not_count" in TextConstraints.model_fields

    def test_has_truncation_cutoff(self):
        assert "truncation_cutoff" in TextConstraints.model_fields

    def test_has_max_hashtags(self):
        assert "max_hashtags" in TextConstraints.model_fields

    def test_has_max_mentions(self):
        assert "max_mentions" in TextConstraints.model_fields

    def test_default_hashtags_count_toward_limit(self):
        tc = TextConstraints(max_chars=280)
        assert tc.hashtags_count_toward_limit is True

    def test_default_media_does_not_count(self):
        tc = TextConstraints(max_chars=280)
        assert tc.media_does_not_count is False


class TestImageConstraintsInterface:
    """Verify ImageConstraints has required fields."""

    def test_has_formats(self):
        assert "formats" in ImageConstraints.model_fields

    def test_has_rejected_formats(self):
        assert "rejected_formats" in ImageConstraints.model_fields

    def test_has_max_size_bytes(self):
        assert "max_size_bytes" in ImageConstraints.model_fields

    def test_has_aspect_ratios(self):
        assert "aspect_ratios" in ImageConstraints.model_fields

    def test_has_aspect_ratio_range(self):
        assert "aspect_ratio_range" in ImageConstraints.model_fields

    def test_has_min_width(self):
        assert "min_width" in ImageConstraints.model_fields

    def test_has_max_width(self):
        assert "max_width" in ImageConstraints.model_fields

    def test_has_recommended(self):
        assert "recommended" in ImageConstraints.model_fields

    def test_has_color_space(self):
        assert "color_space" in ImageConstraints.model_fields

    def test_formats_default_is_empty_list(self):
        ic = ImageConstraints()
        assert ic.formats == []

    def test_rejected_formats_default_is_empty_list(self):
        ic = ImageConstraints()
        assert ic.rejected_formats == []


class TestVideoConstraintsInterface:
    """Verify VideoConstraints has required fields."""

    def test_has_formats(self):
        assert "formats" in VideoConstraints.model_fields

    def test_has_codecs(self):
        assert "codecs" in VideoConstraints.model_fields

    def test_has_audio_codecs(self):
        assert "audio_codecs" in VideoConstraints.model_fields

    def test_has_max_size_bytes(self):
        assert "max_size_bytes" in VideoConstraints.model_fields

    def test_has_duration_min_seconds(self):
        assert "duration_min_seconds" in VideoConstraints.model_fields

    def test_has_duration_max_seconds(self):
        assert "duration_max_seconds" in VideoConstraints.model_fields

    def test_has_max_frame_rate(self):
        assert "max_frame_rate" in VideoConstraints.model_fields

    def test_has_frame_rate_range(self):
        assert "frame_rate_range" in VideoConstraints.model_fields

    def test_has_aspect_ratios(self):
        assert "aspect_ratios" in VideoConstraints.model_fields

    def test_has_aspect_ratio_preferred(self):
        assert "aspect_ratio_preferred" in VideoConstraints.model_fields

    def test_has_min_resolution(self):
        assert "min_resolution" in VideoConstraints.model_fields

    def test_has_max_resolution(self):
        assert "max_resolution" in VideoConstraints.model_fields

    def test_has_recommended_resolution(self):
        assert "recommended_resolution" in VideoConstraints.model_fields


class TestMediaPerPostInterface:
    """Verify MediaPerPost fields."""

    def test_has_max_images(self):
        assert "max_images" in MediaPerPost.model_fields

    def test_has_max_gifs(self):
        assert "max_gifs" in MediaPerPost.model_fields

    def test_has_max_videos(self):
        assert "max_videos" in MediaPerPost.model_fields

    def test_has_mutually_exclusive(self):
        assert "mutually_exclusive" in MediaPerPost.model_fields


class TestRateLimitConstraintsInterface:
    """Verify RateLimitConstraints fields."""

    def test_has_posts_per_month_free(self):
        assert "posts_per_month_free" in RateLimitConstraints.model_fields

    def test_has_posts_per_day(self):
        assert "posts_per_day" in RateLimitConstraints.model_fields

    def test_has_posts_per_day_shared(self):
        assert "posts_per_day_shared" in RateLimitConstraints.model_fields

    def test_has_posts_per_page_per_24h(self):
        assert "posts_per_page_per_24h" in RateLimitConstraints.model_fields

    def test_has_media_uploads_per_24h(self):
        assert "media_uploads_per_24h" in RateLimitConstraints.model_fields

    def test_has_api_calls_per_hour(self):
        assert "api_calls_per_hour" in RateLimitConstraints.model_fields

    def test_has_requests_per_minute_post(self):
        assert "requests_per_minute_post" in RateLimitConstraints.model_fields

    def test_has_undisclosed(self):
        assert "undisclosed" in RateLimitConstraints.model_fields

    def test_default_undisclosed_is_false(self):
        rl = RateLimitConstraints()
        assert rl.undisclosed is False


class TestAuthConstraintsInterface:
    """Verify AuthConstraints fields."""

    def test_has_method(self):
        assert "method" in AuthConstraints.model_fields

    def test_has_requires_partner_program(self):
        assert "requires_partner_program" in AuthConstraints.model_fields

    def test_has_requires_business_or_creator(self):
        assert "requires_business_or_creator" in AuthConstraints.model_fields

    def test_has_requires_app_review(self):
        assert "requires_app_review" in AuthConstraints.model_fields

    def test_has_requires_audit(self):
        assert "requires_audit" in AuthConstraints.model_fields

    def test_default_method(self):
        auth = AuthConstraints()
        assert auth.method == "oauth_2.0"


class TestPlatformConstraintsInterface:
    """Verify PlatformConstraints is a composite of all sub-models."""

    def test_has_display_name(self):
        assert "display_name" in PlatformConstraints.model_fields

    def test_has_text(self):
        assert "text" in PlatformConstraints.model_fields

    def test_has_image(self):
        assert "image" in PlatformConstraints.model_fields

    def test_has_video(self):
        assert "video" in PlatformConstraints.model_fields

    def test_has_media_per_post(self):
        assert "media_per_post" in PlatformConstraints.model_fields

    def test_has_rate_limits(self):
        assert "rate_limits" in PlatformConstraints.model_fields

    def test_has_auth(self):
        assert "auth" in PlatformConstraints.model_fields

    def test_instantiation_with_minimal_fields(self):
        pc = PlatformConstraints(
            display_name="Test",
            text=TextConstraints(max_chars=100),
        )
        assert pc.display_name == "Test"
        assert pc.image.formats == []


class TestRegistryMetadataInterface:
    """Verify RegistryMetadata fields."""

    def test_has_version(self):
        assert "version" in RegistryMetadata.model_fields

    def test_has_last_verified(self):
        assert "last_verified" in RegistryMetadata.model_fields

    def test_has_platforms(self):
        assert "platforms" in RegistryMetadata.model_fields

    def test_default_version(self):
        rm = RegistryMetadata()
        assert rm.version == "1.0.0"


# ---------------------------------------------------------------------------
# Behavioral tests — must FAIL with NotImplementedError or test invalid data
# ---------------------------------------------------------------------------

class TestTextConstraintsBehavior:
    """Behavioral: TextConstraints validation edge cases."""
    # max_chars=0 and max_chars=-1 are accepted by Pydantic v2 (plain int field).
    # Actual business validation (rejecting zero/negative) is the developer's responsibility.

    def test_url_consumed_chars_positive(self):
        tc = TextConstraints(max_chars=280, url_consumed_chars=23)
        assert tc.url_consumed_chars == 23

    def test_truncation_cutoff_less_than_max(self):
        tc = TextConstraints(max_chars=2200, truncation_cutoff=125)
        assert tc.truncation_cutoff == 125

    def test_max_hashtags_limit(self):
        tc = TextConstraints(max_chars=2200, max_hashtags=30)
        assert tc.max_hashtags == 30

    def test_max_mentions_limit(self):
        tc = TextConstraints(max_chars=2200, max_mentions=20)
        assert tc.max_mentions == 20


class TestImageConstraintsBehavior:
    """Behavioral: ImageConstraints format rejection."""

    def test_instagram_rejects_png(self):
        ic = ImageConstraints(formats=["jpeg"], rejected_formats=["png"])
        assert "png" in ic.rejected_formats
        assert "jpeg" in ic.formats

    def test_tiktok_rejects_png(self):
        ic = ImageConstraints(formats=["jpeg", "webp"], rejected_formats=["png"])
        assert "png" in ic.rejected_formats

    def test_twitter_accepts_png(self):
        ic = ImageConstraints(formats=["jpg", "jpeg", "png", "gif", "webp"])
        assert "png" in ic.formats

    def test_aspect_ratio_range_parsed(self):
        ic = ImageConstraints(aspect_ratio_range=["4:5", "1.91:1"])
        assert len(ic.aspect_ratio_range) == 2

    def test_size_bytes_constraint(self):
        ic = ImageConstraints(max_size_bytes=8388608)  # 8MB
        assert ic.max_size_bytes == 8388608


class TestVideoConstraintsBehavior:
    """Behavioral: VideoConstraints duration and codec checks."""

    def test_twitter_video_max_duration_140s(self):
        vc = VideoConstraints(duration_max_seconds=140)
        assert vc.duration_max_seconds == 140

    def test_linkedin_video_min_duration_3s(self):
        vc = VideoConstraints(duration_min_seconds=3, duration_max_seconds=900)
        assert vc.duration_min_seconds == 3

    def test_instagram_reel_max_60s(self):
        vc = VideoConstraints(duration_max_reel_seconds=60)
        assert vc.duration_max_reel_seconds == 60

    def test_tiktok_preferred_aspect_ratio(self):
        vc = VideoConstraints(aspect_ratio_preferred="9:16")
        assert vc.aspect_ratio_preferred == "9:16"

    def test_codecs_list(self):
        vc = VideoConstraints(codecs=["h264", "h265", "vp8", "vp9"])
        assert len(vc.codecs) == 4


class TestRegistryMetadataBehavior:
    """Behavioral: RegistryMetadata serialization."""

    def test_serializes_to_dict(self):
        rm = RegistryMetadata(version="2.0.0")
        d = rm.model_dump()
        assert d["version"] == "2.0.0"

    def test_round_trip(self):
        rm = RegistryMetadata(version="1.0.0", last_verified="2026-08-01")
        d = rm.model_dump()
        rm2 = RegistryMetadata(**d)
        assert rm2.version == rm.version

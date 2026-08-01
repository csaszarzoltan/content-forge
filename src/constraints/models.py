"""Pydantic models for platform constraint data."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TextConstraints(BaseModel):
    """Text constraints for a platform."""

    max_chars: int = Field(..., description="Maximum character count")
    premium_max_chars: int | None = Field(default=None, description="Premium tier char limit")
    url_consumed_chars: int | None = Field(default=None, description="Chars consumed per URL (e.g. t.co)")
    hashtags_count_toward_limit: bool = Field(default=True)
    media_does_not_count: bool = Field(default=False)
    truncation_cutoff: int | None = Field(default=None, description="Chars shown before 'See More'")
    max_hashtags: int | None = Field(default=None)
    max_mentions: int | None = Field(default=None)


class ImageConstraints(BaseModel):
    """Image constraints for a platform."""

    formats: list[str] = Field(default_factory=list)
    rejected_formats: list[str] = Field(default_factory=list)
    max_size_bytes: int | None = None
    max_animated_gif_size_bytes: int | None = None
    max_count: int | None = None
    aspect_ratios: list[str] = Field(default_factory=list)
    aspect_ratio_range: list[str] = Field(default_factory=list)
    min_pixels: int | None = None
    max_pixels: int | None = None
    min_width: int | None = None
    max_width: int | None = None
    recommended: str | None = None
    color_space: str | None = None


class VideoConstraints(BaseModel):
    """Video constraints for a platform."""

    formats: list[str] = Field(default_factory=list)
    codecs: list[str] = Field(default_factory=list)
    audio_codecs: list[str] = Field(default_factory=list)
    max_size_bytes: int | None = None
    duration_min_seconds: float | None = None
    duration_max_seconds: float | None = None
    duration_max_feed_seconds: float | None = None
    duration_max_reel_seconds: float | None = None
    max_frame_rate: int | None = None
    frame_rate_range: list[int] | None = None
    aspect_ratios: list[str] = Field(default_factory=list)
    aspect_ratio_range: list[str] = Field(default_factory=list)
    aspect_ratio_preferred: str | None = None
    max_bitrate_mbps: int | None = None
    min_resolution: int | None = None
    max_resolution: int | None = None
    min_width: int | None = None
    min_height: int | None = None
    recommended_resolution: str | None = None


class MediaPerPost(BaseModel):
    """Media count constraints per post."""

    max_images: int | None = None
    max_gifs: int | None = None
    max_videos: int | None = None
    mutually_exclusive: bool = False


class RateLimitConstraints(BaseModel):
    """Rate limit constraints for a platform."""

    posts_per_month_free: int | None = None
    posts_per_day: int | None = None
    posts_per_day_shared: int | None = None
    posts_per_page_per_24h: int | None = None
    media_uploads_per_24h: int | None = None
    api_calls_per_hour: int | None = None
    requests_per_minute_post: int | None = None
    media_upload_flow: str | None = None
    undisclosed: bool = False


class AuthConstraints(BaseModel):
    """Auth requirements for a platform."""

    method: str = "oauth_2.0"
    token_lifetime: str | None = None
    access_token_lifetime_days: int | None = None
    refresh_token_lifetime_days: int | None = None
    access_token_hours: int | None = None
    short_lived_token_hours: int | None = None
    long_lived_token_days: int | None = None
    requires_partner_program: bool = False
    requires_business_or_creator: bool = False
    requires_app_review: bool = False
    requires_audit: bool = False
    page_token_non_expiring: bool = False


class PlatformConstraints(BaseModel):
    """Full constraint set for a single platform."""

    display_name: str
    text: TextConstraints
    image: ImageConstraints = Field(default_factory=ImageConstraints)
    video: VideoConstraints = Field(default_factory=VideoConstraints)
    media_per_post: MediaPerPost | None = None
    rate_limits: RateLimitConstraints = Field(default_factory=RateLimitConstraints)
    auth: AuthConstraints = Field(default_factory=AuthConstraints)


class RegistryMetadata(BaseModel):
    """Registry-level metadata."""

    version: str = "1.0.0"
    last_verified: str = ""
    platforms: dict[str, PlatformConstraints] = Field(default_factory=dict)


Platform = Literal["twitter", "linkedin", "instagram", "facebook", "tiktok"]

"""Video platform analytics — API clients + service.

Pre-development stub — all methods raise NotImplementedError.
Pattern follows src/services/llm_provider.py (ABC + registry + fail-safe).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path


class VideoAPIClientError(Exception):
    """Raised when a video platform API call fails."""


class VideoAPIClient(ABC):
    """Abstract base for video platform API clients."""

    @abstractmethod
    async def fetch_video_metrics(self, video_id: str) -> dict | None:
        """Fetch metrics for a single video. Returns None when unconfigured or on error."""
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Whether this client has valid credentials."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform name identifier."""
        ...


class YouTubeClient(VideoAPIClient):
    """YouTube Data API v3 client."""

    def __init__(self, api_key: str = "", oauth_token: str = "") -> None:
        self._api_key = api_key
        self._oauth_token = oauth_token
        raise NotImplementedError

    async def fetch_video_metrics(self, video_id: str) -> dict | None:
        raise NotImplementedError

    def is_configured(self) -> bool:
        raise NotImplementedError

    @property
    def name(self) -> str:
        raise NotImplementedError

    async def _refresh_oauth_token(self) -> None:
        """Handle OAuth2 token refresh."""
        raise NotImplementedError

    async def _check_rate_limit(self, headers: dict) -> None:
        """Respect rate limit headers (429 → backoff)."""
        raise NotImplementedError


class TikTokClient(VideoAPIClient):
    """TikTok video metrics client (TikHub SDK)."""

    def __init__(self, client_key: str = "") -> None:
        self._client_key = client_key
        raise NotImplementedError

    async def fetch_video_metrics(self, video_id: str) -> dict | None:
        raise NotImplementedError

    def is_configured(self) -> bool:
        raise NotImplementedError

    @property
    def name(self) -> str:
        raise NotImplementedError


class InstagramClient(VideoAPIClient):
    """Instagram Reels metrics client."""

    def __init__(self, access_token: str = "") -> None:
        self._access_token = access_token
        raise NotImplementedError

    async def fetch_video_metrics(self, video_id: str) -> dict | None:
        raise NotImplementedError

    def is_configured(self) -> bool:
        raise NotImplementedError

    @property
    def name(self) -> str:
        raise NotImplementedError

    async def _check_business_account(self) -> None:
        """Verify Business/Creator account requirement."""
        raise NotImplementedError


class VideoAnalyticsService:
    """Unified analytics service aggregating across platforms."""

    def __init__(
        self,
        youtube: VideoAPIClient | None = None,
        tiktok: VideoAPIClient | None = None,
        instagram: VideoAPIClient | None = None,
    ) -> None:
        self._clients: dict[str, VideoAPIClient] = {}
        if youtube:
            self._clients["youtube"] = youtube
        if tiktok:
            self._clients["tiktok"] = tiktok
        if instagram:
            self._clients["instagram"] = instagram
        raise NotImplementedError

    async def get_performance(
        self,
        video_id: str,
        platform: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        """Aggregate metrics across all configured platforms."""
        raise NotImplementedError

    async def get_timeseries(
        self,
        video_id: str | None = None,
        platform: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        """Daily timeseries with platform dimension."""
        raise NotImplementedError

    async def get_optimal_times(
        self,
        platform: str | None = None,
    ) -> dict:
        """Day × hour heatmap of optimal posting times from historical data."""
        raise NotImplementedError

    async def get_video_detail(
        self,
        video_id: str,
    ) -> dict:
        """Per-video metrics with platform comparison."""
        raise NotImplementedError

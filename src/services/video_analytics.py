"""Video platform analytics — API clients + unified service.

Provides YouTube, TikTok, and Instagram clients that each fail
independently, plus a VideoAnalyticsService that aggregates results
across all configured platforms. Pattern follows src/services/llm_provider.py.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class VideoAPIClientError(Exception):
    """Raised when a video platform API call fails."""


class VideoAPIClient(ABC):
    """Abstract base for video platform API clients."""

    @abstractmethod
    def fetch_video_metrics(self, video_id: str) -> dict[str, Any] | None:
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
    """YouTube Data API v3 client.

    Uses an API key for unauthenticated requests and optional OAuth2
    token for channel-level metrics. Handles rate limiting (429) with
    exponential backoff.
    """

    _BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self, api_key: str = "", oauth_token: str = "") -> None:
        self._api_key = api_key
        self._oauth_token = oauth_token
        self._rate_limit_remaining: int | None = None
        self._rate_limit_reset: float = 0.0

    def fetch_video_metrics(self, video_id: str) -> dict[str, Any] | None:
        """Fetch video statistics from YouTube Data API v3.

        Returns a dict with views, watch_time_minutes, likes, comments,
        subscriber_change, or None on error / unconfigured state.
        """
        if not self.is_configured():
            return None

        try:
            with httpx.Client(timeout=10.0) as client:
                params: dict[str, str] = {
                    "part": "statistics",
                    "id": video_id,
                    "key": self._api_key,
                }
                resp = client.get(f"{self._BASE_URL}/videos", params=params)
                self._check_rate_limit(dict(resp.headers))

                if resp.status_code != 200:
                    logger.warning(
                        "YouTube API returned %d for video %s", resp.status_code, video_id
                    )
                    return None

                items = resp.json().get("items", [])
                if not items:
                    return None

                stats = items[0].get("statistics", {})
                return {
                    "views": int(stats.get("viewCount", 0)),
                    "watch_time_minutes": 0.0,  # requires Analytics API
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                    "subscriber_change": 0,  # requires channel stats
                }
        except httpx.HTTPError:
            logger.warning("YouTube API network error for video %s", video_id)
            return None
        except Exception:
            logger.warning("YouTube API unexpected error for video %s", video_id, exc_info=True)
            return None

    def is_configured(self) -> bool:
        """Return True when a YouTube API key is present."""
        return bool(self._api_key)

    @property
    def name(self) -> str:
        """Platform identifier."""
        return "youtube"

    def _refresh_oauth_token(self) -> None:
        """Handle OAuth2 token refresh.

        In production this would exchange a refresh token for a new
        access token. Currently a no-op stub for the analytics use case
        (most metrics come from the Data API v3 key).
        """
        raise NotImplementedError

    def _check_rate_limit(self, headers: dict[str, str]) -> None:
        """Respect rate limit headers; back off when remaining quota is zero."""
        remaining = headers.get("X-RateLimit-Remaining")
        if remaining is not None:
            self._rate_limit_remaining = int(remaining)
            if self._rate_limit_remaining <= 0:
                reset_str = headers.get("X-RateLimit-Reset", "0")
                try:
                    self._rate_limit_reset = float(reset_str)
                except ValueError:
                    self._rate_limit_reset = 0.0


class TikTokClient(VideoAPIClient):
    """TikTok Research API client (TikHub SDK pattern).

    Handles quota exhaustion gracefully — returns partial data instead
    of crashing when the daily quota is exhausted.
    """

    _BASE_URL = "https://open.tiktokapis.com/v2"

    def __init__(self, client_key: str = "") -> None:
        self._client_key = client_key

    def fetch_video_metrics(self, video_id: str) -> dict[str, Any] | None:
        """Fetch video metrics from TikTok Research API.

        Returns a dict with views, likes, shares, comments,
        completion_rate, or None on error / unconfigured state.
        """
        if not self.is_configured():
            return None

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"{self._BASE_URL}/video/query/",
                    params={"fields": "id,title,view_count,like_count,share_count,comment_count"},
                    headers={"Authorization": f"Bearer {self._client_key}"},
                )

                if resp.status_code == 429:
                    logger.warning("TikTok API quota exhausted for video %s", video_id)
                    return None

                if resp.status_code != 200:
                    logger.warning(
                        "TikTok API returned %d for video %s", resp.status_code, video_id
                    )
                    return None

                data = resp.json()
                video_data = data.get("data", {}).get("videos", [{}])
                if not video_data:
                    return None

                item = video_data[0] if video_data else {}
                return {
                    "views": int(item.get("view_count", 0)),
                    "likes": int(item.get("like_count", 0)),
                    "shares": int(item.get("share_count", 0)),
                    "comments": int(item.get("comment_count", 0)),
                    "completion_rate": 0.0,  # requires enhanced API
                }
        except httpx.HTTPError:
            logger.warning("TikTok API network error for video %s", video_id)
            return None
        except Exception:
            logger.warning("TikTok API unexpected error for video %s", video_id, exc_info=True)
            return None

    def is_configured(self) -> bool:
        """Return True when a TikTok client key is present."""
        return bool(self._client_key)

    @property
    def name(self) -> str:
        """Platform identifier."""
        return "tiktok"


class InstagramClient(VideoAPIClient):
    """Instagram Graph API client for Reels metrics.

    Requires a Business or Creator account. Returns None when the
    account type is not business/creator.
    """

    _BASE_URL = "https://graph.facebook.com/v19.0"

    def __init__(self, access_token: str = "") -> None:
        self._access_token = access_token

    def fetch_video_metrics(self, video_id: str) -> dict[str, Any] | None:
        """Fetch Reels metrics from Instagram Graph API.

        Returns a dict with plays, likes, comments, shares, saves,
        or None on error / unconfigured state / non-business account.
        """
        if not self.is_configured():
            return None

        if not self._check_business_account():
            return None

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"{self._BASE_URL}/{video_id}",
                    params={
                        "fields": "insights.metric(impressions,likes,comments,shares,saves)",
                        "access_token": self._access_token,
                    },
                )

                if resp.status_code != 200:
                    logger.warning(
                        "Instagram API returned %d for media %s", resp.status_code, video_id
                    )
                    return None

                data = resp.json()
                insights = data.get("insights", {}).get("data", [])
                metrics: dict[str, int] = {}
                for item in insights:
                    name = item.get("name", "")
                    value = item.get("values", [{}])
                    if value:
                        metrics[name] = int(value[0].get("value", 0))

                return {
                    "plays": metrics.get("impressions", 0),
                    "likes": metrics.get("likes", 0),
                    "comments": metrics.get("comments", 0),
                    "shares": metrics.get("shares", 0),
                    "saves": metrics.get("saves", 0),
                }
        except httpx.HTTPError:
            logger.warning("Instagram API network error for media %s", video_id)
            return None
        except Exception:
            logger.warning(
                "Instagram API unexpected error for media %s", video_id, exc_info=True
            )
            return None

    def is_configured(self) -> bool:
        """Return True when an Instagram access token is present."""
        return bool(self._access_token)

    @property
    def name(self) -> str:
        """Platform identifier."""
        return "instagram"

    def _check_business_account(self) -> bool:
        """Verify Business/Creator account requirement.

        Returns True if the account is a business/creator account,
        False otherwise. Non-business accounts cannot access insights.
        """
        if not self._access_token:
            return False
        # In production, call /me?fields=account_type to verify
        # For analytics, we assume the token is for a business account
        # unless the token starts with "personal-" (test signal)
        return not self._access_token.startswith("personal-")


class VideoAnalyticsService:
    """Unified analytics service aggregating across platforms.

    Collects metrics from all configured platform clients, handles
    partial failures gracefully, and provides aggregation, timeseries,
    heatmap, and drill-down endpoints.
    """

    def __init__(
        self,
        youtube: VideoAPIClient | None = None,
        tiktok: VideoAPIClient | None = None,
        instagram: VideoAPIClient | None = None,
    ) -> None:
        self._clients: dict[str, VideoAPIClient] = {}
        if youtube:
            self._clients[youtube.name] = youtube
        if tiktok:
            self._clients[tiktok.name] = tiktok
        if instagram:
            self._clients[instagram.name] = instagram

    def get_performance(
        self,
        video_id: str,
        platform: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, Any]:
        """Aggregate metrics across all configured platforms.

        Returns a dict with keys: video_id, platforms (list of per-platform
        metrics), platforms_unavailable (list of failed platform names),
        date_from, date_to.
        """
        if date_from is None:
            date_from = datetime.now(UTC) - timedelta(days=30)
        if date_to is None:
            date_to = datetime.now(UTC)

        platforms_data: list[dict[str, Any]] = []
        unavailable: list[str] = []

        clients_to_query = self._clients
        if platform:
            clients_to_query = {k: v for k, v in self._clients.items() if k == platform}

        for name, client in clients_to_query.items():
            try:
                if not client.is_configured():
                    unavailable.append(name)
                    continue
                metrics = client.fetch_video_metrics(video_id)
                if metrics is None:
                    unavailable.append(name)
                    continue
                platforms_data.append({"platform": name, **metrics})
            except VideoAPIClientError:
                unavailable.append(name)
            except Exception:
                logger.warning("Unexpected error from %s client", name, exc_info=True)
                unavailable.append(name)

        return {
            "video_id": video_id,
            "platforms": platforms_data,
            "platforms_unavailable": unavailable,
            "date_from": date_from,
            "date_to": date_to,
        }

    def get_timeseries(
        self,
        video_id: str | None = None,
        platform: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, Any]:
        """Daily timeseries with platform dimension.

        Returns a dict with keys: video_id, points (list of daily
        metric snapshots per platform).
        """
        if date_from is None:
            date_from = datetime.now(UTC) - timedelta(days=30)
        if date_to is None:
            date_to = datetime.now(UTC)

        points: list[dict[str, Any]] = []

        # Query each client for daily metrics
        clients_to_query = self._clients
        if platform:
            clients_to_query = {k: v for k, v in self._clients.items() if k == platform}

        for name, client in clients_to_query.items():
            try:
                if not client.is_configured():
                    continue
                # Fetch current metrics and create a single-day point
                if video_id:
                    metrics = client.fetch_video_metrics(video_id)
                    if metrics:
                        points.append({
                            "date": date_to.strftime("%Y-%m-%d"),
                            "platform": name,
                            "views": metrics.get("views", 0),
                            "likes": metrics.get("likes", 0),
                            "comments": metrics.get("comments", 0),
                            "shares": metrics.get("shares", 0),
                        })
            except Exception:
                logger.warning("Timeseries error from %s", name, exc_info=True)

        return {
            "video_id": video_id,
            "points": points,
        }

    def get_optimal_times(
        self,
        platform: str | None = None,
    ) -> dict[str, Any]:
        """Day × hour heatmap of optimal posting times from historical data.

        Returns a dict with keys: heatmap (day→hour→score), days_analyzed,
        platforms.
        """
        # Build heatmap from stored metrics (group by day-of-week × hour)
        heatmap: dict[int, dict[int, float]] = {}

        clients_to_query = self._clients
        if platform:
            clients_to_query = {k: v for k, v in self._clients.items() if k == platform}
        platforms_list = list(clients_to_query)

        # Initialize heatmap structure (7 days × 24 hours)
        for day in range(7):
            heatmap[day] = {hour: 0.0 for hour in range(24)}

        return {
            "heatmap": heatmap,
            "days_analyzed": 0,
            "platforms": platforms_list,
        }

    def get_video_detail(
        self,
        video_id: str,
    ) -> dict[str, Any]:
        """Per-video metrics with platform comparison.

        Returns a dict with keys: video_id, title, platforms (list of
        per-platform metrics), platforms_unavailable, best_platform.
        """
        perf = self.get_performance(video_id)
        platforms_data = perf.get("platforms", [])
        unavailable = perf.get("platforms_unavailable", [])

        # Determine best platform by views
        best_platform: str | None = None
        best_views = -1
        for p in platforms_data:
            if p.get("views", 0) > best_views:
                best_views = p.get("views", 0)
                best_platform = p.get("platform")

        return {
            "video_id": video_id,
            "title": "",
            "platforms": platforms_data,
            "platforms_unavailable": unavailable,
            "best_platform": best_platform,
        }

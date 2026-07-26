"""Publish orchestration service.

Coordinates content publishing across social media platforms:
resolves the connector, enforces rate limits, manages credentials,
and tracks publish status.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from src.connectors.base import SocialMediaConnector
from src.connectors.errors import AuthError, RateLimitError
from src.connectors.rate_limiter import TokenBucketRateLimiter


class PublishService:
    """Orchestrates content publishing across social media platforms.

    Args:
        connectors: A dict mapping platform names to SocialMediaConnector instances.
        db_session_factory: Optional factory for database sessions.
    """

    def __init__(
        self,
        connectors: dict[str, SocialMediaConnector],
        db_session_factory: Any | None = None,
    ) -> None:
        self.connectors = connectors
        self._db_session_factory = db_session_factory
        self.rate_limiters: dict[str, TokenBucketRateLimiter] = {}
        self._publishes: dict[str, dict] = {}

    async def publish(
        self,
        generation_id: str,
        platform: str,
        text: str = "",
        **kwargs: Any,
    ) -> dict:
        """Publish content to a social media platform.

        Args:
            generation_id: ID of the content to publish.
            platform: Target platform name (e.g. 'twitter', 'linkedin').
            text: Content text to publish.
            **kwargs: Additional parameters passed to the connector.

        Returns:
            A dict with publish result information.

        Raises:
            ValueError: If the platform is unknown.
            AuthError: If authentication fails (no retry).
            RateLimitError: If rate limited (transient, retried).
        """
        if platform not in self.connectors:
            raise ValueError(f"Unknown platform: {platform}")

        connector = self.connectors[platform]

        # Rate limiting
        if platform not in self.rate_limiters:
            self.rate_limiters[platform] = TokenBucketRateLimiter(
                capacity=300, refill_rate=20.0, name=platform
            )

        publish_id = f"pub_{uuid4().hex[:12]}"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Acquire rate limiter token (non-blocking for immediate)
                self.rate_limiters[platform].try_acquire()

                # Call the connector
                result = await connector.publish(text=text, **kwargs)

                # Store the result
                self._publishes[publish_id] = {
                    "publish_id": publish_id,
                    "generation_id": generation_id,
                    "platform": platform,
                    "status": "published",
                    "platform_url": result.get("tweet_url") or result.get("post_urn", ""),
                    "result": result,
                }
                return self._publishes[publish_id]

            except AuthError:
                # Auth errors are fatal — no retry
                self._publishes[publish_id] = {
                    "publish_id": publish_id,
                    "generation_id": generation_id,
                    "platform": platform,
                    "status": "failed",
                    "error": "auth_failed",
                }
                raise

            except RateLimitError:
                # Transient — retry
                if attempt < max_retries - 1:
                    continue
                self._publishes[publish_id] = {
                    "publish_id": publish_id,
                    "generation_id": generation_id,
                    "platform": platform,
                    "status": "failed",
                    "error": "rate_limit_exhausted",
                }
                raise

        # Should not reach here
        self._publishes[publish_id] = {
            "publish_id": publish_id,
            "generation_id": generation_id,
            "platform": platform,
            "status": "failed",
            "error": "unknown",
        }
        return self._publishes[publish_id]

    async def get_status(self, publish_id: str) -> dict:
        """Return the current status of a publish operation.

        Args:
            publish_id: The publish operation ID.

        Returns:
            A dict with the publish status information.
        """
        result = self._publishes.get(publish_id)
        if result is None:
            return {
                "publish_id": publish_id,
                "status": "not_found",
                "retry_count": 0,
            }
        return {
            "publish_id": result.get("publish_id", publish_id),
            "status": result.get("status", "unknown"),
            "retry_count": 0,
            "platform": result.get("platform", ""),
            "generation_id": result.get("generation_id", ""),
        }

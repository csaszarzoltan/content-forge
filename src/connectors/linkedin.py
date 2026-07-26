"""LinkedIn API v2 connector with OAuth 2.0 Bearer token auth."""

from __future__ import annotations

from typing import Any

import httpx

from src.connectors.base import SocialMediaConnector
from src.connectors.errors import AuthError, PublishError, RateLimitError


class LinkedInConnector(SocialMediaConnector):
    """Connector for LinkedIn API v2 (REST).

    Uses OAuth 2.0 Bearer token authentication.
    """

    BASE_URL = "https://api.linkedin.com"
    MAX_CHARS = 3000

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token: str,
        max_retries: int = 3,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token = access_token
        self._max_retries = max_retries
        self._client: httpx.AsyncClient = httpx.AsyncClient()

    @property
    def platform_name(self) -> str:
        return "linkedin"

    def _auth_header(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"}

    async def publish(self, text: str, **kwargs: Any) -> dict:
        """Create a post on LinkedIn.

        Supports text-only shares and link/article shares.
        """
        max_retries = kwargs.get("max_retries", self._max_retries)
        url = f"{self.BASE_URL}/rest/posts"
        headers = self._auth_header()
        headers["Content-Type"] = "application/json"
        headers["X-Restli-Protocol-Version"] = "2.0.0"
        headers["LinkedIn-Version"] = "202401"

        # Build the post body
        author = kwargs.get("author", "urn:li:person:current_user")

        article_url = kwargs.get("article_url")
        article_title = kwargs.get("article_title")

        if article_url:
            # Link/article share
            body = {
                "author": author,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": text},
                        "shareMediaCategory": "ARTICLE",
                        "media": [
                            {
                                "status": "READY",
                                "originalUrl": article_url,
                                "title": {"text": article_title or ""},
                            }
                        ],
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                },
            }
        else:
            # Text-only share
            body = {
                "author": author,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": text},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                },
            }

        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                response = await self._client.post(url, json=body, headers=headers)
                if response.status_code == 201:
                    data = response.json()
                    post_id = data.get("id", "")
                    return {
                        "id": post_id,
                        "post_urn": post_id,
                        "status": "published",
                    }
                if response.status_code in (401, 403):
                    raise AuthError(f"LinkedIn auth failed: {response.text}")
                if response.status_code == 429:
                    raise RateLimitError(f"LinkedIn rate limited: {response.text}")
                if response.status_code >= 500:
                    last_error = PublishError(f"LinkedIn server error: {response.text}")
                    continue
                last_error = PublishError(f"LinkedIn publish failed: {response.text}")
                continue
            except (AuthError, RateLimitError):
                raise
            except httpx.HTTPError as exc:
                last_error = PublishError(f"LinkedIn HTTP error: {exc}")
                continue

        raise last_error or PublishError("LinkedIn publish failed after retries")

    async def preview(self, text: str, **kwargs: Any) -> dict:
        """Return preview info: character count and format validation."""
        return {
            "char_count": len(text),
            "within_limit": len(text) <= self.MAX_CHARS,
            "format": "text",
        }

    async def validate_credentials(self) -> bool:
        """Test credentials by calling GET /v2/userinfo."""
        url = f"{self.BASE_URL}/v2/userinfo"
        headers = self._auth_header()
        try:
            response = await self._client.get(url, headers=headers)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

"""Twitter (X) API v2 connector with OAuth 1.0a signing."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote as url_quote

import httpx

from src.connectors.base import SocialMediaConnector
from src.connectors.errors import AuthError, PublishError, RateLimitError


def _oauth1_signature(
    method: str,
    url: str,
    params: dict[str, str],
    consumer_secret: str,
    token_secret: str,
) -> str:
    """Create an OAuth 1.0a HMAC-SHA1 signature."""
    import hashlib
    import hmac

    # Create signature base string
    param_string = "&".join(
        f"{url_quote(k, safe='')}={url_quote(v, safe='')}"
        for k, v in sorted(params.items())
    )
    base_string = "&".join(
        url_quote(s, safe="")
        for s in [method.upper(), url, param_string]
    )

    signing_key = f"{url_quote(consumer_secret, safe='')}&{url_quote(token_secret, safe='')}"
    signature = hmac.new(
        signing_key.encode(),
        base_string.encode(),
        hashlib.sha1,
    ).digest()
    import base64

    return base64.b64encode(signature).decode()


def _oauth1_header(
    method: str,
    url: str,
    api_key: str,
    api_secret: str,
    access_token: str,
    access_token_secret: str,
) -> dict[str, str]:
    """Build an OAuth 1.0a Authorization header dict."""
    params: dict[str, str] = {
        "oauth_consumer_key": api_key,
        "oauth_nonce": str(int(time.time() * 1000)),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": access_token,
        "oauth_version": "1.0",
    }
    signature = _oauth1_signature(
        method, url, params, api_secret, access_token_secret,
    )
    params["oauth_signature"] = signature
    header_value = "OAuth " + ", ".join(
        f'{url_quote(k, safe="")}="{url_quote(v, safe="")}"'
        for k, v in sorted(params.items())
    )
    return {"Authorization": header_value}


class TwitterConnector(SocialMediaConnector):
    """Connector for Twitter (X) API v2.

    Uses OAuth 1.0a User Context authentication.
    """

    BASE_URL = "https://api.twitter.com/2"
    MAX_CHARS = 280

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        access_token: str,
        access_token_secret: str,
        max_retries: int = 3,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._access_token = access_token
        self._access_token_secret = access_token_secret
        self._max_retries = max_retries
        self._client: httpx.AsyncClient = httpx.AsyncClient()

    @property
    def platform_name(self) -> str:
        return "twitter"

    def _build_auth_headers(self, method: str, url: str) -> dict[str, str]:
        """Build OAuth 1.0a signed headers."""
        return _oauth1_header(
            method,
            url,
            self._api_key,
            self._api_secret,
            self._access_token,
            self._access_token_secret,
        )

    async def publish(self, text: str, **kwargs: Any) -> dict:
        """Post a tweet. Truncates to 280 characters if needed."""
        max_retries = kwargs.get("max_retries", self._max_retries)
        truncated = text[: self.MAX_CHARS]
        url = f"{self.BASE_URL}/tweets"
        headers = self._build_auth_headers("POST", url)
        headers["Content-Type"] = "application/json"

        payload = {"text": truncated}

        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                response = await self._client.post(
                    url, json=payload, headers=headers
                )
                if response.status_code == 201:
                    data = response.json()
                    result = data.get("data", {})
                    tweet_id = result.get("id", "")
                    return {
                        "id": tweet_id,
                        "tweet_url": f"https://twitter.com/user/status/{tweet_id}",
                        "status": "published",
                    }
                if response.status_code in (401, 403):
                    raise AuthError(f"Twitter auth failed: {response.text}")
                if response.status_code == 429:
                    raise RateLimitError(f"Twitter rate limited: {response.text}")
                if response.status_code >= 500:
                    last_error = PublishError(f"Twitter server error: {response.text}")
                    continue  # retry
                # Other error
                last_error = PublishError(f"Twitter publish failed: {response.text}")
                continue
            except (AuthError, RateLimitError):
                raise
            except httpx.HTTPError as exc:
                last_error = PublishError(f"Twitter HTTP error: {exc}")
                continue

        raise last_error or PublishError("Twitter publish failed after retries")

    async def preview(self, text: str, **kwargs: Any) -> dict:
        """Return preview info: character count and truncated version."""
        truncated = text[: self.MAX_CHARS]
        return {
            "char_count": len(text),
            "truncated": truncated,
            "will_be_truncated": len(text) > self.MAX_CHARS,
        }

    async def validate_credentials(self) -> bool:
        """Test credentials by calling GET /2/users/me."""
        url = f"{self.BASE_URL}/users/me"
        headers = self._build_auth_headers("GET", url)
        try:
            response = await self._client.get(url, headers=headers)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

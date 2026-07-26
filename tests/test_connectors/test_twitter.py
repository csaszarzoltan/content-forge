"""Interface and behavioral tests for TwitterConnector.

Interface tests  — verify imports, class hierarchy, method signatures (should PASS with stubs).
Behavioral tests — verify HTTP mocking, truncation, error handling (RED until implementation).

All HTTP calls are mocked via httpx.MockTransport — no real API calls.
"""

from __future__ import annotations

import inspect

import pytest


class TestTwitterConnectorInterface:
    """Verify the TwitterConnector interface."""

    def test_twitter_connector_importable(self):
        """TwitterConnector should be importable from src.connectors.twitter."""
        from src.connectors.twitter import TwitterConnector

        assert TwitterConnector is not None

    def test_twitter_connector_extends_base(self):
        """TwitterConnector should extend SocialMediaConnector."""
        from src.connectors.base import SocialMediaConnector
        from src.connectors.twitter import TwitterConnector

        assert issubclass(TwitterConnector, SocialMediaConnector)

    def test_twitter_connector_platform_name(self):
        """TwitterConnector.platform_name should return 'twitter'."""
        from src.connectors.twitter import TwitterConnector

        connector = TwitterConnector(api_key="k", api_secret="s", access_token="t", access_token_secret="ts")
        assert connector.platform_name == "twitter"

    def test_twitter_publish_is_async(self):
        """TwitterConnector.publish should be a coroutine function."""
        from src.connectors.twitter import TwitterConnector

        assert hasattr(TwitterConnector, "publish")
        assert inspect.iscoroutinefunction(TwitterConnector.publish)

    def test_twitter_preview_is_async(self):
        """TwitterConnector.preview should be a coroutine function."""
        from src.connectors.twitter import TwitterConnector

        assert hasattr(TwitterConnector, "preview")
        assert inspect.iscoroutinefunction(TwitterConnector.preview)

    def test_twitter_validate_credentials_is_async(self):
        """TwitterConnector.validate_credentials should be a coroutine function."""
        from src.connectors.twitter import TwitterConnector

        assert hasattr(TwitterConnector, "validate_credentials")
        assert inspect.iscoroutinefunction(TwitterConnector.validate_credentials)


class TestTwitterConnectorBehavioral:
    """Behavioral tests for TwitterConnector — RED until implemented.

    All tests use httpx.MockTransport to simulate API responses.
    """

    @pytest.fixture
    def connector(self):
        """Create a TwitterConnector with dummy credentials."""
        from src.connectors.twitter import TwitterConnector

        return TwitterConnector(
            api_key="test_api_key",
            api_secret="test_api_secret",
            access_token="test_access_token",
            access_token_secret="test_token_secret",
        )

    @pytest.mark.asyncio
    async def test_publish_returns_tweet_url(self, connector):
        """publish() should return a dict with tweet_url on success."""
        import httpx

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(201, json={"data": {"id": "123456789", "text": "Hello world"}})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            result = await connector.publish(text="Hello world")
            assert isinstance(result, dict)
            assert "tweet_url" in result or "id" in result

    @pytest.mark.asyncio
    async def test_publish_truncates_long_content(self, connector):
        """Content longer than 280 characters should be truncated before posting."""
        import httpx

        long_text = "A" * 500
        captured_text = None

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_text
            import json
            body = json.loads(request.content)
            captured_text = body.get("text", "")
            return httpx.Response(201, json={"data": {"id": "123", "text": captured_text}})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            await connector.publish(text=long_text)
            assert captured_text is not None
            assert len(captured_text) <= 280

    @pytest.mark.asyncio
    async def test_publish_raises_auth_error_on_401(self, connector):
        """A 401 response should raise AuthError."""
        import httpx

        from src.connectors.errors import AuthError

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"title": "Unauthorized", "detail": "Invalid credentials"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            with pytest.raises(AuthError):
                await connector.publish(text="Hello")

    @pytest.mark.asyncio
    async def test_publish_raises_rate_limit_on_429(self, connector):
        """A 429 response should raise RateLimitError."""
        import httpx

        from src.connectors.errors import RateLimitError

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"title": "Too Many Requests"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            with pytest.raises(RateLimitError):
                await connector.publish(text="Hello")

    @pytest.mark.asyncio
    async def test_publish_retries_on_5xx(self, connector):
        """A 5xx response should trigger a retry up to max_retries."""
        import httpx

        attempt_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            return httpx.Response(500, json={"title": "Internal Server Error"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            with pytest.raises(Exception):
                await connector.publish(text="Hello")
            assert attempt_count > 1, "Should have retried on 5xx"

    @pytest.mark.asyncio
    async def test_publish_fails_after_max_retries(self, connector):
        """Repeated 5xx responses should eventually raise after exhausting retries."""
        import httpx

        from src.connectors.errors import PublishError

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={"title": "Service Unavailable"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            with pytest.raises(PublishError):
                await connector.publish(text="Hello", max_retries=2)

    @pytest.mark.asyncio
    async def test_preview_returns_formatted_text(self, connector):
        """preview() should return a dict with formatted preview text."""
        import httpx

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(201, json={"data": {"id": "123"}})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            result = await connector.preview(text="Hello world")
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_validate_credentials_true(self, connector):
        """validate_credentials() should return True when credentials are valid."""
        import httpx

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": {"id": "me"}})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            result = await connector.validate_credentials()
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_credentials_false(self, connector):
        """validate_credentials() should return False when credentials are invalid."""
        import httpx

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"title": "Unauthorized"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            result = await connector.validate_credentials()
            assert result is False

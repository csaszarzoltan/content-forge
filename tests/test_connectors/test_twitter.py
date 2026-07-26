"""Interface and behavioral tests for TwitterConnector.

Interface tests  — verify imports, class hierarchy, method signatures (should PASS with stubs).
Behavioral tests — verify HTTP mocking, truncation, error handling (RED until implementation).
Edge-case tests  — verify boundary conditions, error propagation, and recovery.

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

    def test_twitter_connector_has_base_url(self):
        """TwitterConnector should have BASE_URL constant."""
        from src.connectors.twitter import TwitterConnector

        assert hasattr(TwitterConnector, "BASE_URL")
        assert TwitterConnector.BASE_URL == "https://api.twitter.com/2"

    def test_twitter_connector_has_max_chars(self):
        """TwitterConnector should have MAX_CHARS constant."""
        from src.connectors.twitter import TwitterConnector

        assert hasattr(TwitterConnector, "MAX_CHARS")
        assert TwitterConnector.MAX_CHARS == 280


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

    @pytest.mark.asyncio
    async def test_publish_403_raises_auth_error(self, connector):
        """A 403 response should also raise AuthError."""
        import httpx

        from src.connectors.errors import AuthError

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, json={"title": "Forbidden"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            with pytest.raises(AuthError):
                await connector.publish(text="Hello")


class TestTwitterConnectorEdgeCases:
    """Edge-case tests for TwitterConnector — boundary conditions and error recovery."""

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
    async def test_publish_exact_280_chars_no_truncation(self, connector):
        """Content exactly 280 chars should post without truncation."""
        import httpx

        exact_text = "B" * 280
        captured_text = None

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_text
            import json
            body = json.loads(request.content)
            captured_text = body.get("text", "")
            return httpx.Response(201, json={"data": {"id": "e280", "text": captured_text}})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            await connector.publish(text=exact_text)
            assert captured_text is not None
            assert len(captured_text) == 280
            assert captured_text == exact_text

    @pytest.mark.asyncio
    async def test_publish_over_280_truncated_length(self, connector):
        """Content over 280 chars should have the body truncated."""
        import httpx

        long_text = "C" * 500
        captured_text = None

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_text
            import json
            body = json.loads(request.content)
            captured_text = body.get("text", "")
            return httpx.Response(201, json={"data": {"id": "trunc", "text": captured_text}})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            await connector.publish(text=long_text)
            assert captured_text is not None
            assert len(captured_text) == 280
            # Verify it's the first 280 chars
            assert captured_text == "C" * 280

    @pytest.mark.asyncio
    async def test_publish_network_timeout_retries(self, connector):
        """Network timeout should be caught and trigger retry."""
        import httpx

        from src.connectors.errors import PublishError

        attempt_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            raise httpx.TimeoutException("Connection timed out after 5s")

        connector._max_retries = 2
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            with pytest.raises(PublishError):
                await connector.publish(text="Hello")
            # Should have retried (initial attempt + retries)
            assert attempt_count >= 2, f"Expected at least 2 attempts, got {attempt_count}"

    @pytest.mark.asyncio
    async def test_publish_503_triggers_retry(self, connector):
        """503 Service Unavailable should trigger a retry."""
        import httpx

        attempt_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            return httpx.Response(503, json={"title": "Service Unavailable"})

        connector._max_retries = 2
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            with pytest.raises(Exception):
                await connector.publish(text="Hello")
            assert attempt_count > 1, f"Expected retries, got {attempt_count}"

    @pytest.mark.asyncio
    async def test_publish_network_connection_error_retries(self, connector):
        """Connection errors (DNS failure, refused) should trigger retry."""
        import httpx

        from src.connectors.errors import PublishError

        attempt_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            raise httpx.ConnectError("Connection refused")

        connector._max_retries = 2
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            with pytest.raises(PublishError):
                await connector.publish(text="Hello")
            assert attempt_count >= 2

    @pytest.mark.asyncio
    async def test_preview_returns_char_count(self, connector):
        """preview() should return accurate character count."""
        text = "Hello, this is a test post for preview!"
        result = await connector.preview(text=text)
        assert result["char_count"] == len(text)
        assert "truncated" in result
        assert "will_be_truncated" in result
        assert result["will_be_truncated"] is False

    @pytest.mark.asyncio
    async def test_preview_will_truncate_long_text(self, connector):
        """preview() should indicate when text will be truncated."""
        text = "X" * 500
        result = await connector.preview(text=text)
        assert result["will_be_truncated"] is True
        assert result["char_count"] == 500
        assert len(result["truncated"]) == 280

    @pytest.mark.asyncio
    async def test_publish_returns_id_and_url_on_success(self, connector):
        """publish() should include both id and tweet_url in response."""
        import httpx

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(201, json={"data": {"id": "98765", "text": "Check"}})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            result = await connector.publish(text="Check")
            assert result["id"] == "98765"
            assert "tweet_url" in result
            assert "98765" in result["tweet_url"]
            assert result["status"] == "published"

    @pytest.mark.asyncio
    async def test_publish_sends_json_content_type(self, connector):
        """publish() request should include Content-Type: application/json."""
        import httpx

        content_type = None

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal content_type
            content_type = request.headers.get("content-type", "")
            return httpx.Response(201, json={"data": {"id": "ct"}})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            await connector.publish(text="Hello")
            assert content_type == "application/json"

    @pytest.mark.asyncio
    async def test_validate_credentials_http_error_returns_false(self, connector):
        """validate_credentials() should return False on HTTP error (not crash)."""
        import httpx

        async def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Network error")

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            result = await connector.validate_credentials()
            assert result is False

    # ── Parameterized error-handling tests ────────────────────────

    @pytest.mark.parametrize(
        ("status_code", "expected_error"),
        [
            (400, "PublishError"),
            (404, "PublishError"),
            (406, "PublishError"),
            (410, "PublishError"),
            (422, "PublishError"),
            (500, "PublishError"),
            (502, "PublishError"),
            (503, "PublishError"),
            (504, "PublishError"),
        ],
    )
    @pytest.mark.asyncio
    async def test_publish_various_error_codes(self, connector, status_code, expected_error):
        """Various HTTP error codes should produce appropriate error types."""
        import httpx

        from src.connectors.errors import PublishError

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code, json={"error": f"Error {status_code}"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            with pytest.raises(PublishError):
                await connector.publish(text="Hello", max_retries=1)

    @pytest.mark.parametrize(
        ("status_code", "expected_error"),
        [
            (401, "AuthError"),
            (403, "AuthError"),
        ],
    )
    @pytest.mark.asyncio
    async def test_publish_auth_error_codes(self, connector, status_code, expected_error):
        """401/403 should raise AuthError immediately (no retry)."""
        import httpx

        from src.connectors.errors import AuthError

        attempt_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            return httpx.Response(status_code, json={"error": f"Auth error {status_code}"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            with pytest.raises(AuthError):
                await connector.publish(text="Hello", max_retries=3)
            assert attempt_count == 1, "Auth errors should not retry"

    @pytest.mark.parametrize(
        ("content_length", "expected_sent_length"),
        [
            (0, 0),
            (1, 1),
            (100, 100),
            (279, 279),
            (280, 280),
            (281, 280),
            (350, 280),
            (500, 280),
        ],
    )
    @pytest.mark.asyncio
    async def test_publish_various_content_lengths(self, connector, content_length, expected_sent_length):
        """Publish should handle content at various lengths."""
        import httpx

        text = "A" * content_length
        captured = None

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured
            import json
            body = json.loads(request.content)
            captured = body.get("text", "")
            return httpx.Response(201, json={"data": {"id": "len_test"}})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            await connector.publish(text=text)
            assert len(captured) == expected_sent_length

"""Interface and behavioral tests for LinkedInConnector.

Interface tests  — verify imports, class hierarchy, method signatures (should PASS with stubs).
Behavioral tests — verify UGC post creation, link shares, error handling (RED until implementation).
Edge-case tests  — verify boundary conditions, error recovery, and input validation.

All HTTP calls are mocked via httpx.MockTransport — no real API calls.
"""

from __future__ import annotations

import inspect

import pytest


class TestLinkedInConnectorInterface:
    """Verify the LinkedInConnector interface."""

    def test_linkedin_connector_importable(self):
        """LinkedInConnector should be importable from src.connectors.linkedin."""
        from src.connectors.linkedin import LinkedInConnector

        assert LinkedInConnector is not None

    def test_linkedin_connector_extends_base(self):
        """LinkedInConnector should extend SocialMediaConnector."""
        from src.connectors.base import SocialMediaConnector
        from src.connectors.linkedin import LinkedInConnector

        assert issubclass(LinkedInConnector, SocialMediaConnector)

    def test_linkedin_connector_platform_name(self):
        """LinkedInConnector.platform_name should return 'linkedin'."""
        from src.connectors.linkedin import LinkedInConnector

        connector = LinkedInConnector(client_id="cid", client_secret="cs", access_token="at")
        assert connector.platform_name == "linkedin"

    def test_linkedin_publish_is_async(self):
        """LinkedInConnector.publish should be a coroutine function."""
        from src.connectors.linkedin import LinkedInConnector

        assert hasattr(LinkedInConnector, "publish")
        assert inspect.iscoroutinefunction(LinkedInConnector.publish)

    def test_linkedin_preview_is_async(self):
        """LinkedInConnector.preview should be a coroutine function."""
        from src.connectors.linkedin import LinkedInConnector

        assert hasattr(LinkedInConnector, "preview")
        assert inspect.iscoroutinefunction(LinkedInConnector.preview)

    def test_linkedin_validate_credentials_is_async(self):
        """LinkedInConnector.validate_credentials should be a coroutine function."""
        from src.connectors.linkedin import LinkedInConnector

        assert hasattr(LinkedInConnector, "validate_credentials")
        assert inspect.iscoroutinefunction(LinkedInConnector.validate_credentials)

    def test_linkedin_connector_has_base_url(self):
        """LinkedInConnector should have BASE_URL constant."""
        from src.connectors.linkedin import LinkedInConnector

        assert hasattr(LinkedInConnector, "BASE_URL")
        assert LinkedInConnector.BASE_URL == "https://api.linkedin.com"

    def test_linkedin_connector_has_max_chars(self):
        """LinkedInConnector should have MAX_CHARS constant."""
        from src.connectors.linkedin import LinkedInConnector

        assert hasattr(LinkedInConnector, "MAX_CHARS")
        assert LinkedInConnector.MAX_CHARS == 3000


class TestLinkedInConnectorBehavioral:
    """Behavioral tests for LinkedInConnector — RED until implemented.

    All tests use httpx.MockTransport to simulate API responses.
    """

    @pytest.fixture
    def connector(self):
        """Create a LinkedInConnector with dummy credentials."""
        from src.connectors.linkedin import LinkedInConnector

        return LinkedInConnector(
            client_id="test_client_id",
            client_secret="test_client_secret",
            access_token="test_access_token",
        )

    @pytest.mark.asyncio
    async def test_publish_returns_post_urn(self, connector):
        """publish() should return a dict with post_urn on success."""
        import httpx

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(201, json={"id": "urn:li:ugcPost:123456"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            result = await connector.publish(text="Hello LinkedIn")
            assert isinstance(result, dict)
            assert "post_urn" in result or "id" in result

    @pytest.mark.asyncio
    async def test_publish_text_only(self, connector):
        """publish() should create a text-only UGC post."""
        import httpx

        async def handler(request: httpx.Request) -> httpx.Response:
            import json
            body = json.loads(request.content)
            # Verify UGC post structure for text-only
            assert "author" in body
            assert "lifecycleState" in body
            assert "specificContent" in body
            return httpx.Response(201, json={"id": "urn:li:ugcPost:789"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            result = await connector.publish(text="Just text")
            assert result is not None

    @pytest.mark.asyncio
    async def test_publish_link_share(self, connector):
        """publish() should support link shares with article URL."""
        import httpx

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(201, json={"id": "urn:li:ugcPost:link123"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            result = await connector.publish(
                text="Check this out",
                article_url="https://example.com/article",
                article_title="Great Article",
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_publish_raises_auth_error_on_401(self, connector):
        """A 401 response should raise AuthError."""
        import httpx

        from src.connectors.errors import AuthError

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"message": "Invalid access token"})

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
            return httpx.Response(429, json={"message": "Rate limit exceeded"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            with pytest.raises(RateLimitError):
                await connector.publish(text="Hello")

    @pytest.mark.asyncio
    async def test_publish_retries_on_5xx(self, connector):
        """A 5xx response should trigger a retry."""
        import httpx

        attempt_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            return httpx.Response(500, json={"message": "Internal server error"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            with pytest.raises(Exception):
                await connector.publish(text="Hello")
            assert attempt_count > 1, "Should have retried on 5xx"

    @pytest.mark.asyncio
    async def test_preview_returns_dict(self, connector):
        """preview() should return a dict with preview data."""
        result = await connector.preview(text="LinkedIn post preview")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_validate_credentials_true(self, connector):
        """validate_credentials() should return True with valid token."""
        import httpx

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"sub": "urn:li:person:123"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            result = await connector.validate_credentials()
            assert result is True


class TestLinkedInConnectorEdgeCases:
    """Edge-case tests for LinkedInConnector — boundary conditions and error recovery."""

    @pytest.fixture
    def connector(self):
        """Create a LinkedInConnector with dummy credentials."""
        from src.connectors.linkedin import LinkedInConnector

        return LinkedInConnector(
            client_id="test_client_id",
            client_secret="test_client_secret",
            access_token="test_access_token",
        )

    @pytest.mark.asyncio
    async def test_publish_link_share_sends_article_body(self, connector):
        """Article share should include ARTICLE media category and originalUrl."""
        import httpx

        captured_body = None

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            import json
            captured_body = json.loads(request.content)
            return httpx.Response(201, json={"id": "urn:li:ugcPost:art1"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            await connector.publish(
                text="Article share",
                article_url="https://example.com/article",
                article_title="Test Article",
            )
            assert captured_body is not None
            sc = captured_body["specificContent"]["com.linkedin.ugc.ShareContent"]
            assert sc["shareMediaCategory"] == "ARTICLE"
            assert sc["media"][0]["originalUrl"] == "https://example.com/article"
            assert sc["media"][0]["title"]["text"] == "Test Article"

    @pytest.mark.asyncio
    async def test_publish_403_raises_auth_error(self, connector):
        """A 403 response should also raise AuthError."""
        import httpx

        from src.connectors.errors import AuthError

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, json={"message": "Forbidden"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            with pytest.raises(AuthError):
                await connector.publish(text="Hello")

    @pytest.mark.asyncio
    async def test_publish_network_error_retries(self, connector):
        """Network errors should trigger retry and eventually raise PublishError."""
        import httpx

        from src.connectors.errors import PublishError

        attempt_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            raise httpx.ConnectError("Connection refused by LinkedIn")

        connector._max_retries = 2
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            with pytest.raises(PublishError):
                await connector.publish(text="Hello")
            assert attempt_count >= 2

    @pytest.mark.asyncio
    async def test_publish_503_retry(self, connector):
        """503 response should trigger retry."""
        import httpx

        attempt_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempt_count
            attempt_count += 1
            return httpx.Response(503, json={"message": "Service Unavailable"})

        connector._max_retries = 2
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            with pytest.raises(Exception):
                await connector.publish(text="Hello")
            assert attempt_count > 1

    @pytest.mark.asyncio
    async def test_preview_within_limit(self, connector):
        """preview() should indicate when content is within char limit."""
        text = "Short post"
        result = await connector.preview(text=text)
        assert result["within_limit"] is True
        assert result["char_count"] == len(text)

    @pytest.mark.asyncio
    async def test_preview_over_limit(self, connector):
        """preview() should indicate when content exceeds char limit."""
        long_text = "L" * 4000
        result = await connector.preview(text=long_text)
        assert result["within_limit"] is False
        assert result["char_count"] == 4000

    @pytest.mark.asyncio
    async def test_publish_returns_id_and_post_urn(self, connector):
        """publish() should return both id and post_urn on success."""
        import httpx

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(201, json={"id": "urn:li:ugcPost:result1"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            result = await connector.publish(text="Result test")
            assert result["id"] == "urn:li:ugcPost:result1"
            assert result["post_urn"] == "urn:li:ugcPost:result1"
            assert result["status"] == "published"

    @pytest.mark.asyncio
    async def test_publish_sends_correct_headers(self, connector):
        """publish() request should include LinkedIn-specific headers."""
        import httpx

        headers_seen = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal headers_seen
            headers_seen = dict(request.headers)
            return httpx.Response(201, json={"id": "urn:li:ugcPost:hdr"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            connector._client = client
            await connector.publish(text="Header test")
            assert headers_seen.get("x-restli-protocol-version") == "2.0.0"
            assert headers_seen.get("linkedin-version") == "202401"
            assert headers_seen.get("authorization") == "Bearer test_access_token"

    @pytest.mark.asyncio
    async def test_validate_credentials_http_error_returns_false(self, connector):
        """validate_credentials() should return False on network error."""
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
        ("status_code",),
        [
            (400,),
            (404,),
            (406,),
            (410,),
            (422,),
            (500,),
            (502,),
            (503,),
            (504,),
        ],
    )
    @pytest.mark.asyncio
    async def test_publish_various_error_codes(self, connector, status_code):
        """Various HTTP error codes should produce PublishError."""
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
        ("status_code",),
        [
            (401,),
            (403,),
        ],
    )
    @pytest.mark.asyncio
    async def test_publish_auth_error_codes(self, connector, status_code):
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

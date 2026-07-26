"""Interface and behavioral tests for LinkedInConnector.

Interface tests  — verify imports, class hierarchy, method signatures (should PASS with stubs).
Behavioral tests — verify UGC post creation, link shares, error handling (RED until implementation).

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

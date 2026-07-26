"""Integration tests for the Social Media auto-publishing pipeline.

Tests end-to-end publish flows: schedule → publish → verify status,
connector error propagation and retry, and auth-integrated publish.

All HTTP/API calls use mocked transports — no real external services.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


class TestPublishIntegration:
    """Integration tests for the publish pipeline end-to-end."""

    # ────────────────────────────────────────────────────────────────
    # Integration 1: End-to-end publish → verify status through API
    # ────────────────────────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_e2e_publish_then_status(self):
        """End-to-end: publish via API → verify status via API.

        Injects a mock PublishService with a real connector so the
        endpoint stores and retrieves publish records.
        """
        from unittest.mock import AsyncMock, MagicMock

        from httpx import ASGITransport, AsyncClient

        from src.main import app
        from src.services.publish_service import PublishService

        # Inject a PublishService with a mock Twitter connector into app state
        mock_twitter = MagicMock()
        mock_twitter.platform_name = "twitter"
        mock_twitter.publish = AsyncMock(return_value={"tweet_url": "https://twitter.com/s/42", "status": "published"})
        mock_twitter.preview = AsyncMock(return_value={})

        test_service = PublishService(connectors={"twitter": mock_twitter})
        app.state.publish_service = test_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Step 1: POST /api/v1/publish with valid Twitter data
            pub_response = await client.post(
                "/api/v1/publish",
                json={
                    "generation_id": "int_gen_1",
                    "platform": "twitter",
                    "text": "Integration test: E2E publish flow",
                },
            )
            assert pub_response.status_code == 201, f"Publish failed: {pub_response.text}"
            pub_data = pub_response.json()
            assert "publish_id" in pub_data
            publish_id = pub_data["publish_id"]

            # Step 2: GET /api/v1/publish/{id} to verify status
            status_response = await client.get(f"/api/v1/publish/{publish_id}")
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["publish_id"] == publish_id
            assert status_data["status"] == "published"

    # ────────────────────────────────────────────────────────────────
    # Integration 2: Connector error propagation — mock 500 → retry → fail
    # ────────────────────────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_connector_error_propagation(self):
        """Mock a connector that always returns 500 — verify PublishService
        retries then propagates the error.

        Uses PublishService directly with a connector mock.
        """
        from unittest.mock import AsyncMock, MagicMock

        from src.connectors.errors import PublishError
        from src.services.publish_service import PublishService

        # Create a failing mock connector
        mock_twitter = MagicMock()
        mock_twitter.platform_name = "twitter"
        mock_twitter.publish = AsyncMock(side_effect=PublishError("Always fails"))
        mock_twitter.preview = AsyncMock(return_value={})
        mock_twitter.validate_credentials = AsyncMock(return_value=False)

        registry = {"twitter": mock_twitter}
        service = PublishService(connectors=registry)

        with pytest.raises(PublishError):
            await service.publish(
                generation_id="int_err_gen",
                platform="twitter",
                text="This should fail",
            )

        # Verify the connector was called (retries happen inside connector)
        assert mock_twitter.publish.await_count >= 1

    # ────────────────────────────────────────────────────────────────
    # Integration 3: Connector error with retry-then-succeed
    # ────────────────────────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_connector_retry_then_succeed(self):
        """Connector fails with transient error on first call, then succeeds.

        Verify PublishService returns success after retry.
        """
        from unittest.mock import AsyncMock, MagicMock

        from src.connectors.errors import RateLimitError
        from src.services.publish_service import PublishService

        mock_twitter = MagicMock()
        mock_twitter.platform_name = "twitter"
        mock_twitter.publish = AsyncMock(
            side_effect=[
                RateLimitError("Rate limited on first try"),
                {"tweet_url": "https://twitter.com/success/42", "status": "published"},
            ]
        )
        mock_twitter.preview = AsyncMock(return_value={})
        mock_twitter.validate_credentials = AsyncMock(return_value=True)

        registry = {"twitter": mock_twitter}
        service = PublishService(connectors=registry)

        result = await service.publish(
            generation_id="int_retry_gen",
            platform="twitter",
            text="Retry then succeed",
        )
        assert result["status"] == "published"
        assert mock_twitter.publish.await_count == 2

    # ────────────────────────────────────────────────────────────────
    # Integration 4: Multi-platform publish from same generation
    # ────────────────────────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_multi_platform_publish_same_generation(self):
        """Same generation content published to both platforms should succeed."""
        from unittest.mock import AsyncMock, MagicMock

        from src.services.publish_service import PublishService

        mock_twitter = MagicMock()
        mock_twitter.platform_name = "twitter"
        mock_twitter.publish = AsyncMock(return_value={"tweet_url": "https://twitter.com/t/1", "status": "published"})
        mock_twitter.preview = AsyncMock(return_value={})
        mock_twitter.validate_credentials = AsyncMock(return_value=True)

        mock_linkedin = MagicMock()
        mock_linkedin.platform_name = "linkedin"
        mock_linkedin.publish = AsyncMock(return_value={"post_urn": "urn:li:post:1", "status": "published"})
        mock_linkedin.preview = AsyncMock(return_value={})
        mock_linkedin.validate_credentials = AsyncMock(return_value=True)

        registry = {"twitter": mock_twitter, "linkedin": mock_linkedin}
        service = PublishService(connectors=registry)

        gen_id = "multi_platform_gen"
        result_t = await service.publish(generation_id=gen_id, platform="twitter", text="Multi platform")
        result_l = await service.publish(generation_id=gen_id, platform="linkedin", text="Multi platform")

        assert result_t["status"] == "published"
        assert result_l["status"] == "published"
        assert result_t["publish_id"] != result_l["publish_id"]

    # ────────────────────────────────────────────────────────────────
    # Integration 5: Auth + publish via API endpoint
    # ────────────────────────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_auth_and_publish_via_endpoint(self):
        """Publish endpoint with optional auth should work without token."""
        from httpx import ASGITransport, AsyncClient

        from src.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # The endpoint uses get_optional_current_user, so no auth required
            response = await client.post(
                "/api/v1/publish",
                json={
                    "generation_id": "int_auth_gen",
                    "platform": "twitter",
                    "text": "Auth integration test",
                },
            )
            assert response.status_code == 201, f"Body: {response.text}"

            # Also test with Authorization header (optional but valid format)
            response2 = await client.post(
                "/api/v1/publish",
                json={
                    "generation_id": "int_auth_gen2",
                    "platform": "linkedin",
                    "text": "With auth header",
                },
                headers={"Authorization": "Bearer test_token"},
            )
            # Should still work (Bearer token is optional, if invalid user is None)
            assert response2.status_code == 201, f"Body: {response2.text}"

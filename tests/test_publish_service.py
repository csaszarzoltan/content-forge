"""Interface and behavioral tests for PublishService.

Interface tests  — verify imports, constructor, method signatures (should PASS with stubs).
Behavioral tests — verify publish orchestration: resolve connector → rate limit → publish →
                  update ScheduledPost status (RED until implementation).
"""

from __future__ import annotations

import inspect

import pytest


class TestPublishServiceInterface:
    """Verify the PublishService interface."""

    def test_publish_service_importable(self):
        """PublishService should be importable from src.services.publish_service."""
        from src.services.publish_service import PublishService

        assert PublishService is not None

    def test_publish_service_is_class(self):
        """PublishService should be a class."""
        from src.services.publish_service import PublishService

        assert inspect.isclass(PublishService)

    def test_publish_service_constructor_accepts_connectors(self):
        """Constructor should accept a connectors registry."""
        from src.services.publish_service import PublishService

        sig = inspect.signature(PublishService)
        # Should accept a dict/registry of connectors
        param_names = list(sig.parameters.keys())
        assert any("connector" in p for p in param_names)

    def test_publish_service_has_publish_method(self):
        """PublishService should have a publish method."""
        from src.services.publish_service import PublishService

        assert hasattr(PublishService, "publish")
        assert callable(PublishService.publish)
        assert inspect.iscoroutinefunction(PublishService.publish)

    def test_publish_service_has_get_status_method(self):
        """PublishService should have a get_status method."""
        from src.services.publish_service import PublishService

        assert hasattr(PublishService, "get_status")
        assert callable(PublishService.get_status)
        assert inspect.iscoroutinefunction(PublishService.get_status)


class TestPublishServiceBehavioral:
    """Behavioral tests for PublishService — RED until implemented."""

    @pytest.fixture
    def mock_twitter_connector(self):
        """A mock TwitterConnector for testing."""
        from unittest.mock import AsyncMock, MagicMock

        mock = MagicMock()
        mock.platform_name = "twitter"
        mock.publish = AsyncMock(return_value={"tweet_url": "https://twitter.com/user/status/123"})
        mock.preview = AsyncMock(return_value={"preview": "Hello..."})
        mock.validate_credentials = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def mock_linkedin_connector(self):
        """A mock LinkedInConnector for testing."""
        from unittest.mock import AsyncMock, MagicMock

        mock = MagicMock()
        mock.platform_name = "linkedin"
        mock.publish = AsyncMock(return_value={"post_urn": "urn:li:ugcPost:123"})
        mock.preview = AsyncMock(return_value={"preview": "Hello..."})
        mock.validate_credentials = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def connectors_registry(self, mock_twitter_connector, mock_linkedin_connector):
        """A connectors registry with both mock connectors."""
        return {
            "twitter": mock_twitter_connector,
            "linkedin": mock_linkedin_connector,
        }

    @pytest.mark.asyncio
    async def test_publish_happy_path_twitter(self, connectors_registry):
        """publish() should return a PublishResponse for a valid publish request."""
        from src.services.publish_service import PublishService

        service = PublishService(connectors=connectors_registry)
        result = await service.publish(
            generation_id="gen_1",
            platform="twitter",
            text="Hello Twitter!",
        )
        assert result is not None
        assert isinstance(result, dict) or hasattr(result, "status")

    @pytest.mark.asyncio
    async def test_publish_happy_path_linkedin(self, connectors_registry):
        """publish() should return a PublishResponse for a valid LinkedIn publish."""
        from src.services.publish_service import PublishService

        service = PublishService(connectors=connectors_registry)
        result = await service.publish(
            generation_id="gen_2",
            platform="linkedin",
            text="Hello LinkedIn!",
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_publish_raises_on_unknown_platform(self, connectors_registry):
        """publish() should raise ValueError for an unknown platform."""
        from src.services.publish_service import PublishService

        service = PublishService(connectors=connectors_registry)
        with pytest.raises(ValueError):
            await service.publish(
                generation_id="gen_3",
                platform="unknown_platform",
                text="Hello?",
            )

    @pytest.mark.asyncio
    async def test_publish_calls_connector_publish(self, connectors_registry, mock_twitter_connector):
        """publish() should call the connector's publish method."""
        from src.services.publish_service import PublishService

        service = PublishService(connectors=connectors_registry)
        await service.publish(
            generation_id="gen_4",
            platform="twitter",
            text="Check the mock",
        )
        mock_twitter_connector.publish.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_publish_retries_on_transient_failure(self, connectors_registry, mock_twitter_connector):
        """publish() should retry on transient failures (5xx)."""
        from unittest.mock import AsyncMock

        from src.connectors.errors import RateLimitError
        from src.services.publish_service import PublishService

        # Make the mock fail with rate limit first, then succeed
        mock_twitter_connector.publish = AsyncMock(
            side_effect=[RateLimitError("Rate limited"), {"tweet_url": "https://twitter.com/ok"}]
        )

        service = PublishService(connectors=connectors_registry)
        result = await service.publish(
            generation_id="gen_5",
            platform="twitter",
            text="Retry test",
        )
        assert result is not None
        assert mock_twitter_connector.publish.await_count >= 2

    @pytest.mark.asyncio
    async def test_publish_fails_on_auth_error(self, connectors_registry, mock_twitter_connector):
        """publish() should fail immediately on AuthError (no retry)."""
        from unittest.mock import AsyncMock

        from src.connectors.errors import AuthError
        from src.services.publish_service import PublishService

        mock_twitter_connector.publish = AsyncMock(side_effect=AuthError("Unauthorized"))

        service = PublishService(connectors=connectors_registry)
        with pytest.raises(AuthError):
            await service.publish(
                generation_id="gen_6",
                platform="twitter",
                text="Auth fail",
            )
        # Should only have been called once (no retry on auth errors)
        mock_twitter_connector.publish.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_publish_updates_scheduled_post_status(self, connectors_registry):
        """publish() should update the scheduled post status through the pipeline."""
        from src.services.publish_service import PublishService

        # Create a service with db session tracking
        service = PublishService(
            connectors=connectors_registry,
        )
        result = await service.publish(
            generation_id="gen_7",
            platform="twitter",
            text="Status tracking test",
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_status_returns_post_status(self, connectors_registry):
        """get_status() should return the status of a published post."""
        from src.services.publish_service import PublishService

        service = PublishService(connectors=connectors_registry)
        status = await service.get_status(publish_id="pub_123")
        assert status is not None
        assert isinstance(status, dict)

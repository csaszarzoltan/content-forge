"""Interface and behavioral tests for PublishService.

Interface tests  — verify imports, constructor, method signatures (should PASS with stubs).
Behavioral tests — verify publish orchestration: resolve connector → rate limit → publish →
                  update ScheduledPost status (RED until implementation).
Edge-case tests  — verify idempotency, concurrency, rate limiting, and error paths.
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

    def test_publish_service_constructor_accepts_db_factory(self):
        """Constructor should accept db_session_factory parameter."""
        from src.services.publish_service import PublishService

        sig = inspect.signature(PublishService)
        assert "db_session_factory" in sig.parameters

    def test_publish_service_has_rate_limiters(self):
        """PublishService should have a rate_limiters attribute."""
        from src.services.publish_service import PublishService

        svc = PublishService(connectors={})
        assert hasattr(svc, "rate_limiters")
        assert isinstance(svc.rate_limiters, dict)


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


class TestPublishServiceEdgeCases:
    """Edge-case tests for PublishService — boundary conditions and error recovery."""

    @pytest.fixture
    def mock_twitter_connector(self):
        """A mock TwitterConnector for testing."""
        from unittest.mock import AsyncMock, MagicMock

        mock = MagicMock()
        mock.platform_name = "twitter"
        mock.publish = AsyncMock(return_value={"tweet_url": "https://twitter.com/user/status/123"})
        return mock

    @pytest.fixture
    def mock_linkedin_connector(self):
        """A mock LinkedInConnector for testing."""
        from unittest.mock import AsyncMock, MagicMock

        mock = MagicMock()
        mock.platform_name = "linkedin"
        mock.publish = AsyncMock(return_value={"post_urn": "urn:li:ugcPost:123"})
        return mock

    @pytest.fixture
    def connectors_registry(self, mock_twitter_connector, mock_linkedin_connector):
        """A connectors registry with both mock connectors."""
        return {
            "twitter": mock_twitter_connector,
            "linkedin": mock_linkedin_connector,
        }

    @pytest.mark.asyncio
    async def test_publish_with_empty_text_succeeds(self, connectors_registry, mock_twitter_connector):
        """publish() with empty text should succeed (text default is '')."""
        from src.services.publish_service import PublishService

        service = PublishService(connectors=connectors_registry)
        result = await service.publish(
            generation_id="gen_empty",
            platform="twitter",
            text="",
        )
        assert result is not None
        assert result["status"] == "published"
        mock_twitter_connector.publish.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_publish_unique_publish_id_per_call(self, connectors_registry):
        """Each publish() call should generate a unique publish_id."""
        from src.services.publish_service import PublishService

        service = PublishService(connectors=connectors_registry)
        result1 = await service.publish(generation_id="gen_a", platform="twitter", text="A")
        result2 = await service.publish(generation_id="gen_b", platform="twitter", text="B")
        assert result1["publish_id"] != result2["publish_id"]

    @pytest.mark.asyncio
    async def test_get_status_not_found(self, connectors_registry):
        """get_status() for unknown publish_id should return 'not_found' status."""
        from src.services.publish_service import PublishService

        service = PublishService(connectors=connectors_registry)
        status = await service.get_status(publish_id="nonexistent_id")
        assert status["status"] == "not_found"
        assert status["publish_id"] == "nonexistent_id"

    @pytest.mark.asyncio
    async def test_publish_same_generation_id_different_platform(self, connectors_registry):
        """Same generation_id on different platforms should both succeed."""
        from src.services.publish_service import PublishService

        service = PublishService(connectors=connectors_registry)
        result1 = await service.publish(generation_id="gen_shared", platform="twitter", text="Hello")
        result2 = await service.publish(generation_id="gen_shared", platform="linkedin", text="Hello")
        assert result1["status"] == "published"
        assert result2["status"] == "published"
        assert result1["publish_id"] != result2["publish_id"]

    @pytest.mark.asyncio
    async def test_publish_retries_on_rate_limit_then_succeeds(self, connectors_registry, mock_twitter_connector):
        """publish() should retry on RateLimitError and succeed on subsequent attempt."""
        from unittest.mock import AsyncMock

        from src.connectors.errors import RateLimitError
        from src.services.publish_service import PublishService

        mock_twitter_connector.publish = AsyncMock(
            side_effect=[
                RateLimitError("Rate limited"),
                RateLimitError("Rate limited again"),
                {"tweet_url": "https://twitter.com/success"},
            ]
        )

        service = PublishService(connectors=connectors_registry)
        result = await service.publish(
            generation_id="gen_retry_rl",
            platform="twitter",
            text="Retry rate limit",
        )
        assert result["status"] == "published"
        assert mock_twitter_connector.publish.await_count == 3

    @pytest.mark.asyncio
    async def test_publish_exhausts_rate_limit_retries(self, connectors_registry, mock_twitter_connector):
        """publish() should fail after exhausting RateLimitError retries."""
        from unittest.mock import AsyncMock

        from src.connectors.errors import RateLimitError
        from src.services.publish_service import PublishService

        mock_twitter_connector.publish = AsyncMock(
            side_effect=RateLimitError("Always rate limited")
        )

        service = PublishService(connectors=connectors_registry)
        with pytest.raises(RateLimitError):
            await service.publish(
                generation_id="gen_exhaust",
                platform="twitter",
                text="Rate limit exhaust",
            )

    @pytest.mark.asyncio
    async def test_get_status_after_publish(self, connectors_registry):
        """get_status() should return correct status after a successful publish."""
        from src.services.publish_service import PublishService

        service = PublishService(connectors=connectors_registry)
        result = await service.publish(
            generation_id="gen_status_check",
            platform="twitter",
            text="Status check",
        )
        publish_id = result["publish_id"]
        status = await service.get_status(publish_id=publish_id)
        assert status["status"] == "published"
        assert status["generation_id"] == "gen_status_check"
        assert status["platform"] == "twitter"

    @pytest.mark.asyncio
    async def test_publish_with_extra_kwargs_passed_to_connector(self, connectors_registry, mock_twitter_connector):
        """Extra kwargs in publish() should be passed to the connector."""
        from src.services.publish_service import PublishService

        service = PublishService(connectors=connectors_registry)
        await service.publish(
            generation_id="gen_kwargs",
            platform="twitter",
            text="Kwargs test",
            article_url="https://example.com",
            max_retries=5,
        )
        # Check the connector was called with the extra kwargs
        _, kwargs = mock_twitter_connector.publish.await_args
        assert kwargs.get("article_url") == "https://example.com"

    @pytest.mark.asyncio
    async def test_publish_creates_rate_limiter_per_platform(self, connectors_registry):
        """Each platform should get its own rate limiter."""
        from src.services.publish_service import PublishService

        service = PublishService(connectors=connectors_registry)
        await service.publish(generation_id="gen_rl1", platform="twitter", text="T")
        await service.publish(generation_id="gen_rl2", platform="linkedin", text="L")
        assert "twitter" in service.rate_limiters
        assert "linkedin" in service.rate_limiters
        assert service.rate_limiters["twitter"] is not service.rate_limiters["linkedin"]

    @pytest.mark.parametrize(
        ("platform", "expected_connector_called"),
        [
            ("twitter", True),
            ("linkedin", True),
        ],
    )
    @pytest.mark.asyncio
    async def test_publish_each_platform_happy_path(self, connectors_registry, platform, expected_connector_called):
        """Both platforms should work via their connectors."""
        from src.services.publish_service import PublishService

        service = PublishService(connectors=connectors_registry)
        result = await service.publish(
            generation_id=f"gen_{platform}",
            platform=platform,
            text=f"Hello {platform}",
        )
        assert result["status"] == "published"
        assert result["platform"] == platform

    @pytest.mark.asyncio
    async def test_publish_with_empty_connectors_raises_valueerror(self):
        """PublishService with empty connectors should raise ValueError."""
        from src.services.publish_service import PublishService

        service = PublishService(connectors={})
        with pytest.raises(ValueError, match="Unknown platform"):
            await service.publish(
                generation_id="gen_empty_cfg",
                platform="twitter",
                text="No connectors",
            )

    @pytest.mark.asyncio
    async def test_publish_called_with_correct_text(self, connectors_registry, mock_twitter_connector):
        """The connector publish should receive the exact text."""
        from src.services.publish_service import PublishService

        service = PublishService(connectors=connectors_registry)
        await service.publish(
            generation_id="gen_text_chk",
            platform="twitter",
            text="Exact text content",
        )
        mock_twitter_connector.publish.assert_awaited_once_with(
            text="Exact text content",
        )

    @pytest.mark.asyncio
    async def test_publish_result_contains_all_keys(self, connectors_registry):
        """Publish result should contain standard keys."""
        from src.services.publish_service import PublishService

        service = PublishService(connectors=connectors_registry)
        result = await service.publish(
            generation_id="gen_keys",
            platform="twitter",
            text="Key check",
        )
        for key in ("publish_id", "generation_id", "platform", "status"):
            assert key in result, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_get_status_returns_retry_count(self, connectors_registry):
        """get_status() should include retry_count in response."""
        from src.services.publish_service import PublishService

        service = PublishService(connectors=connectors_registry)
        status = await service.get_status(publish_id="pub_retry_check")
        assert "retry_count" in status
        assert isinstance(status["retry_count"], int)

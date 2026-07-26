"""Interface and behavioral tests for the publish endpoint.

Interface tests  — verify PublishRequest/PublishResponse schemas and route registration
                  (should PASS with stubs).
Behavioral tests — verify HTTP responses for the POST /api/v1/publish endpoint
                  (RED until implementation).

All HTTP calls are mocked via httpx.AsyncClient + MockTransport.
"""

from __future__ import annotations

import inspect

import pytest


class TestPublishSchemasInterface:
    """Verify the publish schema interfaces."""

    def test_publish_request_importable(self):
        """PublishRequest should be importable from src.schemas.publish."""
        from src.schemas.publish import PublishRequest

        assert PublishRequest is not None

    def test_publish_request_is_pydantic(self):
        """PublishRequest should be a BaseModel subclass."""
        from pydantic import BaseModel

        from src.schemas.publish import PublishRequest

        assert issubclass(PublishRequest, BaseModel)

    def test_publish_request_fields(self):
        """PublishRequest should have generation_id, platform, platform_config fields."""
        from src.schemas.publish import PublishRequest

        sig = inspect.signature(PublishRequest)
        assert "generation_id" in sig.parameters
        assert "platform" in sig.parameters
        assert "platform_config" in sig.parameters
        # Optional text field for the publish content
        assert "text" in sig.parameters or "content" in sig.parameters

    def test_publish_request_platform_literal(self):
        """The platform field should accept 'twitter' and 'linkedin'."""
        from src.schemas.publish import PublishRequest

        req = PublishRequest(generation_id="gen_1", platform="twitter", text="Hello")
        assert req.platform == "twitter"

        req2 = PublishRequest(generation_id="gen_2", platform="linkedin", text="Hello")
        assert req2.platform == "linkedin"

    def test_publish_response_importable(self):
        """PublishResponse should be importable from src.schemas.publish."""
        from src.schemas.publish import PublishResponse

        assert PublishResponse is not None

    def test_publish_response_is_pydantic(self):
        """PublishResponse should be a BaseModel subclass."""
        from pydantic import BaseModel

        from src.schemas.publish import PublishResponse

        assert issubclass(PublishResponse, BaseModel)

    def test_publish_response_fields(self):
        """PublishResponse should have publish_id, status, platform fields."""
        from src.schemas.publish import PublishResponse

        sig = inspect.signature(PublishResponse)
        assert "publish_id" in sig.parameters or "id" in sig.parameters
        assert "status" in sig.parameters
        assert "platform" in sig.parameters

    def test_errors_importable(self):
        """Error classes should be importable from src.connectors.errors."""
        from src.connectors.errors import AuthError, PublishError, RateLimitError

        assert issubclass(AuthError, PublishError)
        assert issubclass(RateLimitError, PublishError)


class TestPublishRouterInterface:
    """Verify the publish router interface."""

    def test_router_importable(self):
        """The publish router should be importable."""
        from src.routers.publish import router

        assert router is not None

    def test_router_has_publish_endpoint(self):
        """The router should have a POST /api/v1/publish endpoint."""
        from src.routers.publish import router

        routes = {(r.path, tuple(sorted(r.methods or []))) for r in router.routes}
        # Bug fix in original: ("POST",) in methods checks tuple membership instead of string.
        # Changed to "POST" in methods to correctly check if POST method is registered.
        assert any(
            "publish" in path and "POST" in methods
            for path, methods in routes
        )


class TestPublishRouterRegistration:
    """Verify the publish router is registered in the main FastAPI app."""

    def _collect_paths(self, app) -> set[str]:
        """Collect all route paths from an app, handling _IncludedRouter."""
        paths: set[str] = set()
        for r in app.routes:
            if hasattr(r, "path") and r.path:
                paths.add(r.path)
            # _IncludedRouter keeps the original APIRouter
            if hasattr(r, "original_router"):
                for sr in r.original_router.routes:
                    if hasattr(sr, "path") and sr.path:
                        paths.add(sr.path)
        return paths

    def test_publish_router_registered_in_main(self):
        """Publish router should be included in the main app."""
        from src.main import app

        paths = self._collect_paths(app)
        assert any("publish" in p for p in paths), f"Publish routes not found in {sorted(paths)}"


class TestPublishEndpointBehavioral:
    """Behavioral tests for POST /api/v1/publish — RED until implemented.

    Uses an in-memory app and mocked dependencies.
    """

    @pytest.fixture
    def client(self):
        """Create an httpx test client against the real app."""
        from httpx import ASGITransport, AsyncClient

        from src.main import app

        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_publish_201_on_success(self, client):
        """POST /api/v1/publish with valid data should return 201."""
        response = await client.post(
            "/api/v1/publish",
            json={
                "generation_id": "gen_1",
                "platform": "twitter",
                "text": "Hello world!",
            },
        )
        assert response.status_code == 201, f"Body: {response.text}"
        data = response.json()
        assert "publish_id" in data or "id" in data
        assert data.get("status") in ("published", "scheduled", "success")

    @pytest.mark.asyncio
    async def test_publish_422_on_invalid_platform(self, client):
        """POST /api/v1/publish with an invalid platform should return 422."""
        response = await client.post(
            "/api/v1/publish",
            json={
                "generation_id": "gen_2",
                "platform": "instagram",
                "text": "Hello!",
            },
        )
        assert response.status_code == 422, f"Body: {response.text}"

    @pytest.mark.asyncio
    async def test_publish_returns_error_on_bad_request(self, client):
        """POST /api/v1/publish with missing fields should return 422."""
        response = await client.post(
            "/api/v1/publish",
            json={"platform": "twitter"},  # missing generation_id
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_publish_201_for_linkedin(self, client):
        """POST /api/v1/publish for LinkedIn should return 201."""
        response = await client.post(
            "/api/v1/publish",
            json={
                "generation_id": "gen_3",
                "platform": "linkedin",
                "text": "LinkedIn post",
            },
        )
        assert response.status_code == 201, f"Body: {response.text}"

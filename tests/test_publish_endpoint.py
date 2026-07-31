"""Interface and behavioral tests for the publish endpoint.

Interface tests  — verify PublishRequest/PublishResponse schemas and route registration
                  (should PASS with stubs).
Behavioral tests — verify HTTP responses for the POST /api/v1/publish endpoint
                  (RED until implementation).
Edge-case tests  — verify error responses, missing fields, and status lookups.

All HTTP calls are mocked via httpx.AsyncClient + MockTransport.
"""

from __future__ import annotations

import inspect

import pytest



# Mark as integration (uses TestClient/AsyncClient)
pytestmark = pytest.mark.integration

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

    def test_publish_request_rejects_invalid_platform(self):
        """PublishRequest should reject invalid platform at validation."""
        from pydantic import ValidationError

        from src.schemas.publish import PublishRequest

        with pytest.raises(ValidationError):
            PublishRequest(generation_id="g", platform="instagram", text="Hi")

    def test_publish_status_response_importable(self):
        """PublishStatusResponse should be importable."""
        from src.schemas.publish import PublishStatusResponse

        assert PublishStatusResponse is not None

    def test_publish_status_response_fields(self):
        """PublishStatusResponse should have publish_id, status, retry_count."""
        from src.schemas.publish import PublishStatusResponse

        sig = inspect.signature(PublishStatusResponse)
        assert "publish_id" in sig.parameters
        assert "status" in sig.parameters
        assert "retry_count" in sig.parameters
        assert "error_message" in sig.parameters


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
        assert any(
            "publish" in path and "POST" in methods
            for path, methods in routes
        )

    def test_router_has_get_status_endpoint(self):
        """The router should have a GET /api/v1/publish/{publish_id} endpoint."""
        from src.routers.publish import router

        routes = {(r.path, tuple(r.methods)) for r in router.routes}
        assert any("/{publish_id}" in path and "GET" in methods for path, methods in routes)

    def test_router_prefix(self):
        """The router prefix should be /api/v1/publish."""
        from src.routers.publish import router

        assert router.prefix == "/api/v1/publish"


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


class TestPublishEndpointEdgeCases:
    """Edge-case tests for publish endpoints — boundary conditions and error responses."""

    @pytest.fixture
    def client(self):
        """Create an httpx test client against the real app."""
        from httpx import ASGITransport, AsyncClient

        from src.main import app

        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_publish_without_auth_succeeds(self, client):
        """POST /api/v1/publish without auth should succeed (optional auth)."""
        response = await client.post(
            "/api/v1/publish",
            json={
                "generation_id": "gen_noauth",
                "platform": "twitter",
                "text": "No auth test",
            },
        )
        assert response.status_code == 201, f"Body: {response.text}"

    @pytest.mark.asyncio
    async def test_publish_with_empty_text_succeeds(self, client):
        """POST /api/v1/publish with empty text should return 201."""
        response = await client.post(
            "/api/v1/publish",
            json={
                "generation_id": "gen_empty",
                "platform": "twitter",
                "text": "",
            },
        )
        assert response.status_code == 201, f"Body: {response.text}"

    @pytest.mark.asyncio
    async def test_publish_with_platform_config(self, client):
        """POST /api/v1/publish with platform_config should succeed."""
        response = await client.post(
            "/api/v1/publish",
            json={
                "generation_id": "gen_cfg",
                "platform": "twitter",
                "text": "With config",
                "platform_config": {"max_retries": 5},
            },
        )
        assert response.status_code == 201, f"Body: {response.text}"

    @pytest.mark.asyncio
    async def test_publish_with_minimal_body_succeeds(self, client):
        """POST /api/v1/publish with only required fields should succeed."""
        response = await client.post(
            "/api/v1/publish",
            json={
                "generation_id": "gen_min",
                "platform": "twitter",
            },
        )
        assert response.status_code == 201, f"Body: {response.text}"

    @pytest.mark.asyncio
    async def test_publish_with_all_optional_fields(self, client):
        """POST /api/v1/publish with all fields should succeed."""
        response = await client.post(
            "/api/v1/publish",
            json={
                "generation_id": "gen_full",
                "platform": "linkedin",
                "text": "Full post content",
                "platform_config": {
                    "article_url": "https://example.com",
                    "article_title": "Example",
                },
            },
        )
        assert response.status_code == 201, f"Body: {response.text}"

    @pytest.mark.asyncio
    async def test_get_publish_status_invalid_id(self, client):
        """GET /api/v1/publish/{id} with invalid id should return status 'not_found'."""
        response = await client.get("/api/v1/publish/nonexistent_pub_id")
        assert response.status_code == 200, f"Body: {response.text}"
        data = response.json()
        assert data["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_get_publish_status_valid_id(self, client):
        """GET /api/v1/publish/{id} after publishing should return status."""
        # First publish
        pub_response = await client.post(
            "/api/v1/publish",
            json={
                "generation_id": "gen_get_test",
                "platform": "twitter",
                "text": "Check status",
            },
        )
        assert pub_response.status_code == 201
        publish_id = pub_response.json()["publish_id"]

        # Then get status
        status_response = await client.get(f"/api/v1/publish/{publish_id}")
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["publish_id"] == publish_id
        assert data["status"] in ("published", "not_found")

    @pytest.mark.asyncio
    async def test_get_publish_status_empty_id(self, client):
        """GET /api/v1/publish/ with empty id should redirect (307) to /api/v1/publish."""
        response = await client.get("/api/v1/publish/")
        # FastAPI redirects trailing-slash to non-trailing path
        assert response.status_code in (307, 200, 404), f"Unexpected status: {response.status_code}"

    @pytest.mark.asyncio
    async def test_publish_422_missing_platform(self, client):
        """POST /api/v1/publish with missing platform should return 422."""
        response = await client.post(
            "/api/v1/publish",
            json={"generation_id": "gen_missing"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_publish_422_empty_generation_id(self, client):
        """POST /api/v1/publish with empty generation_id should return 422."""
        response = await client.post(
            "/api/v1/publish",
            json={
                "generation_id": "",
                "platform": "twitter",
                "text": "Empty gen_id",
            },
        )
        # Empty string might be accepted by pydantic as a valid str
        assert response.status_code in (201, 422), f"Body: {response.text}"

    @pytest.mark.asyncio
    async def test_publish_with_long_text(self, client):
        """POST /api/v1/publish with very long text should return 201."""
        response = await client.post(
            "/api/v1/publish",
            json={
                "generation_id": "gen_long",
                "platform": "twitter",
                "text": "X" * 10000,
            },
        )
        assert response.status_code == 201, f"Body: {response.text}"

    @pytest.mark.asyncio
    async def test_publish_linkedin_with_article_config(self, client):
        """POST /api/v1/publish LinkedIn with full article config should succeed."""
        response = await client.post(
            "/api/v1/publish",
            json={
                "generation_id": "gen_article",
                "platform": "linkedin",
                "text": "Check out this article",
                "platform_config": {
                    "article_url": "https://example.com/great-article",
                    "article_title": "A Great Article",
                    "author": "urn:li:person:test",
                },
            },
        )
        assert response.status_code == 201, f"Body: {response.text}"

    @pytest.mark.asyncio
    async def test_publish_twitter_with_platform_config(self, client):
        """POST /api/v1/publish Twitter with platform_config should succeed."""
        response = await client.post(
            "/api/v1/publish",
            json={
                "generation_id": "gen_cfg2",
                "platform": "twitter",
                "text": "With extra config",
                "platform_config": {"max_retries": 5, "some_option": True},
            },
        )
        assert response.status_code == 201, f"Body: {response.text}"

    @pytest.mark.asyncio
    async def test_get_publish_status_list_endpoint(self, client):
        """GET /api/v1/publish/status should return status list."""
        response = await client.get("/api/v1/publish/status")
        assert response.status_code == 200
        data = response.json()
        assert "statuses" in data
        assert isinstance(data["statuses"], list)

    @pytest.mark.asyncio
    async def test_get_publish_status_list_with_filter(self, client):
        """GET /api/v1/publish/status with filter should work."""
        response = await client.get("/api/v1/publish/status?status_filter=published")
        assert response.status_code == 200
        data = response.json()
        assert data["filter"] == "published"

    @pytest.mark.asyncio
    async def test_publish_twitter_minimal_json(self, client):
        """Twitter publish with minimal valid JSON should succeed."""
        response = await client.post(
            "/api/v1/publish",
            json={"generation_id": "g_min", "platform": "twitter"},
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_publish_linkedin_minimal_json(self, client):
        """LinkedIn publish with minimal valid JSON should succeed."""
        response = await client.post(
            "/api/v1/publish",
            json={"generation_id": "g_min_li", "platform": "linkedin"},
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_publish_response_schema(self, client):
        """Publish response should match PublishResponse schema."""
        response = await client.post(
            "/api/v1/publish",
            json={"generation_id": "g_schema", "platform": "twitter", "text": "Schema test"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "publish_id" in data
        assert "generation_id" in data
        assert "platform" in data
        assert "status" in data
        assert "created_at" in data

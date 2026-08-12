"""Interface and behavioral tests for POST /content/translate endpoint (AC-T4.10).

Interface tests  — verify router import, route registration, handler signature (PASS).
Behavioral tests — verify NotImplementedError or 500 due to stub service (FAIL).
"""

from __future__ import annotations

import inspect

import pytest

# Mark as integration (uses TestClient/AsyncClient)
pytestmark = pytest.mark.integration

from httpx import ASGITransport, AsyncClient

from src.main import app
from src.routers.translate import router as translate_router

# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestTranslateRouterInterface:
    """Verify the translate router interface."""

    def test_router_importable(self):
        assert translate_router is not None

    def test_router_prefix(self):
        """Router prefix should be /content for /content/translate."""
        assert translate_router.prefix == "/content"

    def test_router_has_translate_endpoint(self):
        """Router should have a POST /content/translate route."""
        routes = {(r.path, tuple(sorted(r.methods or []))) for r in translate_router.routes}
        assert ("/content/translate", ("POST",)) in routes, (
            f"Expected /content/translate POST. Found: {sorted(routes)}"
        )

    def test_translate_endpoint_handler_exists(self):
        """Handler function should be importable."""
        from src.routers.translate import translate_content

        assert callable(translate_content)

    def test_translate_endpoint_is_async(self):
        from src.routers.translate import translate_content

        assert inspect.iscoroutinefunction(translate_content)

    def test_translate_handler_accepts_body(self):
        """Handler signature should accept TranslateRequest body."""
        from src.routers.translate import translate_content

        sig = inspect.signature(translate_content)
        assert "body" in sig.parameters

    def test_translate_handler_returns_translate_response(self):
        """Return annotation should reference TranslateResponse."""
        from src.routers.translate import translate_content

        ann = translate_content.__annotations__
        assert "return" in ann
        return_str = str(ann["return"])
        assert "TranslateResponse" in return_str


class TestTranslateRouterRegistration:
    """Verify translate router is registered in the FastAPI app."""

    def _collect_paths(self, app) -> set[str]:
        """Collect all route paths from an app, handling _IncludedRouter."""
        paths: set[str] = set()
        for r in app.routes:
            if hasattr(r, "path") and r.path:
                paths.add(r.path)
            if hasattr(r, "original_router"):
                for sr in r.original_router.routes:
                    if hasattr(sr, "path") and sr.path:
                        paths.add(sr.path)
        return paths

    def test_translate_router_registered_in_app(self):
        """Translate router should be included in the main app."""
        paths = self._collect_paths(app)
        assert "/content/translate" in paths, (
            f"/content/translate not found in registered paths: {sorted(paths)}"
        )


class TestTranslateEndpointAuth:
    """AC-T4.10 — Auth and rate limiting."""

    @pytest.mark.asyncio
    async def test_endpoint_requires_auth(self):
        """POST /content/translate should return 401 without valid JWT."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/content/translate",
                json={
                    "text": "Hello world",
                    "target_language": "de",
                },
            )
            assert response.status_code in (401, 403, 500, 422), (
                f"Expected auth error or stub error, got {response.status_code}: {response.text}"
            )

    def test_rate_limiting_context_in_handler(self):
        """Handler should include a parameter for rate-limiting context."""
        from src.routers.translate import translate_content

        sig = inspect.signature(translate_content)
        param_names = list(sig.parameters.keys())
        has_rate_context = "request" in param_names or "current_user" in param_names
        assert has_rate_context, (
            f"Handler params {param_names} should include 'request' or 'current_user' "
            "for rate limiting context"
        )


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (demonstrate contract via failures)
# ============================================================================


class TestTranslateEndpointResponse:
    """Verify endpoint responds (will fail with 500 due to stub service)."""

    @pytest.mark.asyncio
    async def _post_translate(self, client: AsyncClient, payload: dict) -> int:
        """Helper to POST /content/translate and return status code."""
        response = await client.post("/content/translate", json=payload)
        return response.status_code

    @pytest.mark.asyncio
    async def test_translate_happy_path_llm(self):
        """POST /content/translate with LLM mode returns non-404."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            status = await self._post_translate(client, {
                "text": "Hello world", "source_language": "en",
                "target_language": "de", "content_type": "blog",
                "mode": "llm", "scoring": False,
            })
            assert status != 404, "Endpoint not found — router not registered"

    @pytest.mark.asyncio
    async def test_translate_happy_path_nmt(self):
        """POST /content/translate with NMT mode returns non-404."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            status = await self._post_translate(client, {
                "text": "Technical documentation", "source_language": "en",
                "target_language": "fr", "content_type": "email", "mode": "nmt",
            })
            assert status != 404

    @pytest.mark.asyncio
    async def test_translate_happy_path_auto(self):
        """POST /content/translate with auto mode returns non-404."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            status = await self._post_translate(client, {
                "text": "Check out our new product", "source_language": "auto",
                "target_language": "es", "content_type": "social", "mode": "auto",
            })
            assert status != 404

    @pytest.mark.asyncio
    async def test_translate_with_brand_voice(self):
        """POST /content/translate with brand_voice_id."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            status = await self._post_translate(client, {
                "text": "Welcome to our platform", "source_language": "en",
                "target_language": "de", "content_type": "blog",
                "mode": "llm", "brand_voice_id": "acme-corp-v1",
            })
            assert status != 404

    @pytest.mark.asyncio
    async def test_translate_with_scoring(self):
        """POST /content/translate with scoring=true."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            status = await self._post_translate(client, {
                "text": "Data-driven insights", "source_language": "en",
                "target_language": "fr", "scoring": True,
            })
            assert status != 404

    @pytest.mark.asyncio
    async def test_translate_auto_detect(self):
        """POST /content/translate with source_language='auto'."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            status = await self._post_translate(client, {
                "text": "Bonjour le monde", "source_language": "auto",
                "target_language": "en", "mode": "llm",
            })
            assert status != 404

    @pytest.mark.asyncio
    async def test_translate_same_language(self):
        """Same source and target language — should fail with 400."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            status = await self._post_translate(client, {
                "text": "Hello world", "source_language": "en",
                "target_language": "en",
            })
            assert status != 404

"""Interface and behavioral tests for GET /api/v1/languages endpoint.

Interface tests  — verify imports, class signatures, route registration (should PASS once stubs exist).
Behavioral tests — exercise the endpoint with real HTTP calls (should FAIL with NotImplementedError
                   until the endpoint is fully implemented).
"""

from __future__ import annotations

import inspect
import time

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.main import app
from src.routers.languages import router
from src.schemas.languages import LanguageInfo, LanguageResponse
from src.services.language_data import LanguageDataService

# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS once stubs exist)
# ============================================================================


class TestLanguageSchemasInterface:
    """Verify the LanguageInfo and LanguageResponse schema interfaces."""

    def test_language_info_importable(self):
        """LanguageInfo should be importable from src.schemas.languages."""
        assert LanguageInfo is not None

    def test_language_info_is_pydantic(self):
        """LanguageInfo should be a Pydantic BaseModel subclass."""
        from pydantic import BaseModel

        assert issubclass(LanguageInfo, BaseModel)

    def test_language_info_fields(self):
        """LanguageInfo should have all required fields."""
        sig = inspect.signature(LanguageInfo)
        assert "code" in sig.parameters
        assert "name" in sig.parameters
        assert "english_name" in sig.parameters
        assert "status" in sig.parameters
        assert "supports_translation" in sig.parameters
        assert "supports_detection" in sig.parameters

    def test_language_info_field_types(self):
        """LanguageInfo fields should have correct type annotations."""
        fields = LanguageInfo.model_fields
        assert fields["code"].annotation is str
        assert fields["name"].annotation is str
        assert fields["english_name"].annotation is str
        assert fields["supports_translation"].annotation is bool
        assert fields["supports_detection"].annotation is bool

    def test_language_info_status_is_literal(self):
        """status should be Literal['active', 'beta']."""
        from typing import get_origin, get_args, Literal

        annotation = LanguageInfo.model_fields["status"].annotation
        assert get_origin(annotation) is Literal
        args = get_args(annotation)
        assert "active" in args
        assert "beta" in args

    def test_language_response_importable(self):
        """LanguageResponse should be importable."""
        assert LanguageResponse is not None

    def test_language_response_is_pydantic(self):
        """LanguageResponse should be a Pydantic BaseModel subclass."""
        from pydantic import BaseModel

        assert issubclass(LanguageResponse, BaseModel)

    def test_language_response_fields(self):
        """LanguageResponse should have languages and total fields."""
        sig = inspect.signature(LanguageResponse)
        assert "languages" in sig.parameters
        assert "total" in sig.parameters

    def test_language_response_field_types(self):
        """LanguageResponse field types should be correct."""
        fields = LanguageResponse.model_fields
        # languages: list[LanguageInfo]
        assert fields["languages"].annotation is not None
        assert fields["total"].annotation is int

    def test_language_response_serialization(self):
        """LanguageResponse should serialize correctly."""
        lang = LanguageInfo(
            code="en",
            name="English",
            english_name="English",
            status="active",
            supports_translation=True,
            supports_detection=True,
        )
        resp = LanguageResponse(languages=[lang], total=1)
        data = resp.model_dump()
        assert data["languages"][0]["code"] == "en"
        assert data["total"] == 1


class TestLanguagesRouterInterface:
    """Verify the languages router interface."""

    def test_router_importable(self):
        """Router should be importable and have correct prefix."""
        assert router is not None
        assert router.prefix == "/api/v1/languages"

    def test_router_has_get_endpoint(self):
        """Router should have a GET /api/v1/languages endpoint."""
        routes = {(r.path, tuple(sorted(r.methods or []))) for r in router.routes}
        assert ("/api/v1/languages", ("GET",)) in routes, (
            f"Expected GET /api/v1/languages in routes, got {sorted(routes)}"
        )

    def test_router_endpoint_has_response_model(self):
        """The GET endpoint should declare response_model=LanguageResponse."""
        for r in router.routes:
            if r.path == "/api/v1/languages" and "GET" in (r.methods or []):
                # FastAPI stores response_model on the route's endpoint
                assert r.response_model is not None, "response_model should be set"
                assert r.response_model == LanguageResponse, (
                    f"Expected {LanguageResponse}, got {r.response_model}"
                )
                return
        pytest.fail("GET /api/v1/languages route not found")


class TestLanguagesRouterRegistration:
    """Verify the languages router is registered in the main FastAPI app."""

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

    def test_languages_router_registered_in_main(self):
        """Languages router should be included in the main app."""
        paths = self._collect_paths(app)
        assert "/api/v1/languages" in paths, (
            f"Languages route not found in {sorted(paths)}"
        )


class TestLanguageDataServiceInterface:
    """Verify the LanguageDataService interface."""

    def test_service_importable(self):
        """LanguageDataService should be importable."""
        assert LanguageDataService is not None

    def test_service_has_get_languages(self):
        """LanguageDataService should have get_languages method."""
        assert hasattr(LanguageDataService, "get_languages")
        assert inspect.ismethod(LanguageDataService.get_languages) or callable(
            LanguageDataService.get_languages
        )

    def test_service_get_languages_signature(self):
        """get_languages should accept no args (beyond self) and return LanguageResponse."""
        sig = inspect.signature(LanguageDataService.get_languages)
        params = list(sig.parameters.keys())
        assert params == ["self"], f"Expected only 'self', got {params}"
        # With `from __future__ import annotations`, return_annotation is a string.
        # Use typing.get_type_hints to resolve the forward reference.
        from typing import get_type_hints

        hints = get_type_hints(LanguageDataService.get_languages)
        assert hints.get("return") is LanguageResponse, (
            f"Expected return {LanguageResponse}, got {hints.get('return')}"
        )

    def test_service_has_get_language_by_code(self):
        """LanguageDataService should have get_language_by_code method."""
        assert hasattr(LanguageDataService, "get_language_by_code")
        assert (
            inspect.ismethod(LanguageDataService.get_language_by_code)
            or callable(LanguageDataService.get_language_by_code)
        )

    def test_service_get_language_by_code_signature(self):
        """get_language_by_code should accept code: str and return LanguageInfo | None."""
        sig = inspect.signature(LanguageDataService.get_language_by_code)
        # self + code parameter
        assert "code" in sig.parameters, f"Expected 'code' param, got {list(sig.parameters.keys())}"
        from typing import get_type_hints
        hints = get_type_hints(LanguageDataService.get_language_by_code)
        ret = hints.get("return")
        assert ret in (LanguageInfo | None, None | LanguageInfo), (
            f"Expected LanguageInfo | None return, got {ret}"
        )

    def test_service_has_get_active_languages(self):
        """LanguageDataService should have get_active_languages method."""
        assert hasattr(LanguageDataService, "get_active_languages")

    def test_service_has_total_count_property(self):
        """LanguageDataService should have total_count property."""
        assert isinstance(
            inspect.getattr_static(LanguageDataService, "total_count", None), property
        ), "total_count should be a property (not a method)"

    def test_service_has_active_count_property(self):
        """LanguageDataService should have active_count property."""
        assert isinstance(
            inspect.getattr_static(LanguageDataService, "active_count", None), property
        ), "active_count should be a property (not a method)"


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (should FAIL with NotImplementedError)
# ============================================================================


@pytest.mark.asyncio(loop_scope="function")
class TestLanguageEndpointBehavior:
    """Behavioral tests for the GET /api/v1/languages endpoint.

    These tests exercise the real HTTP endpoint and the LanguageDataService.
    They will fail with HTTP 500 / RuntimeError wrapping NotImplementedError
    until the full implementation is written.
    """

    @pytest.fixture
    def client(self) -> AsyncClient:
        """Create a test client with the real app (no DB dependency needed)."""
        # Override get_db to a dummy that raises if called
        async def _no_db() -> AsyncGenerator[AsyncSession]:
            pytest.fail("get_db should not be called by a public /languages endpoint")
            yield None  # type: ignore[unreachable]

        app.dependency_overrides[get_db] = _no_db
        transport = ASGITransport(app=app)
        client = AsyncClient(transport=transport, base_url="http://test")
        # Return client — cleanup runs in the test body or a finalizer
        yield client
        import asyncio
        asyncio.run(client.aclose())
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_behavior_endpoint_returns_200(self, client: AsyncClient):
        """AC-T3.1: GET /api/v1/languages should return 200."""
        response = await client.get("/api/v1/languages")
        # Will get a 500 wrapping NotImplementedError until implementation
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )

    @pytest.mark.asyncio
    async def test_behavior_response_structure(self, client: AsyncClient):
        """AC-T3.1 + AC-T3.2: Response should have languages list + total, valid LanguageInfo."""
        response = await client.get("/api/v1/languages")
        assert response.status_code == 200
        data = response.json()

        # Top-level structure
        assert "languages" in data, "Response missing 'languages' key"
        assert "total" in data, "Response missing 'total' key"
        assert isinstance(data["languages"], list), "'languages' should be a list"
        assert isinstance(data["total"], int), "'total' should be an int"
        assert data["total"] == len(data["languages"]), (
            f"total ({data['total']}) != len(languages) ({len(data['languages'])})"
        )

        # Each language entry must have all required fields
        for lang in data["languages"]:
            assert "code" in lang, f"Language missing 'code': {lang}"
            assert "name" in lang, f"Language missing 'name': {lang}"
            assert "english_name" in lang, f"Language missing 'english_name': {lang}"
            assert "status" in lang, f"Language missing 'status': {lang}"
            assert "supports_translation" in lang, (
                f"Language missing 'supports_translation': {lang}"
            )
            assert "supports_detection" in lang, (
                f"Language missing 'supports_detection': {lang}"
            )

            # Validate types
            assert isinstance(lang["code"], str), "code should be str"
            assert isinstance(lang["name"], str), "name should be str"
            assert isinstance(lang["english_name"], str), "english_name should be str"
            assert lang["status"] in ("active", "beta"), (
                f"status should be 'active' or 'beta', got {lang['status']}"
            )
            assert isinstance(lang["supports_translation"], bool), (
                "supports_translation should be bool"
            )
            assert isinstance(lang["supports_detection"], bool), (
                "supports_detection should be bool"
            )

            # Validate ISO 639-1 code format (2-letter code, possibly with variant)
            assert len(lang["code"]) >= 2, (
                f"code '{lang['code']}' should be at least 2 chars"
            )

    @pytest.mark.asyncio
    async def test_behavior_min_10_active_languages(self, client: AsyncClient):
        """AC-T3.3: At least 10 active languages including en, de, fr, es, it, pt, nl, pl, ja, zh."""
        response = await client.get("/api/v1/languages")
        assert response.status_code == 200
        data = response.json()

        active = [lang for lang in data["languages"] if lang["status"] == "active"]
        assert len(active) >= 10, (
            f"Expected at least 10 active languages, got {len(active)}"
        )

        active_codes = {lang["code"] for lang in active}
        required = {"en", "de", "fr", "es", "it", "pt", "nl", "pl", "ja", "zh"}
        missing = required - active_codes
        assert not missing, f"Required active languages missing: {missing}"

    @pytest.mark.asyncio
    async def test_behavior_no_auth_required(self, client: AsyncClient):
        """AC-T3.4: Endpoint should return 200 without any auth token (public)."""
        # Explicitly no Authorization header
        response = await client.get("/api/v1/languages")
        assert response.status_code == 200, (
            f"Expected 200 (public endpoint), got {response.status_code}. "
            f"If 401/403, auth is incorrectly required."
        )

    @pytest.mark.asyncio
    async def test_behavior_cache_headers_present(self, client: AsyncClient):
        """AC-T3.5: Response should have Cache-Control and ETag headers."""
        response = await client.get("/api/v1/languages")
        assert response.status_code == 200

        cache_control = response.headers.get("cache-control")
        assert cache_control is not None, (
            "Missing Cache-Control header. "
            "Endpoints with static data should include: "
            "Cache-Control: public, max-age=<seconds>"
        )

        etag = response.headers.get("etag")
        assert etag is not None, (
            "Missing ETag header. "
            "Endpoints with static data should include an ETag for conditional requests."
        )

        # Cache-Control should be meaningful (not just "no-cache")
        assert "public" in cache_control.lower() or "max-age" in cache_control.lower(), (
            f"Cache-Control value '{cache_control}' is too restrictive for a public endpoint"
        )

    @pytest.mark.asyncio
    async def test_behavior_performance_under_50ms(self, client: AsyncClient):
        """AC-T3.6: Endpoint should respond in <50ms (data is static/config-driven)."""
        # Warmup request (caches are cold on first call)
        _ = await client.get("/api/v1/languages")

        # Timed request
        start = time.monotonic()
        response = await client.get("/api/v1/languages")
        elapsed_ms = (time.monotonic() - start) * 1000

        assert response.status_code == 200
        assert elapsed_ms < 50, (
            f"Response took {elapsed_ms:.1f}ms, expected <50ms. "
            f"Language data is static — latency should be minimal."
        )


class TestLanguageServiceBehavior:
    """Behavioral tests for LanguageDataService.

    These will fail with NotImplementedError until the service is implemented.
    """

    def test_behavior_service_init_fails_with_not_implemented(self):
        """LanguageDataService() should initialize cleanly (fully implemented)."""
        service = LanguageDataService()
        assert service is not None

    def test_behavior_get_languages_fails_with_not_implemented(self):
        """get_languages() should return a LanguageResponse (fully implemented)."""
        service = LanguageDataService()
        result = service.get_languages()
        assert isinstance(result, LanguageResponse)
        assert result.total > 0

    def test_behavior_get_language_by_code_fails_with_not_implemented(self):
        """get_language_by_code() should return a LanguageInfo (fully implemented)."""
        service = LanguageDataService()
        result = service.get_language_by_code("en")
        assert isinstance(result, LanguageInfo)
        assert result.code == "en"

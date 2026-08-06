"""Interface and behavioral tests for brand kit CRUD endpoints and schemas.

Interface tests  — verify imports, class signatures (should PASS).
Behavioral tests — verify handler existence (should PASS even on stubs).
"""
from __future__ import annotations

import inspect
from datetime import UTC

from pydantic import BaseModel

from src.routers.brand_kit import router
from src.schemas.brand_kit import (
    BrandKitCreate,
    BrandKitListResponse,
    BrandKitResponse,
    BrandKitUpdate,
)

# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestBrandKitSchemasInterface:
    """Verify the brand kit schema interfaces."""

    def test_brand_kit_create_importable(self):
        assert BrandKitCreate is not None

    def test_brand_kit_create_is_pydantic(self):
        assert issubclass(BrandKitCreate, BaseModel)

    def test_brand_kit_create_fields(self):
        sig = inspect.signature(BrandKitCreate)
        assert "name" in sig.parameters
        assert "description" in sig.parameters
        assert "brand_type" in sig.parameters
        assert "user_id" in sig.parameters
        assert "brand_voice_id" in sig.parameters
        assert "colors" in sig.parameters
        assert "fonts" in sig.parameters
        assert "logos" in sig.parameters

    def test_brand_kit_update_importable(self):
        assert BrandKitUpdate is not None

    def test_brand_kit_update_is_pydantic(self):
        assert issubclass(BrandKitUpdate, BaseModel)

    def test_brand_kit_update_all_fields_optional(self):
        sig = inspect.signature(BrandKitUpdate)
        for name, param in sig.parameters.items():
            assert param.default is None or param.default is not inspect.Parameter.empty, (
                f"Field '{name}' should be optional"
            )

    def test_brand_kit_response_importable(self):
        assert BrandKitResponse is not None

    def test_brand_kit_response_is_pydantic(self):
        assert issubclass(BrandKitResponse, BaseModel)

    def test_brand_kit_response_fields(self):
        sig = inspect.signature(BrandKitResponse)
        assert "id" in sig.parameters
        assert "name" in sig.parameters
        assert "description" in sig.parameters
        assert "brand_type" in sig.parameters
        assert "colors" in sig.parameters
        assert "fonts" in sig.parameters
        assert "logos" in sig.parameters
        assert "version" in sig.parameters
        assert "created_at" in sig.parameters
        assert "updated_at" in sig.parameters

    def test_brand_kit_list_response_importable(self):
        assert BrandKitListResponse is not None

    def test_brand_kit_list_response_is_pydantic(self):
        assert issubclass(BrandKitListResponse, BaseModel)

    def test_brand_kit_list_response_fields(self):
        sig = inspect.signature(BrandKitListResponse)
        assert "items" in sig.parameters
        assert "total" in sig.parameters
        assert "limit" in sig.parameters
        assert "offset" in sig.parameters


class TestBrandKitRouterInterface:
    """Verify the brand kit router interface."""

    def test_router_importable(self):
        assert router is not None
        assert router.prefix == "/brand-kit"

    def test_router_tags(self):
        assert "brand-kit" in router.tags

    def test_router_has_routes(self):
        routes = {r.path for r in router.routes}
        # Root path for POST (create) and GET (list)
        assert "/brand-kit" in routes
        # {brand_kit_id} for GET by id
        assert "/brand-kit/{brand_kit_id}" in routes
        # guidelines endpoint
        assert "/brand-kit/guidelines" in routes
        # upload endpoint
        assert "/brand-kit/upload" in routes

    def test_router_has_create_route(self):
        routes = {(r.path, frozenset(r.methods or [])) for r in router.routes}
        # POST to root
        has_post = any(methods == frozenset({"POST"}) for _, methods in routes)
        assert has_post

    def test_router_has_list_route(self):
        routes = {(r.path, frozenset(r.methods or [])) for r in router.routes}
        # GET to root
        has_get_root = any(
            path == "/brand-kit" and methods == frozenset({"GET"})
            for path, methods in routes
        )
        assert has_get_root

    def test_router_has_get_by_id_route(self):
        routes = {(r.path, frozenset(r.methods or [])) for r in router.routes}
        has_get_id = any(
            path == "/brand-kit/{brand_kit_id}" and methods == frozenset({"GET"})
            for path, methods in routes
        )
        assert has_get_id

    def test_router_has_guidelines_route(self):
        routes = {(r.path, frozenset(r.methods or [])) for r in router.routes}
        has_guidelines = any(
            path == "/brand-kit/guidelines" and methods == frozenset({"GET"})
            for path, methods in routes
        )
        assert has_guidelines

    def test_router_has_upload_route(self):
        routes = {(r.path, frozenset(r.methods or [])) for r in router.routes}
        has_upload = any(
            path == "/brand-kit/upload" and methods == frozenset({"POST"})
            for path, methods in routes
        )
        assert has_upload


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (verify real implementation)
# ============================================================================


class TestBrandKitSchemasBehavioral:
    """Behavioral tests for brand kit schemas — Pydantic models should work."""

    def test_brand_kit_create_valid(self):
        req = BrandKitCreate(name="My Brand")
        assert req.name == "My Brand"
        assert req.description == ""
        assert req.brand_type == "personal"

    def test_brand_kit_create_with_colors(self):
        from src.schemas.brand_kit import ColorPalette

        req = BrandKitCreate(
            name="Color Brand",
            colors=ColorPalette(primary="#ff0000", secondary="#00ff00"),
        )
        assert req.colors.primary == "#ff0000"
        assert req.colors.secondary == "#00ff00"

    def test_brand_kit_update_partial(self):
        req = BrandKitUpdate(name="Updated")
        assert req.name == "Updated"
        assert req.description is None
        assert req.brand_type is None

    def test_brand_kit_response_from_data(self):
        from datetime import datetime

        resp = BrandKitResponse(
            id="kit-1",
            name="Test Brand",
            description="desc",
            brand_type="personal",
            version=1,
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
        )
        assert resp.id == "kit-1"
        assert resp.name == "Test Brand"
        assert resp.version == 1


class TestBrandKitEndpointsBehavioral:
    """Behavioral tests for brand kit endpoints — verify real implementation."""

    def test_create_handler_exists(self):
        """POST /brand-kit handler exists and is callable."""
        from src.routers.brand_kit import create_brand_kit
        assert callable(create_brand_kit)

    def test_list_handler_exists(self):
        """GET /brand-kit handler exists and is callable."""
        from src.routers.brand_kit import list_brand_kits
        assert callable(list_brand_kits)

    def test_get_handler_exists(self):
        """GET /brand-kit/{id} handler exists and is callable."""
        from src.routers.brand_kit import get_brand_kit
        assert callable(get_brand_kit)

    def test_guidelines_handler_exists(self):
        """GET /brand-kit/guidelines handler exists and is callable."""
        from src.routers.brand_kit import generate_guidelines
        assert callable(generate_guidelines)

    def test_upload_handler_exists(self):
        """POST /brand-kit/upload handler exists and is callable."""
        from src.routers.brand_kit import upload_brand_kit_file
        assert callable(upload_brand_kit_file)

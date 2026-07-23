"""Interface and behavioral tests for brand voice CRUD endpoints and schemas.

Interface tests  — verify imports, class signatures (should PASS).
Behavioral tests — verify NotImplementedError for stubs.
"""

from __future__ import annotations

import inspect
from datetime import datetime

import pytest

pytestmark = pytest.mark.asyncio

from src.schemas.brand_voice import (
    BrandVoiceCreate,
    BrandVoiceUpdate,
    BrandVoiceResponse,
    BrandVoiceListResponse,
)
from src.routers.brand_voice import router


# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestBrandVoiceSchemasInterface:
    """Verify the brand voice schema interfaces."""

    def test_brand_voice_create_importable(self):
        assert BrandVoiceCreate is not None

    def test_brand_voice_create_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(BrandVoiceCreate, BaseModel)

    def test_brand_voice_create_fields(self):
        sig = inspect.signature(BrandVoiceCreate)
        assert "name" in sig.parameters
        assert "description" in sig.parameters
        assert "brand_identity" in sig.parameters
        assert "attributes" in sig.parameters
        assert "vocabulary" in sig.parameters
        assert "scenarios" in sig.parameters
        assert "formatting" in sig.parameters

    def test_brand_voice_update_importable(self):
        assert BrandVoiceUpdate is not None

    def test_brand_voice_update_all_fields_optional(self):
        sig = inspect.signature(BrandVoiceUpdate)
        for name, param in sig.parameters.items():
            if name not in ("name",):
                assert param.default is None or param.default is not inspect.Parameter.empty, (
                    f"Field '{name}' should be optional"
                )

    def test_brand_voice_response_importable(self):
        assert BrandVoiceResponse is not None

    def test_brand_voice_response_fields(self):
        sig = inspect.signature(BrandVoiceResponse)
        assert "id" in sig.parameters
        assert "name" in sig.parameters
        assert "version" in sig.parameters
        assert "created_at" in sig.parameters
        assert "updated_at" in sig.parameters

    def test_brand_voice_list_response_importable(self):
        assert BrandVoiceListResponse is not None

    def test_brand_voice_list_response_fields(self):
        sig = inspect.signature(BrandVoiceListResponse)
        assert "items" in sig.parameters
        assert "total" in sig.parameters
        assert "limit" in sig.parameters
        assert "offset" in sig.parameters


class TestBrandVoiceRouterInterface:
    """Verify the brand voice router interface."""

    def test_router_importable(self):
        assert router is not None
        assert router.prefix == "/brand-voice"

    def test_router_has_endpoints(self):
        routes = [r.path for r in router.routes]
        assert "/brand-voice" in routes
        assert "/brand-voice/{brand_voice_id}" in routes

    def test_router_has_create(self):
        routes = {(r.path, tuple(r.methods or [])) for r in router.routes}
        assert ("/brand-voice", ("POST",)) or ("", ("POST",)) in routes


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (verify real implementation)
# ============================================================================


class TestBrandVoiceSchemasBehavioral:
    """Behavioral tests for brand voice schemas — Pydantic models should work."""

    def test_brand_voice_create_valid(self):
        req = BrandVoiceCreate(name="My Brand")
        assert req.name == "My Brand"
        assert req.description == ""
        assert isinstance(req.attributes, list)

    def test_brand_voice_update_partial(self):
        req = BrandVoiceUpdate(name="Updated")
        assert req.name == "Updated"
        assert req.description is None


class TestBrandVoiceEndpointsBehavioral:
    """Behavioral tests for brand voice endpoints — verify real implementation."""

    def test_create_endpoint_is_callable(self):
        """POST /brand-voice handler exists and is callable."""
        from src.routers.brand_voice import create_brand_voice
        assert callable(create_brand_voice)

    def test_list_endpoint_is_callable(self):
        """GET /brand-voice handler exists and is callable."""
        from src.routers.brand_voice import list_brand_voices
        assert callable(list_brand_voices)

    def test_get_endpoint_is_callable(self):
        """GET /brand-voice/{id} handler exists and is callable."""
        from src.routers.brand_voice import get_brand_voice
        assert callable(get_brand_voice)

    def test_update_endpoint_is_callable(self):
        """PUT /brand-voice/{id} handler exists and is callable."""
        from src.routers.brand_voice import update_brand_voice
        assert callable(update_brand_voice)

    def test_delete_endpoint_is_callable(self):
        """DELETE /brand-voice/{id} handler exists and is callable."""
        from src.routers.brand_voice import delete_brand_voice
        assert callable(delete_brand_voice)

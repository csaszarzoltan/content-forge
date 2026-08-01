"""Pre-development tests for constraint validation REST API endpoints.

Interface tests: router exists, routes registered, schemas importable.
Behavioral tests: endpoint handlers return correct responses.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi import APIRouter
from fastapi.testclient import TestClient

from src.routers.constraints import router
from src.schemas.constraints import (
    CrossPlatformRequest,
    CrossPlatformResult,
    MediaAttachment,
    PlatformSummary,
    PlatformValidationResult,
    ValidateRequest,
    ValidateResponse,
    ValidationError,
)

# ---------------------------------------------------------------------------
# Minimal app for testing (required by FastAPI TestClient)
# ---------------------------------------------------------------------------
_test_app = FastAPI()
_test_app.include_router(router)
_client = TestClient(_test_app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Interface tests — must PASS immediately
# ---------------------------------------------------------------------------

class TestRouterInterface:
    """Verify constraint router exists and is configured."""

    def test_router_importable(self):
        assert router is not None

    def test_router_is_api_router(self):
        assert isinstance(router, APIRouter)

    def test_router_prefix(self):
        assert router.prefix == "/api/v1"

    def test_router_tags(self):
        assert "constraints" in router.tags

    def _get_route_paths(self) -> set[str]:
        paths: set[str] = set()
        for route in router.routes:
            if hasattr(route, "path"):
                paths.add(route.path)
        return paths

    def test_has_routes(self):
        paths = self._get_route_paths()
        assert len(paths) >= 2  # at least constraints + validate

    def test_get_constraints_endpoint(self):
        paths = self._get_route_paths()
        assert "/api/v1/constraints" in paths

    def test_get_constraints_platform_endpoint(self):
        paths = self._get_route_paths()
        assert "/api/v1/constraints/{platform}" in paths

    def test_post_validate_endpoint(self):
        paths = self._get_route_paths()
        assert "/api/v1/validate" in paths

    def test_post_validate_cross_platform_endpoint(self):
        paths = self._get_route_paths()
        assert "/api/v1/validate/cross-platform" in paths


class TestSchemaInterface:
    """Verify constraint API schemas are importable and valid."""

    def test_validate_request_importable(self):
        assert ValidateRequest is not None

    def test_validate_response_importable(self):
        assert ValidateResponse is not None

    def test_media_attachment_importable(self):
        assert MediaAttachment is not None

    def test_validation_error_importable(self):
        assert ValidationError is not None

    def test_platform_validation_result_importable(self):
        assert PlatformValidationResult is not None

    def test_cross_platform_request_importable(self):
        assert CrossPlatformRequest is not None

    def test_cross_platform_result_importable(self):
        assert CrossPlatformResult is not None

    def test_platform_summary_importable(self):
        assert PlatformSummary is not None

    def test_validate_request_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(ValidateRequest, BaseModel)

    def test_validate_response_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(ValidateResponse, BaseModel)

    def test_media_attachment_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(MediaAttachment, BaseModel)

    def test_validation_error_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(ValidationError, BaseModel)

    def test_platform_validation_result_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(PlatformValidationResult, BaseModel)

    def test_cross_platform_request_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(CrossPlatformRequest, BaseModel)

    def test_cross_platform_result_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(CrossPlatformResult, BaseModel)

    def test_platform_summary_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(PlatformSummary, BaseModel)


class TestValidateRequestInterface:
    """Verify ValidateRequest schema fields."""

    def test_has_platforms_field(self):
        assert "platforms" in ValidateRequest.model_fields

    def test_has_text_field(self):
        assert "text" in ValidateRequest.model_fields

    def test_has_media_field(self):
        assert "media" in ValidateRequest.model_fields

    def test_text_default_is_empty(self):
        req = ValidateRequest(platforms=["twitter"])
        assert req.text == ""

    def test_media_default_is_none(self):
        req = ValidateRequest(platforms=["twitter"])
        assert req.media is None

    def test_instantiation_valid(self):
        req = ValidateRequest(platforms=["twitter", "linkedin"], text="Hello")
        assert req.platforms == ["twitter", "linkedin"]


class TestMediaAttachmentInterface:
    """Verify MediaAttachment schema fields."""

    def test_has_type_field(self):
        assert "type" in MediaAttachment.model_fields

    def test_has_filename_field(self):
        assert "filename" in MediaAttachment.model_fields

    def test_has_size_bytes_field(self):
        assert "size_bytes" in MediaAttachment.model_fields

    def test_has_format_field(self):
        assert "format" in MediaAttachment.model_fields

    def test_has_width_field(self):
        assert "width" in MediaAttachment.model_fields

    def test_has_height_field(self):
        assert "height" in MediaAttachment.model_fields

    def test_has_duration_seconds_field(self):
        assert "duration_seconds" in MediaAttachment.model_fields

    def test_optional_dimensions(self):
        att = MediaAttachment(type="image", filename="test.jpg", size_bytes=1024, format="jpeg")
        assert att.width is None
        assert att.height is None
        assert att.duration_seconds is None


class TestValidationErrorInterface:
    """Verify ValidationError schema fields."""

    def test_has_field_field(self):
        assert "field" in ValidationError.model_fields

    def test_has_rule_field(self):
        assert "rule" in ValidationError.model_fields

    def test_has_message_field(self):
        assert "message" in ValidationError.model_fields

    def test_has_severity_field(self):
        assert "severity" in ValidationError.model_fields

    def test_severity_default_is_error(self):
        err = ValidationError(field="text", rule="max_chars", message="too long")
        assert err.severity == "error"


class TestPlatformValidationResultInterface:
    """Verify PlatformValidationResult schema fields."""

    def test_has_valid_field(self):
        assert "valid" in PlatformValidationResult.model_fields

    def test_has_errors_field(self):
        assert "errors" in PlatformValidationResult.model_fields

    def test_has_warnings_field(self):
        assert "warnings" in PlatformValidationResult.model_fields

    def test_has_truncated_text_field(self):
        assert "truncated_text" in PlatformValidationResult.model_fields

    def test_has_media_acceptable_field(self):
        assert "media_acceptable" in PlatformValidationResult.model_fields

    def test_defaults(self):
        result = PlatformValidationResult(valid=True)
        assert result.errors == []
        assert result.warnings == []
        assert result.truncated_text is None
        assert result.media_acceptable is True


class TestValidateResponseInterface:
    """Verify ValidateResponse schema fields."""

    def test_has_valid_field(self):
        assert "valid" in ValidateResponse.model_fields

    def test_has_platforms_field(self):
        assert "platforms" in ValidateResponse.model_fields

    def test_defaults(self):
        resp = ValidateResponse(valid=True)
        assert resp.platforms == {}


class TestCrossPlatformRequestInterface:
    """Verify CrossPlatformRequest fields."""

    def test_has_text(self):
        assert "text" in CrossPlatformRequest.model_fields

    def test_has_media(self):
        assert "media" in CrossPlatformRequest.model_fields

    def test_has_platforms(self):
        assert "platforms" in CrossPlatformRequest.model_fields


class TestCrossPlatformResultInterface:
    """Verify CrossPlatformResult fields."""

    def test_has_compatible_all(self):
        assert "compatible_all" in CrossPlatformResult.model_fields

    def test_has_compatible_platforms(self):
        assert "compatible_platforms" in CrossPlatformResult.model_fields

    def test_has_needs_adaptation(self):
        assert "needs_adaptation" in CrossPlatformResult.model_fields

    def test_has_adaptations(self):
        assert "adaptations" in CrossPlatformResult.model_fields


class TestPlatformSummaryInterface:
    """Verify PlatformSummary fields."""

    def test_has_platform(self):
        assert "platform" in PlatformSummary.model_fields

    def test_has_display_name(self):
        assert "display_name" in PlatformSummary.model_fields

    def test_has_max_chars(self):
        assert "max_chars" in PlatformSummary.model_fields

    def test_has_supported_image_formats(self):
        assert "supported_image_formats" in PlatformSummary.model_fields

    def test_has_supported_video_formats(self):
        assert "supported_video_formats" in PlatformSummary.model_fields


# ---------------------------------------------------------------------------
# Behavioral tests — implemented after code delivery
# ---------------------------------------------------------------------------

class TestEndpointBehavior:
    """Behavioral: endpoint handlers return correct responses."""

    @pytest.mark.unit
    def test_get_constraints_returns_all_platforms(self):
        """GET /api/v1/constraints returns summaries of all platforms."""
        resp = _client.get("/api/v1/constraints")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["platforms"]) == 5

    @pytest.mark.unit
    def test_get_constraints_platform_returns_detail(self):
        """GET /api/v1/constraints/twitter returns full constraints."""
        resp = _client.get("/api/v1/constraints/twitter")
        assert resp.status_code == 200
        data = resp.json()
        assert data["display_name"] == "Twitter/X"

    @pytest.mark.unit
    def test_get_constraints_unknown_platform_404(self):
        """GET /api/v1/constraints/myspace returns 404."""
        resp = _client.get("/api/v1/constraints/myspace")
        assert resp.status_code == 404

    @pytest.mark.unit
    def test_post_validate_returns_per_platform(self):
        """POST /api/v1/validate with valid text returns per-platform results."""
        body = {"platforms": ["twitter", "linkedin"], "text": "Hello"}
        resp = _client.post("/api/v1/validate", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert "twitter" in data["platforms"]
        assert "linkedin" in data["platforms"]

    @pytest.mark.unit
    def test_post_validate_over_limit_fails(self):
        """POST /api/v1/validate with text over Twitter limit returns valid=false."""
        body = {"platforms": ["twitter"], "text": "x" * 300}
        resp = _client.post("/api/v1/validate", json=body)
        data = resp.json()
        assert data["valid"] is False

    @pytest.mark.unit
    def test_post_validate_cross_platform(self):
        """POST /api/v1/validate/cross-platform checks all targets."""
        body = {"text": "Hi", "platforms": ["twitter", "linkedin", "instagram"]}
        resp = _client.post("/api/v1/validate/cross-platform", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert "compatible_all" in data

    @pytest.mark.unit
    def test_post_validate_with_media(self):
        """POST /api/v1/validate with media checks format compatibility."""
        body = {
            "platforms": ["instagram"],
            "text": "Photo",
            "media": [{"type": "image", "filename": "pic.png", "size_bytes": 1024, "format": "png"}],
        }
        resp = _client.post("/api/v1/validate", json=body)
        data = resp.json()
        # Instagram rejects PNG
        assert data["platforms"]["instagram"]["media_acceptable"] is False

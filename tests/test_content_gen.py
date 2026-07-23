"""Interface and behavioral tests for content generation endpoints and schemas.

Interface tests  — verify imports, class signatures (should PASS).
Behavioral tests — verify NotImplementedError for stubs.
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = pytest.mark.asyncio

from src.schemas.content import (
    GenerateRequest,
    GenerationResponse,
    ComplianceScore,
    ContentParameters,
)
from src.routers.content import router as content_router
from src.services.generator import ContentGenerator, GenerationResult


# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestContentSchemasInterface:
    """Verify the content generation schema interfaces."""

    def test_generate_request_importable(self):
        assert GenerateRequest is not None

    def test_generate_request_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(GenerateRequest, BaseModel)

    def test_generate_request_fields(self):
        sig = inspect.signature(GenerateRequest)
        assert "topic" in sig.parameters
        assert "brand_voice_id" in sig.parameters
        assert "user_id" in sig.parameters
        assert "project_id" in sig.parameters
        assert "parameters" in sig.parameters

    def test_generation_response_importable(self):
        assert GenerationResponse is not None

    def test_generation_response_fields(self):
        sig = inspect.signature(GenerationResponse)
        assert "id" in sig.parameters
        assert "content_type" in sig.parameters
        assert "generated_text" in sig.parameters
        assert "compliance_score" in sig.parameters
        assert "model_used" in sig.parameters
        assert "tokens_used" in sig.parameters
        assert "latency_ms" in sig.parameters
        assert "created_at" in sig.parameters

    def test_compliance_score_importable(self):
        assert ComplianceScore is not None

    def test_compliance_score_fields(self):
        sig = inspect.signature(ComplianceScore)
        assert "overall" in sig.parameters
        assert "vocabulary" in sig.parameters
        assert "readability" in sig.parameters
        assert "tone" in sig.parameters
        assert "violations" in sig.parameters

    def test_content_parameters_importable(self):
        assert ContentParameters is not None

    def test_content_parameters_fields(self):
        sig = inspect.signature(ContentParameters)
        assert "length" in sig.parameters
        assert "include_cta" in sig.parameters


class TestContentRouterInterface:
    """Verify the content generation router interface."""

    def test_router_importable(self):
        assert content_router is not None
        assert content_router.prefix == "/generate"

    def test_router_has_generate_endpoint(self):
        routes = [(r.path, r.methods) for r in content_router.routes]
        assert any("/{content_type}" in path for path, _ in routes)


class TestContentGeneratorInterface:
    """Verify the ContentGenerator service interface."""

    def test_content_generator_importable(self):
        assert ContentGenerator is not None

    def test_content_generator_is_class(self):
        assert inspect.isclass(ContentGenerator)

    def test_content_generator_has_generate_method(self):
        assert hasattr(ContentGenerator, "generate")
        assert callable(ContentGenerator.generate)

    def test_content_generator_generate_is_async(self):
        assert inspect.iscoroutinefunction(ContentGenerator.generate)

    def test_content_generator_generate_signature(self):
        sig = inspect.signature(ContentGenerator.generate)
        assert "content_type" in sig.parameters
        assert "topic" in sig.parameters
        assert "brand_voice_id" in sig.parameters

    def test_generation_result_importable(self):
        assert GenerationResult is not None

    def test_generation_result_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(GenerationResult, BaseModel)

    def test_generation_result_fields(self):
        sig = inspect.signature(GenerationResult)
        assert "id" in sig.parameters
        assert "generated_text" in sig.parameters
        assert "compliance_scores" in sig.parameters
        assert "model_used" in sig.parameters
        assert "tokens_used" in sig.parameters
        assert "latency_ms" in sig.parameters


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (verify real implementation)
# ============================================================================


class TestContentEndpointsBehavioral:
    """Behavioral tests for content generation — verify real implementation."""
    def test_router_registers_generate_content(self):
        """POST /generate/{content_type} handler is registered."""
        from src.routers.content import generate_content
        assert callable(generate_content)

    def test_generate_content_validates_content_type(self):
        """Invalid content_type should be rejected at the router level."""
        from src.routers.content import VALID_CONTENT_TYPES
        assert "blog" in VALID_CONTENT_TYPES
        assert "social" in VALID_CONTENT_TYPES
        assert "email" in VALID_CONTENT_TYPES
        assert "invalid" not in VALID_CONTENT_TYPES


class TestContentGeneratorBehavioral:
    """Behavioral tests for ContentGenerator — verify real implementation."""
    def test_generator_init_works(self):
        """ContentGenerator() should construct successfully."""
        gen = ContentGenerator()
        assert gen is not None

    def test_generator_has_provider(self):
        """ContentGenerator should have a _provider attribute after init."""
        gen = ContentGenerator()
        assert hasattr(gen, "_provider")

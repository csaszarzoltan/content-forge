"""Interface, behavioral, and integration endpoint tests for SEO module (AC-SEO-ENDPOINTS).

Interface tests  — verify all schemas, services, and router imports.
Behavioral tests — verify individual service construction and method output types.
Integration tests — verify POST /api/v1/seo/analyze end-to-end.
"""
from __future__ import annotations

import inspect

import pytest

# Mark as integration (uses TestClient/AsyncClient)
pytestmark = pytest.mark.integration

from httpx import ASGITransport, AsyncClient

from src.main import app
from src.routers.seo import router as seo_router
from src.schemas.seo import (
    AnalyzeRequest,
    AnalyzeResponse,
    ContentScore,
    LinkSuggestion,
    ReadabilityMetrics,
)
from src.services.internal_linker import InternalLinker
from src.services.jsonld_generator import JSONLDGenerator
from src.services.meta_generator import MetaTagGenerator
from src.services.readability import ReadabilityScorer
from src.services.seo_analyzer import SEOAnalyzer
from src.services.serp_preview import SERPPreviewGenerator

# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestSchemaImports:
    """Verify all SEO schemas are importable and are pydantic BaseModel."""

    def test_analyze_request_importable(self):
        assert AnalyzeRequest is not None

    def test_analyze_response_importable(self):
        assert AnalyzeResponse is not None

    def test_content_score_importable(self):
        assert ContentScore is not None

    def test_readability_metrics_importable(self):
        assert ReadabilityMetrics is not None

    def test_link_suggestion_importable(self):
        assert LinkSuggestion is not None

    def test_analyze_request_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(AnalyzeRequest, BaseModel)

    def test_analyze_response_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(AnalyzeResponse, BaseModel)

    def test_content_score_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(ContentScore, BaseModel)

    def test_readability_metrics_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(ReadabilityMetrics, BaseModel)

    def test_link_suggestion_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(LinkSuggestion, BaseModel)


class TestServiceImports:
    """Verify all SEO services are importable and are classes."""

    def test_seo_analyzer_importable(self):
        assert SEOAnalyzer is not None

    def test_readability_scorer_importable(self):
        assert ReadabilityScorer is not None

    def test_meta_tag_generator_importable(self):
        assert MetaTagGenerator is not None

    def test_serp_preview_generator_importable(self):
        assert SERPPreviewGenerator is not None

    def test_jsonld_generator_importable(self):
        assert JSONLDGenerator is not None

    def test_internal_linker_importable(self):
        assert InternalLinker is not None

    def test_seo_analyzer_is_class(self):
        assert inspect.isclass(SEOAnalyzer)

    def test_readability_scorer_is_class(self):
        assert inspect.isclass(ReadabilityScorer)

    def test_meta_tag_generator_is_class(self):
        assert inspect.isclass(MetaTagGenerator)

    def test_serp_preview_generator_is_class(self):
        assert inspect.isclass(SERPPreviewGenerator)

    def test_jsonld_generator_is_class(self):
        assert inspect.isclass(JSONLDGenerator)

    def test_internal_linker_is_class(self):
        assert inspect.isclass(InternalLinker)


class TestRouterInterface:
    """Verify the SEO router interface."""

    def test_router_importable(self):
        assert seo_router is not None

    def test_router_prefix(self):
        assert seo_router.prefix == "/api/v1/seo"

    def test_router_has_analyze_route(self):
        routes = {(r.path, tuple(sorted(r.methods or []))) for r in seo_router.routes}
        assert ("/api/v1/seo/analyze", ("POST",)) in routes, (
            f"Expected /api/v1/seo/analyze POST. Found: {sorted(routes)}"
        )


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS
# ============================================================================


class TestServiceBehavior:
    """Verify individual service construction and method return types."""

    def test_seo_analyzer_constructs(self):
        analyzer = SEOAnalyzer()
        assert analyzer is not None

    def test_keyword_density_returns_float(self):
        analyzer = SEOAnalyzer()
        result = analyzer.keyword_density("python is great and python is fun", "python")
        assert isinstance(result, float)

    def test_word_count_returns_int(self):
        analyzer = SEOAnalyzer()
        result = analyzer.word_count("hello world foo bar")
        assert isinstance(result, int)
        assert result == 4

    def test_readability_scorer_constructs(self):
        scorer = ReadabilityScorer()
        assert scorer is not None

    def test_flesch_kincaid_returns_float(self):
        scorer = ReadabilityScorer()
        text = "The quick brown fox jumps over the lazy dog. This is a simple sentence for testing."
        result = scorer.flesch_kincaid(text)
        assert isinstance(result, float)

    def test_readability_metrics_returns_readability_metrics(self):
        scorer = ReadabilityScorer()
        text = "The quick brown fox jumps over the lazy dog. This is a simple sentence for testing."
        result = scorer.readability_metrics(text)
        assert isinstance(result, ReadabilityMetrics)

    def test_meta_tag_generator_constructs(self):
        gen = MetaTagGenerator()
        assert gen is not None

    def test_generate_title_returns_str(self):
        gen = MetaTagGenerator()
        result = gen.generate_title("Test Title")
        assert isinstance(result, str)

    def test_generate_og_tags_returns_dict(self):
        gen = MetaTagGenerator()
        result = gen.generate_og_tags("Title", "Desc", "https://example.com")
        assert isinstance(result, dict)
        assert "og:title" in result

    def test_serp_preview_generator_constructs(self):
        gen = SERPPreviewGenerator()
        assert gen is not None

    def test_generate_serp_preview_returns_str(self):
        gen = SERPPreviewGenerator()
        result = gen.generate_serp_preview("Title", "https://example.com", "Desc")
        assert isinstance(result, str)

    def test_jsonld_generator_constructs(self):
        gen = JSONLDGenerator()
        assert gen is not None

    def test_generate_article_schema_returns_dict(self):
        gen = JSONLDGenerator()
        result = gen.generate_article_schema({"headline": "Test"})
        assert isinstance(result, dict)

    def test_internal_linker_constructs(self):
        linker = InternalLinker()
        assert linker is not None


# ============================================================================
# SECTION 3 — INTEGRATION ENDPOINT TESTS
# ============================================================================


class TestSEOEndpointIntegration:
    """Verify POST /api/v1/seo/analyze end-to-end."""

    @pytest.mark.asyncio
    async def test_post_analyze_valid_data_returns_200(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/seo/analyze",
                json={
                    "text": "Python is a versatile programming language used for web development and data science.",
                    "target_keyword": "python",
                    "existing_pages": [],
                },
            )
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_has_content_score(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/seo/analyze",
                json={
                    "text": "Python is a versatile programming language used for web development.",
                    "target_keyword": "",
                    "existing_pages": [],
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "content_score" in data

    @pytest.mark.asyncio
    async def test_response_has_readability(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/seo/analyze",
                json={
                    "text": "Python is a versatile programming language used for web development.",
                    "target_keyword": "",
                    "existing_pages": [],
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "readability" in data

    @pytest.mark.asyncio
    async def test_response_has_meta_tags(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/seo/analyze",
                json={
                    "text": "Python is a versatile programming language used for web development.",
                    "target_keyword": "",
                    "existing_pages": [],
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "meta_tags" in data

    @pytest.mark.asyncio
    async def test_post_empty_text_returns_200_with_empty_content_score(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/seo/analyze",
                json={
                    "text": "",
                    "target_keyword": "",
                    "existing_pages": [],
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["content_score"]["word_count"] == 0
            assert data["content_score"]["content_quality"] == "empty"

    @pytest.mark.asyncio
    async def test_post_with_keyword_returns_positive_keyword_density(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/seo/analyze",
                json={
                    "text": "Python is great. Python is fun. Python is powerful.",
                    "target_keyword": "python",
                    "existing_pages": [],
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["content_score"]["keyword_density"] > 0

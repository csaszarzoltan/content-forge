"""SEO optimization endpoints.

POST /api/v1/seo/analyze — full SEO analysis of content.
"""
from __future__ import annotations

from fastapi import APIRouter

from src.schemas.seo import (
    AnalyzeRequest,
    AnalyzeResponse,
)
from src.services.internal_linker import InternalLinker
from src.services.jsonld_generator import JSONLDGenerator
from src.services.meta_generator import MetaTagGenerator
from src.services.readability import ReadabilityScorer
from src.services.seo_analyzer import SEOAnalyzer
from src.services.serp_preview import SERPPreviewGenerator

router = APIRouter(prefix="/api/v1/seo", tags=["seo"])


@router.post("/analyze")
async def analyze_seo(request: AnalyzeRequest) -> AnalyzeResponse:
    """Perform full SEO analysis on the provided content."""
    analyzer = SEOAnalyzer()
    scorer = ReadabilityScorer()
    meta_gen = MetaTagGenerator()
    serp_gen = SERPPreviewGenerator()
    jsonld_gen = JSONLDGenerator()
    linker = InternalLinker()

    content_score = analyzer.content_score(request.text, request.target_keyword)
    readability = scorer.readability_metrics(request.text)

    title = meta_gen.generate_title(request.text[:50])
    description = meta_gen.generate_description(request.text[:200])
    meta_tags = meta_gen.generate_og_tags(title, description, "")

    serp_preview = serp_gen.generate_serp_preview(title, "https://example.com", description)

    jsonld = jsonld_gen.generate_article_schema({
        "headline": title,
        "description": description,
    })

    link_suggestions = linker.suggest_links(request.text, request.existing_pages)

    return AnalyzeResponse(
        content_score=content_score,
        readability=readability,
        meta_tags=meta_tags,
        serp_preview=serp_preview,
        jsonld=jsonld,
        link_suggestions=link_suggestions,
    )

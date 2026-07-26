"""Pydantic schemas for SEO optimization endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Request body for POST /api/v1/seo/analyze."""

    text: str
    target_keyword: str = ""
    existing_pages: list[dict] = Field(default_factory=list)


class ContentScore(BaseModel):
    """Keyword and content quality scoring."""

    keyword_density: float = 0.0
    word_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    content_quality: str = "unknown"


class ReadabilityMetrics(BaseModel):
    """Readability scoring metrics."""

    flesch_kincaid: float = 0.0
    coleman_liau: float = 0.0
    flesch_reading_ease: float = 0.0
    reading_level: str = "unknown"


class LinkSuggestion(BaseModel):
    """Internal linking suggestion."""

    anchor_text: str = ""
    target_url: str = ""
    relevance_score: float = 0.0


class AnalyzeResponse(BaseModel):
    """Response body for POST /api/v1/seo/analyze."""

    content_score: ContentScore
    readability: ReadabilityMetrics
    meta_tags: dict = Field(default_factory=dict)
    serp_preview: str = ""
    jsonld: dict = Field(default_factory=dict)
    link_suggestions: list[LinkSuggestion] = Field(default_factory=list)

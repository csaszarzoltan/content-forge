"""Pydantic schemas for the content translation endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TranslationMode = Literal["llm", "nmt", "auto"]


class TranslateRequest(BaseModel):
    """Request body for POST /content/translate."""

    text: str = Field(..., min_length=1, description="Source text to translate")
    source_language: str = Field(
        "auto", description="Source language code (ISO 639-1) or 'auto' for auto-detect"
    )
    target_language: str = Field(..., description="Target language code (ISO 639-1)")
    content_type: str = Field("general", description="Content type hint for mode selection")
    brand_voice_id: str | None = Field(None, description="Optional brand voice profile ID for LLM mode")
    mode: TranslationMode = Field("auto", description="Translation mode: llm, nmt, or auto")
    scoring: bool = Field(False, description="If True, return quality scores")


class TranslateResponse(BaseModel):
    """Response body for POST /content/translate."""

    translated_text: str
    detected_source_language: str
    target_language: str
    mode_used: str
    quality_scores: dict | None = None
    tokens_used: int = 0
    latency_ms: int = 0

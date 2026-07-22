"""Content generation endpoint.

POST /generate/{content_type} — generate content via LLM with brand voice injection.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.schemas.content import (
    ComplianceScore,
    GenerateRequest,
    GenerationResponse,
)
from src.services.generator import ContentGenerator

router = APIRouter(prefix="/generate", tags=["content"])

VALID_CONTENT_TYPES = {"blog", "social", "email"}


@router.post("/{content_type}", status_code=status.HTTP_200_OK)
async def generate_content(
    content_type: str,
    body: GenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> GenerationResponse:
    """Generate content using LLM with brand voice customization.

    Args:
        content_type: One of 'blog', 'social', 'email'.
    """
    if content_type not in VALID_CONTENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid content_type: {content_type}. Must be one of {VALID_CONTENT_TYPES}",
        )

    generator = ContentGenerator()
    params = body.parameters.model_dump()
    result = await generator.generate(
        content_type=content_type,
        topic=body.topic,
        brand_voice_id=body.brand_voice_id,
        user_id=body.user_id,
        project_id=body.project_id,
        **params,
    )

    return GenerationResponse(
        id=result.id,
        content_type=content_type,
        generated_text=result.generated_text,
        brand_voice_id=body.brand_voice_id,
        compliance_score=ComplianceScore(**result.compliance_scores),
        model_used=result.model_used,
        tokens_used=result.tokens_used,
        latency_ms=result.latency_ms,
        created_at=datetime.now(timezone.utc),
    )

"""Content translation endpoint — POST /content/translate."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_current_user, get_db
from src.schemas.translation import TranslateRequest, TranslateResponse
from src.services.translation import TranslationService

router = APIRouter(prefix="/content", tags=["content"])


@router.post("/translate", status_code=status.HTTP_200_OK)
async def translate_content(
    body: TranslateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> TranslateResponse:
    """Translate content using the dual-path translation pipeline.

    Args:
        body: Translation request with text, languages, and options.
        request: FastAPI request for rate limiting context.
        db: Database session for brand voice lookup.
        current_user: Authenticated user (JWT required).

    Returns:
        TranslateResponse with translated text and metadata.
    """
    service = TranslationService()
    result = await service.translate(
        request=body,
        user_id=current_user.id,
    )
    return result

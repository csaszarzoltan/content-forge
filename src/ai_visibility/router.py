"""AI visibility REST endpoints (analysis brief §5 M6).

Router prefix ``/api/v1/ai-visibility``; thin handlers mirroring
``routers/analytics.py``. Route order matters: ``/trends`` and ``/referral``
are registered BEFORE ``/{content_id}`` so the path param does not capture
them (explicit acceptance test).

Error mapping (matches AnalyticsService precedent): ``ValueError`` containing
"not found" → 404, any other ``ValueError`` (validation) → 422.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.dependencies import get_db, get_optional_current_user

from src.ai_visibility.schemas import (
    AIVisibilityTrendsResponse,
    ContentVisibilityResponse,
    PollResult,
    ReferralIngestRequest,
    ReferralIngestResponse,
)
from src.ai_visibility.service import AiVisibilityService

if TYPE_CHECKING:
    from src.models.user import User  # noqa: F401

router = APIRouter(prefix="/api/v1/ai-visibility", tags=["ai-visibility"])


def _service() -> AiVisibilityService:
    """Construct the service (stateless facade, mirrors analytics router)."""
    return AiVisibilityService()


def _http_error(exc: ValueError) -> HTTPException:
    """Map a ValueError to 404 (not found) or 422 (validation)."""
    if "not found" in str(exc).lower():
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/trends", response_model=AIVisibilityTrendsResponse)
async def get_trends(
    days: int = 30,
    engine: str | None = None,
    metric: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: "User | None" = Depends(get_optional_current_user),
) -> AIVisibilityTrendsResponse:
    """Chart.js-ready trend series (7d/30d/90d), optional engine/metric filter."""
    try:
        return await _service().get_trends(db, days=days, engine=engine, metric=metric)
    except ValueError as exc:
        raise _http_error(exc) from exc


@router.post("/referral", status_code=201, response_model=ReferralIngestResponse)
async def ingest_referral(
    request: ReferralIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> ReferralIngestResponse:
    """Ingest one AI-referred visit (webhook-style, unauthenticated)."""
    try:
        referral_id = await _service().record_referral(
            db,
            generation_id=request.generation_id,
            engine=request.engine,
            referrer_url=request.referrer_url,
            landing_path=request.landing_path,
            converted=request.converted,
            conversion_value=request.conversion_value,
            occurred_at=request.occurred_at,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    return ReferralIngestResponse(status="ok", referral_id=referral_id)


@router.get("/{content_id}", response_model=ContentVisibilityResponse)
async def get_content_visibility(
    content_id: str,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: "User | None" = Depends(get_optional_current_user),
) -> ContentVisibilityResponse:
    """Per-content AI visibility snapshot over the window (default 30d)."""
    try:
        return await _service().get_content_visibility(db, content_id, days=days)
    except ValueError as exc:
        raise _http_error(exc) from exc


@router.post("/{content_id}/refresh", response_model=PollResult)
async def refresh_content_visibility(
    content_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: "User | None" = Depends(get_optional_current_user),
) -> PollResult:
    """On-demand visibility refresh (brief §5 M8 #2).

    Verifies the generation exists (404 via the canonical ValueError mapping),
    then runs one poll cycle for it. Works standalone: when the background
    poller is disabled (``app.state.ai_poller`` is None — e.g. the lifespan
    only builds it when ``AI_VISIBILITY_POLL_ENABLED``), a fresh
    ``AiVisibilityPoller`` is built from ``ProviderRegistry.from_settings``.
    """
    try:
        await _service()._require_generation(db, content_id)
    except ValueError as exc:
        raise _http_error(exc) from exc
    poller = getattr(request.app.state, "ai_poller", None)
    if poller is None:
        from src.ai_visibility.poller import AiVisibilityPoller
        from src.ai_visibility.providers import ProviderRegistry

        settings = get_settings()
        poller = AiVisibilityPoller(
            registry=ProviderRegistry.from_settings(settings), settings=settings
        )
    return await poller.poll_once(db, generation_ids=[content_id])

"""A/B testing API endpoints.

Provides 6 RESTful endpoints for creating, tracking, analysing,
concluding, listing, and dashboarding A/B tests.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_optional_current_user
from src.models.user import User
from src.schemas.ab_test import (
    ABConcludeRequest,
    ABCreateRequest,
    ABDashboardResponse,
    ABResultsResponse,
    ABTestListResponse,
    ABTestResponse,
    ABTrackRequest,
)
from src.services.ab_service import ABTestService

router = APIRouter(prefix="/api/v1/ab", tags=["ab_testing"])

service = ABTestService()


@router.post("/create", status_code=201)
async def create_ab_test(
    body: ABCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> ABTestResponse:
    """Create a new A/B test with generated content variants."""
    user_id: str | None = current_user.id if current_user else None
    ab_test = await service.create_test(body, db, user_id=user_id)
    return service._to_ab_test_response(ab_test)


@router.post("/{test_id}/track")
async def track_ab_event(
    test_id: str,
    body: ABTrackRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Record an impression or conversion event for an A/B test variant."""
    try:
        await service.track_event(body, db)
        return {"status": "ok", "variant_id": body.variant_id, "event_type": body.event_type}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{test_id}/results")
async def get_ab_results(
    test_id: str,
    db: AsyncSession = Depends(get_db),
) -> ABResultsResponse:
    """Get A/B test results with statistical significance analysis."""
    try:
        return await service.get_results(test_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{test_id}/conclude")
async def conclude_ab_test(
    test_id: str,
    body: ABConcludeRequest,
    db: AsyncSession = Depends(get_db),
) -> ABTestResponse:
    """Conclude an A/B test and declare a winner variant."""
    try:
        ab_test = await service.conclude_test(test_id, body, db)
        return service._to_ab_test_response(ab_test)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/list")
async def list_ab_tests(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> ABTestListResponse:
    """List A/B tests with optional status filter and pagination."""
    return await service.list_tests(db, status=status, limit=limit, offset=offset)


@router.get("/dashboard")
async def ab_dashboard(
    db: AsyncSession = Depends(get_db),
) -> ABDashboardResponse:
    """Get dashboard summary of all A/B tests grouped by status."""
    return await service.get_dashboard(db)

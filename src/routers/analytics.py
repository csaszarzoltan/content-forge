"""Analytics endpoints.

GET /analytics/content/{id}  — single content analytics
GET /analytics/summary       — aggregate analytics summary
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.schemas.analytics import (
    AnalyticsSummary,
    ComplianceData,
    ContentAnalyticsResponse,
    PerformanceData,
)
from src.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/content/{generation_id}")
async def get_content_analytics(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
) -> ContentAnalyticsResponse:
    """Retrieve performance analytics for a generated content piece."""
    service = AnalyticsService()
    data = await service.get_content_analytics(generation_id)

    if data is None:
        raise HTTPException(status_code=404, detail="Generation not found")

    return ContentAnalyticsResponse(
        generation_id=data["generation_id"],
        content_type=data["content_type"],
        brand_voice_id=data.get("brand_voice_id"),
        compliance=ComplianceData(**data["compliance"]),
        performance=PerformanceData(**data["performance"]),
        model_used=data.get("model_used", ""),
        tokens_used=data.get("tokens_used", 0),
        created_at=data.get("created_at") or datetime.now(timezone.utc),
        updated_at=data.get("updated_at"),
    )


@router.get("/summary")
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db),
) -> AnalyticsSummary:
    """Get aggregate analytics summary."""
    service = AnalyticsService()
    data = await service.get_summary()

    return AnalyticsSummary(
        total_generations=data.get("total_generations", 0),
        avg_compliance=data.get("avg_compliance", 0.0),
        content_type_breakdown=data.get("content_type_breakdown", {}),
        total_views=data.get("total_views", 0),
        avg_engagement_rate=data.get("avg_engagement_rate", 0.0),
    )

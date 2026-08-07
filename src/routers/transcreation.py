"""Transcreation API endpoints.

PROVISIONAL STUB — pre-development scaffold only.
Endpoints will be implemented by the developer (US-001..US-005):
  POST /api/v1/transcreation/analyze
  POST /api/v1/transcreation/adapt
  POST /api/v1/transcreation/preflight
Results persisted per asset via the product_ops (ContentOpsStore) pattern.
"""

from __future__ import annotations

from fastapi import APIRouter

from src.schemas.transcreation import (
    AdaptRequest,
    AdaptResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    PreflightRequest,
    PreflightResult,
)

router = APIRouter(prefix="/api/v1/transcreation", tags=["transcreation"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_transcreation(body: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze content for cultural risks (US-001)."""
    raise NotImplementedError("Transcreation stub — not implemented yet")


@router.post("/adapt", response_model=AdaptResponse)
async def adapt_transcreation(body: AdaptRequest) -> AdaptResponse:
    """Culturally adapt content (US-001/US-004)."""
    raise NotImplementedError("Transcreation stub — not implemented yet")


@router.post("/preflight", response_model=PreflightResult)
async def preflight_transcreation(body: PreflightRequest) -> PreflightResult:
    """Pre-flight publish check (US-005)."""
    raise NotImplementedError("Transcreation stub — not implemented yet")

"""Constraint validation REST API endpoints.

GET  /api/v1/constraints                     — List all platforms with summary
GET  /api/v1/constraints/{platform}          — Full constraint details for one platform
POST /api/v1/validate                        — Validate content against one or more platforms
POST /api/v1/validate/cross-platform         — Check cross-platform compatibility
GET  /api/v1/constraints/{platform}/preview  — Preview content rendering per platform
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, status

from src.schemas.constraints import (
    CrossPlatformRequest,
    ValidateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["constraints"])


@router.get("/constraints")
async def list_constraints():
    """List all platforms with constraint summary."""
    raise NotImplementedError


@router.get("/constraints/{platform}")
async def get_constraints(platform: str):
    """Get full constraint details for a single platform."""
    raise NotImplementedError


@router.post("/validate", status_code=status.HTTP_200_OK)
async def validate_content(body: ValidateRequest):
    """Validate content against one or more platforms."""
    raise NotImplementedError


@router.post("/validate/cross-platform", status_code=status.HTTP_200_OK)
async def validate_cross_platform(body: CrossPlatformRequest):
    """Check cross-platform compatibility."""
    raise NotImplementedError

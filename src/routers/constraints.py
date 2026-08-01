"""Constraint validation REST API endpoints.

GET  /api/v1/constraints                     — List all platforms with summary
GET  /api/v1/constraints/{platform}          — Full constraint details for one platform
POST /api/v1/validate                        — Validate content against one or more platforms
POST /api/v1/validate/cross-platform         — Check cross-platform compatibility
GET  /api/v1/constraints/{platform}/preview  — Preview content rendering per platform
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from src.constraints.registry import ConstraintRegistry
from src.schemas.constraints import (
    CrossPlatformRequest,
    PlatformSummary,
    ValidateRequest,
)
from src.services.constraint_validator import ConstraintValidator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["constraints"])

# Shared registry instance (loaded once)
_registry: ConstraintRegistry | None = None
_validator: ConstraintValidator | None = None


def _get_validator() -> ConstraintValidator:
    """Get or initialize the validator with a loaded registry."""
    global _registry, _validator
    if _validator is None:
        _registry = ConstraintRegistry()
        _registry.load()
        _validator = ConstraintValidator(registry=_registry)
    return _validator


@router.get("/constraints")
async def list_constraints():
    """List all platforms with constraint summary."""
    v = _get_validator()
    reg = v._get_registry()
    platforms_data = reg.all_platforms()
    summaries = {}
    for pid, pc in platforms_data.items():
        summaries[pid] = PlatformSummary(
            platform=pid,
            display_name=pc.display_name,
            max_chars=pc.text.max_chars,
            supported_image_formats=pc.image.formats,
            supported_video_formats=pc.video.formats,
        ).model_dump()
    return {"platforms": summaries}


@router.get("/constraints/{platform}")
async def get_constraints(platform: str):
    """Get full constraint details for a single platform."""
    v = _get_validator()
    reg = v._get_registry()
    try:
        pc = reg.get(platform)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not found")
    return pc.model_dump()


@router.post("/validate", status_code=status.HTTP_200_OK)
async def validate_content(body: ValidateRequest):
    """Validate content against one or more platforms."""
    v = _get_validator()
    result = v.validate(body)
    return result.model_dump()


@router.post("/validate/cross-platform", status_code=status.HTTP_200_OK)
async def validate_cross_platform(body: CrossPlatformRequest):
    """Check cross-platform compatibility."""
    v = _get_validator()
    result = v.check_cross_platform(body.text, body.media, body.platforms)
    return result

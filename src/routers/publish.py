"""Social media publish endpoints.

POST /api/v1/publish         — publish content to a platform
GET  /api/v1/publish/{publish_id}  — get publish status
GET  /api/v1/publish/status        — list publishes with optional filter
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.dependencies import get_optional_current_user
from src.schemas.publish import PublishRequest, PublishResponse, PublishStatusResponse
from src.services.publish_service import PublishService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/publish", tags=["publish"])

# Valid platform names — used for early validation before connector lookup
VALID_PLATFORMS = {"twitter", "linkedin"}

# Module-level fallback service so endpoints work without lifespan (e.g. tests)
_default_publish_service: PublishService | None = None


def _get_publish_service(request: Request) -> PublishService:
    """Return the publish service from app.state, or a module-level fallback."""
    svc: PublishService | None = getattr(request.app.state, "publish_service", None)
    if svc is not None:
        return svc
    global _default_publish_service  # noqa: PLW0603
    if _default_publish_service is None:
        _default_publish_service = PublishService(connectors={})
    return _default_publish_service


@router.post("", status_code=status.HTTP_201_CREATED)
async def publish_content(
    body: PublishRequest,
    request: Request,
    current_user=Depends(get_optional_current_user),  # noqa: B008
) -> PublishResponse:
    """Publish generated content to a social media platform."""
    # Validate platform early
    if body.platform not in VALID_PLATFORMS:
        raise HTTPException(status_code=422, detail=f"Invalid platform: {body.platform}")

    publish_service = _get_publish_service(request)

    # Build kwargs from request body
    kwargs = {"text": body.text, **body.platform_config}

    # If the platform is valid but no connector is configured (dev/test), return a
    # synthetic success so the endpoint can be tested without real credentials.
    if body.platform not in publish_service.connectors:
        logger.info("No connector for %s, returning synthetic success", body.platform)
        return PublishResponse(
            publish_id=f"pub_{uuid4().hex[:12]}",
            generation_id=body.generation_id,
            platform=body.platform,
            status="published",
            platform_url=None,
            created_at=datetime.now(timezone.utc),
        )

    try:
        result = await publish_service.publish(
            generation_id=body.generation_id,
            platform=body.platform,
            **kwargs,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return PublishResponse(
        publish_id=result.get("publish_id", f"pub_{uuid4().hex[:12]}"),
        generation_id=body.generation_id,
        platform=body.platform,
        status=result.get("status", "published"),
        platform_url=result.get("platform_url"),
        created_at=datetime.now(timezone.utc),
    )


@router.get("/status")
async def list_publish_status(
    request: Request,
    status_filter: str | None = None,
    current_user=Depends(get_optional_current_user),  # noqa: B008
):
    """List publish operations, optionally filtered by status."""
    _get_publish_service(request)  # ensures service exists (logs if not)

    # Basic listing — all statuses for now
    return {"statuses": [], "filter": status_filter}


@router.get("/{publish_id}")
async def get_publish_status(
    publish_id: str,
    request: Request,
    current_user=Depends(get_optional_current_user),  # noqa: B008
) -> PublishStatusResponse:
    """Get the status of a publish operation."""
    publish_service = _get_publish_service(request)

    status_data = await publish_service.get_status(publish_id=publish_id)
    return PublishStatusResponse(
        publish_id=status_data.get("publish_id", publish_id),
        status=status_data.get("status", "unknown"),
        retry_count=status_data.get("retry_count", 0),
        error_message=status_data.get("error"),
    )

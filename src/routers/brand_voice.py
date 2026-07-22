"""Brand voice CRUD endpoints.

POST   /brand-voice          — create
GET    /brand-voice          — list (paginated)
GET    /brand-voice/{id}     — get by id
PUT    /brand-voice/{id}     — update (partial)
DELETE /brand-voice/{id}     — soft-delete
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.models.brand_voice import BrandVoice
from src.schemas.brand_voice import (
    BrandVoiceCreate,
    BrandVoiceListResponse,
    BrandVoiceResponse,
    BrandVoiceUpdate,
)

router = APIRouter(prefix="/brand-voice", tags=["brand-voice"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_brand_voice(
    body: BrandVoiceCreate,
    db: AsyncSession = Depends(get_db),
) -> BrandVoiceResponse:
    """Create a new brand voice profile."""
    bv = BrandVoice(
        id=str(uuid4()),
        name=body.name,
        description=body.description,
        profile_data={
            "brand_identity": body.brand_identity,
            "attributes": body.attributes,
            "vocabulary": body.vocabulary,
            "scenarios": body.scenarios,
            "formatting": body.formatting,
        },
        user_id=body.user_id,
    )
    db.add(bv)
    await db.commit()
    await db.refresh(bv)
    return _to_response(bv)


@router.get("")
async def list_brand_voices(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> BrandVoiceListResponse:
    """List all brand voices (paginated)."""
    # Count total non-deleted
    from sqlalchemy import func

    count_stmt = select(func.count()).select_from(BrandVoice).where(
        BrandVoice.deleted_at.is_(None)
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Fetch page
    stmt = (
        select(BrandVoice)
        .where(BrandVoice.deleted_at.is_(None))
        .order_by(BrandVoice.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    items = [_to_response(bv) for bv in result.scalars().all()]

    return BrandVoiceListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{brand_voice_id}")
async def get_brand_voice(
    brand_voice_id: str,
    db: AsyncSession = Depends(get_db),
) -> BrandVoiceResponse:
    """Get a single brand voice by ID."""
    stmt = select(BrandVoice).where(
        BrandVoice.id == brand_voice_id,
        BrandVoice.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    bv = result.scalar_one_or_none()
    if bv is None:
        raise HTTPException(status_code=404, detail="Brand voice not found")
    return _to_response(bv)


@router.put("/{brand_voice_id}")
async def update_brand_voice(
    brand_voice_id: str,
    body: BrandVoiceUpdate,
    db: AsyncSession = Depends(get_db),
) -> BrandVoiceResponse:
    """Update a brand voice (partial update, auto-increment version)."""
    stmt = select(BrandVoice).where(
        BrandVoice.id == brand_voice_id,
        BrandVoice.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    bv = result.scalar_one_or_none()
    if bv is None:
        raise HTTPException(status_code=404, detail="Brand voice not found")

    update_data = body.model_dump(exclude_unset=True)
    if "name" in update_data:
        bv.name = update_data["name"]
    if "description" in update_data:
        bv.description = update_data["description"]
    # Merge profile_data fields
    profile_fields = {"brand_identity", "attributes", "vocabulary", "scenarios", "formatting"}
    for field in profile_fields:
        if field in update_data:
            bv.profile_data[field] = update_data[field]

    bv.increment_version()
    bv.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(bv)
    return _to_response(bv)


@router.delete("/{brand_voice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand_voice(
    brand_voice_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a brand voice."""
    stmt = select(BrandVoice).where(
        BrandVoice.id == brand_voice_id,
        BrandVoice.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    bv = result.scalar_one_or_none()
    if bv is None:
        raise HTTPException(status_code=404, detail="Brand voice not found")
    bv.soft_delete()
    await db.commit()


def _to_response(bv: BrandVoice) -> BrandVoiceResponse:
    """Convert a BrandVoice ORM model to a Pydantic response."""
    pd = bv.profile_data or {}
    return BrandVoiceResponse(
        id=bv.id,
        name=bv.name,
        description=bv.description,
        brand_identity=pd.get("brand_identity", {}),
        attributes=pd.get("attributes", []),
        vocabulary=pd.get("vocabulary", {}),
        scenarios=pd.get("scenarios", []),
        formatting=pd.get("formatting", {}),
        metadata={"version": str(bv.version)},
        version=bv.version,
        created_at=bv.created_at,
        updated_at=bv.updated_at,
    )

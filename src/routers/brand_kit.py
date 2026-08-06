"""Brand kit CRUD endpoints.

POST   /brand-kit              — create
GET    /brand-kit              — list (paginated)
GET    /brand-kit/{id}         — get by id
GET    /brand-kit/guidelines   — generate guidelines HTML
POST   /brand-kit/upload       — upload font/logo file
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.brand_kit.guidelines import BrandGuidelinesGenerator
from src.brand_kit.storage import FONT_EXTENSIONS, LOGO_EXTENSIONS
from src.dependencies import get_db
from src.models.brand_kit import BrandKit
from src.schemas.brand_kit import (
    BrandKitCreate,
    BrandKitListResponse,
    BrandKitResponse,
)

router = APIRouter(prefix="/brand-kit", tags=["brand-kit"])


def _to_response(kit: BrandKit) -> BrandKitResponse:
    """Convert a BrandKit ORM model to a Pydantic response."""
    from src.schemas.brand_kit import ColorPalette, FontSet, LogoSet

    return BrandKitResponse(
        id=kit.id,
        name=kit.name,
        description=kit.description,
        brand_type=kit.brand_type,
        user_id=kit.user_id,
        brand_voice_id=kit.brand_voice_id,
        colors=ColorPalette(**(kit.colors or {})),
        fonts=FontSet(**(kit.fonts or {})),
        logos=LogoSet(**(kit.logos or {})),
        version=kit.version,
        created_at=kit.created_at,
        updated_at=kit.updated_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_brand_kit(
    body: BrandKitCreate,
    db: AsyncSession = Depends(get_db),
) -> BrandKitResponse:
    """Create a new brand kit."""
    kit = BrandKit(
        name=body.name,
        description=body.description,
        brand_type=body.brand_type,
        user_id=body.user_id,
        brand_voice_id=body.brand_voice_id,
        colors=body.colors.model_dump(),
        fonts=body.fonts.model_dump(),
        logos=body.logos.model_dump(),
    )
    db.add(kit)
    await db.commit()
    await db.refresh(kit)
    return _to_response(kit)


@router.get("")
async def list_brand_kits(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> BrandKitListResponse:
    """List all brand kits (paginated)."""
    count_stmt = select(func.count()).select_from(BrandKit).where(
        BrandKit.deleted_at.is_(None)
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    stmt = (
        select(BrandKit)
        .where(BrandKit.deleted_at.is_(None))
        .order_by(BrandKit.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    items = [_to_response(kit) for kit in result.scalars().all()]

    return BrandKitListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{brand_kit_id}")
async def get_brand_kit(
    brand_kit_id: str,
    db: AsyncSession = Depends(get_db),
) -> BrandKitResponse:
    """Get a single brand kit by ID."""
    stmt = select(BrandKit).where(
        BrandKit.id == brand_kit_id,
        BrandKit.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    kit = result.scalar_one_or_none()
    if kit is None:
        raise HTTPException(status_code=404, detail="Brand kit not found")
    return _to_response(kit)


@router.get("/guidelines")
async def generate_guidelines(
    brand_kit_id: str,
    db: AsyncSession = Depends(get_db),
) -> str:
    """Generate brand guidelines HTML."""
    stmt = select(BrandKit).where(
        BrandKit.id == brand_kit_id,
        BrandKit.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    kit = result.scalar_one_or_none()
    if kit is None:
        raise HTTPException(status_code=404, detail="Brand kit not found")
    gen = BrandGuidelinesGenerator()
    return gen.generate(_to_response(kit))


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_brand_kit_file(
    brand_kit_id: str,
    file_type: str = "logo",
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload a font or logo file."""
    stmt = select(BrandKit).where(
        BrandKit.id == brand_kit_id,
        BrandKit.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    kit = result.scalar_one_or_none()
    if kit is None:
        raise HTTPException(status_code=404, detail="Brand kit not found")

    allowed = FONT_EXTENSIONS if file_type == "font" else LOGO_EXTENSIONS
    return {"message": "Upload endpoint ready", "allowed_types": list(allowed)}

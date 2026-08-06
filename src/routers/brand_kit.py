"""Brand kit CRUD endpoints.

POST   /brand-kit              — create
GET    /brand-kit              — list (paginated)
GET    /brand-kit/{id}         — get by id
GET    /brand-kit/guidelines   — generate guidelines HTML
POST   /brand-kit/upload       — upload font/logo file
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.brand_kit.guidelines import BrandGuidelinesGenerator
from src.brand_kit.storage import FONT_EXTENSIONS, LOGO_EXTENSIONS, BrandKitStorage
from src.config import Settings
from src.dependencies import get_db, get_settings_dep
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
    db: AsyncSession = Depends(get_db),  # noqa: B008
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
    db: AsyncSession = Depends(get_db),  # noqa: B008
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
    db: AsyncSession = Depends(get_db),  # noqa: B008
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
    db: AsyncSession = Depends(get_db),  # noqa: B008
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
    file: UploadFile = File(...),  # noqa: B008
    brand_kit_id: str = Form(...),
    file_type: str = Form("logo"),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    app_settings: Settings = Depends(get_settings_dep),  # noqa: B008
) -> dict:
    """Upload a font or logo file for a brand kit.

    The file is validated (extension whitelist + sanitized filename + size
    cap of ``MAX_UPLOAD_SIZE_MB``, 413 on oversized), stored under
    ``UPLOAD_ROOT/brand_kit/<kit_id>/<fonts|logos>/``, and the brand kit's
    ``fonts``/``logos`` JSON field is updated with the stored relative path.
    """
    storage = BrandKitStorage(app_settings.UPLOAD_ROOT)
    stmt = select(BrandKit).where(
        BrandKit.id == brand_kit_id,
        BrandKit.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    kit = result.scalar_one_or_none()
    if kit is None:
        raise HTTPException(status_code=404, detail="Brand kit not found")

    if file_type not in ("font", "logo"):
        raise HTTPException(
            status_code=400,
            detail="file_type must be 'font' or 'logo'",
        )
    allowed = FONT_EXTENSIONS if file_type == "font" else LOGO_EXTENSIONS

    # Defense in depth: reject disallowed extensions, then sanitize the
    # filename (strips directory components, rejects path traversal).
    if not storage.validate_file_type(file.filename or "", allowed):
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed for {file_type}. Allowed: {sorted(allowed)}",
        )
    try:
        filename = storage.validate_filename(file.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # F5 (DoS): cap upload size. Reject early on Content-Length when present,
    # then read in bounded chunks so a lying client can't exhaust memory.
    max_bytes = app_settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(status_code=413, detail="File too large")
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(status_code=413, detail="File too large")
        chunks.append(chunk)
    data = b"".join(chunks)
    if file_type == "font":
        stored_path = await storage.save_font(brand_kit_id, filename, data)
        fonts = dict(kit.fonts or {})
        fonts["heading_file"] = stored_path
        kit.fonts = fonts
    else:
        stored_path = await storage.save_logo(brand_kit_id, filename, data)
        logos = dict(kit.logos or {})
        logos["primary"] = stored_path
        logos["primary_format"] = Path(filename).suffix.lower().lstrip(".")
        logos["primary_size"] = len(data)
        kit.logos = logos

    kit.increment_version()
    await db.commit()
    await db.refresh(kit)

    return {
        "path": stored_path,
        "filename": filename,
        "size": len(data),
        "brand_kit_id": brand_kit_id,
        "file_type": file_type,
    }

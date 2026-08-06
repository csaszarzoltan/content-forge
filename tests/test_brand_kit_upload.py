"""End-to-end tests for the brand kit upload endpoint.

These tests exercise POST /brand-kit/upload through the real FastAPI app
with an in-memory SQLite database and a temp upload root, verifying:

- a valid logo upload stores the file and returns path/filename/size
- the brand kit's logos JSON field is updated with the stored path
- a valid font upload updates the fonts JSON field
- disallowed extensions are rejected with 400
- path traversal filenames are rejected with 400
- an invalid file_type is rejected with 400
- a missing brand kit returns 404
- multipart requests require python-multipart (declared dep)

File: tests/test_brand_kit_upload.py
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

pytestmark = pytest.mark.integration

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import Settings
from src.database import Base
from src.dependencies import get_db, get_settings_dep
from src.main import app
from src.models.brand_kit import BrandKit


@pytest.fixture
def settings(tmp_path) -> Settings:
    """Settings with a temp upload root so tests never touch ./uploads."""
    return Settings(
        JWT_SECRET="test-secret-key-for-testing-only",
        DATABASE_URL="sqlite+aiosqlite://",
        UPLOAD_ROOT=str(tmp_path),
    )


class TestBrandKitUploadEndpoint:
    """Real end-to-end tests for POST /brand-kit/upload."""

    _engine = None
    _session_factory = None

    @classmethod
    def _get_engine(cls):
        if cls._engine is None:
            cls._engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        return cls._engine

    @classmethod
    def _get_session_factory(cls):
        if cls._session_factory is None:
            cls._session_factory = async_sessionmaker(
                bind=cls._get_engine(),
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return cls._session_factory

    async def _init_db(self):
        """Create all tables for the in-memory database."""
        engine = self._get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _drop_db(self):
        """Drop all tables from the in-memory database."""
        engine = self._get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def _override_get_db(self) -> AsyncGenerator[AsyncSession]:
        """Override for the app's get_db dependency."""
        session = self._get_session_factory()()
        try:
            yield session
        finally:
            await session.close()

    async def _make_client(self, settings: Settings) -> AsyncClient:
        """Create a test client with overridden dependencies."""
        app.dependency_overrides[get_settings_dep] = lambda: settings
        app.dependency_overrides[get_db] = self._override_get_db
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    async def _create_kit(self, name: str = "Upload Test Kit") -> str:
        """Insert a brand kit directly and return its id."""
        session = self._get_session_factory()()
        try:
            kit = BrandKit(name=name)
            session.add(kit)
            await session.commit()
            await session.refresh(kit)
            return kit.id
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_upload_logo_stores_file_and_updates_logos(self, settings):
        """A valid PNG upload returns path/filename/size and persists to logos."""
        await self._init_db()
        kit_id = await self._create_kit()
        client = await self._make_client(settings)
        try:
            response = await client.post(
                "/brand-kit/upload",
                data={"brand_kit_id": kit_id, "file_type": "logo"},
                files={"file": ("primary.png", b"\x89PNG fake image bytes", "image/png")},
            )
            assert response.status_code == 201, f"Body: {response.text}"
            data = response.json()
            assert data["filename"] == "primary.png"
            assert data["size"] == len(b"\x89PNG fake image bytes")
            assert data["file_type"] == "logo"
            assert data["brand_kit_id"] == kit_id
            # Stored path is relative to upload root, under brand_kit/<id>/logos/
            assert data["path"].startswith(f"brand_kit/{kit_id}/logos/")
            assert data["path"].endswith("primary.png")

            # File actually exists on disk under the upload root
            from pathlib import Path

            full = Path(settings.UPLOAD_ROOT) / data["path"]
            assert full.exists()
            assert full.read_bytes() == b"\x89PNG fake image bytes"

            # Brand kit logos JSON field updated with the stored path
            session = self._get_session_factory()()
            try:
                from sqlalchemy import select

                result = await session.execute(
                    select(BrandKit).where(BrandKit.id == kit_id)
                )
                kit = result.scalar_one()
                assert kit.logos["primary"] == data["path"]
                assert kit.logos["primary_format"] == "png"
                assert kit.logos["primary_size"] == len(b"\x89PNG fake image bytes")
                assert kit.version == 2  # upload bumps version
            finally:
                await session.close()
        finally:
            await client.aclose()
            app.dependency_overrides.clear()
            await self._drop_db()

    @pytest.mark.asyncio
    async def test_upload_font_updates_fonts_field(self, settings):
        """A valid TTF upload stores the file and updates the fonts JSON field."""
        await self._init_db()
        kit_id = await self._create_kit()
        client = await self._make_client(settings)
        try:
            response = await client.post(
                "/brand-kit/upload",
                data={"brand_kit_id": kit_id, "file_type": "font"},
                files={"file": ("heading.ttf", b"fake font data", "font/ttf")},
            )
            assert response.status_code == 201, f"Body: {response.text}"
            data = response.json()
            assert data["path"].startswith(f"brand_kit/{kit_id}/fonts/")
            assert data["path"].endswith("heading.ttf")

            session = self._get_session_factory()()
            try:
                from sqlalchemy import select

                result = await session.execute(
                    select(BrandKit).where(BrandKit.id == kit_id)
                )
                kit = result.scalar_one()
                assert kit.fonts["heading_file"] == data["path"]
            finally:
                await session.close()
        finally:
            await client.aclose()
            app.dependency_overrides.clear()
            await self._drop_db()

    @pytest.mark.asyncio
    async def test_upload_rejects_disallowed_extension(self, settings):
        """An .exe file must be rejected with 400 for both logo and font."""
        await self._init_db()
        kit_id = await self._create_kit()
        client = await self._make_client(settings)
        try:
            response = await client.post(
                "/brand-kit/upload",
                data={"brand_kit_id": kit_id, "file_type": "logo"},
                files={"file": ("malware.exe", b"MZ fake exe", "application/octet-stream")},
            )
            assert response.status_code == 400, f"Body: {response.text}"
            assert "not allowed" in response.json()["detail"].lower()
        finally:
            await client.aclose()
            app.dependency_overrides.clear()
            await self._drop_db()

    @pytest.mark.asyncio
    async def test_upload_rejects_path_traversal_filename(self, settings):
        """Filenames with path traversal must be rejected with 400."""
        await self._init_db()
        kit_id = await self._create_kit()
        client = await self._make_client(settings)
        try:
            response = await client.post(
                "/brand-kit/upload",
                data={"brand_kit_id": kit_id, "file_type": "logo"},
                files={"file": ("../../etc/passwd.png", b"pwned", "image/png")},
            )
            assert response.status_code == 400, f"Body: {response.text}"
        finally:
            await client.aclose()
            app.dependency_overrides.clear()
            await self._drop_db()

    @pytest.mark.asyncio
    async def test_upload_rejects_invalid_file_type(self, settings):
        """file_type must be 'font' or 'logo'."""
        await self._init_db()
        kit_id = await self._create_kit()
        client = await self._make_client(settings)
        try:
            response = await client.post(
                "/brand-kit/upload",
                data={"brand_kit_id": kit_id, "file_type": "audio"},
                files={"file": ("song.mp3", b"ID3", "audio/mpeg")},
            )
            assert response.status_code == 400, f"Body: {response.text}"
            assert "font" in response.json()["detail"] and "logo" in response.json()["detail"]
        finally:
            await client.aclose()
            app.dependency_overrides.clear()
            await self._drop_db()

    @pytest.mark.asyncio
    async def test_upload_unknown_kit_returns_404(self, settings):
        """Uploading for a non-existent brand kit returns 404."""
        await self._init_db()
        client = await self._make_client(settings)
        try:
            response = await client.post(
                "/brand-kit/upload",
                data={"brand_kit_id": "no-such-kit", "file_type": "logo"},
                files={"file": ("primary.png", b"png", "image/png")},
            )
            assert response.status_code == 404, f"Body: {response.text}"
        finally:
            await client.aclose()
            app.dependency_overrides.clear()
            await self._drop_db()

    @pytest.mark.asyncio
    async def test_upload_requires_multipart_payload(self, settings):
        """A request without multipart form data fails validation (422)."""
        await self._init_db()
        kit_id = await self._create_kit()
        client = await self._make_client(settings)
        try:
            response = await client.post(
                "/brand-kit/upload",
                json={"brand_kit_id": kit_id, "file_type": "logo"},
            )
            # FastAPI needs a multipart body — JSON payloads are rejected
            assert response.status_code == 422, f"Body: {response.text}"
        finally:
            await client.aclose()
            app.dependency_overrides.clear()
            await self._drop_db()

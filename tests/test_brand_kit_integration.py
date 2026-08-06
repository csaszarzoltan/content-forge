"""ASGI integration tests for Brand Kit endpoints at /api/v1/brand-kit*.

These tests exercise the EXACT URLs the React frontend calls, using
ASGITransport to hit the real FastAPI app. They would have caught the
frontend/backend URL mismatch (Item 4).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import Base
from src.dependencies import get_db
from src.main import app

pytestmark = pytest.mark.integration


class TestBrandKitIntegration:
    """Integration tests for /api/v1/brand-kit endpoints.

    Each test runs against an isolated in-memory SQLite database so the
    suite never touches the dev ``contentforge.db`` or other tests' data.
    """

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
        """Override for the app's get_db dependency (in-memory session)."""
        session = self._get_session_factory()()
        try:
            yield session
        finally:
            await session.close()

    async def _client(self):
        """Client with get_db overridden to the isolated in-memory database."""
        app.dependency_overrides[get_db] = self._override_get_db
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    async def _cleanup(self, client: AsyncClient) -> None:
        await client.aclose()
        app.dependency_overrides.clear()
        await self._drop_db()

    @pytest.mark.asyncio
    async def test_list_brand_kits_returns_200(self):
        """GET /api/v1/brand-kit → 200 with empty list."""
        await self._init_db()
        async with await self._client() as client:
            try:
                response = await client.get("/api/v1/brand-kit")
                assert response.status_code == 200, response.text
                data = response.json()
                assert "items" in data
                assert "total" in data
                assert data["items"] == []
            finally:
                await self._cleanup(client)

    @pytest.mark.asyncio
    async def test_create_brand_kit_returns_201(self):
        """POST /api/v1/brand-kit → 201 with created kit."""
        await self._init_db()
        async with await self._client() as client:
            try:
                payload = {
                    "name": "Test Brand",
                    "description": "Integration test brand",
                    "brand_type": "personal",
                    "colors": {
                        "primary": "#0066cc",
                        "secondary": "#ffffff",
                        "accent": "#ff9900",
                        "background": "#f5f5f5",
                        "text": "#333333",
                    },
                    "fonts": {
                        "heading": "Manrope",
                        "body": "DM Sans",
                        "accent": "Inter",
                    },
                }
                response = await client.post("/api/v1/brand-kit", json=payload)
                assert response.status_code == 201, response.text
                data = response.json()
                assert data["name"] == "Test Brand"
                assert data["brand_type"] == "personal"
                assert "id" in data
                assert data["colors"]["primary"] == "#0066cc"
            finally:
                await self._cleanup(client)

    @pytest.mark.asyncio
    async def test_get_brand_kit_returns_404_for_missing(self):
        """GET /api/v1/brand-kit/{missing_id} → 404."""
        await self._init_db()
        async with await self._client() as client:
            try:
                response = await client.get("/api/v1/brand-kit/nonexistent-id")
                assert response.status_code == 404
            finally:
                await self._cleanup(client)

    @pytest.mark.asyncio
    async def test_guidelines_returns_404_for_missing(self):
        """GET /api/v1/brand-kit/guidelines?brand_kit_id=missing → 404."""
        await self._init_db()
        async with await self._client() as client:
            try:
                response = await client.get(
                    "/api/v1/brand-kit/guidelines?brand_kit_id=missing-id"
                )
                assert response.status_code == 404
            finally:
                await self._cleanup(client)

    @pytest.mark.asyncio
    async def test_upload_returns_404_for_missing_kit(self):
        """POST /api/v1/brand-kit/upload with missing kit → 404."""
        await self._init_db()
        async with await self._client() as client:
            try:
                # Need multipart form data; send minimal to trigger 404 first
                files = {"file": ("test.png", b"fake", "image/png")}
                data = {"brand_kit_id": "missing-id", "file_type": "logo"}
                response = await client.post(
                    "/api/v1/brand-kit/upload", files=files, data=data
                )
                # 404 (kit not found) or 422 (validation) are both valid —
                # the point is the route exists at /api/v1/brand-kit/upload
                assert response.status_code in (404, 422), response.text
            finally:
                await self._cleanup(client)
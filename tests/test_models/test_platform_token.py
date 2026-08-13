"""Interface and behavioral tests for the PlatformToken ORM model.

Interface tests  — verify imports, tablename, columns, FK (should PASS with stubs).
Behavioral tests — verify encryption/decryption and CRUD (RED until implementation).
"""

from __future__ import annotations

from datetime import UTC

import pytest


class TestPlatformTokenModelInterface:
    """Verify the PlatformToken ORM model interface."""

    def test_platform_token_importable(self):
        """PlatformToken should be importable from src.models.platform_token."""
        from src.models.platform_token import PlatformToken

        assert PlatformToken is not None

    def test_platform_token_is_sqlalchemy_model(self):
        """PlatformToken should be an SQLAlchemy declarative model."""
        from src.models.platform_token import PlatformToken

        assert hasattr(PlatformToken, "__tablename__")

    def test_platform_token_tablename(self):
        """PlatformToken.__tablename__ should be 'platform_tokens'."""
        from src.models.platform_token import PlatformToken

        assert PlatformToken.__tablename__ == "platform_tokens"

    def test_platform_token_columns(self):
        """PlatformToken should have the required columns."""
        from src.models.platform_token import PlatformToken

        cols = {c.name for c in PlatformToken.__table__.columns}
        assert "id" in cols
        assert "user_id" in cols
        assert "platform" in cols
        assert "access_token_encrypted" in cols
        assert "refresh_token_encrypted" in cols or "refresh_token" in cols
        assert "expires_at" in cols
        assert "created_at" in cols
        assert "updated_at" in cols

    def test_platform_token_has_user_fk(self):
        """PlatformToken.user_id should be a ForeignKey to users.id."""
        from src.models.platform_token import PlatformToken

        user_id_col = PlatformToken.__table__.columns["user_id"]
        # Check it has foreign keys
        fks = user_id_col.foreign_keys
        assert len(fks) >= 1
        # The FK should reference the users table
        fk_targets = {fk.column.table.name for fk in fks if fk.column.table is not None}
        assert any("user" in t for t in fk_targets)

    def test_platform_token_platform_column(self):
        """PlatformToken.platform should be a non-nullable String."""
        from src.models.platform_token import PlatformToken

        platform_col = PlatformToken.__table__.columns["platform"]
        assert not platform_col.nullable

    def test_platform_token_encryption_field_type(self):
        """PlatformToken.access_token_encrypted should store encrypted token data."""
        from src.models.platform_token import PlatformToken

        col = PlatformToken.__table__.columns["access_token_encrypted"]
        # Should be a String column (or Text)
        assert col.type.python_type is str

    def test_platform_token_exported_from_models(self):
        """PlatformToken should be exported from src.models."""
        from src import models

        assert hasattr(models, "PlatformToken")


class TestPlatformTokenBehavioral:
    """Behavioral tests for PlatformToken — RED until implemented."""

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_roundtrip(self):
        """Encrypting then decrypting a token should return the original."""
        from src.models.platform_token import PlatformToken

        token = PlatformToken(
            user_id="user_1",
            platform="twitter",
        )
        # Use the model's encrypt/decrypt helpers
        original_token = "my-secret-twitter-token-12345"
        try:
            encrypted = token.encrypt_token(original_token)
            assert encrypted != original_token
            decrypted = token.decrypt_token(encrypted)
            assert decrypted == original_token
        except AttributeError:
            # Alternative: use module-level encrypt/decrypt
            from src.models.platform_token import decrypt_token, encrypt_token

            encrypted = encrypt_token(original_token)
            assert encrypted != original_token
            decrypted = decrypt_token(encrypted)
            assert decrypted == original_token

    @pytest.mark.asyncio
    async def test_create_platform_token_in_db(self):
        """Creating a PlatformToken in the database should persist it."""
        from datetime import datetime

        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from src.database import Base
        from src.models.platform_token import PlatformToken

        # Create in-memory SQLite database
        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        session = session_factory()
        try:
            token = PlatformToken(
                user_id="user_1",
                platform="twitter",
                access_token_encrypted="encrypted_token_value",
                refresh_token_encrypted="encrypted_refresh_token",
                expires_at=datetime.now(UTC),
            )
            session.add(token)
            await session.commit()
            await session.refresh(token)

            assert token.id is not None
            assert token.user_id == "user_1"
            assert token.platform == "twitter"

            # Query it back
            result = await session.execute(
                select(PlatformToken).where(PlatformToken.user_id == "user_1")
            )
            fetched = result.scalar_one()
            assert fetched.id == token.id
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_update_platform_token(self):
        """Updating a PlatformToken should persist the changes."""
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from src.database import Base
        from src.models.platform_token import PlatformToken

        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        session = session_factory()
        try:
            token = PlatformToken(
                user_id="user_2",
                platform="linkedin",
                access_token_encrypted="old_token",
            )
            session.add(token)
            await session.commit()

            # Update the token
            token.access_token_encrypted = "new_token"
            token.platform = "linkedin"
            await session.commit()

            # Verify update
            result = await session.execute(
                select(PlatformToken).where(PlatformToken.id == token.id)
            )
            fetched = result.scalar_one()
            assert fetched.access_token_encrypted == "new_token"
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_delete_platform_token(self):
        """Deleting a PlatformToken should remove it from the database."""
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from src.database import Base
        from src.models.platform_token import PlatformToken

        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        session = session_factory()
        try:
            token = PlatformToken(
                user_id="user_3",
                platform="twitter",
                access_token_encrypted="deletable_token",
            )
            session.add(token)
            await session.commit()

            # Delete it
            await session.delete(token)
            await session.commit()

            # Verify deletion
            result = await session.execute(
                select(PlatformToken).where(PlatformToken.user_id == "user_3")
            )
            assert result.scalar_one_or_none() is None
        finally:
            await session.close()
            await engine.dispose()

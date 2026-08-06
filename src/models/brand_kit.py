"""BrandKit ORM model.

Represents a persisted brand kit (visual identity).
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class BrandKit(Base):
    """Persistent brand kit."""

    __tablename__ = "brand_kits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    brand_type: Mapped[str] = mapped_column(String(50), default="personal")
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    brand_voice_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    colors: Mapped[dict] = mapped_column(JSON, default=dict)
    fonts: Mapped[dict] = mapped_column(JSON, default=dict)
    logos: Mapped[dict] = mapped_column(JSON, default=dict)
    guidelines_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def soft_delete(self) -> None:
        """Mark the record as deleted."""
        self.deleted_at = datetime.now(UTC)

    def increment_version(self) -> None:
        """Bump the version number."""
        self.version += 1

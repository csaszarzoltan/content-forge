"""PlatformToken ORM model for storing encrypted social media credentials."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.services.token_encryption import decrypt_token, encrypt_token


class PlatformToken(Base):
    """Encrypted social media platform credentials for a user.

    Stores OAuth tokens encrypted at rest using Fernet symmetric encryption.
    """

    __tablename__ = "platform_tokens"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=True, default="")
    refresh_token_encrypted: Mapped[str] = mapped_column(Text, nullable=True, default="")
    scopes: Mapped[str | None] = mapped_column(String(256), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def encrypt_token(self, token_data: str) -> str:
        """Encrypt and store a token string.

        Args:
            token_data: The plaintext token to encrypt.

        Returns:
            The encrypted token string.
        """
        enc = encrypt_token(token_data)
        self.access_token_encrypted = enc
        return enc

    def decrypt_token(self, encrypted: str | None = None) -> str:
        """Decrypt an encrypted token string.

        Args:
            encrypted: The encrypted token. Defaults to access_token_encrypted.

        Returns:
            The decrypted plaintext token.
        """
        source = encrypted if encrypted is not None else self.access_token_encrypted
        return decrypt_token(source)

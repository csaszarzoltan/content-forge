"""Token encryption/decryption helpers using Fernet symmetric encryption.

Uses the ENCRYPTION_KEY from settings when available, or falls back
to a module-level generated key for development/testing.
"""

from __future__ import annotations

from cryptography.fernet import Fernet

from src.config import get_settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Return a Fernet instance, initialised from settings or a module-level fallback."""
    global _fernet
    if _fernet is not None:
        return _fernet
    try:
        settings = get_settings()
        key = settings.ENCRYPTION_KEY
        if key:
            _fernet = Fernet(key.encode() if isinstance(key, str) else key)
            return _fernet
    except Exception:
        pass
    # Fallback: generate a module-level key for dev/test
    _fernet = Fernet(Fernet.generate_key())
    return _fernet


def encrypt_token(token_data: str) -> str:
    """Encrypt a token string using Fernet.

    Args:
        token_data: The plaintext token to encrypt.

    Returns:
        The encrypted token as a URL-safe base64 string.
    """
    f = _get_fernet()
    return f.encrypt(token_data.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt a Fernet-encrypted token string.

    Args:
        encrypted: The encrypted token.

    Returns:
        The decrypted plaintext token.
    """
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()

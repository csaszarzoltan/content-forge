"""JWT authentication service: token creation, password hashing, user lookup.

Provides helper functions for the auth endpoints and dependency injection:
- create_access_token / create_refresh_token
- verify_password / hash_password
- authenticate_user / create_user
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models.user import User
from src.schemas.auth import RegisterRequest

# Password hashing context — bcrypt recommended for production
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: str,
    settings: Settings,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a short-lived JWT access token containing the user id.

    Payload: {"sub": user_id, "exp": expiry, "type": "access"}
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(UTC) + expires_delta
    to_encode: dict = {
        "sub": user_id,
        "exp": expire,
        "type": "access",
        "iat": datetime.now(UTC),
        "jti": str(uuid4()),
    }
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: str,
    settings: Settings,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a long-lived JWT refresh token.

    Payload: {"sub": user_id, "exp": expiry, "type": "refresh"}
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    expire = datetime.now(UTC) + expires_delta
    to_encode: dict = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
        "iat": datetime.now(UTC),
        "jti": str(uuid4()),
    }
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, settings: Settings) -> dict | None:
    """Decode and validate a JWT token.

    Returns the payload dict on success, or None if the token is
    expired, malformed, or otherwise invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Look up a user by their email address."""
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """Look up a user by their primary key."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """Verify email + password and return the User, or None on failure."""
    user = await get_user_by_email(db, email)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def create_user(
    db: AsyncSession,
    body: RegisterRequest,
) -> User:
    """Create a new user with a hashed password.

    Raises ValueError if the email is already taken.
    """
    existing = await get_user_by_email(db, body.email)
    if existing is not None:
        msg = "Email already registered"
        raise ValueError(msg)

    user = User(
        id=str(uuid4()),
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name or body.email.split("@")[0],
        is_active=True,
        role="user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_refresh_token_hash(
    db: AsyncSession,
    user: User,
    refresh_token: str | None,
) -> None:
    """Store or clear the hashed refresh token on the user record."""
    user.refresh_token_hash = hash_password(refresh_token) if refresh_token else None
    await db.commit()

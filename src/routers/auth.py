"""Auth endpoints: register, login, refresh, and current-user retrieval.

Real implementation using python-jose and passlib.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_current_user, get_db, get_settings_dep
from src.models.user import User
from src.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from src.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_user,
    decode_token,
    get_user_by_id,
    update_refresh_token_hash,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user account.

    Returns 201 with the user profile.
    Raises 409 Conflict if the email is already registered.
    """
    try:
        user = await create_user(db, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return _user_to_response(user)


@router.post("/login")
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    settings=Depends(get_settings_dep),
) -> TokenResponse:
    """Authenticate with email + password.

    Returns 200 with access_token, refresh_token, token_type, expires_in.
    Raises 401 Unauthorized for invalid credentials.
    """
    user = await authenticate_user(db, body.email, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.id, settings)
    refresh_token = create_refresh_token(user.id, settings)

    # Store hashed refresh token for rotation
    await update_refresh_token_hash(db, user, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    settings=Depends(get_settings_dep),
) -> TokenResponse:
    """Exchange a refresh token for a new access/refresh pair.

    Validates the refresh token, then issues a fresh token pair.
    Raises 401 for invalid or expired refresh tokens.
    """
    payload = decode_token(body.refresh_token, settings)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload["sub"]
    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Issue fresh token pair
    access_token = create_access_token(user.id, settings)
    refresh_token = create_refresh_token(user.id, settings)

    # Rotate refresh token
    await update_refresh_token_hash(db, user, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me")
async def me(
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> UserResponse:
    """Return the authenticated user's profile.

    Requires a valid Bearer access token.
    """
    return _user_to_response(current_user)


def _user_to_response(user: User) -> UserResponse:
    """Convert a User ORM model to a Pydantic response."""
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        organization_id=user.organization_id,
        created_at=user.created_at,
    )

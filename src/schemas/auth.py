"""Pydantic schemas for JWT authentication endpoints.

Defines request/response models for register, login,
refresh, and current-user retrieval.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """Request body for POST /auth/register."""

    email: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        description="Valid email address",
    )
    password: str = Field(
        ..., min_length=8, description="Password (min 8 characters)"
    )
    display_name: str = Field("", description="Optional display name")


class LoginRequest(BaseModel):
    """Request body for POST /auth/login."""

    email: str = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")


class RefreshRequest(BaseModel):
    """Request body for POST /auth/refresh."""

    refresh_token: str = Field(..., description="Valid refresh token")


class TokenResponse(BaseModel):
    """Response body for login and refresh endpoints."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # seconds (15 min default)


class UserResponse(BaseModel):
    """Response body representing an authenticated user profile."""

    id: str
    email: str
    display_name: str
    role: str
    organization_id: str | None = None
    created_at: datetime

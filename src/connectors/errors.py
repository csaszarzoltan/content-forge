"""Custom exception hierarchy for social media connectors."""

from __future__ import annotations


class ConnectorError(Exception):
    """Base exception for all connector errors."""


class PublishError(ConnectorError):
    """Raised when a publish operation fails (5xx or unrecoverable error)."""


class AuthError(PublishError):
    """Raised on authentication/authorization failures (401/403)."""


class RateLimitError(PublishError):
    """Raised when rate limit is exceeded (429)."""

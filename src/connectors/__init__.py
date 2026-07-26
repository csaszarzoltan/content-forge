"""Social media connector package for ContentForge.

Provides abstract base class, platform-specific connectors,
rate limiter, and error types.
"""

from src.connectors.base import SocialMediaConnector
from src.connectors.errors import AuthError, ConnectorError, PublishError, RateLimitError

__all__ = [
    "SocialMediaConnector",
    "ConnectorError",
    "AuthError",
    "RateLimitError",
    "PublishError",
]

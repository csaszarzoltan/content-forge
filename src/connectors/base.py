"""Abstract base class for social media platform connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SocialMediaConnector(ABC):
    """Abstract base for publishing content to a social media platform.

    Subclasses must implement all abstract methods and properties.
    """

    @abstractmethod
    async def publish(self, text: str, **kwargs: Any) -> dict:
        """Publish content to the platform.

        Args:
            text: The content text to publish.
            **kwargs: Platform-specific parameters.

        Returns:
            A dict containing the publish result (id, url, etc.).
        """

    @abstractmethod
    async def preview(self, text: str, **kwargs: Any) -> dict:
        """Preview how the content will look on the platform.

        Args:
            text: The content text to preview.
            **kwargs: Platform-specific parameters.

        Returns:
            A dict containing preview information.
        """

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Validate that the current credentials are valid.

        Returns:
            True if credentials are valid, False otherwise.
        """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform name identifier (e.g. 'twitter', 'linkedin')."""

"""Platform constraint registry — loads and serves constraint data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.constraints.models import PlatformConstraints, RegistryMetadata


class ConstraintRegistry:
    """Load, query, and update platform constraint data from JSON."""

    def __init__(self, registry_path: str | Path | None = None) -> None:
        """Initialize registry. Does NOT load data — call load() explicitly."""
        self._path = Path(registry_path) if registry_path else None
        self._metadata: RegistryMetadata | None = None
        self._platforms: dict[str, PlatformConstraints] = {}

    def load(self) -> None:
        """Load and validate registry data from JSON file."""
        raise NotImplementedError

    def get(self, platform: str) -> PlatformConstraints:
        """Return constraints for a single platform."""
        raise NotImplementedError

    def all_platforms(self) -> dict[str, PlatformConstraints]:
        """Return constraints for all registered platforms."""
        raise NotImplementedError

    def platform_names(self) -> list[str]:
        """Return list of registered platform IDs."""
        raise NotImplementedError

    @property
    def version(self) -> str:
        """Return the registry version string."""
        raise NotImplementedError

    def update(self, platform: str, constraints: PlatformConstraints) -> None:
        """Update constraints for a single platform."""
        raise NotImplementedError

    def export(self) -> dict[str, Any]:
        """Export the full registry as a JSON-serializable dict."""
        raise NotImplementedError

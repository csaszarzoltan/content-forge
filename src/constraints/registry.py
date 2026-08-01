"""Platform constraint registry — loads and serves constraint data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.constraints.models import PlatformConstraints, RegistryMetadata

# Default data directory (sibling to this file)
_DATA_DIR = Path(__file__).parent / "data"


class ConstraintRegistry:
    """Load, query, and update platform constraint data from JSON."""

    def __init__(self, registry_path: str | Path | None = None) -> None:
        """Initialize registry. Does NOT load data — call load() explicitly."""
        self._path = Path(registry_path) if registry_path else None
        self._metadata: RegistryMetadata | None = None
        self._platforms: dict[str, PlatformConstraints] = {}

    def load(self) -> None:
        """Load and validate registry data from JSON file."""
        data_path = self._path or (_DATA_DIR / "registry.json")
        with open(data_path, encoding="utf-8") as fh:
            raw = json.load(fh)

        self._metadata = RegistryMetadata(
            version=raw.get("version", "1.0.0"),
            last_verified=raw.get("last_verified", ""),
        )
        self._platforms = {}
        for platform_id, pdata in raw.get("platforms", {}).items():
            self._platforms[platform_id] = PlatformConstraints(**pdata)
            self._metadata.platforms[platform_id] = self._platforms[platform_id]

    def get(self, platform: str) -> PlatformConstraints:
        """Return constraints for a single platform."""
        if platform not in self._platforms:
            raise KeyError(f"Unknown platform: {platform!r}")
        return self._platforms[platform]

    def all_platforms(self) -> dict[str, PlatformConstraints]:
        """Return constraints for all registered platforms."""
        return dict(self._platforms)

    def platform_names(self) -> list[str]:
        """Return list of registered platform IDs."""
        return sorted(self._platforms.keys())

    @property
    def version(self) -> str:
        """Return the registry version string."""
        if self._metadata is None:
            raise NotImplementedError("Registry not loaded")
        return self._metadata.version

    def update(self, platform: str, constraints: PlatformConstraints) -> None:
        """Update constraints for a single platform."""
        self._platforms[platform] = constraints
        if self._metadata is not None:
            self._metadata.platforms[platform] = constraints

    def export(self) -> dict[str, Any]:
        """Export the full registry as a JSON-serializable dict."""
        if self._metadata is None:
            raise NotImplementedError("Registry not loaded")
        return {
            "version": self._metadata.version,
            "last_verified": self._metadata.last_verified,
            "platforms": {
                pid: pc.model_dump() for pid, pc in self._platforms.items()
            },
        }

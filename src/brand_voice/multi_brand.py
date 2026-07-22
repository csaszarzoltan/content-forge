"""Multi-brand voice profile manager with scoping support.

Manages multiple brand voice profiles with project-level scoping
and active voice tracking.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from brand_voice.models import VoiceProfile


class VoiceManager:
    """Manages multiple brand voice profiles with scoping."""

    def __init__(self, profiles_dir: str | Path) -> None:
        """Initialize the voice manager.

        Args:
            profiles_dir: Directory where brand profiles are stored as JSON files.
        """
        self._dir = Path(profiles_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._brands: dict[str, dict] = {}  # brand_id -> {"name": ..., "profile": ...}
        self._active: dict[str, str] = {}  # scope -> brand_id
        self._load()

    def _brand_file(self, brand_id: str) -> Path:
        return self._dir / f"{brand_id}.json"

    def _active_file(self) -> Path:
        return self._dir / "_active.json"

    def _index_file(self) -> Path:
        return self._dir / "_index.json"

    def _load(self) -> None:
        """Load brand index and active mappings from disk."""
        idx_path = self._index_file()
        if idx_path.exists():
            self._brands = json.loads(idx_path.read_text(encoding="utf-8"))
        active_path = self._active_file()
        if active_path.exists():
            self._active = json.loads(active_path.read_text(encoding="utf-8"))

    def _save_index(self) -> None:
        self._index_file().write_text(
            json.dumps(self._brands, indent=2), encoding="utf-8"
        )

    def _save_active(self) -> None:
        self._active_file().write_text(
            json.dumps(self._active, indent=2), encoding="utf-8"
        )

    def create_brand(self, name: str, profile: VoiceProfile) -> str:
        """Register a new brand.

        Args:
            name: Human-readable brand name.
            profile: Voice profile for the brand.

        Returns:
            Generated brand ID.
        """
        brand_id = str(uuid.uuid4())[:8]
        self._brands[brand_id] = {"name": name, "profile": profile.model_dump()}
        self._brand_file(brand_id).write_text(
            profile.model_dump_json(indent=2), encoding="utf-8"
        )
        self._save_index()
        return brand_id

    def get_brand(self, brand_id: str) -> VoiceProfile:
        """Get a brand's voice profile.

        Args:
            brand_id: Brand identifier.

        Returns:
            VoiceProfile for the brand.

        Raises:
            KeyError: If brand_id not found.
        """
        if brand_id not in self._brands:
            raise KeyError(f"Brand '{brand_id}' not found")
        profile_file = self._brand_file(brand_id)
        if profile_file.exists():
            return VoiceProfile.model_validate_json(
                profile_file.read_text(encoding="utf-8")
            )
        return VoiceProfile.model_validate(self._brands[brand_id]["profile"])

    def list_brands(self) -> dict[str, str]:
        """Return {brand_id: brand_name} mapping for all registered brands."""
        return {bid: info["name"] for bid, info in self._brands.items()}

    def delete_brand(self, brand_id: str) -> None:
        """Remove a brand profile.

        Args:
            brand_id: Brand identifier to delete.

        Raises:
            KeyError: If brand_id not found.
        """
        if brand_id not in self._brands:
            raise KeyError(f"Brand '{brand_id}' not found")
        del self._brands[brand_id]
        # Remove profile file
        pf = self._brand_file(brand_id)
        if pf.exists():
            pf.unlink()
        # Clear from active scopes
        scopes_to_remove = [s for s, bid in self._active.items() if bid == brand_id]
        for s in scopes_to_remove:
            del self._active[s]
        self._save_index()
        self._save_active()

    def set_active(self, brand_id: str, scope: str = "global") -> None:
        """Set the active brand for a scope.

        Args:
            brand_id: Brand identifier to activate.
            scope: Scope name ("global" or a project name).
        """
        if brand_id not in self._brands:
            raise KeyError(f"Brand '{brand_id}' not found")
        self._active[scope] = brand_id
        self._save_active()

    def get_active(self, scope: str = "global") -> VoiceProfile | None:
        """Get the active voice for a scope.

        Args:
            scope: Scope name ("global" or a project name).

        Returns:
            Active VoiceProfile or None if none set.
        """
        brand_id = self._active.get(scope)
        if brand_id is None:
            return None
        if brand_id not in self._brands:
            return None
        return self.get_brand(brand_id)

    def list_scopes(self) -> dict[str, str]:
        """Return {scope: brand_id} showing which brand is active where."""
        return dict(self._active)


__all__ = ["VoiceManager"]

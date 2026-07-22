"""Voice scoping and persistence layer.

Persists voice selections at user and project level with conflict resolution.
Project-level voice overrides user-level; user-level is fallback.
"""
from __future__ import annotations

import json
from pathlib import Path


class VoiceScope:
    """Manages voice profile scoping and persistence.

    Resolution order: project > user > None.
    Config directory is created automatically if it does not exist.
    """

    def __init__(self, config_dir: str | Path) -> None:
        """Initialize the voice scope manager.

        Args:
            config_dir: Directory for persistent config files.
        """
        self._dir = Path(config_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._users: dict[str, str] = {}  # user_id -> brand_id
        self._projects: dict[str, str] = {}  # project_id -> brand_id
        self._load()

    def _users_file(self) -> Path:
        return self._dir / "user_voices.json"

    def _projects_file(self) -> Path:
        return self._dir / "project_voices.json"

    def _load(self) -> None:
        uf = self._users_file()
        if uf.exists():
            self._users = json.loads(uf.read_text(encoding="utf-8"))
        pf = self._projects_file()
        if pf.exists():
            self._projects = json.loads(pf.read_text(encoding="utf-8"))

    def _save_users(self) -> None:
        self._users_file().write_text(
            json.dumps(self._users, indent=2), encoding="utf-8"
        )

    def _save_projects(self) -> None:
        self._projects_file().write_text(
            json.dumps(self._projects, indent=2), encoding="utf-8"
        )

    def set_user_voice(self, user_id: str, brand_id: str) -> None:
        """Set a user's default voice.

        Args:
            user_id: Unique user identifier.
            brand_id: Brand voice identifier.
        """
        self._users[user_id] = brand_id
        self._save_users()

    def get_user_voice(self, user_id: str) -> str | None:
        """Get a user's default voice ID.

        Args:
            user_id: Unique user identifier.

        Returns:
            Brand voice ID or None if not set.
        """
        return self._users.get(user_id)

    def set_project_voice(self, project_id: str, brand_id: str) -> None:
        """Set a project's voice (overrides user default).

        Args:
            project_id: Unique project identifier.
            brand_id: Brand voice identifier.
        """
        self._projects[project_id] = brand_id
        self._save_projects()

    def get_project_voice(self, project_id: str) -> str | None:
        """Get a project's voice ID.

        Args:
            project_id: Unique project identifier.

        Returns:
            Brand voice ID or None if not set.
        """
        return self._projects.get(project_id)

    def resolve(self, user_id: str, project_id: str | None = None) -> str | None:
        """Resolve the effective voice: project > user > None.

        Args:
            user_id: Unique user identifier.
            project_id: Optional project identifier.

        Returns:
            Effective brand voice ID, or None if no voice is configured.
        """
        if project_id is not None:
            project_voice = self.get_project_voice(project_id)
            if project_voice is not None:
                return project_voice
        return self.get_user_voice(user_id)

    def clear(self, scope: str, scope_id: str) -> None:
        """Clear a voice binding for a scope.

        Args:
            scope: Either "user" or "project".
            scope_id: The user or project identifier.
        """
        if scope == "user":
            self._users.pop(scope_id, None)
            self._save_users()
        elif scope == "project":
            self._projects.pop(scope_id, None)
            self._save_projects()


__all__ = ["VoiceScope"]

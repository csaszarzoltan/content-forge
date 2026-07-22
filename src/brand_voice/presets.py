"""Voice preset gallery — built-in and custom voice profiles.

Loads, lists, and selects from built-in voice presets.
Custom presets persist as JSON files to a user-specified directory.
"""
from __future__ import annotations

import json
from pathlib import Path

from brand_voice.models import (
    FormattingPrefs,
    ScenarioTone,
    VocabularyRules,
    VoiceAttribute,
    VoiceProfile,
)

_BUILTIN_PRESETS: dict[str, dict] = {
    "formal": {
        "id": "preset-formal",
        "name": "formal",
        "description": "Professional, formal voice for corporate communications",
        "brand_identity": {
            "who": "Professional Organization",
            "audience": "Business professionals and stakeholders",
            "purpose": "Convey authority and credibility through formal communication",
        },
        "attributes": [
            VoiceAttribute(name="formality", min_label="casual", max_label="formal", value=0.9),
            VoiceAttribute(name="humor", min_label="serious", max_label="playful", value=0.1),
            VoiceAttribute(name="enthusiasm", min_label="reserved", max_label="excited", value=0.3),
        ],
        "vocabulary": VocabularyRules(
            preferred=["therefore", "consequently", "furthermore", "accordingly"],
            banned=["gonna", "wanna", "kinda", "stuff"],
            jargon_level="heavy",
        ),
        "scenarios": [
            ScenarioTone(
                scenario="incident",
                tone="authoritative",
                instructions="Maintain professional composure. State facts clearly without emotion.",
            ),
            ScenarioTone(
                scenario="launch",
                tone="confident",
                instructions="Highlight achievements with measured enthusiasm.",
            ),
        ],
        "formatting": FormattingPrefs(heading_style="title", bullet_style="numbered", citation_format="footnote"),
        "metadata": {"preset_type": "builtin"},
    },
    "casual": {
        "id": "preset-casual",
        "name": "casual",
        "description": "Friendly, relaxed voice for informal communications",
        "brand_identity": {
            "who": "Friendly Team",
            "audience": "General audience and community members",
            "purpose": "Build approachability through warm, casual tone",
        },
        "attributes": [
            VoiceAttribute(name="formality", min_label="casual", max_label="formal", value=0.2),
            VoiceAttribute(name="humor", min_label="serious", max_label="playful", value=0.6),
            VoiceAttribute(name="enthusiasm", min_label="reserved", max_label="excited", value=0.7),
        ],
        "vocabulary": VocabularyRules(
            preferred=["hey", "awesome", "cool", "thanks"],
            banned=["hereby", "aforementioned", "notwithstanding"],
            jargon_level="none",
        ),
        "scenarios": [
            ScenarioTone(
                scenario="incident",
                tone="transparent",
                instructions="Be honest and straightforward. No jargon.",
            ),
            ScenarioTone(
                scenario="support_reply",
                tone="empathetic",
                instructions="Be friendly and helpful. Use simple language.",
            ),
        ],
        "formatting": FormattingPrefs(heading_style="sentence", bullet_style="dash", citation_format="inline"),
        "metadata": {"preset_type": "builtin"},
    },
    "witty": {
        "id": "preset-witty",
        "name": "witty",
        "description": "Clever, humorous voice with personality",
        "brand_identity": {
            "who": "Witty Brand",
            "audience": "Tech-savvy audience that appreciates humor",
            "purpose": "Entertain while informing through clever writing",
        },
        "attributes": [
            VoiceAttribute(name="formality", min_label="casual", max_label="formal", value=0.3),
            VoiceAttribute(name="humor", min_label="serious", max_label="playful", value=0.9),
            VoiceAttribute(name="enthusiasm", min_label="reserved", max_label="excited", value=0.6),
        ],
        "vocabulary": VocabularyRules(
            preferred=["brilliant", "game-changing", "game-changer", "pro tip"],
            banned=["boring", "standard", "typical"],
            jargon_level="light",
        ),
        "scenarios": [
            ScenarioTone(
                scenario="launch",
                tone="excited",
                instructions="Make it fun. Use wordplay where appropriate.",
            ),
            ScenarioTone(
                scenario="support_reply",
                tone="empathetic",
                instructions="Be helpful but keep the light tone. No jokes about their problem.",
            ),
        ],
        "formatting": FormattingPrefs(heading_style="sentence", bullet_style="dash", citation_format="inline"),
        "metadata": {"preset_type": "builtin"},
    },
    "empathetic": {
        "id": "preset-empathetic",
        "name": "empathetic",
        "description": "Compassionate, understanding voice for sensitive topics",
        "brand_identity": {
            "who": "Empathetic Organization",
            "audience": "Users seeking support or guidance",
            "purpose": "Show genuine care and understanding in every interaction",
        },
        "attributes": [
            VoiceAttribute(name="formality", min_label="casual", max_label="formal", value=0.4),
            VoiceAttribute(name="humor", min_label="serious", max_label="playful", value=0.2),
            VoiceAttribute(name="enthusiasm", min_label="reserved", max_label="excited", value=0.5),
        ],
        "vocabulary": VocabularyRules(
            preferred=["understand", "appreciate", "support", "help"],
            banned=["policy", "terms", "unfortunately we cannot"],
            jargon_level="none",
        ),
        "scenarios": [
            ScenarioTone(
                scenario="incident",
                tone="transparent",
                instructions="Acknowledge impact first, then explain what happened.",
            ),
            ScenarioTone(
                scenario="support_reply",
                tone="empathetic",
                instructions="Lead with understanding. Validate their experience.",
            ),
        ],
        "formatting": FormattingPrefs(heading_style="sentence", bullet_style="dash", citation_format="inline"),
        "metadata": {"preset_type": "builtin"},
    },
    "technical": {
        "id": "preset-technical",
        "name": "technical",
        "description": "Precise, technical voice for developer documentation",
        "brand_identity": {
            "who": "Technical Team",
            "audience": "Software engineers and technical professionals",
            "purpose": "Communicate complex concepts clearly and precisely",
        },
        "attributes": [
            VoiceAttribute(name="formality", min_label="casual", max_label="formal", value=0.6),
            VoiceAttribute(name="humor", min_label="serious", max_label="playful", value=0.1),
            VoiceAttribute(name="enthusiasm", min_label="reserved", max_label="excited", value=0.2),
        ],
        "vocabulary": VocabularyRules(
            preferred=["implement", "configure", "optimize", "deploy", "specification"],
            banned=["magic", "just", "simply", "easy"],
            jargon_level="heavy",
        ),
        "scenarios": [
            ScenarioTone(
                scenario="launch",
                tone="confident",
                instructions="Focus on technical improvements and benchmarks.",
            ),
            ScenarioTone(
                scenario="support_reply",
                tone="patient",
                instructions="Provide step-by-step guidance with code examples.",
            ),
        ],
        "formatting": FormattingPrefs(heading_style="title", bullet_style="numbered", citation_format="inline"),
        "metadata": {"preset_type": "builtin"},
    },
}


class PresetManager:
    """Manages built-in and custom voice presets."""

    def __init__(self, custom_dir: str | Path | None = None) -> None:
        """Initialize the preset manager.

        Args:
            custom_dir: Directory for custom preset JSON files.
                        Created automatically if it does not exist.
        """
        self._custom_dir: Path | None = None
        if custom_dir is not None:
            self._custom_dir = Path(custom_dir)
            self._custom_dir.mkdir(parents=True, exist_ok=True)

    def _load_builtin(self, name: str) -> VoiceProfile:
        """Load a built-in preset by name."""
        data = _BUILTIN_PRESETS[name]
        return VoiceProfile(**{k: v for k, v in data.items()})

    def _custom_path(self, name: str) -> Path | None:
        if self._custom_dir is None:
            return None
        return self._custom_dir / f"{name}.json"

    def list_builtins(self) -> list[str]:
        """Return sorted names of built-in presets."""
        return sorted(_BUILTIN_PRESETS.keys())

    def list_custom(self) -> list[str]:
        """Return sorted names of user-saved custom presets."""
        if self._custom_dir is None or not self._custom_dir.exists():
            return []
        names = [
            p.stem
            for p in self._custom_dir.iterdir()
            if p.suffix == ".json" and p.is_file()
        ]
        return sorted(names)

    def get_preset(self, name: str) -> VoiceProfile:
        """Get a preset by name.

        Args:
            name: Preset name.

        Returns:
            VoiceProfile for the requested preset.

        Raises:
            KeyError: If name not found in builtins or customs.
        """
        if name in _BUILTIN_PRESETS:
            return self._load_builtin(name)
        custom_names = self.list_custom()
        if name in custom_names:
            path = self._custom_path(name)
            data = json.loads(path.read_text(encoding="utf-8"))
            return VoiceProfile.model_validate(data)
        raise KeyError(f"Preset '{name}' not found")

    def save_custom(self, profile: VoiceProfile, name: str) -> None:
        """Save a voice profile as a custom preset.

        Args:
            profile: The voice profile to save.
            name: Name to save it under.
        """
        path = self._custom_path(name)
        if path is None:
            raise ValueError("No custom_dir configured")
        path.write_text(
            profile.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def delete_custom(self, name: str) -> None:
        """Delete a custom preset.

        Args:
            name: Name of the custom preset to delete.

        Raises:
            KeyError: If name not found in custom presets.
        """
        if name not in self.list_custom():
            raise KeyError(f"Custom preset '{name}' not found")
        path = self._custom_path(name)
        path.unlink()

    def remix(self, base_name: str, overrides: dict) -> VoiceProfile:
        """Create a new profile by remixing an existing preset with overrides.

        Args:
            base_name: Name of the preset to use as base.
            overrides: Dict of fields to override on the resulting VoiceProfile.

        Returns:
            A new VoiceProfile. The original preset is not mutated.
        """
        base = self.get_preset(base_name)
        data = base.model_dump()
        data.update(overrides)
        return VoiceProfile.model_validate(data)


__all__ = ["PresetManager"]

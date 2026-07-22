"""Pydantic models for brand voice profile structure.

Defines the data schema matching the BRAND_VOICE.md 5-section format:
Identity, Voice Attributes, Vocabulary, Scenarios, Formatting.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class VoiceAttribute(BaseModel):
    """A single attribute on the brand voice spectrum (e.g., formal ↔ casual)."""

    name: str = Field(description="Attribute name, e.g. 'tone' or 'formality'")
    min_label: str = Field(description="Label at the low end of the spectrum (0.0)")
    max_label: str = Field(description="Label at the high end of the spectrum (1.0)")
    value: float = Field(ge=0.0, le=1.0, description="Position on the spectrum, 0.0–1.0")


class VocabularyRules(BaseModel):
    """Preferred and banned vocabulary for the brand voice."""

    preferred: list[str] = Field(default_factory=list, description="Words and phrases to use")
    banned: list[str] = Field(default_factory=list, description="Words and phrases to avoid")
    jargon_level: Literal["none", "light", "heavy"] = Field(
        default="light", description="Industry jargon tolerance"
    )


class ScenarioTone(BaseModel):
    """Scenario-specific tone guidance."""

    scenario: str = Field(description="Scenario name, e.g. 'incident', 'launch'")
    tone: str = Field(description="Tone descriptor, e.g. 'transparent', 'excited'")
    instructions: str = Field(description="Free-text guidance for the scenario")


class FormattingPrefs(BaseModel):
    """Formatting preferences for brand voice output."""

    heading_style: str = Field(default="sentence", description="e.g. 'sentence', 'title'")
    bullet_style: str = Field(default="dash", description="e.g. 'dash', 'numbered'")
    citation_format: str = Field(default="inline", description="e.g. 'inline', 'footnote'")


class VoiceProfile(BaseModel):
    """Complete brand voice profile matching the BRAND_VOICE.md 5-section format."""

    id: str = Field(description="Unique identifier for the voice profile")
    name: str = Field(description="Human-readable name")
    description: str = Field(description="Brief description of the voice")
    brand_identity: dict[str, str] = Field(
        default_factory=lambda: {"who": "", "audience": "", "purpose": ""},
        description="Brand identity: who, audience, purpose",
    )
    attributes: list[VoiceAttribute] = Field(default_factory=list)
    vocabulary: VocabularyRules = Field(default_factory=VocabularyRules)
    scenarios: list[ScenarioTone] = Field(default_factory=list)
    formatting: FormattingPrefs = Field(default_factory=FormattingPrefs)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (source_file, created_at, version, etc.)",
    )

    def to_system_prompt(self) -> str:
        """Generate a structured system prompt block with all voice sections.

        Returns:
            A formatted string suitable for use as an LLM system prompt.
        """
        lines: list[str] = []
        lines.append(f"# Brand Voice: {self.name}")
        lines.append("")
        lines.append("## Identity")
        for key, val in self.brand_identity.items():
            lines.append(f"- {key}: {val}")
        lines.append("")
        if self.attributes:
            lines.append("## Voice Attributes")
            for attr in self.attributes:
                lines.append(
                    f"- {attr.name}: {attr.value:.1f} "
                    f"({attr.min_label} ↔ {attr.max_label})"
                )
            lines.append("")
        lines.append("## Vocabulary")
        if self.vocabulary.preferred:
            lines.append(f"- Preferred: {', '.join(self.vocabulary.preferred)}")
        if self.vocabulary.banned:
            lines.append(f"- Banned: {', '.join(self.vocabulary.banned)}")
        lines.append(f"- Jargon level: {self.vocabulary.jargon_level}")
        lines.append("")
        if self.scenarios:
            lines.append("## Scenarios")
            for sc in self.scenarios:
                lines.append(f"- {sc.scenario} ({sc.tone}): {sc.instructions}")
            lines.append("")
        lines.append("## Formatting")
        lines.append(f"- Heading style: {self.formatting.heading_style}")
        lines.append(f"- Bullet style: {self.formatting.bullet_style}")
        lines.append(f"- Citation format: {self.formatting.citation_format}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the profile to a dictionary."""
        return self.model_dump(mode="python")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VoiceProfile":
        """Create a VoiceProfile from a dictionary."""
        return cls.model_validate(data)

    @model_validator(mode="after")
    def _validate_attributes(self) -> "VoiceProfile":
        """Ensure all attribute values are within 0.0–1.0 range."""
        for attr in self.attributes:
            if not (0.0 <= attr.value <= 1.0):
                raise ValueError(
                    f"Attribute '{attr.name}' value {attr.value} is out of range [0.0, 1.0]"
                )
        return self


__all__ = [
    "VoiceAttribute",
    "VocabularyRules",
    "ScenarioTone",
    "FormattingPrefs",
    "VoiceProfile",
]

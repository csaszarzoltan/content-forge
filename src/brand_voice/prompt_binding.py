"""Prompt template library with voice binding.

Binds voice profiles to reusable prompt templates for content generation.
Supports multiple content types (email, landing_page, social_post, etc.).
"""
from __future__ import annotations

from brand_voice.models import VoiceProfile
from brand_voice.presets import PresetManager
from brand_voice.templates import TemplateEngine

_CONTENT_TYPE_RULES: dict[str, str] = {
    "email": (
        "When writing emails:\n"
        "- Use a clear, descriptive subject line\n"
        "- Open with a personalized greeting\n"
        "- Keep paragraphs short (2-3 sentences)\n"
        "- End with a clear call to action\n"
    ),
    "landing_page": (
        "When writing landing page copy:\n"
        "- Lead with the value proposition\n"
        "- Use benefit-driven headlines\n"
        "- Include social proof elements\n"
        "- End with a prominent CTA\n"
    ),
    "social_post": (
        "When writing social media posts:\n"
        "- Keep it concise (under 280 chars for X/Twitter)\n"
        "- Use emojis strategically\n"
        "- Include relevant hashtags\n"
        "- Encourage engagement\n"
    ),
    "faq": (
        "When writing FAQ answers:\n"
        "- Start with a direct answer\n"
        "- Provide supporting details\n"
        "- Use bullet points for lists\n"
        "- Link to additional resources\n"
    ),
    "support_reply": (
        "When writing support replies:\n"
        "- Acknowledge the issue first\n"
        "- Provide step-by-step instructions\n"
        "- Use the customer's name\n"
        "- Offer follow-up assistance\n"
    ),
}


class PromptBinder:
    """Binds voice profiles to prompt templates for content generation."""

    def __init__(
        self,
        template_engine: TemplateEngine,
        preset_manager: PresetManager | None = None,
    ) -> None:
        """Initialize the prompt binder.

        Args:
            template_engine: TemplateEngine instance for rendering prompts.
            preset_manager: Optional PresetManager for preset lookups.
        """
        self._engine = template_engine
        self._preset_manager = preset_manager

    def create_prompt(
        self,
        content_type: str,
        profile: VoiceProfile,
        topic: str,
        **kwargs,
    ) -> str:
        """Generate a complete prompt for content creation.

        Args:
            content_type: Type of content ("email", "landing_page", "social_post", "faq", "support_reply").
            profile: Active voice profile.
            topic: Subject/topic of the content.
            **kwargs: Additional context (audience, length, format, etc.).

        Returns:
            Complete prompt string ready to send to an LLM.
        """
        lines: list[str] = []
        lines.append(f"# Content Creation: {content_type.replace('_', ' ').title()}")
        lines.append(f"## Topic: {topic}")
        lines.append("")

        # Voice profile section
        lines.append("## Brand Voice Rules")
        for attr in profile.attributes:
            lines.append(
                f"- {attr.name}: {attr.value:.1f} ({attr.min_label} ↔ {attr.max_label})"
            )
        if profile.vocabulary.preferred:
            lines.append(f"- Preferred words: {', '.join(profile.vocabulary.preferred)}")
        if profile.vocabulary.banned:
            lines.append(f"- Avoid: {', '.join(profile.vocabulary.banned)}")
        lines.append(f"- Jargon level: {profile.vocabulary.jargon_level}")
        lines.append("")

        # Content type rules
        if content_type in _CONTENT_TYPE_RULES:
            lines.append(f"## {content_type.replace('_', ' ').title()} Guidelines")
            lines.append(_CONTENT_TYPE_RULES[content_type])
            lines.append("")

        # Additional kwargs
        for key, val in kwargs.items():
            lines.append(f"- {key}: {val}")

        return "\n".join(lines)

    def create_system_prompt(
        self,
        profile: VoiceProfile,
        content_type: str | None = None,
    ) -> str:
        """Generate a system prompt that constrains LLM output to brand voice.

        Args:
            profile: Active voice profile.
            content_type: Optional content type for additional constraints.

        Returns:
            System prompt string.
        """
        parts: list[str] = []
        parts.append(f"You are writing for brand: {profile.name}")
        parts.append(f"Description: {profile.description}")
        parts.append("")
        parts.append("## Brand Voice")
        for attr in profile.attributes:
            parts.append(
                f"- {attr.name}: {attr.value:.1f} ({attr.min_label} ↔ {attr.max_label})"
            )
        if profile.vocabulary.preferred:
            parts.append(f"- Preferred: {', '.join(profile.vocabulary.preferred)}")
        if profile.vocabulary.banned:
            parts.append(f"- Banned: {', '.join(profile.vocabulary.banned)}")
        parts.append(f"- Jargon level: {profile.vocabulary.jargon_level}")
        parts.append("")

        if content_type and content_type in _CONTENT_TYPE_RULES:
            parts.append(f"## Content Type: {content_type}")
            parts.append(_CONTENT_TYPE_RULES[content_type])

        return "\n".join(parts)

    def list_content_types(self) -> list[str]:
        """Return available content types."""
        return sorted(_CONTENT_TYPE_RULES.keys())


__all__ = ["PromptBinder"]

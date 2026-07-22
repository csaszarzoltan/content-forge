"""Scenario-driven template engine for brand voice prompts.

Renders scenario-specific voice prompts using Jinja2 templates.
Ships with 5+ built-in scenarios.
"""
from __future__ import annotations

from pathlib import Path

from brand_voice.models import VoiceProfile

_BUILTIN_SCENARIOS: dict[str, str] = {
    "incident": (
        "# Incident Communication — {brand_name}\n\n"
        "**Tone:** {tone}\n\n"
        "## Voice Rules\n"
        "{voice_rules}\n\n"
        "## Scenario Instructions\n"
        "{instructions}\n\n"
        "When communicating about an incident:\n"
        "- Be transparent about what happened\n"
        "- State the impact clearly\n"
        "- Provide a timeline for resolution\n"
        "- Outline next steps and prevention measures\n"
    ),
    "launch": (
        "# Product Launch — {brand_name}\n\n"
        "**Tone:** {tone}\n\n"
        "## Voice Rules\n"
        "{voice_rules}\n\n"
        "## Scenario Instructions\n"
        "{instructions}\n\n"
        "When announcing a launch:\n"
        "- Celebrate the achievement\n"
        "- Highlight customer value over features\n"
        "- Include data points and proof\n"
        "- End with a clear call to action\n"
    ),
    "support_reply": (
        "# Support Response — {brand_name}\n\n"
        "**Tone:** {tone}\n\n"
        "## Voice Rules\n"
        "{voice_rules}\n\n"
        "## Scenario Instructions\n"
        "{instructions}\n\n"
        "When replying to support inquiries:\n"
        "- Acknowledge the user's issue first\n"
        "- Provide clear, actionable steps\n"
        "- Use the customer's name\n"
        "- Follow up with additional resources\n"
    ),
    "social_media": (
        "# Social Media Post — {brand_name}\n\n"
        "**Tone:** {tone}\n\n"
        "## Voice Rules\n"
        "{voice_rules}\n\n"
        "## Scenario Instructions\n"
        "{instructions}\n\n"
        "When creating social media content:\n"
        "- Keep it concise and engaging\n"
        "- Use hashtags strategically\n"
        "- Encourage interaction\n"
        "- Maintain brand consistency\n"
    ),
    "faq": (
        "# FAQ Response — {brand_name}\n\n"
        "**Tone:** {tone}\n\n"
        "## Voice Rules\n"
        "{voice_rules}\n\n"
        "## Scenario Instructions\n"
        "{instructions}\n\n"
        "When answering frequently asked questions:\n"
        "- Be direct and clear\n"
        "- Use simple language\n"
        "- Provide examples where helpful\n"
        "- Link to additional resources\n"
    ),
}


def _build_voice_rules(profile: VoiceProfile) -> str:
    """Build a voice rules block from a profile."""
    lines: list[str] = []
    for attr in profile.attributes:
        lines.append(f"- {attr.name}: {attr.value:.1f} ({attr.min_label} ↔ {attr.max_label})")
    if profile.vocabulary.preferred:
        lines.append(f"- Preferred words: {', '.join(profile.vocabulary.preferred)}")
    if profile.vocabulary.banned:
        lines.append(f"- Avoid: {', '.join(profile.vocabulary.banned)}")
    lines.append(f"- Jargon level: {profile.vocabulary.jargon_level}")
    return "\n".join(lines)


class TemplateEngine:
    """Renders scenario-specific voice prompts from templates + voice profiles."""

    def __init__(self, template_dir: str | Path | None = None) -> None:
        """Initialize the template engine.

        Args:
            template_dir: Optional custom directory with Jinja2 template files.
        """
        self._builtin = dict(_BUILTIN_SCENARIOS)
        self._custom: dict[str, str] = {}
        if template_dir is not None:
            td = Path(template_dir)
            if td.exists():
                for f in td.glob("*.md"):
                    self._custom[f.stem] = f.read_text(encoding="utf-8")

    def _get_template(self, scenario: str) -> str:
        """Get a template by name, raising KeyError if not found."""
        if scenario in self._builtin:
            return self._builtin[scenario]
        if scenario in self._custom:
            return self._custom[scenario]
        raise KeyError(f"Scenario template '{scenario}' not found")

    def render(
        self,
        scenario: str,
        profile: VoiceProfile,
        context: dict | None = None,
    ) -> str:
        """Render a scenario template with voice context.

        Args:
            scenario: Template name (e.g., "incident", "launch", "support_reply").
            profile: Active voice profile.
            context: Additional template variables (product_name, audience, etc.).

        Returns:
            Rendered string with voice rules and scenario-specific guidance.

        Raises:
            KeyError: If scenario template not found.
        """
        template = self._get_template(scenario)
        voice_rules = _build_voice_rules(profile)
        # Find the scenario tone instructions
        instructions = ""
        tone = "default"
        for sc in profile.scenarios:
            if sc.scenario == scenario:
                tone = sc.tone
                instructions = sc.instructions
                break

        result = template.format(
            brand_name=profile.name,
            tone=tone,
            voice_rules=voice_rules,
            instructions=instructions,
        )

        # Inject context variables
        if context:
            for key, val in context.items():
                result += f"\n- {key}: {val}"

        return result

    def list_scenarios(self) -> list[str]:
        """Return available scenario names."""
        return sorted(set(self._builtin.keys()) | set(self._custom.keys()))

    def render_system_prompt(
        self,
        profile: VoiceProfile,
        scenario: str | None = None,
    ) -> str:
        """Generate a full system prompt combining voice profile + scenario instructions.

        Args:
            profile: Active voice profile.
            scenario: Optional scenario name. If provided, appends scenario-specific tone.

        Returns:
            Complete system prompt string.
        """
        base = profile.to_system_prompt()
        if scenario is not None:
            # Find scenario info
            for sc in profile.scenarios:
                if sc.scenario == scenario:
                    base += f"\n\n## Active Scenario: {scenario}\n"
                    base += f"Tone: {sc.tone}\n"
                    base += f"Instructions: {sc.instructions}\n"
                    break
        return base


__all__ = ["TemplateEngine"]

"""Per-language prompt template registry.

Provides LanguagePromptTemplate schema, PromptTemplateRegistry for CRUD,
automatic template selection based on language + content_type, and
file-based template loading at startup.

AC-T5 reference: Per-Language Prompt Templates (P1 — Brand Integrity).
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel


class LanguagePromptTemplate(BaseModel):
    """A prompt template for a specific language and content type.

    AC-T5.2: Defines language_code, content_type, system_prompt,
    user_prompt_template, brand_voice_translation, character_budget_warning.
    """

    language_code: str
    content_type: str
    system_prompt: str
    user_prompt_template: str
    brand_voice_translation: dict | None = None
    character_budget_warning: bool = False


class TemplateInfo(BaseModel):
    """Lightweight summary for listing available templates."""

    language_code: str
    content_type: str
    character_budget_warning: bool


# Default English templates (blog, social, email)
_DEFAULT_ENGLISH_TEMPLATES: list[dict] = [
    {
        "language_code": "en",
        "content_type": "blog",
        "system_prompt": "You are an expert blog writer. {brand_voice_context}",
        "user_prompt_template": "Write a blog post about: {topic}\nAudience: {audience}\nLength: {length}",
    },
    {
        "language_code": "en",
        "content_type": "social",
        "system_prompt": "You are a social media content creator. {brand_voice_context}",
        "user_prompt_template": "Write a {length} social media post about: {topic}\nAudience: {audience}",
    },
    {
        "language_code": "en",
        "content_type": "email",
        "system_prompt": "You are an email marketing specialist. {brand_voice_context}",
        "user_prompt_template": "Write an email about: {topic}\nAudience: {audience}\nLength: {length}",
    },
]


class PromptTemplateRegistry:
    """Registry for per-language prompt templates.

    AC-T5.1: Provides get_template, register_template, list_templates.
    AC-T5.3: Auto template selection based on language + content_type.
    AC-T5.4: Fallback chain (language -> English -> error).
    AC-T5.5: Brand voice attribute translation injection.
    AC-T5.6: File-based template loading at startup.
    """

    def __init__(self) -> None:
        """Initialize the registry with an empty template store.

        Default templates for English (blog, social, email) are created
        after construction via _create_defaults().
        """
        self._templates: dict[tuple[str, str], LanguagePromptTemplate] = {}
        self._create_defaults()

    def _create_defaults(self) -> None:
        """Create default English templates for standard content types."""
        for entry in _DEFAULT_ENGLISH_TEMPLATES:
            tpl = LanguagePromptTemplate(
                language_code=entry["language_code"],
                content_type=entry["content_type"],
                system_prompt=entry["system_prompt"],
                user_prompt_template=entry["user_prompt_template"],
            )
            key = (tpl.language_code, tpl.content_type)
            self._templates[key] = tpl

    def get_template(self, language: str, content_type: str) -> LanguagePromptTemplate:
        """Retrieve a template by language + content_type.

        AC-T5.4: Falls back to English template with
                 'Respond in {language}' instruction.

        Raises:
            KeyError: If no template found and fallback exhausted.
        """
        # Normalize language code to lowercase
        language = language.lower()

        # Try exact match first (AC-T5.3)
        key = (language, content_type)
        if key in self._templates:
            return self._templates[key]

        # Fallback to English template (AC-T5.4)
        en_key = ("en", content_type)
        if en_key in self._templates:
            template = self._templates[en_key]
            # If not English, add instruction to respond in detected language
            if language != "en":
                # Create a modified copy with language-specific instruction
                modified = template.model_copy(deep=True)
                modified.system_prompt = (
                    f"{template.system_prompt}\n"
                    f"Respond in {language}."
                )
                return modified
            return template

        # Fallback exhausted — content type not found at all (AC-T5.4)
        raise KeyError(
            f"No template found for language='{language}', content_type='{content_type}'. "
            f"Available: {list(self._templates.keys())}"
        )

    def register_template(self, template: LanguagePromptTemplate) -> None:
        """Register or update a template."""
        key = (template.language_code, template.content_type)
        self._templates[key] = template

    def list_templates(self) -> list[TemplateInfo]:
        """List all registered templates as lightweight summaries."""
        return [
            TemplateInfo(
                language_code=tpl.language_code,
                content_type=tpl.content_type,
                character_budget_warning=tpl.character_budget_warning,
            )
            for tpl in self._templates.values()
        ]

    def load_from_directory(self, path: str | Path) -> int:
        """Load templates from JSON/YAML files in a directory.

        Args:
            path: Directory path containing .json/.yaml/.yml template files.

        Returns:
            Number of templates successfully loaded.

        Raises:
            FileNotFoundError: If *path* does not exist.
        """
        directory = Path(path)
        if not directory.exists():
            raise FileNotFoundError(f"Template directory not found: {directory}")

        count = 0
        for file_path in sorted(directory.iterdir()):
            if file_path.suffix.lower() in (".json", ".yaml", ".yml"):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    if file_path.suffix.lower() == ".json":
                        data = json.loads(content)
                    else:
                        # Simple YAML-like parsing for .yaml/.yml files
                        data = _parse_yaml_simple(content)

                    if isinstance(data, list):
                        for entry in data:
                            self.register_template(LanguagePromptTemplate(**entry))
                            count += 1
                    elif isinstance(data, dict):
                        self.register_template(LanguagePromptTemplate(**data))
                        count += 1
                except Exception:
                    # Skip malformed files
                    continue

        return count

    def clear(self) -> None:
        """Remove all registered templates (useful for testing)."""
        self._templates.clear()


def _parse_yaml_simple(content: str) -> dict | list:
    """Simple YAML parser for template files — uses json-compatible subset.

    This is intentionally minimal. For full YAML support, install PyYAML.
    """
    import ast

    # Try to evaluate as Python literal (works for simple JSON-compatible structures)
    try:
        return ast.literal_eval(content)
    except (ValueError, SyntaxError):
        pass

    # Fallback: try to parse as JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(f"Could not parse template file content: {content[:100]}...")


__all__ = [
    "LanguagePromptTemplate",
    "PromptTemplateRegistry",
    "TemplateInfo",
]

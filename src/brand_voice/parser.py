"""Parser for BRAND_VOICE.md files.

Parses structured markdown voice definitions into VoiceProfile instances.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from brand_voice.models import (
    FormattingPrefs,
    ScenarioTone,
    VocabularyRules,
    VoiceAttribute,
    VoiceProfile,
)

REQUIRED_SECTIONS = {"Identity", "Voice Attributes", "Vocabulary", "Scenarios", "Formatting"}


class ParseError(Exception):
    """Raised when BRAND_VOICE.md is malformed or missing required sections."""

    pass


def _parse_attributes(lines: list[str]) -> list[VoiceAttribute]:
    """Parse voice attribute lines like '- formality: 0.7 (casual ↔ formal)'."""
    attrs: list[VoiceAttribute] = []
    for line in lines:
        line = line.strip().lstrip("- ").strip()
        if not line:
            continue
        # Pattern: name: value (min ↔ max)
        m = re.match(
            r"(\w+):\s*([\d.]+)\s*\(([^↔]+)↔([^)]+)\)",
            line,
        )
        if m:
            attrs.append(
                VoiceAttribute(
                    name=m.group(1),
                    value=float(m.group(2)),
                    min_label=m.group(3).strip(),
                    max_label=m.group(4).strip(),
                )
            )
    return attrs


def _parse_list_field(value_str: str) -> list[str]:
    """Parse a comma-separated field into a list of strings."""
    return [item.strip() for item in value_str.split(",") if item.strip()]


def _parse_section(content: str, section_name: str) -> list[str]:
    """Extract lines under a ## section heading."""
    pattern = rf"^#{{1,2}}\s+{re.escape(section_name)}\s*$"
    lines = content.split("\n")
    result: list[str] = []
    in_section = False
    for line in lines:
        if re.match(pattern, line, re.MULTILINE):
            in_section = True
            continue
        if in_section and re.match(r"^#{1,2}\s+\S", line):
            break
        if in_section:
            result.append(line)
    return result


def _parse_identity(lines: list[str]) -> dict[str, str]:
    """Parse identity key: value pairs."""
    identity: dict[str, str] = {}
    for line in lines:
        line = line.strip().lstrip("- ").strip()
        if ":" in line and not line.startswith("#"):
            key, _, val = line.partition(":")
            key = key.strip().lower()
            val = val.strip()
            if key and key in ("who", "audience", "purpose"):
                identity[key] = val
    return identity


def _parse_scenarios(lines: list[str]) -> list[ScenarioTone]:
    """Parse scenario lines like '- incident: transparent'."""
    scenarios: list[ScenarioTone] = []
    for line in lines:
        line = line.strip().lstrip("- ").strip()
        if not line:
            continue
        if ":" in line:
            name, _, tone = line.partition(":")
            scenarios.append(
                ScenarioTone(
                    scenario=name.strip(),
                    tone=tone.strip(),
                    instructions=f"Follow the {name.strip()} scenario guidelines.",
                )
            )
    return scenarios


def _parse_formatting(lines: list[str]) -> FormattingPrefs:
    """Parse formatting key: value pairs."""
    prefs: dict[str, str] = {}
    for line in lines:
        line = line.strip().lstrip("- ").strip()
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if key in ("heading_style", "bullet_style", "citation_format"):
                prefs[key] = val
    return FormattingPrefs(**prefs)


def _parse_vocabulary(lines: list[str]) -> VocabularyRules:
    """Parse vocabulary section."""
    preferred: list[str] = []
    banned: list[str] = []
    jargon_level = "light"
    for line in lines:
        line = line.strip().lstrip("- ").strip()
        if line.startswith("preferred:"):
            preferred = _parse_list_field(line.split(":", 1)[1])
        elif line.startswith("banned:"):
            banned = _parse_list_field(line.split(":", 1)[1])
        elif line.startswith("jargon_level:"):
            jargon_level = line.split(":", 1)[1].strip()
    return VocabularyRules(preferred=preferred, banned=banned, jargon_level=jargon_level)


def _build_profile(
    content: str,
    source: str = "<unknown>",
) -> VoiceProfile:
    """Build a VoiceProfile from parsed markdown content."""
    sections_found = set()
    for section in REQUIRED_SECTIONS:
        if re.search(rf"^#{{1,2}}\s+{re.escape(section)}\s*$", content, re.MULTILINE):
            sections_found.add(section)

    missing = REQUIRED_SECTIONS - sections_found
    if missing:
        raise ParseError(f"Missing required sections: {', '.join(sorted(missing))}")

    identity_lines = _parse_section(content, "Identity")
    identity = _parse_identity(identity_lines)
    # Derive name from 'who' field or source
    name = identity.get("who", source)

    attr_lines = _parse_section(content, "Voice Attributes")
    attributes = _parse_attributes(attr_lines)

    vocab_lines = _parse_section(content, "Vocabulary")
    vocabulary = _parse_vocabulary(vocab_lines)

    scenario_lines = _parse_section(content, "Scenarios")
    scenarios = _parse_scenarios(scenario_lines)

    formatting_lines = _parse_section(content, "Formatting")
    formatting = _parse_formatting(formatting_lines)

    return VoiceProfile(
        id=source,
        name=name,
        description=f"Brand voice parsed from {source}",
        brand_identity=identity,
        attributes=attributes,
        vocabulary=vocabulary,
        scenarios=scenarios,
        formatting=formatting,
        metadata={"source_file": source},
    )


def parse_brand_voice(file_path: str | Path) -> VoiceProfile:
    """Parse a BRAND_VOICE.md file into a VoiceProfile.

    Args:
        file_path: Path to the BRAND_VOICE.md file.

    Returns:
        Parsed VoiceProfile instance.

    Raises:
        ParseError: If file is missing required sections or has invalid structure.
        FileNotFoundError: If file_path does not exist.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    content = path.read_text(encoding="utf-8")
    return _build_profile(content, source=str(path.name))


def parse_brand_voice_string(content: str, source: str = "<string>") -> VoiceProfile:
    """Parse BRAND_VOICE.md content from a string.

    Args:
        content: Raw markdown content of a BRAND_VOICE.md file.
        source: Source identifier for error messages and metadata.

    Returns:
        Parsed VoiceProfile instance.

    Raises:
        ParseError: If content is missing required sections or has invalid structure.
    """
    return _build_profile(content, source=source)


def validate_brand_voice(data: dict[str, Any]) -> list[str]:
    """Validate a brand voice dict structure.

    Args:
        data: Dictionary representation of a brand voice profile.

    Returns:
        List of validation error strings. Empty list = valid.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["Data must be a dictionary"]

    required_fields = ["id", "name", "description"]
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"Missing or empty required field: '{field}'")

    if "attributes" in data:
        for i, attr in enumerate(data["attributes"]):
            if not isinstance(attr, dict):
                errors.append(f"Attribute at index {i} must be a dictionary")
                continue
            for key in ("name", "min_label", "max_label", "value"):
                if key not in attr:
                    errors.append(f"Attribute at index {i} missing field: '{key}'")
            if "value" in attr:
                val = attr["value"]
                if not isinstance(val, (int, float)) or not (0.0 <= val <= 1.0):
                    errors.append(
                        f"Attribute at index {i} value must be between 0.0 and 1.0, got {val}"
                    )

    if "vocabulary" in data:
        vocab = data["vocabulary"]
        if not isinstance(vocab, dict):
            errors.append("'vocabulary' must be a dictionary")
        else:
            for key in ("preferred", "banned", "jargon_level"):
                if key not in vocab:
                    errors.append(f"'vocabulary' missing field: '{key}'")

    if "scenarios" in data and not isinstance(data["scenarios"], list):
        errors.append("'scenarios' must be a list")

    if "formatting" in data:
        fmt = data["formatting"]
        if not isinstance(fmt, dict):
            errors.append("'formatting' must be a dictionary")

    return errors


__all__ = [
    "ParseError",
    "parse_brand_voice",
    "parse_brand_voice_string",
    "validate_brand_voice",
]

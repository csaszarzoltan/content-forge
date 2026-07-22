# Parser — Brand Voice Markdown Parser

The `brand_voice.parser` module parses structured markdown files (`BRAND_VOICE.md`) into `VoiceProfile` instances. The parser validates that all 5 required sections are present.

## BRAND_VOICE.md Format

```markdown
# Identity
who: Acme Corp
audience: Developers
purpose: Build great tools

## Voice Attributes
- formality: 0.7 (casual ↔ formal)
- humor: 0.3 (serious ↔ playful)

## Vocabulary
preferred: scalable, robust, proven
banned: pivot, synergy, disrupt

## Scenarios
- incident: transparent
- launch: excited

## Formatting
heading_style: sentence
bullet_style: dash
citation_format: inline
```

### Required Sections

All five sections are mandatory:
1. **Identity** — `who`, `audience`, `purpose` key-value pairs
2. **Voice Attributes** — Attribute lines in `name: value (min_label ↔ max_label)` format
3. **Vocabulary** — `preferred:` comma-separated list, `banned:` comma-separated list, `jargon_level:` value
4. **Scenarios** — `- scenario_name: tone` bullet points
5. **Formatting** — `heading_style:`, `bullet_style:`, `citation_format:` values

## API

### parse_brand_voice(file_path: str | Path) -> VoiceProfile

Parses a BRAND_VOICE.md file from disk.

```python
from brand_voice.parser import parse_brand_voice

profile = parse_brand_voice("path/to/BRAND_VOICE.md")
print(profile.name)  # Derived from the 'who' field
```

Raises:
- `FileNotFoundError` — if the file doesn't exist
- `ParseError` — if required sections are missing

### parse_brand_voice_string(content: str, source: str = "<string>") -> VoiceProfile

Parses BRAND_VOICE.md content from a string (no file needed).

```python
from brand_voice.parser import parse_brand_voice_string

content = """\
# Identity
who: Test Brand
audience: QA Engineers
purpose: Validate parsing
## Voice Attributes
- tone: 0.5 (serious ↔ playful)
## Vocabulary
preferred: quality, reliable
banned: crash, bug
## Scenarios
- release: confident
## Formatting
heading_style: title
"""
profile = parse_brand_voice_string(content, source="test.md")
assert profile.metadata["source_file"] == "test.md"
```

### validate_brand_voice(data: dict) -> list[str]

Validates a dictionary representation of a brand voice profile. Returns an empty list when valid, or a list of error strings for invalid data.

```python
from brand_voice.parser import validate_brand_voice

errors = validate_brand_voice({
    "id": "test-v1",
    "name": "Test",
    "description": "Test",
    "attributes": [{"name": "tone", "min_label": "a", "max_label": "b", "value": 0.5}],
    "vocabulary": {"preferred": [], "banned": [], "jargon_level": "light"},
    "scenarios": [],
    "formatting": {"heading_style": "sentence", "bullet_style": "dash", "citation_format": "inline"},
})
assert errors == []  # Valid
```

## Exceptions

### ParseError

Raised when the markdown content is malformed or missing required sections.

```python
from brand_voice.parser import ParseError, parse_brand_voice_string

try:
    parse_brand_voice_string("Who: Broken")  # Missing sections
except ParseError as e:
    print(e)  # "Missing required sections: Formatting, ..."
```

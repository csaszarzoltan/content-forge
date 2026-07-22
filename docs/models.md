# Models — VoiceProfile Data Schema

The `brand_voice.models` module defines the Pydantic-based data structure for brand voice profiles. Every profile follows a 5-section format matching the BRAND_VOICE.md specification.

## VoiceProfile

The root model representing a complete brand voice.

```python
from brand_voice.models import VoiceProfile

profile = VoiceProfile(
    id="acme-corp-v1",
    name="Acme Corp Professional",
    description="Professional and approachable voice for Acme Corporation",
    brand_identity={
        "who": "Acme Corporation, a B2B SaaS company",
        "audience": "Engineering leaders and CTOs",
        "purpose": "Build trust through transparent communication",
    },
    attributes=[...],
    vocabulary=VocabularyRules(...),
    scenarios=[...],
    formatting=FormattingPrefs(...),
    metadata={"version": "1.0.0"},
)
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `str` | Yes | Unique identifier |
| `name` | `str` | Yes | Human-readable name |
| `description` | `str` | Yes | Brief description |
| `brand_identity` | `dict[str, str]` | Yes | `who`, `audience`, `purpose` |
| `attributes` | `list[VoiceAttribute]` | Yes (default `[]`) | Brand voice spectrum attributes |
| `vocabulary` | `VocabularyRules` | Yes (default) | Preferred/banned words + jargon level |
| `scenarios` | `list[ScenarioTone]` | Yes (default `[]`) | Scenario-specific tone guidance |
| `formatting` | `FormattingPrefs` | Yes (default) | Heading/bullet/citation preferences |
| `metadata` | `dict[str, Any]` | Yes (default `{}`) | Additional metadata |

### Methods

#### `to_system_prompt() -> str`

Generates a structured system prompt block with all voice sections, suitable for LLM injection:

```python
prompt = profile.to_system_prompt()
# # Brand Voice: Acme Corp Professional
#
# ## Identity
# - who: Acme Corporation, a B2B SaaS company
# - audience: Engineering leaders and CTOs
# - purpose: Build trust through transparent communication
# ...
```

#### `to_dict() -> dict[str, Any]`

Serializes the profile to a plain dictionary (uses Pydantic's `model_dump`).

#### `from_dict(cls, data: dict[str, Any]) -> VoiceProfile`

Classmethod — creates a VoiceProfile from a dictionary (uses Pydantic's `model_validate`).

## VoiceAttribute

A single attribute on the brand voice spectrum (e.g., formal ↔ casual).

```python
VoiceAttribute(
    name="formality",       # Attribute name
    min_label="casual",     # Label at 0.0 end
    max_label="formal",     # Label at 1.0 end
    value=0.7,              # Position on spectrum (0.0–1.0)
)
```

Value is validated to be in `[0.0, 1.0]` range.

## VocabularyRules

Preferred and banned vocabulary for the brand.

```python
VocabularyRules(
    preferred=["scalable", "robust", "proven"],  # Words to use
    banned=["pivot", "synergy", "disrupt"],       # Words to avoid
    jargon_level="light",                         # "none" | "light" | "heavy"
)
```

## ScenarioTone

Scenario-specific tone guidance.

```python
ScenarioTone(
    scenario="incident",                    # Scenario name
    tone="transparent",                     # Tone descriptor
    instructions="Be direct about what happened.",  # Free-text guidance
)
```

## FormattingPrefs

Formatting preferences for brand voice output.

```python
FormattingPrefs(
    heading_style="sentence",   # "sentence" | "title"
    bullet_style="dash",        # "dash" | "numbered"
    citation_format="inline",   # "inline" | "footnote"
)
```

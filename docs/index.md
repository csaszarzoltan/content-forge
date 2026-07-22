# ContentForge Documentation

Welcome to the ContentForge brand voice customization documentation. This guide covers all 9 modules in the `brand_voice` package.

## Architecture

The package is organized in three tiers:

```
P0 — Core (no internal dependencies)
├── models.py       — VoiceProfile data models (Pydantic)
├── parser.py       — BRAND_VOICE.md markdown parser
├── presets.py      — Built-in + custom preset manager
└── templates.py    — Scenario template engine

P1 — Enhancement (depends on P0)
├── multi_brand.py  — Multi-brand VoiceManager with persistence
├── prompt_binding.py — Content-type-aware prompt generation
└── scoping.py      — User/project voice resolution

P2 — Advanced (depends on P0)
├── compliance.py   — Compliance scoring (readability, banned terms)
└── extraction.py   — Voice profile inference from text samples
```

## Getting Started

### Installation

```bash
pip install contentforge
```

Or from source:

```bash
git clone https://github.com/csaszarzoltan/contentforge.git
cd contentforge
pip install -e ".[dev]"
```

### First steps

```python
from brand_voice.presets import PresetManager

# Load a built-in preset
mgr = PresetManager()
profile = mgr.get_preset("formal")

# Generate an LLM-friendly system prompt
print(profile.to_system_prompt())

# Render a scenario-specific template
from brand_voice.templates import TemplateEngine
engine = TemplateEngine()
print(engine.render("launch", profile))
```

## Module Guides

| Module | Doc | Key Exports |
|--------|-----|-------------|
| Models | [docs/models.md](models.md) | `VoiceProfile`, `VoiceAttribute`, `VocabularyRules`, `ScenarioTone`, `FormattingPrefs` |
| Parser | [docs/parser.md](parser.md) | `parse_brand_voice()`, `parse_brand_voice_string()`, `validate_brand_voice()` |
| Presets | [docs/presets.md](presets.md) | `PresetManager` |
| Templates | [docs/templates.md](templates.md) | `TemplateEngine` |
| Multi-Brand | [docs/multi-brand.md](multi-brand.md) | `VoiceManager` |
| Prompt Binding | [docs/prompt-binding.md](prompt-binding.md) | `PromptBinder` |
| Scoping | [docs/scoping.md](scoping.md) | `VoiceScope` |
| Compliance | [docs/compliance.md](compliance.md) | `ComplianceScorer`, `ComplianceResult` |
| Extraction | [docs/extraction.md](extraction.md) | `VoiceExtractor` |

## Additional Resources

- [README.md](../README.md) — Project overview and quick start
- [CHANGELOG.md](../CHANGELOG.md) — Version history
- [examples/](../examples/) — Runnable code examples

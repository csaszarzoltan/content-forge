# ContentForge

**AI-powered content platform with brand voice customization.**

[![Tests](https://img.shields.io/badge/tests-172%20passing-green)](https://github.com/csaszarzoltan/contentforge)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Parse, manage, and inject brand voice profiles into LLM prompts for consistent, brand-aligned content generation. Ships with 5 built-in voice presets, 5 scenario templates, compliance scoring, and automatic voice extraction from existing content.

---

## Features

| Tier | Module | Description |
|------|--------|-------------|
| P0   | **VoiceProfile models** | Pydantic-based profile with identity, attributes, vocabulary, scenario tones, formatting preferences |
| P0   | **Brand voice parser** | Parse structured markdown (BRAND_VOICE.md) into `VoiceProfile` instances with validation |
| P0   | **Preset manager** | 5 built-in presets (formal, casual, witty, empathetic, technical) + custom preset CRUD + remix |
| P0   | **Template engine** | 5 built-in scenario templates (incident, launch, support_reply, social_media, faq) with voice injection |
| P1   | **Multi-brand management** | `VoiceManager` with JSON persistence, brand CRUD, and per-scope active voice tracking |
| P1   | **Prompt binding** | `PromptBinder` with content-type-specific guidelines (email, landing page, social post, FAQ, support) |
| P1   | **Voice scoping** | `VoiceScope` with user-level and project-level voice resolution (project overrides user) |
| P2   | **Compliance scoring** | `ComplianceScorer` with Flesch-Kincaid readability, banned term detection, vocabulary scoring |
| P2   | **Voice extraction** | `VoiceExtractor` that infers a voice profile from existing text samples via keyword and style analysis |

## Installation

```bash
pip install contentforge
```

Requires Python 3.11+ and Pydantic >= 2.0.

### Development

```bash
git clone https://github.com/csaszarzoltan/contentforge.git
cd contentforge
pip install -e ".[dev]"
pytest          # 172 tests pass
ruff check src/ # zero violations
```

## Quick Start

### 1. Load a preset and generate an LLM system prompt

```python
from brand_voice.presets import PresetManager

mgr = PresetManager()
profile = mgr.get_preset("formal")
prompt = profile.to_system_prompt()
print(prompt)
```

This generates a complete system prompt block with the formal brand voice rules, ready to send to any LLM.

### 2. Render a scenario-specific template

```python
from brand_voice.presets import PresetManager
from brand_voice.templates import TemplateEngine

mgr = PresetManager()
engine = TemplateEngine()
profile = mgr.get_preset("witty")

# Render an incident response with the witty voice
result = engine.render("incident", profile)
print(result)
```

### 3. Score content for brand compliance

```python
from brand_voice.presets import PresetManager
from brand_voice.compliance import ComplianceScorer

mgr = PresetManager()
profile = mgr.get_preset("formal")
scorer = ComplianceScorer(profile)

result = scorer.score("We are pleased to announce our scalable platform.")
print(f"Compliance score: {result.overall_score}")
print(f"Banned terms: {result.banned_terms_found}")
```

### 4. Extract a voice profile from existing content

```python
from brand_voice.extraction import VoiceExtractor

extractor = VoiceExtractor(min_words=50)
samples = [
    "Our scalable platform helps enterprise teams collaborate better.",
    "We provide proven solutions for modern businesses.",
]
profile = extractor.extract(samples)
print(f"Inferred formality: {profile.attributes[0].value}")
print(f"Preferred words: {profile.vocabulary.preferred}")
```

## Module Reference

See the [docs/](docs/) directory for detailed per-feature guides:

| Guide | Content |
|-------|---------|
| [Models](docs/models.md) | `VoiceProfile`, `VoiceAttribute`, `VocabularyRules`, `ScenarioTone`, `FormattingPrefs` |
| [Parser](docs/parser.md) | `parse_brand_voice()`, `parse_brand_voice_string()`, `validate_brand_voice()` |
| [Presets](docs/presets.md) | `PresetManager` — built-in presets, custom CRUD, remix |
| [Templates](docs/templates.md) | `TemplateEngine` — scenario templates, `render()`, `render_system_prompt()` |
| [Multi-Brand](docs/multi-brand.md) | `VoiceManager` — brand CRUD, scope isolation, active voice tracking |
| [Prompt Binding](docs/prompt-binding.md) | `PromptBinder` — content-type-specific prompt generation |
| [Scoping](docs/scoping.md) | `VoiceScope` — user/project voice resolution, persistence |
| [Compliance Scoring](docs/compliance.md) | `ComplianceScorer` — readability, banned terms, vocabulary scoring |
| [Voice Extraction](docs/extraction.md) | `VoiceExtractor` — infer profiles from sample text |

## Examples

Ready-to-run examples in [examples/](examples/):

- [basic_usage.py](examples/basic_usage.py) — End-to-end walkthrough
- [presets.py](examples/presets.py) — Preset management CRUD
- [compliance.py](examples/compliance.py) — Compliance scoring with different texts

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## Tests

```bash
pytest              # 172 tests (interface + behavioral)
pytest -v           # verbose mode
python -m pytest    # same runner
```

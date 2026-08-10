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
| Transcreation | [docs/transcreation.md](transcreation.md) | `TranscreationService`, `LocaleData`, `LocaleFormatter` |
| Video Pipeline | [docs/video-pipeline.md](video-pipeline.md) | `VideoJobStore`, `TTSProvider`, `OpenAITTSProvider`, `split_sections`, `assemble_scenes`, `split_at_section_boundaries` |
| Video Platform Analytics | [docs/video-analytics.md](video-analytics.md) | `VideoAnalyticsService`, `YouTubeClient`, `TikTokClient`, `InstagramClient`, `VideoAPIClient` |

## Additional Resources

- [README.md](../README.md) — Project overview and quick start
- [CHANGELOG.md](../CHANGELOG.md) — Version history
- [Analytics Dashboard](analytics-dashboard.md) — Content performance tracking, scoring, export, trends
- [AI Visibility](ai-visibility.md) — AI assistant mentions/citations, share of voice, referral traffic, Chart.js dashboard
- [Transcreation](transcreation.md) — Cultural risk detection, locale formatting, side-by-side review, preflight gate, export
- [Video Pipeline](video-pipeline.md) — Blog/script → scenes → voiceover → MP4, job state machine, per-scene retry, partial export
- [Video Platform Analytics](video-analytics.md) — YouTube/TikTok/Instagram performance tracking, trend charts, optimal posting-time heatmaps, per-video drill-down, CLI
- [Social Media Publishing](social-publishing.md) — Platform connectors, publish API, rate limiting
- [examples/](../examples/) — Runnable code examples

## Product workspaces

- [Content operations workspaces](product-workspaces.md)
- [Implementation research](research/APPLICATION_RESEARCH_REPORT.md)
- [Feature requirements index](research/FEATURE_REQUIREMENTS_INDEX.md)

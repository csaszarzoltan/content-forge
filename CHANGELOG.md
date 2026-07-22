# Changelog

## [0.2.0] — 2026-07-22

### Features
- **Brand voice customization system** — Parse, manage, and inject brand voice profiles into LLM prompts
- **VoiceProfile model** — Pydantic-based profile with attributes, vocabulary rules, scenario tones, and formatting preferences
- **Brand voice parser** — Parse YAML/JSON brand voice definitions with validation and error reporting
- **Preset manager** — Load, list, and manage built-in and custom brand voice presets
- **Template engine** — Render Jinja-style templates with brand voice context injection
- **Multi-brand management** — VoiceManager for CRUD operations across multiple brand profiles
- **Prompt binder** — Bind voice profiles to content prompts with system prompt generation
- **Voice scoping** — Per-user and per-project voice scope resolution with config persistence
- **Compliance scoring** — Score content against brand voice compliance (banned terms, vocabulary, readability)
- **Voice extraction** — Extract brand voice profiles from sample text via keyword analysis

### Tests
- 171 brand voice tests (models, parser, presets, templates, multi-brand, prompt binding, scoping, compliance, extraction)
- 1 existing contentforge test — all 172 tests pass

## [0.1.0] — 2026-07-22

### Features
- Initial ContentForge scaffold with FastAPI

# Changelog

## [0.3.1] — 2026-07-22

### Documentation
- Merged API documentation from scratch workspace to master — 6 new docs: API Overview, Content Generation API, Brand Voice API, Scheduling API, Analytics API, Deployment Guide
- Added 5 new API example scripts: api_client.py, api_brand_voice.py, api_content_generation.py, api_scheduling.py, api_analytics.py
- Updated README.md: test badge (172 → 315), API endpoint reference in Module Reference table, API Quick Start section, expanded Examples list

## [0.3.0] — 2026-07-22

### Features
- **FastAPI REST API** — Full set of REST endpoints for brand voice CRUD, content generation, scheduling, and analytics
- **Async SQLAlchemy database** — PostgreSQL-ready async engine with declarative models, sessions, and migration support
- **Data models** — BrandVoice, Generation, ScheduledPost, ContentAnalytics ORM models with soft-delete and version tracking
- **Pydantic schemas** — 15+ request/response validation schemas across all domains
- **LLM provider service** — OpenAI-compatible provider with configurable model, base URL, and error handling
- **Content generator service** — Template-driven generation with brand voice injection and validation
- **Scheduler service** — In-memory scheduling service with lifecycle management and status tracking
- **Analytics service** — Content performance metrics tracking with summary aggregation
- **Configuration system** — Pydantic-settings based config with environment variable loading and singleton access
- **Railway deployment** — Dockerfile + railway.json for containerized deployment, HEALTHCHECK endpoint, CORS middleware
- **Documentation** — 10 new docs pages covering all modules (brand voice, compliance, extraction, models, multi-brand, parser, presets, prompt-binding, scoping, templates)
- **Usage examples** — basic_usage.py, compliance.py, presets.py with real API workflows

### Fixes
- Guard against empty `response.choices` list in LLM provider — raises `ValueError` instead of `IndexError` on content filter or rate limit edge cases

### Tests
- 143 new tests across 8 test modules (analytics, brand_voice CRUD, config, content generation, database, DB models, dependencies, scheduling)
- 285 pass, 27 expected behavioral failures (stub-replaced-by-real-implementation), 3 skipped — ruff clean

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

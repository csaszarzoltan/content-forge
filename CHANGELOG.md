# Changelog

## [0.8.0] — 2026-07-27

### Features
- **A/B Testing Framework** — Full statistical A/B test lifecycle with chi-squared significance calculator
- **ABTestService** — Service layer covering create, track track events, conclude with winner, and result retrieval
- **AbStatsService** — Chi-squared significance calculator using scipy for statistical validity
- **6 REST API endpoints** — `POST /api/v1/ab/experiments`, `POST /api/v1/ab/experiments/{id}/track`, `GET /api/v1/ab/experiments/{id}/results`, `POST /api/v1/ab/experiments/{id}/conclude`, `GET /api/v1/ab/experiments`, `GET /api/v1/ab/dashboard`
- **Dashboard aggregation** — Summary endpoint for experiment overview with status breakdown

### Tests
- 109 new A/B testing tests covering all service layers, statistical calculations, and API endpoints
- Total: 1318 passing, 27 skipped

### Docs
- Added social media publishing documentation (api-overview, dedicated guide)
- Updated README with social publishing feature row and corrected test count badge

### Fixes
- Replaced truncated JWT token examples with `***` placeholders in API docs

## [0.7.0] — 2026-07-26

### Features
- **Social Media Auto-Publishing** — Full create→optimize→publish workflow with platform connectors
- **SocialMediaConnector ABC** — Abstract base for platform adapters (publish, preview, validate_credentials)
- **Twitter/X Publisher** — OAuth 1.0a signed API v2 posting with 280-char truncation and rate limiting
- **LinkedIn Publisher** — OAuth 2.0 UGC post creation with text/link share support
- **Rate Limiting** — Token bucket algorithm per platform (Twitter: 300/15min, LinkedIn: 750/day)
- **PlatformToken Model** — Encrypted OAuth token storage per user per platform via Fernet
- **PublishService** — Orchestrator: resolve connector → rate limit → publish → status update → retry
- **New API endpoint** — `POST /api/v1/publish` — publish content to social platforms
- **Publishing Status Tracking** — scheduled → publishing → published | failed lifecycle

### Dependencies
- Promoted `httpx` from dev to core dependency (required for async HTTP calls to platform APIs)
- Added `cryptography` (required for Fernet token encryption)

### Tests
- 128 new tests across connectors, rate limiter, publish endpoint, publish service, integration
- Total: 1209 passing, 27 skipped — ruff clean

## [0.6.0] — 2026-07-26

### Features
- **SEO Content Optimization Engine** — Full SEO analysis pipeline with 6 specialized services
- **SEO Analyzer** — Keyword density, word/sentence/paragraph counting, content quality scoring (thin/adequate/comprehensive)
- **Readability Scorer** — Flesch-Kincaid Grade Level, Coleman-Liau Index, Flesch Reading Ease with reading level classification
- **Meta Tag Generator** — Title tag and meta description truncation with "..." suffix, Open Graph tags (og:title, og:description, og:url, og:type), canonical URL normalization
- **SERP Preview Generator** — Google-style search result HTML snippets with HTML escaping, breadcrumb navigation from URL paths
- **JSON-LD Generator** — Schema.org Article, BlogPosting, and WebPage structured data markup
- **Internal Linker** — TF-IDF scoring for term relevance, content-based link suggestions with relevance ranking (max 10 suggestions)
- **New API endpoint** — `POST /api/v1/seo/analyze` — full SEO analysis: content score, readability, meta tags, SERP preview, JSON-LD, internal link suggestions

### Dependencies
- Added `textstat` (>=0.7) — readability scoring formulas

### Tests
- 229 new SEO tests (interface contracts + behavioral verification across all 6 services and API endpoint)
- 1209 total tests — 229 SEO + 980 non-auth regression passing, 27 skipped, ruff clean

### Features
- **Multi-Language Content Generation Engine** — Full multi-language pipeline with language detection, per-language prompt templates, translation quality scoring, and multilingual scheduling
- **Language detection** — Auto-detect input language via `fast-langdetect` with confidence scoring, explicit override, and batch detection
- **Per-language prompt templates** — `PromptTemplateRegistry` with language-scoped templates, brand voice adaptation, and fallback chain (missing language → English + translate wrapper)
- **Translation quality scoring** — BLEU and chrF scoring via `sacrebleu` for automated quality assessment
- **Translation service** — Dual path (LLM generation + NMT translation) with scoring pipeline
- **Multilingual scheduling** — Timezone-aware publishing, language-specific calendars, auto-translate on schedule, cross-language dependency chains
- **New API endpoints** — `POST /api/v1/content/translate` (translate content), `GET /api/v1/languages` (list supported languages with caching via ETag)
- **Brand voice templates** — Per-language brand voice templates (de_blog, fr_social, ja_email) with locale-appropriate voice adaptation

### Documentation
- Added 4 new docs: language-detection.md, prompt-templates.md, translation-pipeline.md, scheduling.md
- Added multilingual_generation.py example — end-to-end workflow from detection to scheduling
- Updated README.md with 🌐 Multi-Language Content Engine section
- Updated docs/api-overview.md and docs/deployment.md for multi-language endpoints and configuration

### Tests
- 380 new tests across 11 test modules (language detection, models, endpoint, translation, prompt templates, scoring, scheduling, auto-detection)
- 760 passing, 27 skipped — ruff clean

## [0.4.0] — 2026-07-23

### Features
- **JWT authentication** — Full auth system with register, login, token refresh, and current-user retrieval
- **User accounts** — User model with email, password (bcrypt-hashed), display name, role, and organization_id
- **Multi-tenant scoping** — `scope_query_by_user` dependency injects `current_user.id` into session for automatic query filtering
- **Token refresh** — Refresh endpoints issue new token pairs and update stored hashes. Previous refresh tokens remain valid until JWT expiry (30 days); add a blacklist for full rotation in production.
- **Optional auth** — `get_optional_current_user` dependency returns `None` for unauthenticated requests, ready for mixed public/protected endpoints

### Documentation
- Added Authentication section to README.md — registration, login, API usage, token refresh, multi-tenant scoping with runnable Python examples
- Added JWT config to .env.example — JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
- Added auth endpoints to docs/api-overview.md — POST /auth/register, POST /auth/login, POST /auth/refresh, GET /auth/me
- Added JWT environment variables to docs/deployment.md

### Tests
- 26 new auth integration tests (service layer + HTTP endpoints) — 380 total, zero failures
- Test badge updated to 380 passing

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

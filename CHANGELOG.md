# Changelog

## [0.13.0] - 2026-08-05

### Features
- Added working hash-based navigation for all ten sidebar workspaces.
- Added routed My Work, Campaigns, Content, Calendar, Approvals, Localization, Analytics, Brand Governance, Connections, and Admin pages.
- Added a consolidated workspace overview API backed by real SQLite collections.
- Preserved campaign cockpit, versioned editor, and request-review flows inside the routed shell.

### Fixes
- Replaced all inert `href="#"` sidebar placeholders with real routes and active states.
- Added Python 3.11 and 3.12 SciPy dependency markers.
- Added a Windows-friendly backend runner that watches only `src`, preventing node_modules reload loops.

### Tests
- Added React navigation contracts and backend workspace integration coverage.


## [0.12.0] - 2026-08-05

### Features
- Added revision-bound approval requests and human decisions.
- Added approval audit events and asset-level audit API.
- Added Request review to the React content editor.

### Safety
- Editing an approved or pending revision supersedes its approval automatically.
- Stale approval decisions return HTTP 409 instead of approving changed content.
- High-risk self-approval remains blocked.

### Tests
- Added domain, real SQLite, API, stale-decision, request-changes, and audit lifecycle coverage.


## [0.11.0] - 2026-08-05

### Features
- Added a responsive Vite + React + TypeScript Campaign Cockpit with polished onboarding, campaign context, readiness blockers, asset pipeline, content editor, and friendly recovery UI.
- Added durable campaign briefs, editable assets, immutable revision history, restore support, and optimistic autosave conflict protection.
- Added explainable channel readiness and a unified My Work queue for pending approvals and failed publications.

### Fixes
- Preserved compatibility with existing SQLite workspace databases through additive schema migration.
- Normalized short invalid AI visibility queries to the documented provider error contract.
- Pinned bcrypt to the passlib-compatible release used by the verified authentication suite.

### Tests
- Added domain, real SQLite I/O, API contract, revision conflict, readiness, queue, and frontend helper tests.
- Verified the complete Python suite and the frontend test, lint, and production build pipelines.

### Docs
- Documented the v0.11 user flow, frontend commands, and every new API endpoint.
- Added `FEATURES-DONE.md` for machine-readable delivery tracking.

## [0.14.0] — 2026-08-02

### Features
- **AI Visibility Metrics** — track mentions, citations, share of voice, and referral traffic from AI assistants (ChatGPT, Perplexity, Gemini, Google AI Overviews)
- **Per-content snapshot** — `GET /api/v1/ai-visibility/{content_id}` returns summary cards, per-engine metrics for all four engines (zero-filled when no data), sentiment, and a daily time series over a 7/30/90-day window
- **Trends feed** — `GET /api/v1/ai-visibility/trends` returns a Chart.js-ready series (`dates` → labels, `series` → datasets) with per-metric totals, filterable by engine and metric
- **Referral ingestion** — `POST /api/v1/ai-visibility/referral` records an AI-referred visit webhook-style (201), unauthenticated, with optional conversion tracking
- **On-demand refresh** — `POST /api/v1/ai-visibility/{content_id}/refresh` runs one poll cycle for a content piece and returns a `PollResult`; works with the background poller disabled
- **Engine providers** — `AIEngineProvider` abstraction over all four engines: Perplexity and Gemini via real HTTP APIs (`sonar` / `gemini-2.0-flash`), ChatGPT and Google AI Overviews via structured LLM prompts; unconfigured providers degrade gracefully and provider errors never leak credentials
- **Background polling** — opt-in asyncio loop (`AI_VISIBILITY_POLL_ENABLED=true`) with configurable interval and queries per content; per-engine failures are collected in `PollResult.errors` and never abort the cycle
- **Four new tables** — `ai_raw_mentions` (append-only mention log), `ai_engine_metrics` (per-content/per-engine daily aggregates), `ai_referral_traffic` (AI-referred visits), `ai_trend_aggregates` (cross-content daily rollups)

### Fixes
- API keys no longer leak into provider error messages on HTTP/request failures (Perplexity/Gemini error paths report generic status-only text)
- `days` is validated (7/30/90) before any date arithmetic, so extreme values return 422 instead of an unhandled `OverflowError`
- Poller loop exceptions are logged so a silently dead poller is diagnosable
- `AI_VISIBILITY_CONTENT_BASE_URL` is honored when building canonical content URLs for citation detection
- `POST /{content_id}/refresh` is registered in OpenAPI

### Tests
- 157 passing AI visibility tests (metrics, models, schemas, providers, poller, service, API, review fixes); full suite **1966 passing, 27 skipped, 1 failed** — the single failure is the documented pre-written spec contradiction accepted by tech-lead review

### Docs
- New [AI Visibility guide](docs/ai-visibility.md) — metric definitions, data model, provider configuration, API reference, Chart.js dashboard example
- README updated: AI visibility feature row and section, module reference entry, examples list, test badge (1966 passing)
- New [AI visibility example](examples/api_ai_visibility.py) plus 4 AI visibility client methods in `examples/api_client.py`
- API overview, deployment environment table, docs index, and `.env.example` updated with AI visibility endpoints and configuration

## [0.13.0] - 2026-08-02
- Reworked Publish Center around navigable delivery batches.
- Added per-channel delivery details and remote identifiers.
- Added safe retry requests scoped only to failed or retryable channels.
- Preserved successful delivery records to prevent duplicate publication.
- Added TDD coverage for partial-success recovery and fully published batches.

## [0.12.0] - 2026-08-02
- Added actionable approval detail pages and decision forms.
- Added approval validation, accessible errors, and high-risk self-approval protection in browser flows.
- Continued campaign workspace navigation, user-centered states, attention summaries, and contextual recovery.

## [0.10.0] — 2026-08-01

### Features
- **Platform Validation Engine** — validate content against real platform constraints before publishing; supports Twitter/X, LinkedIn, Instagram, Facebook, and TikTok
- **Constraint registry** — JSON-backed registry (`src/constraints/data/registry.json`) with text, image, video, and carousel constraints per platform; versioned and machine-readable
- **Validation API** — `POST /api/v1/validate` validates a single piece of content against a target platform; `POST /api/v1/validate/cross-platform` validates across all platforms simultaneously
- **Constraint query API** — `GET /api/v1/constraints` returns all platforms; `GET /api/v1/constraints/{platform}` returns constraints for one platform
- **Constraint preview** — `GET /api/v1/constraints/{platform}/preview` renders a human-readable summary of platform limits
- **Cross-platform validation** — detect content that fails any platform's constraints in a single call; response includes per-platform pass/fail with detailed violation messages
- **Validation engine service** — `ConstraintValidator` service with structured error reporting, constraint normalization, and platform-aware scoring

### Fixes
- Constraint validator and router updates for edge cases in media constraint checking and error message formatting
- Remediated main-profile session pollution in test suite (pytest markers)

### Tests
- 100+ new validation tests across platform registry, validation engine, and validation API modules; full suite **1783 passing, 27 skipped, 0 failed** — ruff clean
- Platform registry tests verify all 5 platforms load correctly with expected constraint shapes
- Validation engine tests cover text limits, image formats, video constraints, carousel rules, and cross-platform aggregation
- Validation API tests verify HTTP status codes, error response schemas, and cross-platform endpoint behavior

### Docs
- README updated: Platform Validation Engine feature added to feature table, test badge updated (1783 passing)
- New [Platform Validation guide](docs/platform-validation.md) — overview, supported platforms, API reference, constraint registry format, usage examples

## [0.9.0] — 2026-07-31

### Features
- **Content Performance Analytics Dashboard** — event-log based analytics that completes the create → optimize → publish → analyze pipeline
- **Event tracking API** — `POST /api/v1/analytics/track` appends impressions, clicks, shares, comments, conversions, and read-time events to the `analytics_events` table (404 for unknown generation; 422 for invalid channel or `occurred_at` >24h in the future)
- **Dashboard API** — `GET /api/v1/analytics/dashboard` aggregates metrics over a date window (default 30d) with channel/content-type breakdowns, top-5 content, and a daily time series
- **Per-content analytics** — `GET /api/v1/analytics/content/{id}` returns performance, compliance snapshot, and per-channel breakdown for one generation
- **Channel comparison** — `GET /api/v1/analytics/channels` sorts channels by any metric (`impressions`, `clicks`, `shares`, `comments`, `conversions`, `engagement_rate`) and reports the best channel
- **Content scoring** — `GET /api/v1/analytics/score/{id}` computes a deterministic weighted score (`0.35·engagement + 0.25·seo + 0.20·readability + 0.20·compliance`) with A–F grades; missing sub-scores drop out and weights renormalize
- **A/B test correlation** — `GET /api/v1/analytics/ab-results` merges A/B variant results with real analytics conversion data and a chi-squared significance note
- **Export** — `GET /api/v1/analytics/export` exports daily aggregates as CSV or JSON (stdlib only, no new dependencies)
- **Trends & anomalies** — `GET /api/v1/analytics/trends` (7d/30d/90d daily series with anomaly flags) and `GET /api/v1/analytics/anomalies` (z-score detection, |z| ≥ 2.0, ≥ 7 points required)
- **Content operations workspaces** — six accessible browser workspaces: campaign creation, governance approvals, explainable brand voice, channel preview and publish recovery, localization QA, and provenance auditing
- **Versioned `/api/v1` automation contracts** for campaign, approval, publish batch, localization, and provenance resources
- **SQLite-backed workflow state** with explicit transitions, partial-success preservation, idempotent channel retry selection, conflict-of-interest approval protection, locale quality gates, and secret-redacted provenance export
- **Responsive workspace styling** with skip navigation, live status messaging, visible focus, mobile reflow, empty states, and recovery guidance

### Tests
- 237 new analytics tests (184 interface + 53 behavioral) across 5 modules; full suite **1541 passing, 27 skipped, 0 failed** — ruff clean
- Handler-level regression tests pin the POST /track error mapping (unknown generation → 404, invalid channel / future `occurred_at` → 422, valid → 201)
- Deterministic product workflow tests and offline fallback behavior for language detection and readability scoring

### Docs
- New [Analytics Dashboard guide](docs/analytics-dashboard.md) — setup, all 9 endpoints with request/response examples, content scoring explanation, channel comparison usage, A/B test correlation, export options, historical trends, anomaly detection
- README updated: analytics dashboard feature section, module reference, examples list, test badge (1541 passing)
- Rewrote `examples/api_analytics.py` for the v0.9.0 analytics API; `examples/api_client.py` gained 9 analytics client methods
- `docs/analytics.md` marked superseded (legacy stub routes removed in favor of `/api/v1/analytics`)

### Fixes
- `POST /api/v1/analytics/track` now returns **422** (not 404) for invalid channel and `occurred_at` more than 24 hours in the future; 404 is reserved for unknown generations
- Repaired the malformed `pyproject.toml`, removed duplicate dependencies, and aligned application and package versions at 0.9.0
- Constrained `bcrypt` below version 5 for Passlib compatibility
- Replaced runtime NLTK corpus dependency in readability scoring with deterministic local formulas
- Added a cached offline language detector fallback when the optional model cannot be downloaded

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

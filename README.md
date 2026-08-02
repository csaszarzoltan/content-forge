# ContentForge

**AI-powered content platform with brand voice customization.**

[![Tests](https://img.shields.io/badge/tests-1783%20passing-green)](https://github.com/csaszarzoltan/contentforge)
[![Deployed](https://img.shields.io/badge/deployed-Railway-%230B4B5A)](https://contentforge-production-7e96.up.railway.app)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Parse, manage, and inject brand voice profiles into LLM prompts for consistent, brand-aligned content generation. Ships with 5 built-in voice presets, 5 scenario templates, compliance scoring, automatic voice extraction from existing content, and a full REST API.

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
| P0   | **REST API** | FastAPI endpoints for brand voice CRUD, content generation, scheduling, and analytics |
| P1   | **LLM integration** | OpenAI-compatible provider with configurable model, base URL, and content guard |
| P1   | **Content generation** | Template-driven generation with brand voice injection and validation |
| P1   | **Scheduling** | In-memory scheduling service with lifecycle management and status tracking |
| P0   | **Analytics Dashboard** | Event-log based content performance tracking — impressions, clicks, engagement, channel comparison, content scoring, A/B correlation, CSV/JSON export, trends + anomaly detection |
| P1   | **Social Media Publishing** | Pluggable platform connectors (Twitter/X, LinkedIn) with rate limiting, retry, and status tracking |
| P0   | **Platform Validation Engine** | Validate content against real platform constraints (Twitter/X, LinkedIn, Instagram, Facebook, TikTok) before publishing |

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
pytest          # 1783 tests pass
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

### 5. Use the REST API

```python
import httpx

# List all brand voices
resp = httpx.get("http://localhost:8000/brand-voices")
print(resp.json())

# Generate content with a brand voice
resp = httpx.post("http://localhost:8000/content/generate", json={
    "prompt": "Write a product announcement",
    "brand_voice_id": 1,
    "template": "launch",
})
print(resp.json())
```

### 6. Validate content against platform constraints

```bash
# Validate a tweet against Twitter/X constraints
curl -X POST http://localhost:8000/api/v1/validate \
  -H 'Content-Type: application/json' \
  -d '{"platform": "twitter", "content": "Check out our new feature!", "media": []}'

# Cross-platform validation
curl -X POST http://localhost:8000/api/v1/validate/cross-platform \
  -H 'Content-Type: application/json' \
  -d '{"content": "Longform content here...", "media": []}'
```

See the [Platform Validation guide](docs/platform-validation.md) for the full API reference and constraint registry format.

See the [API Overview](docs/api-overview.md) for the complete endpoint reference.

## 🌐 Multi-Language Content Engine

ContentForge supports **full multi-language content generation** — detect input language, select per-language prompt templates, score translation quality, and schedule cross-language publishing.

### Features

| Tier | Module | Description |
|------|--------|-------------|
| P0   | **Language detection** | Auto-detect input language via `fast-langdetect` with confidence scoring, explicit override, and batch detection |
| P0   | **Per-language prompt templates** | `PromptTemplateRegistry` with language-scoped templates, brand voice localization, and English fallback |
| P0   | **Translation scoring** | BLEU + chrF scoring via `sacrebleu` for automated translation quality assessment |
| P1   | **Translation service** | Dual path (LLM generation in target language + NMT-style translation) with quality gate |
| P1   | **Multilingual scheduling** | Timezone-aware publishing, language-specific calendars, auto-translate on schedule, dependency chains |
| P0   | **Languages API** | `GET /api/v1/languages` — list supported languages with ETag-based caching |
| P0   | **Translate API** | `POST /api/v1/content/translate` — translate content between languages with quality scoring |

### Usage

```python
# Language detection
from contentforge.multilang import LanguageDetector
detector = LanguageDetector()
result = detector.detect("I want a blog post about cloud computing")
print(result.language)   # "en"

# Per-language template
from contentforge.multilang import MultiLangTemplateManager
tm = MultiLangTemplateManager()
messages = tm.render("blog-post", language="hu", variables={
    "topic": "Felhőalapú migráció",
    "audience": "IT-vezetők",
    "tone": "szakértői",
    "word_count": 800,
})

# Translation quality scoring
from contentforge.multilang.translation import QualityScorer
scorer = QualityScorer()
score = scorer.score("en", "hu", "Cloud migration reduces costs.",
                     "A felhőalapú migráció csökkenti a költségeket.")
print(f"BLEU: {score.bleu:.3f}, Passed: {score.passed}")

# Multi-language scheduling
scheduler = MultilingualScheduler()
await scheduler.schedule_multilang(
    source_generation_id="gen_abc",
    source_language="en",
    target_languages=["de", "hu"],
    base_publish_at=datetime(2026, 8, 16, 14, 0, tzinfo=timezone.utc),
    stagger_hours=6,
)
```

See the per-feature guides in [docs/](docs/) for details:
- [Language Detection](docs/language-detection.md)
- [Prompt Templates](docs/prompt-templates.md)
- [Translation Pipeline](docs/translation-pipeline.md)
- [Multilingual Scheduling](docs/multilingual-scheduling.md)

## Authentication

ContentForge uses **JWT-based authentication** with access and refresh tokens. All API endpoints require a valid Bearer token (except register and login).

### Setup

Set these environment variables (or add to `.env`):

```bash
JWT_SECRET=your-256-bit-secret             # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_ALGORITHM=HS256                         # Signing algorithm
ACCESS_TOKEN_EXPIRE_MINUTES=15              # Short-lived access tokens
REFRESH_TOKEN_EXPIRE_DAYS=30                # Long-lived refresh tokens
```

### 1. Register a user

```python
import httpx

base_url = "http://localhost:8000"

# Register a new account
resp = httpx.post(f"{base_url}/auth/register", json={
    "email": "alice@example.com",
    "password": "secure-password-8chars",
    "display_name": "Alice",
})
print(resp.status_code)   # 201
print(resp.json())
# {
#   "id": "a1b2c3d4-...",
#   "email": "alice@example.com",
#   "display_name": "Alice",
#   "role": "user",
#   "organization_id": None,
#   "created_at": "2026-07-23T17:39:00+00:00"
# }
```

The password is hashed with **bcrypt** before storage and is never returned in responses. Duplicate emails return `409 Conflict`.

### 2. Login to obtain a JWT token pair

```python
# Login with email + password
resp = httpx.post(f"{base_url}/auth/login", json={
    "email": "alice@example.com",
    "password": "secure-password-8chars",
})
print(resp.status_code)   # 200
data = resp.json()
print(data)
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIs...",
#   "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
#   "token_type": "bearer",
#   "expires_in": 900      # seconds (15 min)
# }

access_token = data["access_token"]
refresh_token = data["refresh_token"]
```

- **Access token** — short-lived (default 15 min). Sent with every authenticated request.
- **Refresh token** — long-lived (default 30 days). Used to get new token pairs without re-logging in.

### 3. Use the token in API requests

Pass the access token via the `Authorization` header:

```python
headers = {"Authorization": f"Bearer {access_token}"}

# Get the authenticated user's profile
resp = httpx.get(f"{base_url}/auth/me", headers=headers)
print(resp.status_code)   # 200
print(resp.json())
# {
#   "id": "a1b2c3d4-...",
#   "email": "alice@example.com",
#   "display_name": "Alice",
#   "role": "user",
#   "organization_id": None,
#   "created_at": "2026-07-23T17:39:00+00:00"
# }

# Protected API endpoints also use the same header:
resp = httpx.get(f"{base_url}/brand-voices", headers=headers)
print(resp.json())

# Without a token, protected endpoints return 401:
resp = httpx.get(f"{base_url}/auth/me")
print(resp.status_code)   # 401
print(resp.json())
# {"detail": "Not authenticated"}
```

Invalid or expired tokens return `401 Unauthorized` with a `WWW-Authenticate: Bearer` header.

### 4. Refresh tokens

When the access token expires, use the refresh token to get a fresh pair:

```python
resp = httpx.post(f"{base_url}/auth/refresh", json={
    "refresh_token": refresh_token,
})
print(resp.status_code)   # 200
data = resp.json()

new_access_token = data["access_token"]
new_refresh_token = data["refresh_token"]   # new token issued; old one still valid until JWT expiry
```

**Token rotation** — each refresh call issues a new refresh token and updates the stored hash, but the previous refresh token remains valid until its JWT expiry (default 30 days). For production deployments, add a token blacklist or check the stored hash on refresh to fully invalidate compromised tokens.

### 5. Full end-to-end workflow

```python
import httpx

base_url = "http://localhost:8000"

# Step 1: Register
httpx.post(f"{base_url}/auth/register", json={
    "email": "bot@example.com", "password": "pass-1234-5678",
})

# Step 2: Login
login = httpx.post(f"{base_url}/auth/login", json={
    "email": "bot@example.com", "password": "pass-1234-5678",
}).json()
token = login["access_token"]

# Step 3: Use token for protected endpoints
headers = {"Authorization": f"Bearer {token}"}
me = httpx.get(f"{base_url}/auth/me", headers=headers).json()
print(f"Logged in as {me['display_name']} ({me['role']})")

# Step 4: Refresh when token expires
new_tokens = httpx.post(f"{base_url}/auth/refresh", json={
    "refresh_token": login["refresh_token"],
}).json()
print(f"New access token: {new_tokens['access_token'][:20]}...")
```

### Multi-tenant scoping

ContentForge supports **multi-tenant isolation** through the `organization_id` field on each user:

| Field | Type | Purpose |
|-------|------|---------|
| `organization_id` | `str \| None` | Groups users into tenants. Set during registration or by an admin. |
| `role` | `str` | Access level — `"user"` (default) or `"admin"`. |

**How scoping works:**

1. When a user authenticates, the `get_current_user` dependency extracts their identity from the JWT.
2. The `scope_query_by_user` dependency injects `current_user.id` into the database session's `info` dict (`db.info["current_user_id"]`).
3. Downstream CRUD endpoints that consume this dependency automatically filter queries by user ID or organization ID, ensuring users only see their own data.

```python
# Protected route using user-scoped session:
@router.get("/brand-voices")
async def list_brand_voices(
    db: AsyncSession = Depends(scope_query_by_user),
    current_user: User = Depends(get_current_user),
):
    # db.info["current_user_id"] is set → queries auto-scope by user
    ...
```

**Best practices for multi-tenant apps:**

- Set `organization_id` at registration time (or via an admin endpoint)
- Use `scope_query_by_user` for all user-owned resources (brand voices, content, schedules, analytics)
- For admin-only operations, check `current_user.role == "admin"`
- Tokens don't encode tenant info — always look up the user's `organization_id` from the database

## 📱 Social Media Publishing

ContentForge can publish generated content directly to Twitter/X and LinkedIn through a pluggable connector architecture. Each platform has a dedicated connector implementing the `SocialMediaConnector` abstract base class with per-platform rate limiting, automatic retry on transient errors, and Fernet-encrypted credential storage.

### Features

| Tier | Module | Description |
|------|--------|-------------|
| P0   | **Platform connectors** | Twitter/X (OAuth 1.0a) and LinkedIn (OAuth 2.0) with character limit handling |
| P0   | **Rate limiting** | Token bucket algorithm per platform with configurable burst capacity and refill rate |
| P0   | **Publish API** | `POST /api/v1/publish` — publish content, `GET /api/v1/publish/{id}` — check status |
| P1   | **Token encryption** | Fernet symmetric encryption for platform OAuth tokens at rest |
| P1   | **Status tracking** | In-memory publish status with retry count and error messages |

### Usage

```python
import httpx

# Publish to Twitter
resp = httpx.post("http://localhost:8000/api/v1/publish", json={
    "generation_id": "gen_a1b2c3d4e5f6",
    "platform": "twitter",
    "text": "Check out our latest blog post!",
})
print(resp.json())
# {"publish_id": "pub_...", "status": "published", ...}

# Check status
status = httpx.get(f"http://localhost:8000/api/v1/publish/{resp.json()['publish_id']}")
print(status.json())
```

See the [Social Media Publishing Guide](docs/social-publishing.md) for full connector API, configuration, rate limit details, and production readiness considerations.

## 📊 Content Performance Analytics Dashboard

ContentForge v0.9.0 completes the create → optimize → publish → **analyze**
pipeline with an event-log based analytics layer. Track impressions, clicks,
shares, comments, conversions, and read-time events per content piece across
channels, then query aggregated dashboards, per-channel comparisons, A/B test
correlation, deterministic content scores, historical trends, and anomaly
detection — all under `/api/v1/analytics` with zero new dependencies.

### Features

| Tier | Module | Description |
|------|--------|-------------|
| P0   | **Event tracking** | `POST /api/v1/analytics/track` — append-only `analytics_events` log (impression, click, share, comment, conversion, read_time) |
| P0   | **Dashboard API** | `GET /api/v1/analytics/dashboard` — aggregated metrics, channel/content-type breakdowns, top content, daily time series |
| P0   | **Per-content analytics** | `GET /api/v1/analytics/content/{id}` — performance + compliance per generation |
| P0   | **Channel comparison** | `GET /api/v1/analytics/channels` — per-channel metrics sorted by any metric, with best-channel detection |
| P0   | **Content scoring** | `GET /api/v1/analytics/score/{id}` — deterministic weighted score (engagement 35%, SEO 25%, readability 20%, compliance 20%), grades A–F |
| P1   | **A/B test correlation** | `GET /api/v1/analytics/ab-results` — merges A/B variant results with real analytics conversion data + significance note |
| P1   | **Export** | `GET /api/v1/analytics/export` — CSV or JSON export of daily aggregates |
| P1   | **Trends & anomalies** | `GET /api/v1/analytics/trends` / `GET /api/v1/analytics/anomalies` — 7d/30d/90d series, z-score anomaly flags (|z| ≥ 2.0, ≥ 7 points) |

### Usage

```python
import httpx

base = "http://localhost:8000/api/v1/analytics"

# Track an event (no auth required)
httpx.post(f"{base}/track", json={
    "generation_id": "gen_a1b2c3d4e5f6",
    "channel": "twitter",
    "event_type": "click",
    "value": 1,
}).json()
# {"status": "ok", "event_id": "9750950a-..."}

# Query the dashboard (default window: last 30 days)
dash = httpx.get(f"{base}/dashboard").json()
print(dash["totals"])            # impressions, clicks, shares, ... engagement_rate

# Compare channels and export
httpx.get(f"{base}/channels", params={"metric": "engagement_rate"}).json()
export = httpx.get(f"{base}/export", params={"format": "csv"}).json()
open(export["filename"], "w").write(export["data"])
```

Error mapping: unknown `generation_id`/`test_id` → **404**; invalid channel,
metric, period, format, or inverted date window → **422**.

See the [Analytics Dashboard Guide](docs/analytics-dashboard.md) for the full
API reference with request/response examples, the scoring formula, and the
[analytics example](examples/api_analytics.py).

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
| [API Overview](docs/api-overview.md) | Complete REST endpoint reference (base URL, all endpoints, response schemas) |
| [Content Generation API](docs/content-generation.md) | `POST /content/generate` — template-driven content generation with voice injection |
| [Brand Voice API](docs/brand-voice-api.md) | `GET/POST/PUT/DELETE /brand-voices` — brand voice CRUD endpoints |
| [Scheduling API](docs/scheduling.md) | `GET/POST/PUT/DELETE /scheduling` — scheduled post management |
|| [Analytics Dashboard](docs/analytics-dashboard.md) | `POST /api/v1/analytics/track`, `GET /dashboard`, `/content/{id}`, `/channels`, `/ab-results`, `/score/{id}`, `/export`, `/trends`, `/anomalies` — event tracking, content scoring, channel comparison, A/B correlation |
|| [Deployment](docs/deployment.md) | Railway + Docker deployment guide, environment config, health checks |
|| [Social Media Publishing](docs/social-publishing.md) | Platform connectors, rate limiting, publish API, production readiness |
|| [Language Detection](docs/language-detection.md) | Auto-detect input language with fast-langdetect, confidence scoring, batch detection |
|| [Prompt Templates (per-language)](docs/prompt-templates.md) | Language-adaptive prompt templates, brand voice localization, fallback chain |
|| [Translation Pipeline](docs/translation-pipeline.md) | BLEU/chrF quality scoring, cross-language consistency, post-processing |
|| [Multilingual Scheduling](docs/multilingual-scheduling.md) | Timezone-aware publishing, language calendars, auto-translate, dependency chains |

## Examples

Ready-to-run examples in [examples/](examples/):

- [basic_usage.py](examples/basic_usage.py) — End-to-end walkthrough
- [presets.py](examples/presets.py) — Preset management CRUD
- [compliance.py](examples/compliance.py) — Compliance scoring with different texts
- [api_client.py](examples/api_client.py) — Full API client with brand voice CRUD, content generation, scheduling
- [api_brand_voice.py](examples/api_brand_voice.py) — Brand voice API endpoint usage
- [api_content_generation.py](examples/api_content_generation.py) — Content generation API workflows
- [api_scheduling.py](examples/api_scheduling.py) — Scheduled post management via API
- [api_analytics.py](examples/api_analytics.py) — Analytics dashboard walkthrough: track events, dashboard, channel comparison, scoring, trends, export
- [multilingual_generation.py](examples/multilingual_generation.py) — End-to-end multi-language pipeline (detection → templates → scoring → scheduling)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## Tests

```bash
pytest              # 1541 tests (interface + behavioral)
pytest -v           # verbose mode
python -m pytest    # same runner
```

## Content operations workspaces

ContentForge 0.9 adds a browser-based delivery layer to the existing APIs. Start the application and open:

- `/workspace/campaigns` for multi-channel campaign generation and partial-result recovery.
- `/workspace/approvals` for brand, compliance, and publishing-risk decisions.
- `/workspace/voice` for evidence-backed, versioned brand voice rules.
- `/workspace/publish` for channel previews and duplicate-safe retry planning.
- `/workspace/localization` for locale-by-locale semantic and brand QA.
- `/workspace/provenance` for model, prompt-template, human-edit, approval, and delivery traceability.

The workspaces use a lightweight server-rendered architecture. Domain state is implemented in `src.product_ops`, delivery routes in `src.routers.workspaces`, and the responsive design in `src/static/workspaces.css`. The UI layer does not own generation, translation, or connector logic; it coordinates existing domain services and exposes explicit recovery states.

Runtime workflow data uses `CONTENTFORGE_OPS_DB`, defaulting to `/tmp/contentforge_ops.db`. Production deployments should point this variable at a protected persistent volume and enforce tenant-aware authorization at the gateway or application layer.

### Workspace API examples

Create a campaign:

```bash
curl -X POST http://localhost:8000/api/v1/campaigns \
  -H 'Content-Type: application/json' \
  -d '{"name":"Autumn launch","channels":["linkedin","twitter"]}'
```

Capture provenance:

```bash
curl -X POST http://localhost:8000/api/v1/provenance \
  -H 'Content-Type: application/json' \
  -d '{"asset_id":"asset-1","model":"gpt-4o","prompt_template":"launch-v3","voice_version":"voice-2"}'
```

### Reproducible development

```bash
uv sync --extra dev
env -u ENVIRONMENT uv run pytest -q
uv run ruff check src/product_ops.py src/routers/workspaces.py \
  src/services/readability.py src/services/language_detection.py \
  tests/test_product_workspaces.py src/main.py
uv run ruff format --check src/product_ops.py src/routers/workspaces.py \
  src/services/readability.py src/services/language_detection.py \
  tests/test_product_workspaces.py src/main.py
uv build
```

The isolated workflow suite is `tests/test_product_workspaces.py`. The full suite deliberately unsets the host `ENVIRONMENT` variable so configuration-default tests remain deterministic.

## Actionable approval workflow (v0.12.0)
Approval queue cards now open contextual review pages. Reviewers can approve, request changes, or reject with a reason; the browser flow enforces the existing high-risk self-review rule and returns accessible operation feedback.

## Safe publish recovery (v0.13.0)
The Publish Center now provides delivery-batch detail pages with per-channel outcomes. A retry request includes only failed or retryable channels, preserves successful deliveries, and clearly explains the recovery scope before the user acts.

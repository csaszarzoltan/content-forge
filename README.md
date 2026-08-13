# ContentForge

**AI-powered content platform with brand voice customization.**

[![Tests](https://img.shields.io/badge/tests-2443%20passing-green)](https://github.com/csaszarzoltan/contentforge)
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
| P0   | **Brand Kit** | Visual identity management — color palettes (hex/RGB/HSL), font pairings, logo storage, brand guidelines HTML generator, multi-brand support |
| P1   | **AI Visibility Metrics** | Track mentions, citations, share of voice, and referral traffic from AI assistants (ChatGPT, Perplexity, Gemini, Google AI Overviews) with per-content snapshots, Chart.js-ready trends, and optional background polling |
| P0   | **Transcreation** | Cultural risk detection (idioms, references, register, taboo), locale formatting (dates, currency, units, honorifics for 9 locales), side-by-side review, preflight publish gate, and export with flag resolution |
| P0   | **AI Video Generation** | Blog/script → scenes → voiceover → MP4 pipeline with job state machine, per-scene progress and retry, background worker (queued → ready, TTS → render), TTS providers (OpenAI/ElevenLabs/Coqui), style presets, brand voice inheritance, MP4 export, 5-step wizard UI |
| P1   | **Video Platform Analytics** | Unified performance tracking across YouTube, TikTok, and Instagram — aggregated metrics, daily trend charts, optimal posting-time heatmaps, per-video drill-down with best-platform detection; partial data on platform failures (no API keys needed to start the server) |

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
pytest          # 2443 tests pass
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
|| P0   | **Translate API** | `POST /content/translate` — translate content between languages with quality scoring |

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

## 🎨 Brand Kit — Visual Identity Management

ContentForge now manages both **brand voice** (what you say) and **brand kit**
(how it looks) — color palettes, font pairings, logos, and downloadable brand
guidelines in a single platform.

### Features

| Tier | Module | Description |
|------|--------|-------------|
| P0   | **Color palette** | Create and store brand colors (primary, secondary, accent, background, text) with hex validation and computed RGB/HSL |
| P0   | **Font library** | Heading + body + accent font pairing with custom font upload (TTF/OTF/WOFF/WOFF2) |
| P0   | **Logo management** | Upload, store, and serve logos (primary, secondary, icon, watermark) with multi-format support |
| P0   | **Guidelines generator** | Generate self-contained HTML brand guidelines combining visual identity and optional voice profile |
| P1   | **Multi-brand** | Create multiple brand kits per user (personal, business, per-client) |
| P0   | **REST API** | `POST /brand-kit`, `GET /brand-kit`, `GET /brand-kit/{id}`, `GET /brand-kit/guidelines`, `POST /brand-kit/upload` |

### Usage

```python
import httpx

base = "http://localhost:8000"

# Create a brand kit
kit = httpx.post(f"{base}/brand-kit", json={
    "name": "Acme Corp",
    "brand_type": "business",
    "colors": {
        "primary": "#0066cc",
        "secondary": "#ffffff",
        "accent": "#ff9900",
        "background": "#f5f5f5",
        "text": "#333333"
    },
    "fonts": {"heading": "Manrope", "body": "DM Sans", "accent": "Inter"},
}).json()

# Generate brand guidelines
guidelines = httpx.get(f"{base}/brand-kit/guidelines",
                       params={"brand_kit_id": kit["id"]}).text
open("brand-guidelines.html", "w").write(guidelines)
```

See the [Brand Kit guide](docs/brand-kit.md) for the full API reference,
data model, file upload constraints, and multi-brand usage.

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

## 🤖 AI Visibility Metrics

ContentForge v0.14.0 tracks how often your content is **mentioned and cited
by AI assistants** — ChatGPT, Perplexity, Gemini, and Google AI Overviews —
plus the traffic those assistants refer back to your site. Poll the engines
(background loop or on-demand refresh), ingest AI-referred visits webhook-style,
and query per-content snapshots and Chart.js-ready trends under
`/api/v1/ai-visibility` — no authentication required.

### Features

| Tier | Module | Description |
|------|--------|-------------|
| P1   | **Engine providers** | `AIEngineProvider` abstraction over all four engines — Perplexity and Gemini via real HTTP APIs, ChatGPT and Google AI Overviews via structured LLM prompts; graceful degradation when a key is missing |
| P0   | **Per-content snapshot** | `GET /api/v1/ai-visibility/{content_id}` — mentions, citations, `citation_rate`, `share_of_voice`, `mention_rate`, sentiment, referral traffic and conversions per engine (all four engines always present, zero-filled) |
| P0   | **Trends feed** | `GET /api/v1/ai-visibility/trends` — Chart.js-ready 7d/30d/90d series (`dates` → labels, `series` → datasets) with per-metric totals |
| P0   | **Referral ingestion** | `POST /api/v1/ai-visibility/referral` — record an AI-referred visit (201), webhook-style and unauthenticated |
| P1   | **On-demand refresh** | `POST /api/v1/ai-visibility/{content_id}/refresh` — run one poll cycle for a content piece, returning a `PollResult`; works with the background poller disabled |
| P1   | **Background polling** | Opt-in asyncio loop (`AI_VISIBILITY_POLL_ENABLED=true`), interval and queries-per-content configurable; per-engine errors never abort the cycle |

### Usage

```bash
# Per-content visibility snapshot (last 30 days)
curl "http://localhost:8000/api/v1/ai-visibility/{content_id}"

# Chart.js-ready trend series
curl "http://localhost:8000/api/v1/ai-visibility/trends?days=30&metric=citation_rate"

# Record an AI-referred visit
curl -X POST http://localhost:8000/api/v1/ai-visibility/referral \
  -H 'Content-Type: application/json' \
  -d '{"generation_id": "gen_a1b2c3d4e5f6", "engine": "chatgpt", "referrer_url": "https://chatgpt.com/c/abc123"}'

# On-demand visibility refresh (no API keys needed to run the cycle)
curl -X POST http://localhost:8000/api/v1/ai-visibility/{content_id}/refresh
```

```python
import httpx

base = "http://localhost:8000/api/v1/ai-visibility"
content_id = "gen_a1b2c3d4e5f6"

# Snapshot: mentions, citations, share of voice, referral traffic
snap = httpx.get(f"{base}/{content_id}", params={"days": 30}).json()
print(snap["summary"]["total_mentions"], snap["summary"]["ai_referral_traffic"])

# Trends: dates -> Chart.js labels, series -> datasets
trends = httpx.get(f"{base}/trends", params={"days": 30}).json()
print(trends["period"], trends["totals"])
```

Error mapping: unknown `generation_id` → **404**; invalid `days` (only 7/30/90
accepted), unknown `engine`, or unknown `metric` → **422**.

See the [AI Visibility Guide](docs/ai-visibility.md) for the metric
definitions, the four-table data model, provider configuration, and a Chart.js
dashboard example — plus the runnable
[ai-visibility example](examples/api_ai_visibility.py).

## 🌍 Transcreation — Cultural Adaptation

ContentForge v0.14.0 adds a **transcreation** pipeline that goes beyond
translation: it detects cultural risks (idioms, cultural references, register
mismatches, taboo terms), converts locale-specific formatting (dates, currency,
units, honorifics), flags low-confidence segments for human review, and blocks
publishing until risks are resolved or explicitly overridden.

### Features

| Tier | Module | Description |
|------|--------|-------------|
| P0   | **Cultural risk detection** | Scan text for idioms, cultural references, register mismatches, and taboo terms — with LLM-powered and rule-based analysis |
| P0   | **Locale formatting** | Convert dates, currency ($→€), imperial→metric units, and honorific titles (Mr.→Herr) for 9 target locales |
| P0   | **Side-by-side review** | Per-segment accept/edit/reject workflow with literal vs. adapted text comparison |
| P0   | **Preflight publish gate** | Block publishing when high-risk items are detected; override available for explicit human approval |
| P0   | **Export with flag resolution** | Export accepted adaptations only after all low-confidence flags are resolved |
| P1   | **LLM + rule dual path** | LLM provider when configured; deterministic rule-based fallback on any LLM failure |

### Usage

```python
import httpx

base = "http://localhost:8000/api/v1/transcreation"

# Analyze for cultural risks and locale formatting
analysis = httpx.post(f"{base}/analyze", json={
    "text": "It's raining cats and dogs. The upgrade costs $1,000.",
    "target_locale": "de-DE",
}).json()
print(f"Risk items: {len(analysis['risk_items'])}")
print(f"Overall risk: {analysis['overall_risk']}")

# Culturally adapt with reviewer decisions
adaptation = httpx.post(f"{base}/adapt", json={
    "text": "It's raining cats and dogs. The report is ready.",
    "target_locale": "de-DE",
    "accepted_ids": ["seg-1"],
}).json()
print(adaptation["adapted_text"])

# Preflight check before publishing
preflight = httpx.post(f"{base}/preflight", json={
    "asset_id": "asset-1",
    "content": "That's a load of crap.",
    "target_locale": "de-DE",
}).json()
if preflight["blocked"]:
    print(f"Blocked: {preflight['blocked_reasons']}")
```

See the [Transcreation guide](docs/transcreation.md) for the full API
reference, locale table, architecture, and runnable
[transcreation example](examples/api_transcreation.py).

## 🎬 Video Generation — Blog/Script → Scenes → Voiceover → MP4

ContentForge v0.15.0 adds an **AI video generation pipeline**: turn a blog
Generation row, a URL, or raw script text into a narrated MP4 video with a
per-scene job state machine, progress tracking, retry, partial export, and a
5-step wizard UI. The pipeline is brand-voice aware, self-hosted, and renders
with MoviePy 2 + the `imageio-ffmpeg` bundled FFmpeg binary — no system
FFmpeg install required.

### Features

| Tier | Module | Description |
|------|--------|-------------|
| P0   | **Video job API** | `POST/GET /api/v1/video/jobs`, `POST /jobs/{id}/retry`, `GET /jobs/{id}/export`, `POST /jobs/{parent}/combine`, `GET /voices` |
| P0   | **Background worker** | `VideoJobWorker` (lifespan task) drives `queued → ready`: per-scene TTS → `done`, render → `ready`; failures mark scenes `failed` (attempts ≤ 3) so retry/partial-export work in production |
| P0   | **Scene assembly** | Blog sections → ordered scenes with narration; blog images reused per section; broken/missing images fall back to styled title cards |
| P0   | **TTS providers** | OpenAI TTS (default), ElevenLabs (HTTP), Coqui (`video-coqui` optional extra) — `GET /voices` lists selectable voices |
| P0   | **Retry without re-render** | Only failed scenes are re-queued; completed scenes keep cached `audio_path`/`image_path` and attempt counts (US-003) |
| P0   | **Partial export** | After max retries, `GET /export?partial=true` streams the completed scenes with `x-partial: true` + `X-Partial-Skipped` |
| P0   | **MP4 export** | H.264 + AAC, `yuv420p`, resolution selection (`480p`/`720p`/`1080p`, default `720p`) |
| P0   | **5-step wizard UI** | React + TypeScript `#video` workspace: source → outline → style/voice → generate → export, selections preserved across steps (US-004) |
| P1   | **Long-post segmentation** | 10k-char cap; posts split at section boundaries into sequential segment jobs, combined via `POST /jobs/{parent}/combine` (US-002) |

### Usage

```python
import httpx

base = "http://localhost:8000/api/v1/video"

# Create a video job from a script (no API keys needed to run the cycle —
# without a TTS key the worker writes silent placeholder audio per scene)
created = httpx.post(f"{base}/jobs", json={
    "source_type": "script",
    "source_ref": "## Intro\nHello! This is a short test video.",
    "style_preset": "explainer",
    "voice": "alloy",
    "resolution": "480p",
}).json()
job_id = created["job_id"]
print(f"Job {job_id} → {created['state']}")

# Poll until the background worker finishes (state == 'ready')
job = httpx.get(f"{base}/jobs/{job_id}").json()
while job["state"] not in ("ready", "failed"):
    job = httpx.get(f"{base}/jobs/{job_id}").json()
print(f"State: {job['state']} — progress {job['overall_progress']}%")

# Stream the MP4 export to a file
mp4 = httpx.get(f"{base}/jobs/{job_id}/export", params={"resolution": "480p"})
open(f"video_{job_id}.mp4", "wb").write(mp4.content)
print(f"Exported {len(mp4.content)} bytes, content-type {mp4.headers['content-type']}")
```

See the [Video Generation guide](docs/video-pipeline.md) for the full API
reference, state machine, TTS provider configuration, and the runnable
[video example](examples/api_video.py).

## 📈 Video Platform Analytics — YouTube · TikTok · Instagram

ContentForge v0.15.0 adds **video platform analytics**: unified performance
tracking across YouTube, TikTok, and Instagram. Each platform is an
independent client, so a missing key, expired token, or quota error only
affects that platform — it is reported in `platforms_unavailable` and the
rest of the response is served normally (partial data, never a hard
failure).

### Features

| Tier | Module | Description |
|------|--------|-------------|
| P1   | **Performance tracking** | `GET /api/v1/analytics/video-performance` — views, likes, comments, shares (plus platform-specific fields: plays, saves, completion rate, watch time) aggregated per platform, with `video_id` / `platform` / date-range filters |
| P1   | **Trend charts** | `GET /api/v1/analytics/video-performance/timeseries` — daily points per platform, Chart.js-ready |
| P1   | **Optimal posting times** | `GET /api/v1/analytics/video-performance/optimal-times` — day × hour engagement heatmap (0 = Monday, 0–23 h) |
| P1   | **Per-video drill-down** | `GET /api/v1/analytics/video-performance/{video_id}` — one video across all platforms plus `best_platform` detection |
| P1   | **CLI** | `python -m src.cli analytics video-performance [--platform ...] [--days N]` — terminal table of the same aggregation |
| P1   | **Partial-failure resilience** | Platform outages degrade to `platforms_unavailable` entries; all-unconfigured servers still start and serve `200` with empty data |

### Usage

```python
import httpx

base = "http://localhost:8000/api/v1/analytics/video-performance"

# Aggregated metrics across all configured platforms (no keys → 200 with
# empty platforms + platforms_unavailable listing all three)
perf = httpx.get(base, params={"video_id": "abc123"}).json()
print(perf["platforms"])                    # per-platform metric dicts
print(perf["platforms_unavailable"])        # ['youtube', 'tiktok', 'instagram']

# Daily trend points (Chart.js-ready)
trend = httpx.get(f"{base}/timeseries", params={"platform": "youtube"}).json()
print(trend["points"])

# Per-video drill-down with best-platform detection (502 when no platforms
# are configured — see error mapping below)
detail = httpx.get(f"{base}/abc123").json()
print(detail.get("best_platform", detail))
```

Error mapping: inverted date range → **400**; malformed datetime / unknown
platform → **422**; drill-down with all platforms down → **502**; video not
found on any responding platform → **404**.

See the [Video Platform Analytics guide](docs/video-analytics.md) for setup
(API keys, YouTube OAuth2, TikTok Research API access, Instagram Business
account), the full endpoint reference, CLI usage, and error behavior.

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
| [Brand Kit](docs/brand-kit.md) | `POST/GET /brand-kit`, `GET /brand-kit/guidelines`, `POST /brand-kit/upload` — visual identity CRUD, color/font/logo management, HTML guidelines generator |
| [Brand Voice API](docs/brand-voice-api.md) | `GET/POST/PUT/DELETE /brand-voices` — brand voice CRUD endpoints |
| [Scheduling API](docs/scheduling.md) | `GET/POST/PUT/DELETE /scheduling` — scheduled post management |
|| [Analytics Dashboard](docs/analytics-dashboard.md) | `POST /api/v1/analytics/track`, `GET /dashboard`, `/content/{id}`, `/channels`, `/ab-results`, `/score/{id}`, `/export`, `/trends`, `/anomalies` — event tracking, content scoring, channel comparison, A/B correlation |
| [AI Visibility](docs/ai-visibility.md) | `GET /api/v1/ai-visibility/{content_id}`, `/trends`, `POST /referral`, `POST /{content_id}/refresh` — metric definitions, provider configuration, Chart.js dashboard |
|| [Deployment](docs/deployment.md) | Railway + Docker deployment guide, environment config, health checks |
|| [Social Media Publishing](docs/social-publishing.md) | Platform connectors, rate limiting, publish API, production readiness |
|| [Language Detection](docs/language-detection.md) | Auto-detect input language with fast-langdetect, confidence scoring, batch detection |
|| [Prompt Templates (per-language)](docs/prompt-templates.md) | Language-adaptive prompt templates, brand voice localization, fallback chain |
|| [Translation Pipeline](docs/translation-pipeline.md) | BLEU/chrF quality scoring, cross-language consistency, post-processing |
|| [Multilingual Scheduling](docs/multilingual-scheduling.md) | Timezone-aware publishing, language calendars, auto-translate, dependency chains |
| [Transcreation](docs/transcreation.md) | `POST /api/v1/transcreation/analyze`, `/adapt`, `/preflight`, `GET /preflight/{id}`, `POST /override`, `GET /assets/{id}/result`, `POST /assets/{id}/export` — cultural risk detection, locale formatting, side-by-side review, preflight gate, export |
| [Video Generation](docs/video-pipeline.md) | `POST/GET /api/v1/video/jobs`, `POST /jobs/{id}/retry`, `GET /jobs/{id}/export`, `POST /jobs/{parent}/combine`, `GET /voices` — blog/script → scenes → voiceover → MP4, background worker drives jobs to ready, job state machine, per-scene retry, partial export, style presets, brand voice inheritance |
| [Video Platform Analytics](docs/video-analytics.md) | `GET /api/v1/analytics/video-performance`, `/timeseries`, `/optimal-times`, `/{video_id}` — YouTube/TikTok/Instagram performance tracking, trend charts, optimal posting-time heatmaps, per-video drill-down, partial data on platform failures, CLI (`analytics video-performance`) |

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
- [api_ai_visibility.py](examples/api_ai_visibility.py) — AI visibility walkthrough: ingest referrals for all four engines, on-demand refresh, per-content snapshot, trends feed
- [multilingual_generation.py](examples/multilingual_generation.py) — End-to-end multi-language pipeline (detection → templates → scoring → scheduling)
- [api_transcreation.py](examples/api_transcreation.py) — Transcreation walkthrough: analyze cultural risks, adapt with reviewer decisions, preflight check, override, export
- [api_video.py](examples/api_video.py) — Video generation walkthrough: create job from script, poll progress, retry, partial export, MP4 export, voices

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## Tests

```bash
pytest              # 2443 tests (interface + behavioral)
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
uv run ruff check src/services/transcreation.py src/schemas/transcreation.py \
  src/routers/transcreation.py examples/api_transcreation.py
uv build
```

The isolated workflow suite is `tests/test_product_workspaces.py`. The full suite deliberately unsets the host `ENVIRONMENT` variable so configuration-default tests remain deterministic.

## Actionable approval workflow (v0.12.0)
Approval queue cards now open contextual review pages. Reviewers can approve, request changes, or reject with a reason; the browser flow enforces the existing high-risk self-review rule and returns accessible operation feedback.

## Safe publish recovery (v0.13.0)
The Publish Center now provides delivery-batch detail pages with per-channel outcomes. A retry request includes only failed or retryable channels, preserves successful deliveries, and clearly explains the recovery scope before the user acts.

## v0.11 Campaign Cockpit and versioned editor

ContentForge now includes the first research-driven **brief-to-publish vertical slice**:

- **Campaign Cockpit:** a campaign brief, channel asset pipeline, explainable readiness score, and concrete blockers in one context-preserving view. This addresses the research finding that teams lose time and confidence when campaign context is fragmented across tools.
- **Versioned content editor:** every save appends an immutable revision, and optimistic concurrency returns a friendly conflict instead of silently overwriting another editor's work. This addresses unclear publishable versions and unsafe editing.
- **My Work API:** pending approvals and failed publications appear as actionable work items. This addresses the need for a unified queue and operation-specific recovery.

### Run the modern web UI

Terminal 1, API:

```bash
uvicorn src.main:app --reload
```

Terminal 2, React + TypeScript UI:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. The Vite development server proxies `/api` to the FastAPI server. The real flow is: create campaign → see readiness blockers → create channel asset → edit → save a new immutable revision. Errors preserve the draft and provide a retry-oriented message.

### API endpoints added in v0.11

- `POST /api/v1/campaigns`
- `POST /api/v1/campaigns/{campaign_id}/assets`
- `GET /api/v1/campaigns/{campaign_id}/cockpit`
- `PUT /api/v1/assets/{asset_id}/autosave`
- `GET /api/v1/assets/{asset_id}/revisions`
- `GET /api/v1/my-work`

### Frontend verification

```bash
cd frontend
npm test
npm run lint
npm run build
```

## v0.12 Revision-bound approvals

The React editor can now send the current asset version for review. Approval requests are bound to an exact immutable revision. Editing the asset automatically supersedes pending or approved decisions, so changed content cannot inherit an outdated approval. Review decisions and reasons are written to the asset audit trail.

New endpoints:

- `POST /api/v1/assets/{asset_id}/approval`
- `POST /api/v1/approvals/{request_id}/decision`
- `GET /api/v1/assets/{asset_id}/audit`

## v0.13 complete workspace navigation

Every sidebar item now opens a real React workspace with a stable URL hash, active navigation state, browser Back/Forward support, and meaningful loading, empty, data, and error states.

Available routes:

- `#my-work`
- `#campaigns`
- `#content`
- `#calendar`
- `#approvals`
- `#localization`
- `#analytics`
- `#brand`
- `#connections`
- `#admin`

On Windows, start the backend with:

```powershell
python scripts/run_backend.py
```

This watches only `src/`, so installing frontend dependencies no longer restarts the API server. Python 3.11 installs SciPy 1.17.1, while Python 3.12 and later install SciPy 1.18.0.

## Dokumentáció

- [Engineering Standards](docs/engineering-standards.md) — kötelező olvasmány kódírás előtt
- [Döntések / tanulságok](docs/decisions/) — javított hibák és anti-minták
- [Specifikációk](docs/specs/) — feature-ök kanonikus követelményei

- [Módszertan](docs/METHODOLOGY.md) — a lab fejlesztési módszertana (kötelező olvasmány)

## Family Creator

Open the SPA at `#family` to start the guided Family Creator experience. An adult creates a workspace, family members contribute private ideas and drafts, and only an adult can approve the exact current revision and publish it.

### Roles

- **Adult owner:** manages members, creates, reviews, and publishes.
- **Adult collaborator:** creates, reviews, and publishes.
- **Teen contributor:** creates and edits private work and submits it for review; cannot publish or manage credentials.
- **Viewer:** read-only.

The primary flow is **setup -> Home -> four-step project wizard -> exact-revision review -> adult publish**. The family API is under `/api/v1/family`; local/demo clients send `X-User-ID`, `X-User-Name`, and `X-User-Email`. Production deployments should map these actor values from authenticated identity at the trusted gateway.

```bash
python scripts/run_backend.py
cd frontend && npm run dev
# open http://127.0.0.1:5173/#family
```

Troubleshooting: if Home cannot load, use its Retry action; draft and idea controls preserve entered text. A stale approval cannot publish and must be reviewed again.

### Family Creator completion flow

Family routes now require the normal ContentForge JWT. Open `#family`, sign in, then use Members to create bounded invitation links. Contributors edit through the preview-first editor; an 800 ms autosave uses optimistic versions and preserves unsaved text locally. Adults review the exact revision and can inspect per-channel publication results. Unknown provider states must be reconciled before retry.

Security note: browser `X-User-*` headers are ignored. Public invitation previews return no invited email or project data. Pending invitation tokens created by older builds are invalidated because raw token storage was removed.

### Paid-beta publishing configuration

Family publication now calls the real LinkedIn/X connectors when credentials are configured. Set `LINKEDIN_ACCESS_TOKEN` plus `LINKEDIN_AUTHOR_URN`, or all four Twitter/X credential variables. Missing or expired connections are shown as Action required and never reported as published. The adult confirmation screen shows the approved revision, reviewer, destinations, visibility, and timing before sending.

### Paid-beta scheduling and validation status

The paid beta publishes immediately after adult confirmation. Scheduling is intentionally hidden until durable background execution, restart recovery, and timezone tests are implemented. See `docs/family-pilot.md` for the 5-10 household pilot and `docs/provider-sandbox-checklist.md` for real provider verification.

## Family paid-beta release hardening

Family mode uses immediate publishing only. Provider credentials are treated as **configured, not verified** until a non-public LinkedIn or X sandbox test returns a confirmed remote identifier. Unknown external provider state must be reconciled before retry. Family roles expose a shared capability model, and pilot measurement accepts only consented, content-free events. Scheduling remains hidden; the family navigation uses Activity for publication history.
>>>>>>> c9ac53d6a51b6d6321496d5b44be89dbb229cf3c

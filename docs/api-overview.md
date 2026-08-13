# API Overview

Complete reference for all ContentForge REST endpoints.

Base URL: `http://localhost:8000` (local) or your Railway deployment URL.

---

## Endpoints

### `GET /`

Root endpoint — returns API metadata.

```json
{
  "message": "ContentForge API",
  "version": "0.9.0"
}
```

---

### `GET /health`

Health check for deployment monitoring and load balancers.

```json
{
  "status": "healthy",
  "version": "0.9.0",
  "timestamp": "2026-07-22T19:55:00+00:00",
  "checks": {
    "database": "ok",
    "scheduler": "ok",
    "llm_provider": "ok"
  }
}
```

The `llm_provider` check is passive by default — set `HEALTH_CHECK_LLM=true` to enable an actual LLM connectivity probe.

---

### `POST /auth/register`

Register a new user account.

**Request body:**
```json
{
  "email": "alice@example.com",
  "password": "secure-password-8chars",
  "display_name": "Alice"
}
```

**Response** (201 Created):
```json
{
  "id": "a1b2c3d4-...",
  "email": "alice@example.com",
  "display_name": "Alice",
  "role": "user",
  "organization_id": null,
  "created_at": "2026-07-23T17:39:00+00:00"
}
```

**Errors:** `409 Conflict` — email already registered. `422 Unprocessable Entity` — password shorter than 8 characters or invalid email format.

---

### `POST /auth/login`

Authenticate with email + password to receive a JWT token pair.

**Request body:**
```json
{
  "email": "alice@example.com",
  "password": "secure-password-8chars"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbG...NiIs...",
  "refresh_token": "eyJhbG...NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

The `access_token` expires in 15 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`). The `refresh_token` expires in 30 days. Send the access token as `Authorization: Bearer *** on subsequent requests.

**Errors:** `401 Unauthorized` — invalid email or password.

---

### `POST /auth/refresh`

Exchange a valid refresh token for a new token pair. Issues a new token pair and updates the stored hash, but the previous refresh token remains valid until its JWT expiry (default 30 days).

**Request body:**
```json
{
  "refresh_token": "eyJhbG...NiIs..."
}
```

**Response** (200 OK) — same shape as login response.

**Errors:** `401 Unauthorized` — invalid, expired, or already-used refresh token.

---

### `GET /auth/me`

Return the authenticated user's profile. Requires a valid Bearer access token.

**Request headers:**
```
Authorization: Bearer eyJhbG...s...
```

**Response** (200 OK) — same UserResponse shape as register.

**Errors:** `401 Unauthorized` — missing, invalid, or expired token.

---

### `POST /brand-voice`

Create a brand voice profile.

**Request body:**
```json
{
  "name": "TechCorp Pro",
  "description": "Professional tech brand voice",
  "brand_identity": {
    "who": "Enterprise SaaS company",
    "audience": "CTOs and engineering leaders",
    "purpose": "Build trust through clarity"
  },
  "attributes": [
    {"trait": "formality", "value": 0.8, "min_label": "Casual", "max_label": "Formal"}
  ],
  "vocabulary": {
    "preferred": ["scalable", "enterprise-grade", "robust"],
    "banned": ["amazing", "game-changer"]
  },
  "scenarios": [],
  "formatting": null,
  "user_id": null
}
```

**Response** (201 Created):
```json
{
  "id": "a1b2c3d4-...",
  "name": "TechCorp Pro",
  "description": "Professional tech brand voice",
  "brand_identity": {"who": "Enterprise SaaS company", ...},
  "attributes": [...],
  "vocabulary": {"preferred": [...], "banned": [...]},
  "scenarios": [],
  "formatting": {},
  "metadata": {"version": "1"},
  "version": 1,
  "created_at": "2026-07-22T19:55:00+00:00",
  "updated_at": "2026-07-22T19:55:00+00:00"
}
```

---

### `GET /brand-voice`

List all brand voices (paginated). Soft-deleted profiles are excluded.

**Query parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | integer | 20 | Max results (1–100) |
| `offset` | integer | 0 | Pagination offset |

**Response** (200 OK):
```json
{
  "items": [/* BrandVoiceResponse objects */],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

---

### `GET /brand-voice/{id}`

Get a single brand voice by its UUID.

**Response** (200 OK) — same shape as create response.

**Error** (404):
```json
{"detail": "Brand voice not found"}
```

---

### `PUT /brand-voice/{id}`

Partial update of a brand voice. Only send the fields you want to change. Auto-increments the `version` field.

**Request body** (all fields optional):
```json
{
  "name": "New Name",
  "attributes": [{"trait": "formality", "value": 0.9, ...}]
}
```

**Response** (200 OK) — full BrandVoiceResponse with incremented version.

---

### `DELETE /brand-voice/{id}`

Soft-delete a brand voice (sets `deleted_at` timestamp). The profile remains in the database but is excluded from all queries.

**Response** (204 No Content) — no body.

---

### `POST /generate/{content_type}`

Generate content via LLM with brand voice injection.

**Path parameters:**
| Param | Values | Description |
|-------|--------|-------------|
| `content_type` | `blog`, `social`, `email` | Type of content to generate |

**Request body:**
```json
{
  "topic": "Microservices vs Monoliths",
  "brand_voice_id": null,
  "user_id": null,
  "project_id": null,
  "parameters": {
    "audience": "Engineering managers",
    "length": "medium",
    "tone_override": null,
    "include_cta": true,
    "custom_instructions": null
  }
}
```

**Response** (200 OK):
```json
{
  "id": "gen_a1b2c3d4e5f6",
  "content_type": "blog",
  "generated_text": "In the ongoing debate between microservices and monolithic architectures...",
  "brand_voice_id": null,
  "compliance_score": {
    "overall": 0.95,
    "vocabulary": 0.95,
    "readability": 0.95,
    "tone": 0.95,
    "violations": []
  },
  "model_used": "gpt-4o",
  "tokens_used": 456,
  "latency_ms": 1240,
  "created_at": "2026-07-22T19:55:00+00:00"
}
```

**Error** (422):
```json
{"detail": "Invalid content_type: newsletter. Must be one of {'blog', 'social', 'email'}"}
```

---

### `POST /schedule`

Schedule a generated content piece for publishing.

**Request body:**
```json
{
  "generation_id": "gen_a1b2c3d4e5f6",
  "publish_at": "2026-08-01T09:00:00Z",
  "platform": "blog",
  "platform_config": {},
  "retry_on_failure": true,
  "max_retries": 3
}
```

**Platform values:** `twitter`, `linkedin`, `email`, `blog`

**Response** (201 Created):
```json
{
  "schedule_id": "sch_a1b2c3d4e5f6",
  "generation_id": "gen_a1b2c3d4e5f6",
  "status": "scheduled",
  "publish_at": "2026-08-01T09:00:00Z",
  "platform": "blog",
  "created_at": "2026-07-22T19:55:00+00:00"
}
```

**Error** (422) — when `publish_at` is in the past:
```json
{"detail": "publish_at must be in the future"}
```

---

### `GET /schedule/{id}`

Get the current status and metadata of a scheduled post.

**Response** (200 OK):
```json
{
  "schedule_id": "sch_a1b2c3d4e5f6",
  "generation_id": "",
  "status": "pending",
  "publish_at": "2026-08-01T09:00:00Z",
  "platform": "",
  "retry_count": 0,
  "max_retries": 3,
  "created_at": "2026-07-22T19:55:00+00:00",
  "updated_at": "2026-07-22T19:55:00+00:00"
}
```

---

### `DELETE /schedule/{id}`

Cancel a scheduled post.

**Response** (204 No Content) — no body.

---

### `GET /analytics/content/{generation_id}`

> **Removed in v0.9.0** — superseded by `GET /api/v1/analytics/content/{generation_id}`
> (see [Analytics Dashboard](analytics-dashboard.md) for the current API).

### `GET /analytics/summary`

> **Removed in v0.9.0** — superseded by `GET /api/v1/analytics/dashboard`
> (see [Analytics Dashboard](analytics-dashboard.md) for the current API).

### Analytics Dashboard API — `/api/v1/analytics/*`

ContentForge v0.9.0 replaces the legacy analytics stub with an event-log based
dashboard. All endpoints are unauthenticated and accept the optional
`date_from` / `date_to` window parameters (default: last 30 days).

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/analytics/track` | Record an event — `{generation_id, channel, event_type, value, user_identifier?, metadata?, occurred_at?}` → `{status: "ok", event_id}` (201) |
| `GET` | `/api/v1/analytics/dashboard` | Aggregated metrics + channel/content-type breakdowns + top-5 content + daily time series |
| `GET` | `/api/v1/analytics/content/{generation_id}` | Per-content performance and compliance |
| `GET` | `/api/v1/analytics/channels` | Cross-channel comparison, sorted by `metric` (`impressions`, `clicks`, `shares`, `comments`, `conversions`, `engagement_rate`) |
| `GET` | `/api/v1/analytics/ab-results` | A/B variant ↔ analytics correlation (`test_id` required) |
| `GET` | `/api/v1/analytics/export` | Daily aggregates as CSV or JSON (`format=csv\|json`) |
| `GET` | `/api/v1/analytics/score/{generation_id}` | Deterministic content score (0–100) + grade |
| `GET` | `/api/v1/analytics/trends` | 7d/30d/90d daily trend series with anomaly flags |
| `GET` | `/api/v1/analytics/anomalies` | Statistically flagged days (`\|z\| ≥ 2.0`, ≥ 7 data points) |

**Event types:** `impression`, `click`, `share`, `comment`, `conversion`, `read_time`.
**Channels:** `twitter`, `linkedin`, `medium`, `blog`, `email`, `web`, `other`.

**Errors:** unknown `generation_id` / `test_id` → `404`; invalid channel,
metric, period, format, or inverted date window → `422`.

Full request/response examples, the content scoring formula, and usage
walkthroughs live in the [Analytics Dashboard guide](analytics-dashboard.md).

---

### AI Visibility API — `/api/v1/ai-visibility/*`

ContentForge v0.14.0 adds AI visibility tracking: mentions, citations, share
of voice, and referral traffic from AI assistants (ChatGPT, Perplexity,
Gemini, Google AI Overviews). All endpoints are unauthenticated (the auth
dependency is optional).

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/ai-visibility/{content_id}` | Per-content snapshot — `summary` cards, per-engine metrics for all four engines, daily `time_series` (`days=7\|30\|90`, default 30) |
| `GET` | `/api/v1/ai-visibility/trends` | Chart.js-ready trend series — `dates` → labels, `series` → datasets (`days`, optional `engine`, `metric` filters) |
| `POST` | `/api/v1/ai-visibility/referral` | Ingest an AI-referred visit — `{generation_id, engine, referrer_url, landing_path?, converted?, conversion_value?, occurred_at?}` → `{status: "ok", referral_id}` (201) |
| `POST` | `/api/v1/ai-visibility/{content_id}/refresh` | On-demand poll cycle for one content piece → `PollResult` (engines polled, queries run, mentions recorded, errors) |

**Engines:** `chatgpt`, `perplexity`, `gemini`, `google_ai_overviews`.
**Metrics:** `citation_rate`, `share_of_voice`, `mention_rate`,
`ai_referral_traffic`.

**Errors:** unknown `generation_id` → `404`; invalid `days` (only 7/30/90
accepted), unknown `engine`, or unknown `metric` → `422`.

Metric definitions, provider configuration (API keys, poller settings), and a
Chart.js dashboard example live in the
[AI Visibility guide](ai-visibility.md).

---

### `POST /api/v1/publish`

Publish generated content to a social media platform.

**Request body:**

```json
{
  "generation_id": "gen_a1b2c3d4e5f6",
  "platform": "twitter",
  "text": "Check out our latest blog post on microservices vs monoliths!",
  "platform_config": {}
}
```

**Request fields:**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `generation_id` | Yes | string | ID of the generated content to publish |
| `platform` | Yes | string | Target platform — `"twitter"` or `"linkedin"` |
| `text` | No | string | Content text to publish (default: `""`) |
| `platform_config` | No | object | Platform-specific config (`article_url`, `article_title`) |

**Platform-specific `platform_config`:** for `linkedin`, pass `article_url` (string) and `article_title` (string) to create a link share post.

**Response** (201 Created):

```json
{
  "publish_id": "pub_a1b2c3d4e5f6",
  "generation_id": "gen_a1b2c3d4e5f6",
  "platform": "twitter",
  "status": "published",
  "platform_url": "https://twitter.com/user/status/1234567890",
  "created_at": "2026-07-26T12:00:00+00:00"
}
```

**Errors:** `422` — invalid platform. `500` — auth failure or rate limit exhausted.

---

### `GET /api/v1/publish/{publish_id}`

Get the status of a publish operation.

```bash
curl http://localhost:8000/api/v1/publish/pub_a1b2c3d4e5f6
```

**Response** (200 OK):

```json
{
  "publish_id": "pub_a1b2c3d4e5f6",
  "status": "published",
  "retry_count": 0,
  "error_message": null
}
```

Status values: `published`, `failed`, `not_found`.

---

### `GET /api/v1/publish/status`

List publish operations, optionally filtered by status.

```bash
curl http://localhost:8000/api/v1/publish/status
curl "http://localhost:8000/api/v1/publish/status?status_filter=published"
```

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `status_filter` | string | `null` | Filter by status value |

**Response** (200 OK):

```json
{
  "statuses": [],
  "filter": null
}
```

> **Note:** The listing endpoint is an in-memory stub — it always returns an empty `statuses` array. Persistent tracking is planned.

---

### Transcreation — Cultural Adaptation

All endpoints are under `/api/v1/transcreation` and require no authentication.

#### `POST /api/v1/transcreation/analyze`

Detect cultural risks and locale formatting issues.

**Request body:**
```json
{
  "text": "It's raining cats and dogs. The upgrade costs $1,000.",
  "target_locale": "de-DE",
  "source_locale": "auto"
}
```

**Response** (200 OK): `AnalyzeResponse` — `risk_items`, `format_items`, `overall_risk`, `locale`. See [Transcreation guide](transcreation.md) for full schema.

#### `POST /api/v1/transcreation/adapt`

Culturally adapt content with per-segment reviewer decisions.

**Request body:**
```json
{
  "text": "It's raining cats and dogs.",
  "target_locale": "de-DE",
  "accepted_ids": ["seg-1"],
  "rejected_ids": [],
  "edits": {}
}
```

**Response** (200 OK): `AdaptResponse` — `adapted_text`, `segments`, `changes_log`, `flagged_segments`.

#### `POST /api/v1/transcreation/preflight`

Pre-flight publish check — blocks on high-risk items.

**Request body:**
```json
{
  "asset_id": "asset-123",
  "content": "That's a load of crap.",
  "target_locale": "de-DE"
}
```

**Response** (200 OK): `PreflightResult` — `blocked`, `blocked_reasons`, `audit_status`, `override_available`.

#### `GET /api/v1/transcreation/preflight/{asset_id}`

Retrieve the latest stored preflight result for an asset.

#### `POST /api/v1/transcreation/preflight/{asset_id}/override`

Override a preflight block. **Body:** `{"override": true}`. Returns updated `PreflightResult`.

#### `GET /api/v1/transcreation/assets/{asset_id}/result`

Return the full persisted transcreation result (analysis + adaptation + preflight + decisions).

#### `POST /api/v1/transcreation/assets/{asset_id}/export`

Export accepted adaptations. **Body (optional):** `{"accepted_ids": [...], "rejected_ids": [...]}`. Blocked with `409` while low-confidence flags remain unresolved.

---

## Video Generation API — `/api/v1/video/*`

Turn a blog Generation row, a URL, or raw script text into a narrated MP4
video. Jobs run through a background worker (`VideoJobWorker`, lifespan task)
that drives `queued → outline → scenes → render → ready | failed`, so the
public API stays responsive while TTS + render happen off the request path.

#### `POST /api/v1/video/jobs`

Create a video job. **Request body:**

```json
{
  "source_type": "generation_id | url | script",
  "source_ref": "gen-123 | https://example.com/blog/post | ## Intro\nHello.",
  "brand_voice_id": "bv-1",
  "style_preset": "explainer | documentary",
  "voice": "alloy",
  "resolution": "720p",
  "auto_segment": true
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `source_type` | enum | yes | — | `generation_id`, `url`, or `script` |
| `source_ref` | string | yes | — | Generation id, URL, or script text (≤ 200k chars) |
| `brand_voice_id` | string | no | `null` | Brand voice profile id (resolved → `voice_profile_name`) |
| `style_preset` | enum | no | `null` | `explainer` (default) or `documentary` |
| `voice` | string | no | `null` | TTS voice id (e.g. `alloy`) |
| `resolution` | enum | no | `"720p"` | `480p`, `720p`, or `1080p` |
| `auto_segment` | bool | no | `true` | Split long posts into sequential segment jobs |

**Response** (201): `{"job_id": "…", "state": "queued", "segments": null | ["…"]}`.
- `400` malformed/oversize source · `404` unknown `generation_id` · `422` invalid enum/field validation.

#### `GET /api/v1/video/jobs/{job_id}`

Fetch a job with per-scene status and overall progress.

**Response** (200): `VideoJobResponse` — `id`, `source_type`, `source_ref`,
`state`, `brand_voice_id`, `voice_profile_name`, `style_preset`, `voice`,
`resolution`, `segment_order`, `error`, `overall_progress`, `scenes[]`
(each: `id`, `order`, `heading`, `state`, `attempts`, `error`,
`image_path`, `audio_path`), `created_at`, `updated_at`.
- `404` unknown job id (`{"detail": "video job not found"}`).

#### `POST /api/v1/video/jobs/{job_id}/retry`

Re-queue **only** failed scenes; completed scenes are never re-rendered.
Attempts increment per retry; scenes at max retries (3) stay failed.

**Response** (200): `{"retried": ["scene-id", …]}`.
- `404` unknown job · `409` job state not retryable (e.g. `ready`).

#### `GET /api/v1/video/jobs/{job_id}/export?resolution=720p&partial=true`

Stream the rendered MP4 (`Content-Type: video/mp4`). `partial=true` skips
scenes that exhausted retries (failed at max attempts) and adds
`x-partial: true` plus an `X-Partial-Skipped` header listing the skipped
scene ids; without `partial`, a job with any failed scene is `409` (a
partial export must be explicit). Jobs with a pre-rendered `output_path`
(combine results) stream that file directly.

- `409` nothing renderable (no done scenes / job not ready and no partial allowed) · `404` unknown job · `422` invalid resolution.

#### `POST /api/v1/video/jobs/{parent_id}/combine`

Concatenate a segment family's rendered per-scene MP4 clips into one combined
MP4. Uses the rendered **clip** files cached on the scenes by the background
worker (`clip_path`) — never the MP3 audio assets.

**Response** (200): `{"combined_job_id": "…", "url": "/api/v1/video/jobs/…/export"}`.
- `404` unknown or implausible parent id · `409` the parent's segments have no rendered clips yet.

#### `GET /api/v1/video/voices?provider=openai|elevenlabs|coqui`

List selectable TTS voices.

**Response** (200): `{"provider": "openai", "voices": [{"id": "alloy", "name": "Alloy"}, …]}`.
- `422` unknown provider · `503` provider unavailable (missing API key / optional extra not installed).

See the [Video Generation guide](video-pipeline.md) for the state machine,
TTS provider configuration, and a runnable example.

---

## Error handling

All endpoints return standard HTTP status codes:

| Status | Meaning |
|--------|---------|
| `200` | Success |
| `201` | Created |
| `204` | No Content (delete operations) |
| `401` | Unauthorized (missing/invalid credentials) |
| `404` | Resource not found |
| `409` | Conflict (duplicate resource, e.g. email already registered) |
| `422` | Validation error (invalid input) |
| `500` | Internal server error |

Validation errors include a structured detail:

```json
{"detail": [{"loc": ["body", "topic"], "msg": "field required", "type": "value_error.missing"}]}
```

### Family Creator API — `/api/v1/family/*`

Family workspace, invitation, Home, journey, private idea, exact-revision review, and adult publish endpoints are documented in [Family Creator Workspace](family-workspace.md). Side-effecting create/publish operations use `Idempotency-Key`; role and workspace membership are enforced before object access.

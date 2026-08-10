# Video Platform Analytics — YouTube · TikTok · Instagram

ContentForge v0.15.0 adds **video platform analytics**: unified performance
tracking across YouTube, TikTok, and Instagram with trend charts, optimal
posting-time heatmaps, and per-video drill-down — all under
`/api/v1/analytics/video-performance`.

Each platform is an independent client. A missing API key, an expired token,
a quota error, or a network failure only affects that one platform: it is
reported in `platforms_unavailable` and the rest of the response is served
normally. There is no single point of failure and no storage dependency —
all metrics are fetched live from the platform APIs on every request.

The feature answers:

- **How is my video doing?** — `GET /api/v1/analytics/video-performance` (aggregated metrics per platform)
- **What does the trend look like?** — `GET /api/v1/analytics/video-performance/timeseries` (daily points, Chart.js-ready)
- **When should I post?** — `GET /api/v1/analytics/video-performance/optimal-times` (day × hour heatmap)
- **Where does this video win?** — `GET /api/v1/analytics/video-performance/{video_id}` (per-video drill-down + best platform)

---

## Setup

### 1. API keys

All keys are read from environment variables (or `.env`) by the same
Pydantic settings object as the rest of ContentForge. **Empty value ⇒ the
platform client is unconfigured and skipped** — the server starts and serves
partial data without them.

| Variable | Platform | Purpose |
|----------|----------|---------|
| `YOUTUBE_API_KEY` | YouTube | Data API v3 key (unauthenticated video statistics) |
| `YOUTUBE_OAUTH_TOKEN` | YouTube | Optional OAuth2 access token (channel-level metrics, token refresh is a stub for now) |
| `TIKTOK_API_KEY` | TikTok | TikTok Research API access token (used as a Bearer credential) |
| `INSTAGRAM_ACCESS_TOKEN` | Instagram | Instagram Graph API long-lived token (Business/Creator account) |

Example `.env`:

```bash
YOUTUBE_API_KEY=AIza...
YOUTUBE_OAUTH_TOKEN=ya29...
TIKTOK_API_KEY=tiktok_research_token
INSTAGRAM_ACCESS_TOKEN=EAAG...
```

### 2. Platform-specific requirements

| Platform | Requirement | Notes |
|----------|-------------|-------|
| **YouTube** | Google Cloud project with the YouTube Data API v3 enabled + API key | Statistics (`viewCount`, `likeCount`, `commentCount`) come from the key alone; `watch_time_minutes` and `subscriber_change` need the Analytics API and are returned as `0` until an OAuth2 token is wired in |
| **TikTok** | TikTok Research API access (approved developer account) | Access token sent as `Authorization: Bearer`; quota exhaustion (HTTP 429) is handled gracefully — the platform is reported unavailable for that request instead of failing the call |
| **Instagram** | Instagram Business or Creator account + Graph API access token | Reels metrics (impressions, likes, comments, shares, saves) via the Graph API `insights` field; tokens starting with `personal-` are treated as non-business and skipped (test signal) |

### 3. Run the server

```bash
uvicorn src.main:app --reload
```

No background jobs, no database tables, no new runtime dependencies — the
clients use `httpx`, which is already pinned.

---

## API Endpoints

All endpoints live under `/api/v1/analytics/video-performance`. They work
without authentication (the auth dependency is optional) and return JSON.
Query parameters are shared across the endpoints:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `video_id` | string | `""` (empty = all videos) | Platform video/media id to filter on |
| `platform` | string | `null` | Filter to one platform: `youtube`, `tiktok`, `instagram` |
| `date_from` | ISO datetime | 30 days ago (UTC) | Start of the analysis window |
| `date_to` | ISO datetime | now (UTC) | End of the analysis window |

### `GET /api/v1/analytics/video-performance`

Unified performance metrics across all configured platforms. Views, likes,
comments, and shares are normalized per platform; platform-specific metrics
(`watch_time_minutes`, `completion_rate`, `plays`, `saves`,
`subscriber_change`) are included when the platform provides them and `0`
otherwise.

**Request:**

```bash
curl "http://localhost:8000/api/v1/analytics/video-performance?video_id=abc123&date_from=2026-07-01T00:00:00Z"
```

**Response** (`200`):

```json
{
  "video_id": "abc123",
  "platforms": [
    {
      "platform": "youtube",
      "views": 15230,
      "likes": 214,
      "comments": 41,
      "shares": 0,
      "watch_time_minutes": 0.0,
      "subscriber_change": 0,
      "completion_rate": 0.0,
      "plays": 0,
      "saves": 0
    },
    {
      "platform": "instagram",
      "views": 0,
      "likes": 87,
      "comments": 12,
      "shares": 5,
      "watch_time_minutes": 0.0,
      "subscriber_change": 0,
      "completion_rate": 0.0,
      "plays": 3120,
      "saves": 44
    }
  ],
  "platforms_unavailable": ["tiktok"],
  "date_from": "2026-07-01T00:00:00Z",
  "date_to": "2026-08-10T00:00:00Z"
}
```

- `platforms` — one object per platform that returned data, each with the
  normalized metrics and the platform's own fields.
- `platforms_unavailable` — platforms that are unconfigured, failed, or
  rate-limited for this request. **This is how partial data is signaled: a
  `200` with a non-empty `platforms_unavailable` is a successful partial
  response, not an error.**
- `400` — `date_from` is after `date_to`.

### `GET /api/v1/analytics/video-performance/timeseries`

Daily timeseries with a platform dimension — one point per day per platform,
suitable for Chart.js rendering.

**Request:**

```bash
curl "http://localhost:8000/api/v1/analytics/video-performance/timeseries?video_id=abc123&platform=youtube"
```

**Response** (`200`):

```json
{
  "video_id": "abc123",
  "points": [
    {
      "date": "2026-08-10",
      "platform": "youtube",
      "views": 15230,
      "likes": 214,
      "comments": 41,
      "shares": 0
    }
  ]
}
```

Platforms that fail are silently skipped here (no `platforms_unavailable`
field on this endpoint); when nothing is configured the `points` list is
empty. Unconfigured/failed platforms produce no points rather than an error.

### `GET /api/v1/analytics/video-performance/optimal-times`

Day × hour heatmap of optimal posting times. The response is a
`heatmap` of `day_of_week (0 = Monday) → hour (0–23) → engagement score`
(0.0–1.0), ready to render as a 7×24 grid.

**Request:**

```bash
curl "http://localhost:8000/api/v1/analytics/video-performance/optimal-times?platform=instagram"
```

**Response** (`200`):

```json
{
  "heatmap": {
    "0": { "0": 0.0, "1": 0.0, "2": 0.0, "3": 0.0, "4": 0.0, "5": 0.0, "6": 0.0, "7": 0.0, "8": 0.0, "9": 0.0, "10": 0.0, "11": 0.0, "12": 0.0, "13": 0.0, "14": 0.0, "15": 0.0, "16": 0.0, "17": 0.0, "18": 0.0, "19": 0.0, "20": 0.0, "21": 0.0, "22": 0.0, "23": 0.0 },
    "1": { "0": 0.0, "1": 0.0, "2": 0.0, "3": 0.0, "4": 0.0, "5": 0.0, "6": 0.0, "7": 0.0, "8": 0.0, "9": 0.0, "10": 0.0, "11": 0.0, "12": 0.0, "13": 0.0, "14": 0.0, "15": 0.0, "16": 0.0, "17": 0.0, "18": 0.0, "19": 0.0, "20": 0.0, "21": 0.0, "22": 0.0, "23": 0.0 },
    "2": { "0": 0.0, "1": 0.0, "2": 0.0, "3": 0.0, "4": 0.0, "5": 0.0, "6": 0.0, "7": 0.0, "8": 0.0, "9": 0.0, "10": 0.0, "11": 0.0, "12": 0.0, "13": 0.0, "14": 0.0, "15": 0.0, "16": 0.0, "17": 0.0, "18": 0.0, "19": 0.0, "20": 0.0, "21": 0.0, "22": 0.0, "23": 0.0 },
    "3": { "0": 0.0, "1": 0.0, "2": 0.0, "3": 0.0, "4": 0.0, "5": 0.0, "6": 0.0, "7": 0.0, "8": 0.0, "9": 0.0, "10": 0.0, "11": 0.0, "12": 0.0, "13": 0.0, "14": 0.0, "15": 0.0, "16": 0.0, "17": 0.0, "18": 0.0, "19": 0.0, "20": 0.0, "21": 0.0, "22": 0.0, "23": 0.0 },
    "4": { "0": 0.0, "1": 0.0, "2": 0.0, "3": 0.0, "4": 0.0, "5": 0.0, "6": 0.0, "7": 0.0, "8": 0.0, "9": 0.0, "10": 0.0, "11": 0.0, "12": 0.0, "13": 0.0, "14": 0.0, "15": 0.0, "16": 0.0, "17": 0.0, "18": 0.0, "19": 0.0, "20": 0.0, "21": 0.0, "22": 0.0, "23": 0.0 },
    "5": { "0": 0.0, "1": 0.0, "2": 0.0, "3": 0.0, "4": 0.0, "5": 0.0, "6": 0.0, "7": 0.0, "8": 0.0, "9": 0.0, "10": 0.0, "11": 0.0, "12": 0.0, "13": 0.0, "14": 0.0, "15": 0.0, "16": 0.0, "17": 0.0, "18": 0.0, "19": 0.0, "20": 0.0, "21": 0.0, "22": 0.0, "23": 0.0 },
    "6": { "0": 0.0, "1": 0.0, "2": 0.0, "3": 0.0, "4": 0.0, "5": 0.0, "6": 0.0, "7": 0.0, "8": 0.0, "9": 0.0, "10": 0.0, "11": 0.0, "12": 0.0, "13": 0.0, "14": 0.0, "15": 0.0, "16": 0.0, "17": 0.0, "18": 0.0, "19": 0.0, "20": 0.0, "21": 0.0, "22": 0.0, "23": 0.0 }
  },
  "days_analyzed": 0,
  "platforms": ["instagram"]
}
```

> **Note:** the heatmap structure is initialized from the configured
> platforms (7 days × 24 hours), but `days_analyzed` is `0` and all scores
> are `0.0` in this release — the engagement scoring over stored history is
> not implemented yet. The endpoint is contract-stable (shape, day/hour
> indexing, platform filtering); treat the scores as placeholder data until
> the scoring backend lands.

### `GET /api/v1/analytics/video-performance/{video_id}`

Per-video drill-down: metrics for one video across all configured platforms,
plus the best-performing platform by views.

**Request:**

```bash
curl "http://localhost:8000/api/v1/analytics/video-performance/abc123"
```

**Response** (`200`):

```json
{
  "video_id": "abc123",
  "title": "",
  "platforms": [
    {
      "platform": "youtube",
      "views": 15230,
      "likes": 214,
      "comments": 41,
      "shares": 0,
      "watch_time_minutes": 0.0,
      "subscriber_change": 0,
      "completion_rate": 0.0,
      "plays": 0,
      "saves": 0
    }
  ],
  "platforms_unavailable": ["tiktok", "instagram"],
  "best_platform": "youtube"
}
```

- `best_platform` — the platform with the highest `views` among the
  responding platforms, or `null` when none responded.
- `title` — always `""` in this release (video titles are not fetched).
- `404` — the video was not found on any configured platform
  (all platforms responded but returned nothing).
- `502` — every platform is unavailable (no API keys configured, or all
  failed) — the server cannot determine whether the video exists.

---

## CLI

A Typer CLI exposes the same aggregation for terminal use.

```bash
python -m src.cli analytics video-performance                 # all platforms, last 30 days
python -m src.cli analytics video-performance --platform youtube
python -m src.cli analytics video-performance --days 7
```

| Option | Default | Description |
|--------|---------|-------------|
| `--platform` | `null` | Filter by platform (`youtube`, `tiktok`, `instagram`) |
| `--days` | `30` | Number of days to analyze |

Example output (no keys configured):

```
Platform             Views      Likes   Comments     Shares
-------------------------------------------------------
  No data available (no platforms configured or all returned errors)

Unavailable platforms: youtube, tiktok, instagram

Date range: 30 days
```

The CLI reads the same `YOUTUBE_API_KEY` / `TIKTOK_API_KEY` /
`INSTAGRAM_ACCESS_TOKEN` environment variables as the API.

---

## Error Handling

The feature is designed around **partial data on platform failures** —
one platform's outage never fails the request.

| Situation | HTTP | Behavior |
|-----------|------|----------|
| One or more platforms unconfigured/failed/rate-limited, at least one responded | `200` | `platforms_unavailable` lists the failed platforms; data for the rest is returned normally |
| All platforms unconfigured (aggregate endpoints) | `200` | Empty `platforms` / `points` list, all platforms in `platforms_unavailable` |
| All platforms unconfigured (drill-down `/{video_id}`) | `502` | `{"detail": "all_platforms_unavailable"}` — existence cannot be determined |
| Video not found on any responding platform | `404` | `{"detail": "video_not_found"}` |
| `date_from` after `date_to` | `400` | `{"detail": "date_from must be before or equal to date_to"}` |
| Malformed datetime / unknown platform filter | `422` | Pydantic validation error (FastAPI standard) |
| Unexpected internal error | `502` | `{"detail": "video_analytics_error: <exc>"}` |

Client-level guarantees:

- Each client has a 10 s HTTP timeout; `httpx.HTTPError` and unexpected
  exceptions are caught per client and converted to "unavailable", never
  raised to the caller.
- YouTube rate limiting (HTTP 429 / `X-RateLimit-Remaining: 0`) is recorded
  and the client reports the platform unavailable until the quota resets.
- TikTok quota exhaustion (HTTP 429) is handled the same way.
- Tokens are never logged; a missing key simply marks the platform
  unconfigured.

---

## Architecture

| Module | Role |
|--------|------|
| `src/services/video_analytics.py` | `VideoAPIClient` ABC + `YouTubeClient` / `TikTokClient` / `InstagramClient` (each fails independently) + `VideoAnalyticsService` (aggregation, timeseries, heatmap, drill-down) |
| `src/routers/video_analytics.py` | FastAPI router (`/api/v1/analytics/video-performance`), query validation, error mapping |
| `src/schemas/video_analytics.py` | Pydantic v2 response models (normalized per-platform metrics, timeseries points, heatmap, detail) |
| `src/config.py` | `YOUTUBE_API_KEY`, `YOUTUBE_OAUTH_TOKEN`, `TIKTOK_API_KEY`, `INSTAGRAM_ACCESS_TOKEN` settings |
| `src/cli.py` | Typer CLI — `analytics video-performance` command |
| `src/main.py` | Router registration |

The service pattern follows `src/services/llm_provider.py`: a client
abstraction per external platform, each owning its credentials, timeout, and
error handling. The router builds one client per configured platform per
request and hands them to the service — no shared mutable state, no caching
layer, always live data.

# Content Performance Analytics Dashboard

ContentForge v0.9.0 adds an event-log based analytics layer that closes the
create → optimize → publish → **analyze** loop. Every impression, click, share,
comment, conversion, and read-time event is appended to the `analytics_events`
table, and all dashboard metrics are aggregated from that log on read.

The dashboard answers:

- **What performed best?** — `GET /api/v1/analytics/dashboard` and `GET /api/v1/analytics/content/{id}`
- **Which channel wins?** — `GET /api/v1/analytics/channels`
- **Did the A/B test winner actually convert?** — `GET /api/v1/analytics/ab-results`
- **How good is this content?** — `GET /api/v1/analytics/score/{id}` (engagement + SEO + readability + compliance)
- **What happened over time?** — `GET /api/v1/analytics/trends` and `GET /api/v1/analytics/anomalies`
- **Give me the raw numbers** — `GET /api/v1/analytics/export` (CSV or JSON)

All endpoints are under the `/api/v1/analytics` prefix, work without
authentication (the auth dependency is optional), and return Pydantic-validated
JSON. No new runtime dependencies were added — aggregation uses the standard
library (`csv`, `json`, `statistics`).

---

## Setup

1. Run the server (SQLite tables including `analytics_events` are created
   automatically on startup):

   ```bash
   uvicorn src.main:app --reload
   ```

2. Point your event source at `POST /api/v1/analytics/track` (see below).

3. Track at least a few events, then open the dashboard:

   ```bash
   curl http://localhost:8000/api/v1/analytics/dashboard
   ```

There is nothing to configure — no API keys, no external analytics service, no
background jobs. Events are written synchronously on `POST /track` and read
back by every query endpoint.

> **Note on the legacy API:** the pre-v0.9.0 analytics router (`GET /analytics/content/{id}`,
> `GET /analytics/summary`) returned hardcoded stub data and has been replaced
> by the endpoints below. The legacy routes no longer exist.

---

## Data model: the event log

Every tracked action is one row in `analytics_events`:

| Column | Type | Description |
|--------|------|-------------|
| `id` | string (UUID) | Primary key, generated server-side |
| `generation_id` | string (FK → `generations.id`, CASCADE) | The content piece the event belongs to |
| `channel` | string | `twitter`, `linkedin`, `medium`, `blog`, `email`, `web`, `other` |
| `event_type` | string | `impression`, `click`, `share`, `comment`, `conversion`, `read_time` |
| `value` | integer | Event magnitude (default `1`) |
| `user_identifier` | string \| null | Optional anonymous user key |
| `metadata` | JSON | Free-form event metadata (stored; mapped as `event_metadata` in Python) |
| `occurred_at` | datetime (tz) | When the event happened (default: server now) |

### Canonical metric definitions

| Metric | Definition |
|--------|-----------|
| `impressions` | `SUM(value)` of `impression` events |
| `clicks` / `shares` / `comments` / `conversions` | `SUM(value)` of the matching event type |
| `read_time_seconds` | `SUM(value)` of `read_time` events |
| `engagement_rate` | `(clicks + shares + comments + conversions) / impressions`, clamped to `[0.0, 1.0]` |
| `avg_read_time_seconds` | Mean `value` of `read_time` events (per-content endpoint only) |

`value` lets you record weighted events, e.g. a `read_time` event with
`value: 180` for "someone read for 180 seconds", or an `impression` with
`value: 1000` for a bundled view count import. The field is constrained to
`0..1_000_000`.

---

## Tracking events — `POST /api/v1/analytics/track`

Records one analytics event. This is the only write endpoint; it is designed
to be called from webhooks, pixel/script tags, or a server-side collector.

**Request body:**

```json
{
  "generation_id": "gen_blog_launch",
  "channel": "twitter",
  "event_type": "click",
  "value": 3,
  "user_identifier": "user-42",
  "metadata": {"source": "docs-example"},
  "occurred_at": "2026-07-30T12:00:00Z"
}
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `generation_id` | yes | string | ID of the generation the event belongs to (must exist) |
| `channel` | no | string | Default `"web"`; one of the channels listed above |
| `event_type` | yes | enum | `impression`, `click`, `share`, `comment`, `conversion`, `read_time` |
| `value` | no | int | Default `1`; range `0..1_000_000` |
| `user_identifier` | no | string \| null | Anonymous identifier for cohort analysis |
| `metadata` | no | object | Free-form JSON metadata |
| `occurred_at` | no | datetime | Default: server time. Cannot be more than **24 hours in the future** |

**Response** (201 Created):

```json
{
  "status": "ok",
  "event_id": "9750950a-d062-49eb-ac08-b082dbca2ad9"
}
```

`event_id` is a freshly generated UUID — every call appends a row; there is no
deduplication.

**Errors:**

```json
{"detail": "Generation not found"}                                   // 404 — unknown generation_id
{"detail": "Invalid channel: 'myspace'"}                              // 422 — channel not in the allowed set
{"detail": "occurred_at cannot be more than 24 hours in the future"}  // 422 — occurred_at too far in the future
```

Schema-level failures (e.g. `event_type: "like"` or `value: -5`) return the
standard FastAPI 422 validation shape.

---

## Dashboard — `GET /api/v1/analytics/dashboard`

Aggregated metrics over a date window, with content-type and channel
breakdowns, the top-5 content pieces by impressions, and a daily time series.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `date_from` | datetime | 30 days ago | Window start (inclusive) |
| `date_to` | datetime | now | Window end (inclusive) |
| `channel` | string | — | Restrict to one channel |
| `content_type` | string | — | Restrict to one content type (`blog`, `social`, `email`, …) |

```bash
curl "http://localhost:8000/api/v1/analytics/dashboard?date_from=2026-07-01&date_to=2026-07-31"
```

**Response** (200 OK) — real output, truncated `time_series`:

```json
{
  "date_from": "2026-07-01 06:13:23.039859+00:00",
  "date_to": "2026-07-31 06:13:23.039859+00:00",
  "totals": {
    "impressions": 11930,
    "clicks": 363,
    "shares": 26,
    "comments": 9,
    "conversions": 36,
    "read_time_seconds": 720,
    "engagement_rate": 0.036378876781223805
  },
  "content_type_breakdown": {
    "blog": 1,
    "email": 1,
    "social": 1
  },
  "channel_breakdown": {
    "medium": {
      "impressions": 9400, "clicks": 65, "shares": 14, "comments": 9,
      "conversions": 6, "read_time_seconds": 180, "engagement_rate": 0.01
    },
    "email": {
      "impressions": 700, "clicks": 110, "shares": 0, "comments": 0,
      "conversions": 18, "read_time_seconds": 300, "engagement_rate": 0.18285714285714286
    },
    "twitter": {
      "impressions": 1680, "clicks": 188, "shares": 12, "comments": 0,
      "conversions": 12, "read_time_seconds": 0, "engagement_rate": 0.1261904761904762
    },
    "blog": {
      "impressions": 150, "clicks": 0, "shares": 0, "comments": 0,
      "conversions": 0, "read_time_seconds": 240, "engagement_rate": 0.0
    }
  },
  "top_content": [
    {
      "generation_id": "gen_blog_launch",
      "topic": "Understanding content analytics",
      "content_type": "blog",
      "impressions": 10030,
      "engagement_rate": 0.016350947158524427
    },
    {
      "generation_id": "gen_tweet_tips",
      "topic": "5 content marketing tips",
      "content_type": "social",
      "impressions": 1200,
      "engagement_rate": 0.11833333333333333
    }
  ],
  "time_series": [
    {"date": "2026-07-09", "impressions": 220, "clicks": 0, "shares": 0, "comments": 0, "conversions": 0, "engagement_rate": 0.0},
    {"date": "2026-07-18", "impressions": 5220, "clicks": 40, "shares": 0, "comments": 0, "conversions": 0, "engagement_rate": 0.007662835249042145},
    {"date": "2026-07-27", "impressions": 920, "clicks": 55, "shares": 12, "comments": 0, "conversions": 0, "engagement_rate": 0.09571428571428571},
    "… (one point per day that has events, sorted ascending)"
  ]
}
```

Notes:

- `content_type_breakdown` counts **distinct generations** with events, by type.
- `top_content` lists the top **5** generations by impressions (requires the
  generation rows to exist; generations without a matching row are skipped).
- `time_series` contains one point per day **that has at least one event**;
  days without events produce no point.
- `engagement_rate` of `0.0` on a day with impressions but no engagement
  events is normal — it is not an error.

**Errors:** `422` — `date_from` later than `date_to`:

```json
{"detail": "date_from must not be later than date_to"}
```

---

## Per-content performance — `GET /api/v1/analytics/content/{generation_id}`

All metrics for a single generation, plus its per-channel breakdown and the
compliance snapshot stored at generation time.

```bash
curl http://localhost:8000/api/v1/analytics/content/gen_blog_launch
```

**Response** (200 OK):

```json
{
  "generation_id": "gen_blog_launch",
  "content_type": "blog",
  "brand_voice_id": null,
  "topic": "Understanding content analytics",
  "model_used": "gpt-4o",
  "tokens_used": 1200,
  "compliance": {
    "overall": 85.0,
    "vocabulary": 80.0,
    "readability": 75.0,
    "tone": 90.0,
    "violations": []
  },
  "performance": {
    "views": 10030,
    "engagement_rate": 0.016350947158524427,
    "shares": 26,
    "comments": 9,
    "avg_read_time_seconds": 210
  },
  "channel_breakdown": {
    "medium": {"impressions": 9400, "clicks": 65, "shares": 14, "comments": 9, "conversions": 6, "read_time_seconds": 180, "engagement_rate": 0.01},
    "twitter": {"impressions": 480, "clicks": 58, "shares": 12, "comments": 0, "conversions": 0, "read_time_seconds": 0, "engagement_rate": 0.14583333333333334},
    "blog": {"impressions": 150, "clicks": 0, "shares": 0, "comments": 0, "conversions": 0, "read_time_seconds": 240, "engagement_rate": 0.0}
  },
  "score": null,
  "created_at": "2026-07-31 06:13:30",
  "updated_at": null
}
```

- `performance.views` mirrors `impressions` (the event log is the source of truth).
- `avg_read_time_seconds` is the mean `value` of `read_time` events (here:
  `(180 + 240) / 2 = 210`).
- `score` is always `null` on this endpoint — use `GET /score/{id}` for the
  content score.
- Supports the same `date_from` / `date_to` window parameters as the dashboard.

**Error** (404):

```json
{"detail": "Generation not found"}
```

---

## Channel comparison — `GET /api/v1/analytics/channels`

Compare the same metric across channels, sorted best-first, with the overall
winner identified.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `date_from` | datetime | 30 days ago | Window start |
| `date_to` | datetime | now | Window end |
| `metric` | string | `impressions` | Sort metric: `impressions`, `clicks`, `shares`, `comments`, `conversions`, `engagement_rate` |

```bash
curl "http://localhost:8000/api/v1/analytics/channels?metric=engagement_rate&date_from=2026-07-01&date_to=2026-07-31"
```

**Response** (200 OK, `metric=impressions`):

```json
{
  "date_from": "2026-07-01 06:13:30.664019+00:00",
  "date_to": "2026-07-31 06:13:30.664019+00:00",
  "channels": [
    {"channel": "medium", "impressions": 9400, "clicks": 65, "shares": 14, "comments": 9, "conversions": 6, "engagement_rate": 0.01},
    {"channel": "twitter", "impressions": 1680, "clicks": 188, "shares": 12, "comments": 0, "conversions": 12, "engagement_rate": 0.1261904761904762},
    {"channel": "email", "impressions": 700, "clicks": 110, "shares": 0, "comments": 0, "conversions": 18, "engagement_rate": 0.18285714285714286},
    {"channel": "blog", "impressions": 150, "clicks": 0, "shares": 0, "comments": 0, "conversions": 0, "engagement_rate": 0.0}
  ],
  "best_channel": "medium",
  "total_impressions": 11930
}
```

- Channels are returned sorted **descending** by the requested `metric` —
  `best_channel` is simply the first row (channels with no events are absent,
  not zero-filled).
- Only channels that actually have events in the window appear in the list.
- Channels are listed in the order they are first seen in the log, then sorted
  by the metric.

**Error** (422) — invalid metric:

```json
{"detail": "Invalid metric: 'likes'"}
```

---

## A/B test correlation — `GET /api/v1/analytics/ab-results`

Merges the A/B testing framework (v0.8.0) with the analytics event log: for
each variant of an A/B test, it aggregates the analytics events recorded
against the variant's `generation_id` and reports real conversion/engagement
numbers next to the test's declared winner.

**Query parameters:** `test_id` (required), plus the usual `date_from` /
`date_to` window.

```bash
curl "http://localhost:8000/api/v1/analytics/ab-results?test_id=ab_test_launch"
```

**Response** (200 OK):

```json
{
  "ab_test_id": "ab_test_launch",
  "name": "Launch email subject line test",
  "status": "concluded",
  "winner_variant_id": "variant_a",
  "variants": [
    {
      "variant_id": "variant_a",
      "name": "Subject A",
      "variant_type": "control",
      "generation_id": "gen_email_news",
      "impressions": 700,
      "conversions": 18,
      "conversion_rate": 0.025714285714285714,
      "engagement_rate": 0.18285714285714286,
      "is_winner": true
    },
    {
      "variant_id": "variant_b",
      "name": "Subject B",
      "variant_type": "treatment",
      "generation_id": "gen_blog_launch",
      "impressions": 10030,
      "conversions": 6,
      "conversion_rate": 0.0005982053838484546,
      "engagement_rate": 0.016350947158524427,
      "is_winner": false
    }
  ],
  "correlation_note": "Analytics conversion p=0.000 (100.0%) — matches A/B winner"
}
```

- `conversion_rate` = `conversions / impressions` from the **analytics event
  log**, not from the A/B service's own counters.
- `is_winner` mirrors `ABTest.winner_variant_id` (set when the test is
  concluded via the A/B API).
- `correlation_note` runs a chi-squared significance test on the variants'
  analytics conversion counts (via `AbStatsService`, the same calculator the
  A/B framework uses). It is non-empty whenever at least **two** variants have
  impressions; the note says "matches A/B winner" when the analytics numbers
  agree with the declared winner — a quick sanity check that the test's
  conclusion holds in real traffic.
- Variants without a `generation_id` (or whose generation has no events)
  report zeros.

**Error** (404):

```json
{"detail": "AB test not found"}
```

---

## Content scoring — `GET /api/v1/analytics/score/{generation_id}`

Deterministic, reproducible content-quality score (0–100) with a letter grade.
The same generation always scores the same value — the formula has no
randomness and never calls an LLM.

**Formula** — weighted average of four normalized sub-scores:

```
score = 0.35·engagement + 0.25·seo + 0.20·readability + 0.20·compliance
```

| Term | Weight | How it is computed |
|------|--------|--------------------|
| `engagement` | 0.35 | `min(impressions/2000, 1) · 50 + min(engagement_rate, 1) · 50`, clamped to 100 |
| `seo` | 0.25 | `0.7 · word-count tier + 0.3 · keyword-density score` (tiers: empty 0 / thin 30 / adequate 70 / comprehensive 90; density ideal 1.5%, penalty `|density − 1.5| · 40`) |
| `readability` | 0.20 | Flesch Reading Ease of the generated text, clamped to 0–100 |
| `compliance` | 0.20 | Overall compliance score stored on the generation (or the `content_analytics` snapshot) |

**Grade boundaries:** `A ≥ 90`, `B ≥ 75`, `C ≥ 60`, `D ≥ 45`, `F < 45`.

**Missing terms renormalize.** Sub-scores that cannot be computed drop out and
the remaining weights are renormalized — so a social post with no body text
(scores on engagement + compliance only) is still scored fairly, not
penalized for absent data. The dropped terms are returned as `0.0` in the
breakdown:

```bash
curl http://localhost:8000/api/v1/analytics/score/gen_tweet_tips
```

```json
{
  "generation_id": "gen_tweet_tips",
  "score": 48.31,
  "grade": "D",
  "breakdown": {
    "engagement": 35.92,
    "seo": 0.0,
    "readability": 0.0,
    "compliance": 70.0
  }
}
```

A full-text blog post scores on all four terms:

```json
{
  "generation_id": "gen_blog_launch",
  "score": 52.15,
  "grade": "D",
  "breakdown": {
    "engagement": 50.82,
    "seo": 33.0,
    "readability": 45.58,
    "compliance": 85.0
  }
}
```

**Error** (404):

```json
{"detail": "Generation not found"}
```

---

## Export — `GET /api/v1/analytics/export`

Export the raw event log aggregated to one row per `(date, generation_id,
content_type, channel, event_type)`, as CSV or JSON. This is the input you
would feed to a spreadsheet, BI tool, or archive.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `format` | string | `json` | `json` or `csv` |
| `date_from` / `date_to` | datetime | last 30 days | Window |
| `channel` | string | — | Filter by channel |
| `content_type` | string | — | Filter by content type |

**Response** (200 OK) — the `data` field carries the payload as a string:

```json
{
  "format": "json",
  "filename": "analytics_export_20260731.json",
  "content_type": "application/json",
  "data": "[{\"date\": \"2026-07-09\", \"generation_id\": \"gen_blog_launch\", \"content_type\": \"blog\", \"channel\": \"medium\", \"event_type\": \"impression\", \"value\": 220}, ...]"
}
```

CSV mode returns the same shape with `format: "csv"`, `content_type:
"text/csv"`, and a `data` string containing the delimited text. The CSV
columns are fixed:

```csv
date,generation_id,content_type,channel,event_type,value
2026-07-09,gen_blog_launch,blog,medium,impression,220
2026-07-18,gen_blog_launch,blog,medium,impression,5220
2026-07-24,gen_email_news,email,email,conversion,18
```

The suggested filename embeds the export date:
`analytics_export_YYYYMMDD.json` / `analytics_export_YYYYMMDD.csv`.

> The v0.9.0 spec originally proposed `POST /export`; the shipped contract is
> `GET /export` (a pure read, so GET is the safer verb).

**Error** (422) — invalid format:

```json
{"detail": "Invalid format: 'xml' (expected csv or json)"}
```

---

## Historical trends — `GET /api/v1/analytics/trends`

Daily time series for one metric, with per-point anomaly flags.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | string | `30d` | `7d`, `30d`, or `90d` |
| `metric` | string | `impressions` | `impressions`, `clicks`, `shares`, `comments`, `conversions`, `engagement_rate` |
| `channel` | string | — | Restrict to one channel |

```bash
curl "http://localhost:8000/api/v1/analytics/trends?period=30d&metric=impressions&channel=medium"
```

**Response** (200 OK, truncated to the anomaly day):

```json
{
  "period": "30d",
  "metric": "impressions",
  "points": [
    {"date": "2026-07-09", "impressions": 220, "clicks": 0, "shares": 0, "comments": 0, "conversions": 0, "engagement_rate": 0.0, "anomaly": false},
    {"date": "2026-07-17", "impressions": 220, "clicks": 0, "shares": 0, "comments": 0, "conversions": 0, "engagement_rate": 0.0, "anomaly": false},
    {"date": "2026-07-18", "impressions": 5220, "clicks": 40, "shares": 0, "comments": 0, "conversions": 0, "engagement_rate": 0.007662835249042145, "anomaly": true},
    {"date": "2026-07-19", "impressions": 220, "clicks": 0, "shares": 0, "comments": 0, "conversions": 0, "engagement_rate": 0.0, "anomaly": false},
    "…"
  ]
}
```

Each `point` carries every metric (the requested metric is just the one used
for anomaly detection) plus the `anomaly` flag.

---

## Anomaly detection — `GET /api/v1/analytics/anomalies`

Flags statistically unusual days using a standard **z-score** test on the
daily series:

- Computes the mean and population standard deviation of the daily metric
  values.
- Flags any day with `|z| >= 2.0` (about 2 standard deviations from the mean).
- Requires **at least 7 days with data**; shorter series return an empty list
  (no signal, no noise).
- A series with zero variance (all days identical) also returns no anomalies.

**Query parameters:** `period` (`7d`/`30d`/`90d`, default `30d`) and `metric`
(default `impressions`).

```bash
curl "http://localhost:8000/api/v1/analytics/anomalies?period=30d&metric=impressions"
```

**Response** (200 OK) — the 5220-impression day from the trends example above:

```json
{
  "period": "30d",
  "metric": "impressions",
  "anomalies": [
    {
      "date": "2026-07-18",
      "metric": "impressions",
      "value": 5220.0,
      "z_score": 4.442742506796402,
      "direction": "spike"
    }
  ]
}
```

`direction` is `spike` when `z > 0` and `drop` when `z < 0`.

---

## API reference summary

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/analytics/track` | Record an event (201) |
| `GET` | `/api/v1/analytics/dashboard` | Aggregated metrics + breakdowns + time series |
| `GET` | `/api/v1/analytics/content/{generation_id}` | Per-content performance |
| `GET` | `/api/v1/analytics/channels` | Cross-channel comparison |
| `GET` | `/api/v1/analytics/ab-results` | A/B variant ↔ analytics correlation |
| `GET` | `/api/v1/analytics/export` | CSV/JSON export of daily aggregates |
| `GET` | `/api/v1/analytics/score/{generation_id}` | Deterministic content score + grade |
| `GET` | `/api/v1/analytics/trends` | Daily trend series with anomaly flags |
| `GET` | `/api/v1/analytics/anomalies` | Statistically flagged days |

Error mapping: unknown `generation_id` / `test_id` → **404**; invalid
metric, period, format, channel, or inverted date window → **422**.

---

## Related

- [API Overview](api-overview.md) — full endpoint reference
- [Examples: Analytics](../examples/api_analytics.py) — track, query, and export walkthrough
- [Social Media Publishing](social-publishing.md) — the publish layer that produces the traffic you track

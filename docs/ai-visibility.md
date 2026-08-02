# AI Visibility Metrics

ContentForge v0.14.0 adds an **AI visibility tracking layer** that measures
how often your content is mentioned and cited by AI assistants — ChatGPT,
Perplexity, Gemini, and Google AI Overviews — and how much traffic those
assistants refer back to your site.

The feature answers:

- **Am I being cited by AI answers?** — `GET /api/v1/ai-visibility/{content_id}`
  (per-content snapshot: `citation_rate`, `share_of_voice`, `mention_rate`)
- **Where does my AI referral traffic come from?** — the same snapshot reports
  `ai_referral_traffic` and conversions per engine
- **How is visibility trending?** — `GET /api/v1/ai-visibility/trends`
  returns a Chart.js-ready series (7d/30d/90d)
- **How do I record an AI-referred visit?** — `POST /api/v1/ai-visibility/referral`
  (webhook-style ingestion, no auth required)

All endpoints live under the `/api/v1/ai-visibility` prefix, work without
authentication (the auth dependency is optional), and return
Pydantic-validated JSON.

---

## Setup

1. Run the server (SQLite tables — `ai_raw_mentions`, `ai_engine_metrics`,
   `ai_referral_traffic`, `ai_trend_aggregates` — are created automatically on
   startup):

   ```bash
   uvicorn src.main:app --reload
   ```

2. Configure at least one AI engine provider (see
   [Configuration](#configuration) below) or rely on referral ingestion only.

3. Create some content, then check its visibility:

   ```bash
   curl "http://localhost:8000/api/v1/ai-visibility/{content_id}"
   ```

### Configuration

| Environment variable | Required | Default | Description |
|----------------------|----------|---------|-------------|
| `AI_VISIBILITY_POLL_ENABLED` | No | `false` | Start the background polling loop on app startup. Off by default — the `POST /{content_id}/refresh` endpoint works regardless. |
| `AI_VISIBILITY_POLL_INTERVAL_SECONDS` | No | `86400` | Seconds between background poll cycles (default: once per day). |
| `AI_VISIBILITY_POLL_QUERIES_PER_CONTENT` | No | `5` | How many probe queries each engine receives per content piece per poll. |
| `AI_VISIBILITY_CONTENT_BASE_URL` | No | `""` | Public origin of your content (e.g. `https://contentforge.example`). The poller builds the canonical target URL as `<base>/generations/{id}` for citation detection. When empty, a reserved `https://contentforge.example` placeholder is used (deterministic, for tests/dev). |
| `PERPLEXITY_API_KEY` | No | `""` | Enables the Perplexity provider (real HTTP API, model `sonar`). |
| `GEMINI_API_KEY` | No | `""` | Enables the Gemini provider (real HTTP API, model `gemini-2.0-flash`). |
| `CHATGPT_SEARCH_API_KEY` | No | `""` | Enables the ChatGPT provider (structured LLM prompt, requires the app LLM provider). |
| `GOOGLE_AI_SEARCH_API_KEY` | No | `""` | Enables the Google AI Overviews provider (structured LLM prompt, requires the app LLM provider). |

Engines whose key is absent degrade gracefully: the poller still runs them,
but each check returns a "not mentioned" result instead of crashing the
cycle. Providers that are configured but fail (HTTP error, timeout, parse
error) raise `ProviderError` with a generic message — **credentials are never
leaked into error responses** — and the poller records the error and keeps
going.

---

## How it works: providers, polling, and the data flow

Visibility data is collected by **engine providers** — one per AI assistant:

| Engine id | Provider | Mechanism |
|-----------|----------|-----------|
| `chatgpt` | `ChatGPTProvider` | Structured LLM prompt (no stable public ChatGPT search API) |
| `perplexity` | `PerplexityProvider` | Real HTTP API — `https://api.perplexity.ai/chat/completions` (model `sonar`) |
| `gemini` | `GeminiProvider` | Real HTTP API — Google `generateContent` (model `gemini-2.0-flash`, web grounding) |
| `google_ai_overviews` | `GoogleAIOverviewsProvider` | Structured LLM prompt (no stable public AI Overviews API) |

Each check runs a probe query against the content's canonical URL and returns
a normalized `EngineVisibilityResult` (`mentioned`, `cited`, `sentiment`,
`snippet`). `ProviderRegistry` wires providers to settings: constructed
directly it registers all four engines (each degrading gracefully when its key
is missing); `ProviderRegistry.from_settings` registers only engines whose key
is present.

The **poller** (`AiVisibilityPoller`) is the engine that turns provider
results into metrics:

- `poll_once(db)` — the single testable core. For each tracked generation and
  each engine it runs `AI_VISIBILITY_POLL_QUERIES_PER_CONTENT` queries,
  records mentions, recomputes per-engine metrics, and rebuilds trend
  aggregates. It always returns a `PollResult` and never raises — per-engine
  failures land in `PollResult.errors`.
- `start()` / `shutdown()` — an optional background asyncio loop
  (`asyncio.sleep(interval)` between cycles) wired into the app lifespan when
  `AI_VISIBILITY_POLL_ENABLED=true`.
- On-demand refresh — `POST /api/v1/ai-visibility/{content_id}/refresh` runs a
  single `poll_once` cycle for one content piece, and builds a fresh poller
  on the fly when the background poller is disabled.

Mention rows are appended to `ai_raw_mentions`; daily aggregates are upserted
into `ai_engine_metrics` (per content + engine + day) and rolled up into
`ai_trend_aggregates` (per day + engine + metric) so trends queries never scan
the raw log.

---

## Data model

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `ai_raw_mentions` | Append-only raw mention log — one row per probe result that mentioned or cited the content | `generation_id` (FK → `generations.id`), `engine`, `query`, `brand_or_topic`, `mention_type` (`mention` \| `citation`), `cited_url`, `snippet`, `sentiment`, `sentiment_score`, `mentioned_at`, `raw_payload` |
| `ai_engine_metrics` | Per-(content, engine, day) aggregates, upserted by the poller | `generation_id`, `engine`, `metric_date`, `mentions`, `citations`, `citation_rate`, `mention_rate`, `share_of_voice`, `sentiment_positive/neutral/negative/avg`, `samples` — unique on `(generation_id, engine, metric_date)` |
| `ai_referral_traffic` | AI-referred visits and conversions | `generation_id`, `engine`, `referrer_url`, `landing_path`, `converted`, `conversion_value`, `referred_at` |
| `ai_trend_aggregates` | Cross-content daily rollups consumed by `/trends` | `metric_date`, `engine`, `metric`, `value`, `sample_size` — unique on `(metric_date, engine, metric)` |

---

## Metric definitions

All metrics are computed by pure, deterministic functions in
`src/ai_visibility/metrics.py` with zero-division guards and clamping.

| Metric | Definition | Range |
|--------|-----------|-------|
| `citation_rate` | `citations / mentions` — share of AI answers mentioning your brand that also link the content. `0.0` when there are no mentions. | `[0.0, 1.0]` |
| `mention_rate` | `mentions / samples` — how often the brand/content appears across the sampled answer set. `0.0` when no samples were taken. | `[0.0, 1.0]` |
| `share_of_voice` | `own_citations / corpus_citations × 100` — the content's share of all citations across the tracked corpus (all generations sharing the same `brand_or_topic`). `0.0` when the corpus has no citations. | `[0.0, 100.0]` |
| `ai_referral_traffic` | Count of AI-referred visits in the window. In trend aggregates it is the count of `ai_referral_traffic` rows for that day + engine. | non-negative int |
| `ai_referral_conversion_rate` | `conversions / referrals` — conversion rate of AI-referred visits. `0.0` when there are no referrals. | `[0.0, 1.0]` |
| `sentiment_average` | Mean of per-mention sentiment scores (each in `[-1.0, 1.0]`); `0.0` when there are no scored mentions. | `[-1.0, 1.0]` |

The per-content snapshot also reports **sentiment breakdowns** per engine:
counts of `positive`, `neutral`, and `negative` mentions (labels outside these
three are tallied as `unknown`).

---

## API reference

All endpoints are under `/api/v1/ai-visibility`. Authentication is **optional**
on every route — you can query without a token, and pass a JWT bearer token if
you want tenant scoping.

**Errors:** unknown `generation_id` → `404`; invalid `days` (must be 7, 30, or
90), unknown `engine`, or unknown `metric` → `422`.

### `GET /api/v1/ai-visibility/{content_id}`

Per-content AI visibility snapshot over a window (default: last 30 days).

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `days` | int | `30` | Window length in days — one of `7`, `30`, `90` (anything else → 422) |

```bash
curl "http://localhost:8000/api/v1/ai-visibility/gen_a1b2c3d4e5f6?days=30"
```

**Response** (200 OK):

```json
{
  "content_id": "gen_demo_ai_vis",
  "topic": "Understanding AI visibility",
  "content_type": "blog",
  "date_from": "2026-07-04",
  "date_to": "2026-08-02",
  "summary": {
    "total_mentions": 13,
    "total_citations": 3,
    "overall_citation_rate": 0.23076923076923078,
    "avg_share_of_voice": 45.83333333333333,
    "avg_mention_rate": 0.75,
    "ai_referral_traffic": 6,
    "ai_referral_conversions": 2,
    "ai_referral_conversion_rate": 0.3333333333333333
  },
  "engines": [
    {
      "engine": "chatgpt",
      "mentions": 6,
      "citations": 1,
      "citation_rate": 0.16666666666666666,
      "share_of_voice": 100.0,
      "mention_rate": 1.0,
      "sentiment": {
        "positive": 2,
        "neutral": 3,
        "negative": 1,
        "avg": 0.0
      },
      "ai_referral_traffic": 3,
      "ai_referral_conversions": 1,
      "ai_referral_conversion_rate": 0.3333333333333333
    },
    {
      "engine": "perplexity",
      "mentions": 4,
      "citations": 1,
      "citation_rate": 0.25,
      "share_of_voice": 50.0,
      "mention_rate": 1.0,
      "sentiment": {
        "positive": 1,
        "neutral": 3,
        "negative": 0,
        "avg": 0.0
      },
      "ai_referral_traffic": 2,
      "ai_referral_conversions": 1,
      "ai_referral_conversion_rate": 0.5
    },
    {
      "engine": "gemini",
      "mentions": 3,
      "citations": 1,
      "citation_rate": 0.3333333333333333,
      "share_of_voice": 33.33333333333333,
      "mention_rate": 1.0,
      "sentiment": {
        "positive": 0,
        "neutral": 3,
        "negative": 0,
        "avg": 0.0
      },
      "ai_referral_traffic": 1,
      "ai_referral_conversions": 0,
      "ai_referral_conversion_rate": 0.0
    },
    {
      "engine": "google_ai_overviews",
      "mentions": 0,
      "citations": 0,
      "citation_rate": 0.0,
      "share_of_voice": 0.0,
      "mention_rate": 0.0,
      "sentiment": {
        "positive": 0,
        "neutral": 0,
        "negative": 0,
        "avg": 0.0
      },
      "ai_referral_traffic": 0,
      "ai_referral_conversions": 0,
      "ai_referral_conversion_rate": 0.0
    }
  ],
  "time_series": [
    {
      "date": "2026-08-02",
      "citation_rate": 0.23076923076923078,
      "share_of_voice": 61.11111111111111,
      "mention_rate": 1.0,
      "ai_referral_traffic": 6
    }
  ]
}
```



The `engines` array always contains all four engines in canonical order
(`chatgpt`, `perplexity`, `gemini`, `google_ai_overviews`), zero-filled when a
given engine has no data. `time_series` has one point per day that has
engine-metric data in the window.

### `GET /api/v1/ai-visibility/trends`

Chart.js-ready trend series built from `ai_trend_aggregates`. `dates` maps
directly to Chart.js `labels`; each entry in `series` is one dataset.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `days` | int | `30` | Window length — `7`, `30`, or `90` (anything else → 422) |
| `engine` | str | — | Filter to one engine id (`chatgpt`, `perplexity`, `gemini`, `google_ai_overviews`); omit for all |
| `metric` | str | — | Filter to one metric (`citation_rate`, `share_of_voice`, `mention_rate`, `ai_referral_traffic`); omit for all |

```bash
curl "http://localhost:8000/api/v1/ai-visibility/trends?days=30&metric=citation_rate"
```

**Response** (200 OK):

```json
{
  "period": "30d",
  "days": 30,
  "date_from": "2026-07-04",
  "date_to": "2026-08-02",
  "dates": ["2026-07-04", "...", "2026-08-02"],
  "series": [
    {
      "engine": "chatgpt",
      "metric": "citation_rate",
      "data": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.16666666666666666]
    }
  ],
  "totals": {
    "citation_rate": 0.25,
    "share_of_voice": 61.11111111111111,
    "mention_rate": 1.0,
    "ai_referral_traffic": 6.0
  }
}
```



`totals` always contains all four metric keys — rate metrics are the mean
across the window, `ai_referral_traffic` is the sum — `0.0` when there is no
data. Days without data are zero-filled per series.

### `POST /api/v1/ai-visibility/referral`

Ingest one AI-referred visit. Webhook-style and **unauthenticated** — call it
from your analytics pixel, a server-side collector, or a reverse-proxy log
processor when a visitor arrives with a referrer matching an AI assistant.

**Request body:**

```json
{
  "generation_id": "gen_a1b2c3d4e5f6",
  "engine": "chatgpt",
  "referrer_url": "https://chatgpt.com/c/67f3...",
  "landing_path": "/blog/understanding-content-analytics",
  "converted": false,
  "conversion_value": 0.0,
  "occurred_at": "2026-08-02T12:00:00Z"
}
```

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `generation_id` | yes | string | ID of the content the visit landed on (must exist → else 404) |
| `engine` | yes | enum | `chatgpt`, `perplexity`, `gemini`, or `google_ai_overviews` (else 422) |
| `referrer_url` | yes | string | Referrer URL, max 512 chars |
| `landing_path` | no | string | Landing path on your site, default `"/"`, max 255 chars |
| `converted` | no | bool | Whether the visit converted, default `false` |
| `conversion_value` | no | float | Revenue/score of the conversion, default `0.0`, must be ≥ 0 |
| `occurred_at` | no | datetime | When the visit happened; default: server time |

**Response** (201 Created):

```json
{
  "status": "ok",
  "referral_id": "3bb2c3da-072f-4915-bf17-751634f956a2"
}
```

Referrer-domain mapping is provided by `AI_ENGINE_REFERRER_DOMAINS` for
convenience: `chatgpt.com`, `perplexity.ai`, `gemini.google.com`, `google.com`.

### `POST /api/v1/ai-visibility/{content_id}/refresh`

On-demand visibility refresh — runs one poll cycle for the given content
piece and returns the `PollResult`. Works standalone: when the background
poller is disabled (the default), a fresh poller is built from the configured
providers. With no provider API keys configured, the cycle still completes
successfully — `engines_polled` is empty and `queries_run` is `0` (every
provider degrades gracefully). With keys configured, `engines_polled` lists
those engines and `queries_run` = engines × content × queries-per-content.

```bash
curl -X POST http://localhost:8000/api/v1/ai-visibility/gen_a1b2c3d4e5f6/refresh
```

**Response** (200 OK):

```json
{
  "started_at": "2026-08-02T20:26:20.992491Z",
  "finished_at": "2026-08-02T20:26:21.041217Z",
  "engines_polled": [],
  "queries_run": 0,
  "mentions_recorded": 0,
  "errors": []
}
```

`engines_polled` lists only the engines with configured providers;
`errors` collects per-engine failures — the cycle never raises and never
aborts on a single failing engine.

---

## Dashboard configuration (Chart.js)

The `/trends` response is shaped for Chart.js: `dates` → `labels`, `series` →
`datasets`. A minimal line chart for `citation_rate` across all engines:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>AI Visibility — citation rate</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
</head>
<body>
  <canvas id="vis" width="900" height="350"></canvas>
  <script>
    const palette = {
      chatgpt: "#10a37f",
      perplexity: "#20808d",
      gemini: "#4285f4",
      google_ai_overviews: "#34a853"
    };

    fetch("http://localhost:8000/api/v1/ai-visibility/trends?days=30&metric=citation_rate")
      .then((r) => r.json())
      .then((data) => {
        new Chart(document.getElementById("vis"), {
          type: "line",
          data: {
            labels: data.dates,
            datasets: data.series.map((s) => ({
              label: `${s.engine} — citation_rate`,
              data: s.data,
              borderColor: palette[s.engine] ?? "#888",
              tension: 0.2,
              spanGaps: true
            }))
          },
          options: {
            scales: {
              y: { min: 0, max: 1, title: { display: true, text: "citation_rate" } }
            }
          }
        });
      });
  </script>
</body>
</html>
```

The `totals` object is handy for summary cards: display the mean
`citation_rate`, mean `share_of_voice`, mean `mention_rate`, and total
`ai_referral_traffic` for the selected window.

---

## Example

The runnable [AI visibility example](../examples/api_ai_visibility.py)
walks the full loop: generate content (or reuse a generation id), ingest
referrals for all four engines, run an on-demand refresh, then query the
per-content snapshot and the trends feed.

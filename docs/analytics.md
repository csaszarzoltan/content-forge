# Analytics

> **Superseded in v0.9.0.** This page documented the legacy analytics stub
> (`GET /analytics/content/{id}`, `GET /analytics/summary`), which returned
> hardcoded data and has been **removed**. The event-log based Content
> Performance Analytics Dashboard replaced it — see
> **[Analytics Dashboard](analytics-dashboard.md)** for the current API:
>
> - `POST /api/v1/analytics/track` — record impressions, clicks, shares,
>   comments, conversions, read-time events
> - `GET /api/v1/analytics/dashboard` — aggregated metrics, breakdowns, top content
> - `GET /api/v1/analytics/content/{generation_id}` — per-content performance
> - `GET /api/v1/analytics/channels` — cross-channel comparison
> - `GET /api/v1/analytics/ab-results` — A/B variant ↔ analytics correlation
> - `GET /api/v1/analytics/score/{generation_id}` — content quality score
> - `GET /api/v1/analytics/export` — CSV/JSON export
> - `GET /api/v1/analytics/trends` / `GET /api/v1/analytics/anomalies` — historical trends and anomaly detection
>
> ## Related
>
> - [Analytics Dashboard](analytics-dashboard.md) — full guide with request/response examples
> - [API Overview](api-overview.md) — complete endpoint reference
> - [Examples: Analytics](../examples/api_analytics.py)

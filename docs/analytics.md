# Analytics

Track content performance and compliance metrics.

The analytics service is an **in-memory stub** that returns default-zero values. In production, it queries the `generations` and `content_analytics` database tables for real data.

---

## Content analytics

**`GET /analytics/content/{generation_id}`**

Retrieve compliance and performance data for a specific generation.

```bash
curl http://localhost:8000/analytics/content/gen_a1b2c3d4e5f6
```

**Response** (200 OK):
```json
{
  "generation_id": "gen_a1b2c3d4e5f6",
  "content_type": "blog",
  "brand_voice_id": null,
  "compliance": {
    "overall": 0.95,
    "vocabulary": 0.95,
    "readability": 0.95,
    "tone": 0.95,
    "violations": []
  },
  "performance": {
    "views": 142,
    "engagement_rate": 0.037,
    "shares": 12,
    "comments": 8,
    "avg_read_time_seconds": 185
  },
  "model_used": "gpt-4o",
  "tokens_used": 456,
  "created_at": "2026-07-22T19:55:00+00:00",
  "updated_at": "2026-07-23T10:30:00+00:00"
}
```

### Response fields

| Field | Description |
|-------|-------------|
| `generation_id` | The generation UUID |
| `content_type` | `blog`, `social`, or `email` |
| `brand_voice_id` | Brand voice used (may be null) |
| `compliance` | Compliance score breakdown: `overall`, `vocabulary`, `readability`, `tone`, `violations` |
| `performance` | Performance metrics: `views`, `engagement_rate`, `shares`, `comments`, `avg_read_time_seconds` |
| `model_used` | LLM model used for generation |
| `tokens_used` | Total tokens consumed |
| `created_at` / `updated_at` | Timestamps |

**Error** (404):
```json
{"detail": "Generation not found"}
```

---

## Analytics summary

**`GET /analytics/summary`**

Aggregate metrics across all content.

```bash
curl http://localhost:8000/analytics/summary
```

**Response** (200 OK):
```json
{
  "total_generations": 42,
  "avg_compliance": 0.91,
  "content_type_breakdown": {
    "blog": 18,
    "social": 15,
    "email": 9
  },
  "total_views": 5840,
  "avg_engagement_rate": 0.042
}
```

| Field | Description |
|-------|-------------|
| `total_generations` | Total content pieces generated |
| `avg_compliance` | Average compliance score across all content |
| `content_type_breakdown` | Count of generations by type |
| `total_views` | Total views across all published content |
| `avg_engagement_rate` | Average engagement rate (0.0–1.0) |

---

## Production readiness

The analytics service currently returns **hardcoded stub data**. For production:

1. Implement real database queries that JOIN `generations` + `content_analytics` tables
2. Add a webhook endpoint (`POST /analytics/webhook`) for external platforms to push metrics
3. Implement time-range filtering (`?from=...&to=...`) for summary endpoint
4. Add per-brand voice analytics breakdown
5. Consider caching aggregate summaries

---

## Related

- [Content Generation](content-generation.md) — Generate the content tracked here
- [API Overview](api-overview.md) — Full endpoint reference
- [Examples: Analytics](../examples/api_analytics.py)

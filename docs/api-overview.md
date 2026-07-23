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
  "version": "0.3.0"
}
```

---

### `GET /health`

Health check for deployment monitoring and load balancers.

```json
{
  "status": "healthy",
  "version": "0.3.0",
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

Retrieve performance and compliance analytics for a specific generation.

**Response** (200 OK):
```json
{
  "generation_id": "gen_a1b2c3d4e5f6",
  "content_type": "blog",
  "brand_voice_id": null,
  "compliance": {
    "overall": 0.0,
    "vocabulary": 0.0,
    "readability": 0.0,
    "tone": 0.0,
    "violations": []
  },
  "performance": {
    "views": 0,
    "engagement_rate": 0.0,
    "shares": 0,
    "comments": 0,
    "avg_read_time_seconds": 0
  },
  "model_used": "gpt-4o",
  "tokens_used": 0,
  "created_at": "2026-07-22T19:55:00+00:00",
  "updated_at": null
}
```

**Error** (404):
```json
{"detail": "Generation not found"}
```

---

### `GET /analytics/summary`

Get aggregate analytics across all content.

**Response** (200 OK):
```json
{
  "total_generations": 0,
  "avg_compliance": 0.0,
  "content_type_breakdown": {},
  "total_views": 0,
  "avg_engagement_rate": 0.0
}
```

---

## Error handling

All endpoints return standard HTTP status codes:

| Status | Meaning |
|--------|---------|
| `200` | Success |
| `201` | Created |
| `204` | No Content (delete operations) |
| `404` | Resource not found |
| `422` | Validation error (invalid input) |
| `500` | Internal server error |

Validation errors include a structured detail:

```json
{"detail": [{"loc": ["body", "topic"], "msg": "field required", "type": "value_error.missing"}]}
```

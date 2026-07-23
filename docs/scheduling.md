# Content Scheduling

Schedule generated content for automatic publishing at a future time.

The scheduler is an **in-memory service** — jobs are stored in the application's runtime state. In production, the scheduler should be backed by APScheduler with a SQLAlchemy job store for persistence across restarts.

---

## Schedule content

**`POST /schedule`**

```bash
curl -X POST http://localhost:8000/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "generation_id": "gen_a1b2c3d4e5f6",
    "publish_at": "2026-08-01T09:00:00Z",
    "platform": "blog",
    "platform_config": {"channel_id": "my-blog-channel"},
    "retry_on_failure": true,
    "max_retries": 3
  }'
```

**Request fields:**

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `generation_id` | Yes | string | ID of the generated content to publish |
| `publish_at` | Yes | string (ISO 8601) | When to publish — must be in the future |
| `platform` | Yes | string | One of `twitter`, `linkedin`, `email`, `blog` |
| `platform_config` | No | object | Platform-specific config (`account_id`, `channel_id`) |
| `retry_on_failure` | No | bool | Whether to retry on publish failure (default: `true`) |
| `max_retries` | No | int | Max retry attempts (default: `3`) |

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

---

## Get schedule status

**`GET /schedule/{schedule_id}`**

```bash
curl http://localhost:8000/schedule/sch_a1b2c3d4e5f6
```

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

Status values:
| Status | Meaning |
|--------|---------|
| `scheduled` | Post is queued for publishing |
| `pending` | Awaiting publishing time |
| `published` | Successfully published |
| `failed` | Publishing failed after retries |
| `cancelled` | Cancelled by user |

---

## Cancel a scheduled post

**`DELETE /schedule/{schedule_id}`**

```bash
curl -X DELETE http://localhost:8000/schedule/sch_a1b2c3d4e5f6
```

**Response** (204 No Content).

---

## Error cases

| Status | Condition |
|--------|-----------|
| `422` | `publish_at` is in the past |
| `404` | Schedule ID not found (currently not enforced — in-memory stub) |

---

## Production readiness

The current scheduler is an **in-memory stub**. For production:

1. Integrate [APScheduler](https://apscheduler.readthedocs.io/) with `AsyncIOScheduler`
2. Use SQLAlchemy job store for persistence across restarts
3. Implement real platform publishers (Twitter API, LinkedIn API, email SMTP, blog CMS API)
4. Add webhook callbacks for publish status updates

---

## Related

- [Content Generation](content-generation.md) — Generate the content to schedule
- [Examples: Scheduling](../examples/api_scheduling.py)

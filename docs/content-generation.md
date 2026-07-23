# Content Generation

Generate blog posts, social media copy, and emails via LLM with brand voice injection.

**Endpoint:** `POST /generate/{content_type}`

---

## Content types

| Type | Description |
|------|-------------|
| `blog` | Long-form blog articles with structure, paragraphs, and optional calls-to-action |
| `social` | Short-form social media posts optimised for engagement |
| `email` | Email copy suitable for newsletters, announcements, and drip campaigns |

---

## Request

```json
POST /generate/blog
Content-Type: application/json

{
  "topic": "Microservices vs Monoliths in 2026",
  "brand_voice_id": "a1b2c3d4-...",
  "user_id": "user-abc",
  "project_id": "project-xyz",
  "parameters": {
    "audience": "Engineering managers",
    "length": "medium",
    "tone_override": null,
    "include_cta": true,
    "custom_instructions": "Focus on cost implications"
  }
}
```

### Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `topic` | Yes | string | Subject of the content (min 1 character) |
| `brand_voice_id` | No | string or null | Brand voice UUID; falls back to active scope or default preset |
| `user_id` | No | string or null | User identifier for voice scoping |
| `project_id` | No | string or null | Project identifier for voice scoping (overrides user scope) |
| `parameters` | No | object | Optional generation parameters |

### Parameters

| Field | Default | Description |
|-------|---------|-------------|
| `audience` | `null` | Target audience description |
| `length` | `"medium"` | One of `"short"`, `"medium"`, `"long"` |
| `tone_override` | `null` | Override the brand voice tone for this request |
| `include_cta` | `true` | Whether to include a call-to-action |
| `custom_instructions` | `null` | Additional instructions for the LLM |

---

## Response

```json
{
  "id": "gen_a1b2c3d4e5f6",
  "content_type": "blog",
  "generated_text": "In the ongoing debate between microservices and monolithic architectures...",
  "brand_voice_id": "a1b2c3d4-...",
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

### Response fields

| Field | Description |
|-------|-------------|
| `id` | Unique generation ID (prefix `gen_`) |
| `content_type` | The content type requested |
| `generated_text` | The LLM-generated content |
| `brand_voice_id` | Brand voice used (may be null if none resolved) |
| `compliance_score` | Object with compliance dimensions: `overall`, `vocabulary`, `readability`, `tone`, and `violations` list |
| `model_used` | LLM model that generated the content |
| `tokens_used` | Total tokens consumed (prompt + completion) |
| `latency_ms` | LLM call round-trip time in milliseconds |
| `created_at` | ISO 8601 timestamp |

---

## Voice resolution order

When no explicit `brand_voice_id` is provided, the system resolves the voice in this priority:

1. Explicit `brand_voice_id` from the request
2. Project-level voice scope (if `project_id` is set)
3. User-level voice scope (if `user_id` is set)
4. Global default voice
5. No voice — generation proceeds without brand customisation

---

## Error cases

| Status | Condition |
|--------|-----------|
| `422` | Invalid `content_type` (must be `blog`, `social`, or `email`) |
| `422` | Missing or empty `topic` |
| `422` | Invalid `length` value |
| `500` | LLM provider failure (API key missing, rate limit, network error) |

---

## Using curl

```bash
curl -X POST http://localhost:8000/generate/blog \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI in 2026", "parameters": {"length": "short"}}'
```

## Using Python

```python
import httpx

response = httpx.post(
    "http://localhost:8000/generate/blog",
    json={
        "topic": "Future of work",
        "brand_voice_id": "your-bv-id",
        "parameters": {"length": "long", "audience": "HR professionals"},
    },
)
print(response.json()["generated_text"])
```

---

## Related

- [Brand Voice API](brand-voice-api.md) — Create and manage brand voices
- [Scheduling](scheduling.md) — Schedule generated content
- [Analytics](analytics.md) — Track content performance

# Brand Voice API

CRUD operations for brand voice profiles — the foundation of ContentForge's brand-aligned generation.

A brand voice profile captures:
- **Brand identity** — who you are, your audience, your purpose
- **Attributes** — formality, enthusiasm, expertise level (as scored dimensions)
- **Vocabulary** — preferred terms and banned words
- **Scenarios** — per-scenario tone adjustments
- **Formatting** — structural preferences (headers, lists, emoji usage)

---

## Create a brand voice

**`POST /brand-voice`**

```bash
curl -X POST http://localhost:8000/brand-voice \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TechCorp Pro",
    "description": "Professional tech brand",
    "brand_identity": {
      "who": "Enterprise SaaS company",
      "audience": "CTOs and engineering leaders",
      "purpose": "Build trust through clarity"
    },
    "attributes": [
      {"trait": "formality", "value": 0.8, "min_label": "Casual", "max_label": "Formal"},
      {"trait": "enthusiasm", "value": 0.4, "min_label": "Reserved", "max_label": "Energetic"}
    ],
    "vocabulary": {
      "preferred": ["scalable", "enterprise-grade", "robust", "proven"],
      "banned": ["amazing", "game-changer", "disruptive"]
    },
    "scenarios": [
      {"name": "crisis", "tone_adjustment": "more_formal", "banned_terms_extra": ["panic"]}
    ],
    "formatting": {"headers": "sentence_case", "lists": "bullets", "emoji": "never"},
    "user_id": null
  }'
```

**Response** (201 Created): Full [BrandVoiceResponse](#brandvoiceresponse).

---

## List brand voices

**`GET /brand-voice?limit=20&offset=0`**

```bash
curl http://localhost:8000/brand-voice
```

Returns paginated results with `total`, `limit`, `offset`, and `items` array.

---

## Get a brand voice

**`GET /brand-voice/{id}`**

```bash
curl http://localhost:8000/brand-voice/a1b2c3d4-...
```

Returns a single [BrandVoiceResponse](#brandvoiceresponse) or **404**.

---

## Update a brand voice

**`PUT /brand-voice/{id}`**

Partial update — only send fields you want to change. Auto-increments the version.

```bash
curl -X PUT http://localhost:8000/brand-voice/a1b2c3d4-... \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TechCorp Pro v2",
    "attributes": [{"trait": "formality", "value": 0.9, ...}]
  }'
```

**Response** (200 OK): Full [BrandVoiceResponse](#brandvoiceresponse) with `version` incremented by 1.

---

## Delete a brand voice

**`DELETE /brand-voice/{id}`**

```bash
curl -X DELETE http://localhost:8000/brand-voice/a1b2c3d4-...
```

Soft-deletes the profile (sets `deleted_at`). The record stays in the database but is excluded from all queries.

**Response** (204 No Content).

---

## BrandVoiceResponse schema

```json
{
  "id": "a1b2c3d4-...",
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
  "vocabulary": {"preferred": ["scalable"], "banned": ["amazing"]},
  "scenarios": [{"name": "crisis", "tone_adjustment": "more_formal"}],
  "formatting": {"headers": "sentence_case", "lists": "bullets", "emoji": "never"},
  "metadata": {"version": "1"},
  "version": 1,
  "created_at": "2026-07-22T19:55:00+00:00",
  "updated_at": "2026-07-22T19:55:00+00:00"
}
```

---

## Library

The brand voice system also ships as a standalone Python library in `src/brand_voice/` with 9 modules covering presets, templates, compliance scoring, voice extraction, and more. See the [brand voice documentation](index.md).

---

## Related

- [Content Generation](content-generation.md) — Use your brand voices to generate content
- [Brand Voice Library docs](index.md) — Python library reference for presets, templates, compliance
- [Examples: Brand Voice API](../examples/api_brand_voice.py)

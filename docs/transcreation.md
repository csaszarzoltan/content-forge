# Transcreation — Cultural Adaptation & Preflight

ContentForge v0.14.0 adds a **transcreation** pipeline that goes beyond translation: it detects cultural risks, converts locale-specific formatting (dates, currency, units, honorifics), flags low-confidence segments for human review, and blocks publishing until risks are resolved or explicitly overridden.

## Features

| Tier | Module | Description |
|------|--------|-------------|
| P0 | **Cultural risk detection** | Scan text for idioms, cultural references, register mismatches, and taboo terms — with both LLM-powered and rule-based analysis |
| P0 | **Locale formatting** | Convert dates (MM/DD/YYYY → DD.MM.YYYY), currency ($1,000 → 1.000 €), imperial→metric units, and honorific titles (Mr. → Herr) for 9 target locales |
| P0 | **Side-by-side review** | Per-segment accept/edit/reject workflow with literal vs. adapted text comparison |
| P0 | **Preflight publish gate** | Block publishing when high-risk items are detected; override available for explicit human approval |
| P0 | **Export with flag resolution** | Export accepted adaptations only after all low-confidence flags are resolved (US-003 AC2) |
| P1 | **LLM + rule dual path** | LLM provider when configured; deterministic rule-based fallback on any LLM failure (graceful degradation) |
| P1 | **Per-asset persistence** | Analysis, adaptation, and preflight results stored per asset in SQLite (product_ops pattern) |

## Supported Locales

| Locale | Name | Date Format | Currency | Number Format | Units | Honorific Position |
|--------|------|-------------|----------|---------------|-------|--------------------|
| `en-US` | English (US) | MM/DD/YYYY | $ (prefix) | 1,000.00 | imperial | prefix |
| `en-GB` | English (UK) | DD/MM/YYYY | £ (prefix) | 1,000.00 | imperial | prefix |
| `de-DE` | German (Germany) | DD.MM.YYYY | € (suffix) | 1.000,00 | metric | prefix |
| `fr-FR` | French (France) | DD/MM/YYYY | € (suffix) | 1 000,00 | metric | prefix |
| `es-ES` | Spanish (Spain) | DD/MM/YYYY | € (suffix) | 1.000,00 | metric | prefix |
| `it-IT` | Italian (Italy) | DD/MM/YYYY | € (suffix) | 1.000,00 | metric | prefix |
| `pt-BR` | Portuguese (Brazil) | DD/MM/YYYY | R$ (prefix) | 1.000,00 | metric | prefix |
| `ja-JP` | Japanese (Japan) | YYYY/MM/DD | ￥ (prefix) | 1,000.00 | metric | **suffix** |
| `zh-CN` | Chinese (Simplified) | YYYY-MM-DD | ¥ (prefix) | 1,000.00 | metric | **suffix** |

Language prefixes (e.g. `de`, `fr`) are accepted and resolve to the canonical full locale code.

## API Endpoints

All endpoints are under `/api/v1/transcreation` and require no authentication.

### `POST /api/v1/transcreation/analyze`

Detect cultural risks and locale formatting issues in content.

**Request body:**
```json
{
  "text": "It's raining cats and dogs. The upgrade costs $1,000 on 07/04/2026.",
  "target_locale": "de-DE",
  "source_locale": "auto"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | yes | — | Content to analyze (1–100,000 chars) |
| `target_locale` | string | yes | — | Target locale code (e.g. `de-DE`) |
| `source_locale` | string | no | `"auto"` | Source locale or `"auto"` for auto-detect |

**Response** (200 OK):
```json
{
  "risk_items": [
    {
      "id": "risk-1",
      "segment": "It's raining cats and dogs.",
      "category": "idiom",
      "original_text": "raining cats and dogs",
      "issue_description": "English idiom that does not translate literally.",
      "confidence": 0.65,
      "risk_level": "medium",
      "suggested_replacement": "Es regnet in Strömen.",
      "locale": "de-DE"
    }
  ],
  "format_items": [
    {
      "id": "fmt-date-1",
      "original": "07/04/2026",
      "converted": "04.07.2026",
      "format_type": "date",
      "ambiguous": true,
      "locale": "de-DE"
    },
    {
      "id": "fmt-currency-1",
      "original": "$1,000",
      "converted": "1.000 €",
      "format_type": "currency",
      "ambiguous": false,
      "locale": "de-DE"
    }
  ],
  "overall_risk": "medium",
  "locale": "de-DE"
}
```

**Risk categories:** `idiom`, `cultural_reference`, `register`, `taboo`

**Risk levels:** `low`, `medium`, `high`

**Errors:** `422` malformed body (empty text, empty locale); `502`/`503` LLM provider failure.

---

### `POST /api/v1/transcreation/adapt`

Culturally adapt content with per-segment review decisions (accept/edit/reject).

**Request body:**
```json
{
  "text": "It's raining cats and dogs. The report is ready.",
  "target_locale": "de-DE",
  "source_locale": "auto",
  "asset_id": "asset-123",
  "accepted_ids": ["seg-1"],
  "rejected_ids": [],
  "edits": {}
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | yes | — | Content to adapt (1–100,000 chars) |
| `target_locale` | string | yes | — | Target locale code |
| `source_locale` | string | no | `"auto"` | Source locale |
| `asset_id` | string | no | `null` | Asset ID for persistence |
| `accepted_ids` | list[string] | no | `[]` | Segment IDs whose adaptation is accepted |
| `rejected_ids` | list[string] | no | `[]` | Segment IDs whose change is rejected (falls back to literal) |
| `edits` | dict[str,str] | no | `{}` | Segment ID → human-supplied replacement text |

**Response** (200 OK):
```json
{
  "adapted_text": "Es regnet in Strömen. Der Bericht ist fertig.",
  "segments": [
    {
      "id": "seg-1",
      "original": "It's raining cats and dogs.",
      "literal": "Es regnet Katzen und Hunde.",
      "adapted": "Es regnet in Strömen.",
      "risk_item": { "..." : "..." },
      "decision": "accept"
    },
    {
      "id": "seg-2",
      "original": "The report is ready.",
      "literal": "Der Bericht ist fertig.",
      "adapted": "Der Bericht ist fertig.",
      "risk_item": null,
      "decision": null
    }
  ],
  "changes_log": [
    {
      "segment_id": "seg-1",
      "decision": "accept",
      "original": "It's raining cats and dogs.",
      "result": "Es regnet in Strömen."
    }
  ],
  "flagged_segments": []
}
```

**Reviewer decisions:**
- `accepted_ids` — use the cultural adaptation and record accept.
- `rejected_ids` — fall back to the literal translation.
- `edits` — use the human-supplied text and clear any low-confidence flag.

Format conversions (`fmt-*` IDs) are applied automatically unless rejected via `rejected_ids`.

---

### `POST /api/v1/transcreation/preflight`

Pre-flight publish check: blocks until high-risk items are resolved or overridden.

**Request body:**
```json
{
  "asset_id": "asset-123",
  "content": "That's a load of crap.",
  "target_locale": "de-DE"
}
```

**Response** (200 OK):
```json
{
  "asset_id": "asset-123",
  "risk_items": ["..."],
  "format_items": ["..."],
  "blocked": true,
  "blocked_reasons": ["taboo: Potentially offensive language that should be softened before publishing."],
  "audit_status": "fail",
  "override_available": true
}
```

**Audit statuses:**
- `"pass"` — no risk items detected.
- `"review_needed"` — risk items present but none at `high` level.
- `"fail"` — at least one `high` risk item blocks publishing.

---

### `GET /api/v1/transcreation/preflight/{asset_id}`

Retrieve the latest stored preflight result for an asset.

**Response:** Same schema as `PreflightResult` above.

**Errors:** `404` if asset has no stored preflight result.

---

### `POST /api/v1/transcreation/preflight/{asset_id}/override`

Explicitly override a preflight block so publishing may proceed.

**Request body:**
```json
{
  "override": true
}
```

**Response:** Updated `PreflightResult` with `blocked: false` and `audit_status: "review_needed"`.

---

### `GET /api/v1/transcreation/assets/{asset_id}/result`

Return the full persisted transcreation result for an asset (analysis + adaptation + preflight + decisions).

**Errors:** `404` if the asset has no stored result.

---

### `POST /api/v1/transcreation/assets/{asset_id}/export`

Export accepted adaptations. Blocked while low-confidence flags are unresolved (US-003 AC2).

**Request body (optional):**
```json
{
  "accepted_ids": ["risk-1", "risk-3"],
  "rejected_ids": ["risk-2"]
}
```

Passing `accepted_ids` or `rejected_ids` for all flagged segments resolves them so export can proceed.

**Response** (200 OK):
```json
{
  "asset_id": "asset-123",
  "adapted_text": "{\"asset_id\": \"asset-123\", \"accepted_adaptations\": [...]}"
}
```

**Errors:** `409` blocked — unresolved low-confidence segments remain; `404` no analysis found.

## Usage

### Python — analyze and adapt

```python
import httpx

base = "http://localhost:8000/api/v1/transcreation"

# 1. Analyze for cultural risks and locale formatting
analysis = httpx.post(f"{base}/analyze", json={
    "text": "It's raining cats and dogs. The upgrade costs $1,000 on 07/04/2026.",
    "target_locale": "de-DE",
}).json()

print(f"Risk items: {len(analysis['risk_items'])}")
print(f"Format items: {len(analysis['format_items'])}")
print(f"Overall risk: {analysis['overall_risk']}")

# 2. Culturally adapt with reviewer decisions
adaptation = httpx.post(f"{base}/adapt", json={
    "text": "It's raining cats and dogs. The report is ready.",
    "target_locale": "de-DE",
    "accepted_ids": ["seg-1"],  # accept the idiom adaptation
}).json()

print(f"Adapted: {adaptation['adapted_text']}")
print(f"Flagged: {adaptation['flagged_segments']}")

# 3. Run a preflight check before publishing
preflight = httpx.post(f"{base}/preflight", json={
    "asset_id": "asset-1",
    "content": "That's a load of crap.",
    "target_locale": "de-DE",
}).json()

if preflight["blocked"]:
    print(f"Blocked: {preflight['blocked_reasons']}")
    # Override to proceed (requires explicit human approval)
    httpx.post(f"{base}/preflight/asset-1/override", json={"override": True})
```

### Python — direct service usage

```python
import asyncio
from src.services.transcreation import TranscreationService, LocaleData, LocaleFormatter

async def main():
    service = TranscreationService()

    # Analyze
    result = await service.analyze(
        text="It's raining cats and dogs.",
        target_locale="de-DE",
    )
    for item in result.risk_items:
        print(f"[{item.category}] {item.issue_description} (confidence={item.confidence})")

    # Adapt with accept/reject decisions
    adapted = await service.adapt(
        text="It's raining cats and dogs. The report is ready.",
        target_locale="de-DE",
        accepted_ids=["seg-1"],
    )
    print(adapted.adapted_text)
    # → "Es regnet in Strömen. Der Bericht ist fertig."

    # Locale formatting
    formatter = LocaleFormatter()
    print(formatter.convert_date("07/04/2026", "de-DE"))    # 04.07.2026
    print(formatter.convert_currency("$1,000", "de-DE"))    # 1.000 €
    print(formatter.convert_units("10 miles", "de-DE"))      # 16 km
    print(formatter.convert_honorifics("Mr. Smith", "de-DE")) # Herr Smith
    print(formatter.convert_honorifics("Mr. Tanaka", "ja-JP")) # Tanaka 様

asyncio.run(main())
```

### cURL — full workflow

```bash
# Analyze
curl -X POST http://localhost:8000/api/v1/transcreation/analyze \
  -H 'Content-Type: application/json' \
  -d '{"text": "It'\''s raining cats and dogs.", "target_locale": "de-DE"}'

# Adapt with reviewer decisions
curl -X POST http://localhost:8000/api/v1/transcreation/adapt \
  -H 'Content-Type: application/json' \
  -d '{"text": "It'\''s raining cats and dogs. The report is ready.", "target_locale": "de-DE", "accepted_ids": ["seg-1"]}'

# Preflight check
curl -X POST http://localhost:8000/api/v1/transcreation/preflight \
  -H 'Content-Type: application/json' \
  -d '{"asset_id": "asset-1", "content": "That'\''s a load of crap.", "target_locale": "de-DE"}'
```

## Architecture

### Dual-path design

Risk analysis uses the configured LLM provider when available; otherwise a deterministic rule-based engine over a module-level cache of compiled risk patterns is used. Any LLM outage is logged and the cached fallback is served so the API keeps working (graceful degradation).

```
Request → analyze()
  ├─ LLM configured? ──→ LLM risk analysis (structured JSON prompt)
  │     └─ failure ──→ log + fall back to rules
  └─ No LLM / fallback ──→ Rule-based pattern matching
```

### Confidence flagging (US-003)

Segments with risk item confidence below `CONFIDENCE_THRESHOLD` (0.7) are flagged for human review. Low-confidence segments:
- Appear in `AdaptResponse.flagged_segments`.
- Block export until resolved via `accepted_ids` / `rejected_ids` in the export request.

### Preflight flow (US-005)

```
POST /preflight
  ├─ analyze() → risk_items + format_items
  ├─ Any high-risk item? → blocked=True, audit_status="fail"
  ├─ Any risk item?      → blocked=False, audit_status="review_needed"
  └─ No risk items       → blocked=False, audit_status="pass"
```

Publishing proceeds only when `blocked` is `false`. The override endpoint allows explicit human approval to unblock.

## Error Mapping

| HTTP Status | Detail | Cause |
|-------------|--------|-------|
| 422 | Validation error | Empty text, empty locale, malformed body |
| 404 | `transcreation_result_not_found` | Asset ID has no stored result |
| 404 | `transcreation_preflight_not_found` | Asset has no preflight result |
| 409 | `transcreation_export_blocked` | Unresolved low-confidence segments |
| 409 | `transcreation_export_unavailable` | No analysis found for asset |
| 502 | `transcreation_provider_error` | LLM provider returned an error |
| 503 | `transcreation_provider_unavailable` | LLM provider timed out or unreachable |
| 503 | `transcreation_analysis_unavailable` | Analysis service failure |

## Data Model

| Table | Purpose |
|-------|---------|
| `transcreation_results` | Per-asset analysis + adaptation + preflight + decisions |
| `transcreation_flags` | Per-segment flag resolution state (resolved/override) |

Both tables are created automatically by the `product_ops` schema migration.

## Known Limitations

- Currency conversion reformats the symbol and number for the target locale but does **not** apply foreign-exchange rates.
- The rule-based fallback detects a fixed set of 5 risk patterns. LLM-powered analysis is required for comprehensive cultural risk detection.
- Date ambiguity detection (`07/04/2026` could be July 4 or April 7) is only flagged when the source locale is `auto` or US English.

## See Also

- [Translation Pipeline](translation-pipeline.md) — BLEU/chrF quality scoring for translation output
- [Language Detection](language-detection.md) — Auto-detect input language with fast-langdetect
- [Multilingual Scheduling](multilingual-scheduling.md) — Timezone-aware cross-language publishing
- [API Overview](api-overview.md) — Complete REST endpoint reference

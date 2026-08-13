# ContentForge — Content Creation Pipeline (US-001): Requirements Analysis & Task Specs

**Feature:** Content Creation Pipeline — turn one source asset into a consistent cross-platform content package
**Repo:** /home/zoltan/contentforge (HEAD 978298c, v0.15.0)
**Date:** 2026-08-13
**Author:** analyst (t_ef548473)
**Parent epic:** t_ae66fe2c (roadmap #1: content-creation — profit-driven opportunity)
**Status:** ANALYSIS BRIEF — requirements + task specs for the pre-tester → developer pipeline. No code written.

---

## 0. Executive Summary

ContentForge v0.15.0 has all the building blocks for multi-platform content creation — `ContentGenerator` for LLM-driven generation, `ConstraintValidator` for platform-specific rules, `PublishService` for LinkedIn/Twitter delivery, `BrandVoice` for tone consistency, and `ContentOpsStore` for campaign/asset persistence — but they are **not connected into a single coherent workflow**. Today, a user must manually call `/generate/{content_type}` for each platform, then `/validate` separately, then `/publish` separately, with no shared state, no idempotency, and no audit trail across the pipeline.

This brief specifies a **content pipeline** that takes one source asset (a blog post, a rough draft, a URL) and produces a complete cross-platform content package: validated, brand-voice-consistent variants for LinkedIn, Twitter/X, email, and blog — all with workflow state, idempotent operations, provenance tracking, and structured error recovery. The pipeline reuses existing services as building blocks and adds the orchestration layer.

**Key decisions (rationale in §3):**
1. **Orchestration: `ContentPackageStore`** in `src/product_ops.py` (SQLite, matching `TranscreationStore`/`FamilyStore` pattern) — owns the package state machine, variant records, and audit log. No new ORM model; the package is an ops-domain entity, not a user-facing entity like `Generation`.
2. **API: `/api/v1/content-packages`** (POST create, GET status, POST generate, POST validate, POST approve, POST publish) — follows repo convention (`/api/v1/<module>`).
3. **Generation: reuse `ContentGenerator`** with per-platform prompt adaptation — the generator already handles brand voice injection and compliance scoring. The pipeline adds a `PlatformAdapter` that adjusts tone, length, and CTA per platform.
4. **Validation: reuse `ConstraintValidator`** — each variant is validated against its target platform's constraints before approval.
5. **Publishing: reuse `PublishService`** — each approved variant is published to its target channel with idempotent batch delivery.
6. **Frontend: `frontend/src/content-creation.tsx`** — 4-step wizard (Select Source → Configure Platforms → Review & Approve → Publish & Track), hash-routed `#content-creation`.
7. **Idempotency: `Idempotency-Key` header** on create and publish endpoints (matching `FamilyStore` pattern).
8. **Error recovery: structured `RECOVERABLE`/`FATAL` error classification** with per-step retry and partial completion.

---

## 1. Current State Assessment

### 1.1 Verified repo state (contentforge @ 978298c, v0.15.0)

| Layer | Location | Verified pattern |
|---|---|---|
| Content generation | `src/routers/content.py` + `src/services/generator.py` | `POST /generate/{content_type}` for blog/social/email; `ContentGenerator` resolves brand voice (explicit → project → user → default), builds prompts, calls LLM, returns `GenerationResult` with compliance scores |
| Generation ORM | `src/models/generation.py` | `Generation` table: id, brand_voice_id (FK), content_type, topic, parameters (JSON), generated_text, compliance_scores (JSON), model_used, language, tokens_used, latency_ms, created_at |
| Brand voice | `src/models/brand_voice.py` + `src/brand_voice/` | `BrandVoice` ORM with `profile_data` JSON; resolution: explicit id → project scope → user scope → global → default |
| Constraint validation | `src/routers/constraints.py` + `src/services/constraint_validator.py` | `POST /validate` (per-platform), `POST /validate/cross-platform`; `ConstraintValidator` checks text length, hashtags, mentions, media formats against `ConstraintRegistry` |
| Platform constraints | `src/constraints/` | `ConstraintRegistry` loads YAML/JSON per platform (twitter, linkedin, email); `PlatformConstraints` model with text.max_chars, image.formats, video.formats |
| Publishing | `src/routers/publish.py` + `src/services/publish_service.py` | `POST /api/v1/publish` (platform, text, platform_config); `PublishService` with `TwitterConnector`/`LinkedInConnector`; synthetic success when no connector configured |
| Ops persistence | `src/product_ops.py` | `ContentOpsStore` (campaigns, assets, approvals, voice_profiles, voice_rules, publish_batches, deliveries, provenance, asset_revisions, transcreation_results, transcreation_flags); `TranscreationStore`; SQLite, JSON cols, `_audit()`, `_id()` = uuid4 hex |
| Family workflow | `src/routers/family.py` + `src/family/store.py` | `FamilyStore`: workspace → members → projects → assets → revisions → reviews → publish batches → deliveries; idempotency via `family_idempotency` table; audit log; role-based permissions |
| LLM provider | `src/services/llm_provider.py` | `LLMProvider` ABC + `OpenAIProvider` + `get_provider()` factory; lazy client, ImportError → helpful message |
| Config | `src/config.py` | `BaseSettings` with `CONTENTFORGE_` prefix; env-file; case-sensitive; new keys slot in cleanly |
| Frontend | `frontend/src/` | React 19 + TS + Vite SPA, hash routing; `navigation.ts` Route union; `transcreation.tsx` = closest pattern (typed API contract, `validationMessage` from `flow.ts`) |
| Tests | `tests/` | 2608+ tests; patterns: `TestClient` + `pytest.mark.asyncio`; `tests/scratch/` for stubs |
| API convention | `src/routers/*.py` | Modern pattern: `APIRouter(prefix="/api/v1/<module>")` — transcreation, brand-kit, analytics, constraints all use v1 prefix |

### 1.2 Gap analysis (what does NOT exist)

- No `ContentPackageStore` in `product_ops.py` — no pipeline state machine, no variant tracking, no cross-platform orchestration.
- No `POST /api/v1/content-packages` endpoint — no single-entry-point for "turn source into content package".
- No `PlatformAdapter` — no service that adapts a source asset into platform-specific variants (tone, length, CTA adjustments per platform).
- No pipeline state machine — no `draft → generating → validating → ready_to_approve → approved → publishing → published|failed` lifecycle.
- No `Idempotency-Key` header on content generation endpoints — `POST /generate/{content_type}` has no idempotency.
- No provenance chain across the pipeline — `ContentOpsStore.provenance` exists but is not wired to the generation→validate→publish flow.
- No `frontend/src/content-creation.tsx` — no `#content-creation` route; no wizard UI for the pipeline.
- No cross-platform consistency guarantee — each `/generate` call is independent; no mechanism ensures brand voice consistency across LinkedIn vs Twitter vs email versions of the same source.

### 1.3 Constraints & risks

| Risk | Detail | Mitigation |
|---|---|---|
| LLM availability | Generation depends on external LLM API; transient failures possible | Structured error classification (RECOVERABLE/FATAL); per-step retry; partial completion |
| Platform constraint drift | LinkedIn/Twitter limits change over time | `ConstraintRegistry` is YAML-configurable; update without code changes |
| Idempotency key collision | Same key + different payload should fail, not silently merge | `_idem()` pattern from `FamilyStore`: hash payload, reject on mismatch (409) |
| Brand voice consistency | Per-platform adaptation might drift from source voice | `PlatformAdapter` inherits voice profile from source; adapter is a thin transform, not a re-generation |
| Publishing rate limits | Social platforms have rate limits | Per-channel retry with backoff; `PublishService` already handles connector errors |
| Async blocking | LLM calls are async (good), but validation is sync | Validation is CPU-light; no blocking concern. If needed, wrap in executor |

---

## 2. Clustered Options

### 2.1 Pipeline orchestration approach

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. `ContentPackageStore` in `product_ops.py` (SQLite ops store)** | Matches `TranscreationStore`/`FamilyStore`/`ContentOpsStore` pattern; restart-safe; audit log; idempotency table | SQLite write on every state change (fine at this scale) | **Chosen** |
| B. SQLAlchemy ORM model `ContentPackage` | Matches `Generation`/`BrandVoice` pattern; FK relationships | Packages are ops-domain (workflow state), not user-domain (persisted content); ORM adds complexity for a workflow entity | Rejected |
| C. In-memory pipeline state | Simplest | Lost on restart; no audit; no idempotency | Rejected |

### 2.2 Platform adaptation strategy

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. `PlatformAdapter` — thin LLM-based transform per platform** | Uses existing `LLMProvider`; adapter prompt includes platform constraints (char limit, tone, CTA); brand voice inherited | One LLM call per platform variant (cost) | **Chosen** |
| B. Rule-based truncation + template | Zero LLM cost; deterministic | Poor quality; no tone adaptation; can't handle nuanced platform differences | Rejected |
| C. Full re-generation per platform | Each platform gets a fresh LLM generation | Expensive; drift from source; no consistency guarantee | Rejected |

### 2.3 Error classification

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. `RECOVERABLE`/`FATAL` per-step with structured error codes** | Clear retry semantics; frontend can show actionable messages; matches family store pattern | Needs error code taxonomy | **Chosen** |
| B. Generic try/catch with string messages | Simple | No structured retry; frontend can't distinguish transient from permanent | Rejected |

---

## 3. Chosen Tech Stack (with rationale)

| Layer | Choice | Rationale |
|---|---|---|
| Backend framework | FastAPI (existing) | repo standard; async; pydantic validation |
| Pipeline persistence | `ContentPackageStore` in `src/product_ops.py` (sqlite3, JSON cols) | `TranscreationStore`/`FamilyStore` precedent; zero new infra; idempotency table pattern |
| Platform adaptation | `PlatformAdapter` class using existing `LLMProvider` | Reuses LLM provider; thin transform; brand voice injection via prompt |
| Validation | Reuse `ConstraintValidator` from `src/services/constraint_validator.py` | Already validates per-platform text/media constraints |
| Publishing | Reuse `PublishService` from `src/services/publish_service.py` | Already handles LinkedIn/Twitter with error classification |
| Brand voice | Reuse `BrandVoice.profile_data` resolution from `src/brand_voice/` | Existing resolution chain; no duplication |
| Config | `src/config.py` additions: `CONTENT_PACKAGE_MAX_VARIANTS` (default 10), `CONTENT_PACKAGE_GENERATION_TIMEOUT_SECONDS` (default 120) | Existing settings pattern; env overridable |
| Frontend | React 19 + TS + Vite; `content-creation.tsx` hash-routed `#content-creation`; 4-step wizard | `transcreation.tsx` pattern; `validationMessage` reuse |
| Tests | `tests/test_content_creation.py` — interface + behavioral TDD | Existing test patterns; RED → GREEN → refactor |

---

## 4. Prioritized Task List

### P0 — Core pipeline (US-001)

**P0-1. ContentPackageStore + state machine**
- **Module:** `ContentPackageStore` class in `src/product_ops.py`
- **Expected behavior:** persist content packages with state `draft → generating → validating → ready_to_approve → approved → publishing → published|failed`; per-variant records with platform, content, validation_status, publish_status; idempotency table; audit log.
- **Interfaces:**
  - `ContentPackageStore(path)` (extends existing ops DB path)
  - `create_package(source_type, source_ref, platforms, brand_voice_id, idempotency_key) -> dict` — returns `{id, state: "draft", platforms, created_at}`
  - `get_package(id) -> dict` — returns full package with variants, timestamps, audit trail
  - `update_state(id, state) -> None` — validates transition; raises on invalid
  - `save_variants(id, variants: list[dict]) -> None` — saves generated platform variants
  - `get_variants(id) -> list[dict]` — returns all variants with validation/publish status
  - `update_variant(id, variant_id, **fields) -> None` — update single variant (validation_status, publish_status, content, error)
  - `approve(id) -> dict` — transition to `approved` (requires all variants in `validated` state)
  - `audit(id, kind, payload) -> None` — append audit event
  - `history(id) -> list[dict]` — return audit trail for a package
- **Dependencies:** existing `product_ops.py` patterns; `sqlite3`, `json`, `uuid4`, `hashlib`
- **State machine:**
  ```
  draft → generating → validating → ready_to_approve → approved → publishing → published
                         ↓                ↓                            ↓
                      failed           failed                       failed
  ```
  Invalid transitions raise `ValueError("invalid_transition")`.
- **Variant states:** `pending → generated → validated → published|failed`

**P0-2. Content pipeline API router**
- **Module:** `src/routers/content_packages.py` (registered in `src/main.py`)
- **Expected behavior:**
  - `POST /api/v1/content-packages` — body `{source_type: "generation_id"|"text"|"url", source_ref: str, platforms: list[str], brand_voice_id?: str, idempotency_key: str (header)}` → 201 `{id, state:"draft", platforms}`;
    400 malformed/empty platforms/unknown source; 409 idempotency collision.
  - `GET /api/v1/content-packages/{id}` → 200 full package (state, variants, timestamps, audit trail);
    404 unknown id.
  - `POST /api/v1/content-packages/{id}/generate` → triggers generation for all platforms; 200 `{state:"generating"}`; 409 wrong state (not `draft`).
  - `POST /api/v1/content-packages/{id}/validate` → validates all variants against platform constraints; 200 `{state:"validating"}` then auto-transitions to `ready_to_approve` or `failed`; 409 wrong state.
  - `POST /api/v1/content-packages/{id}/approve` → transitions to `approved`; 200; 409 when variants not all validated.
  - `POST /api/v1/content-packages/{id}/publish` → publishes approved variants to platforms; 200 `{state:"publishing"}`; 409 wrong state.
  - `GET /api/v1/content-packages/{id}/history` → 200 audit trail.
  - Error contract: 400 malformed, 404 missing, 409 wrong state / idempotency collision, 502/503 external provider — all JSON `{"detail": ...}`.
- **Dependencies:** P0-1 store, P0-3 adapter, P0-4 validation wiring, P0-5 publish wiring.

**P0-3. PlatformAdapter — per-platform content adaptation**
- **Module:** `src/services/platform_adapter.py`
- **Expected behavior:** given a source asset (text or `Generation` id) and a target platform, produce a platform-optimized variant:
  - Resolve brand voice profile (reuse `BrandVoice.profile_data` resolution).
  - Load platform constraints from `ConstraintRegistry` (char limit, tone guidance).
  - Build an LLM prompt that adapts the source to the platform: adjusts length (truncation/ expansion), tone (professional for LinkedIn, casual for Twitter), CTA placement, hashtag strategy.
  - Call `LLMProvider.generate()` with the adaptation prompt.
  - Return `PlatformVariant` with `{platform, content, char_count, hashtags, mentions, adapted_from: source_id, model_used, tokens_used, latency_ms}`.
  - **Idempotency:** if a variant already exists for this package+platform with `generated` state, return it (no re-generation).
- **Interfaces:**
  - `PlatformAdapter(llm_provider, registry)` — constructor takes LLM provider and constraint registry
  - `async adapt(source_text: str, platform: str, brand_voice: dict | None) -> PlatformVariant` — main method
  - `PLATFORM_PROMPTS: dict[str, str]` — per-platform system prompt templates
  - `PLATFORM_CONSTRAINTS_MAP: dict[str, dict]` — maps platform id to constraint hints for the LLM
- **Dependencies:** `src/services/llm_provider.py`, `src/constraints/registry.py`, `src/brand_voice/`

**P0-4. Validation wiring (reuse ConstraintValidator)**
- **Module:** thin layer in `src/routers/content_packages.py` calling existing `ConstraintValidator`
- **Expected behavior:** for each variant in a package, call `ConstraintValidator.validate()` with the variant's platform and content; update variant's `validation_status` to `validated` or `failed` (with errors list); if any variant fails, package state becomes `failed` with error summary.
- **Interfaces:** inline in router or extracted to `src/services/content_pipeline.py`:
  - `async validate_package(store, package_id) -> dict` — validates all variants, returns summary
- **Dependencies:** existing `ConstraintValidator`, `ConstraintRegistry`

**P0-5. Publish wiring (reuse PublishService)**
- **Module:** thin layer calling existing `PublishService`
- **Expected behavior:** for each approved variant, call `PublishService.publish()` with the variant's platform and content; update variant's `publish_status` to `published` or `failed`; track `remote_id` from platform response; update package state to `published` (all success) or `failed` (partial failure with per-variant errors).
- **Interfaces:**
  - `async publish_package(store, package_id, publish_service) -> dict` — publishes all approved variants
- **Dependencies:** existing `PublishService`, `PublishService.publish()`

**P0-6. Content creation wizard UI**
- **Module:** `frontend/src/content-creation.tsx` (+ `navigation.ts` Route `"content-creation"`, label "Content", icon "📝"), `frontend/src/content-creation.test.tsx`, `frontend/e2e/content-creation.spec.ts`
- **Expected behavior (4 steps, progress indicator):**
  1. **Select Source** — choose a `Generation` from content library (GET /generate history) or paste text; select target platforms (checkboxes: LinkedIn, Twitter/X, Email, Blog); select brand voice (dropdown from brand voices); "Next".
  2. **Configure & Generate** — POST create package + POST generate; show per-platform progress cards (pending → generating → generated); auto-advance when all generated; "Next".
  3. **Review & Validate** — POST validate; show per-platform variant cards with char count, constraint check results (green/red badges); inline edit capability; "Approve" button (POST approve).
  4. **Publish & Track** — POST publish; show per-platform publish status (publishing → published/failed); correlation ID for support; history link; "Done".
  - Empty state when no content library posts.
  - Friendly `validationMessage` on API errors (reuse from `flow.ts`).
  - No console errors; axe a11y clean.
  - "Back" preserves all selections (US-004).
- **Dependencies:** P0-2 API; existing `flow.ts`, `styles.css`, frontend conventions.

**P0-7. Idempotency + error recovery**
- **Module:** `ContentPackageStore._idem()` + error classification
- **Expected behavior:**
  - `Idempotency-Key` header required on `POST /api/v1/content-packages` and `POST /api/v1/content-packages/{id}/publish`.
  - Idempotency table: `(package_id_or_NEW, actor_id, key, request_hash, response_json)`.
  - Same key + same payload → return cached response.
  - Same key + different payload → 409 `idempotency_key_reused`.
  - Error classification: `RECOVERABLE` (LLM timeout, publish transient failure) → retry safe; `FATAL` (invalid input, unknown source) → no retry.
  - Partial completion: if generation succeeds for 3/4 platforms, package state = `failed` with per-variant errors; retry re-generates only `failed` variants.
  - Audit: every state transition, every variant update, every error appended to audit log with timestamp and actor.
- **Dependencies:** `ContentPackageStore`, `_idem()` pattern from `FamilyStore`

---

## 5. Acceptance Criteria per Task

### 5.1 P0-1 ContentPackageStore + state machine
- [ ] `create_package` returns stable id; `get_package` round-trips all fields incl. variants.
- [ ] State transitions valid: `draft→generating→validating→ready_to_approve→approved→publishing→published` and any state → `failed`; invalid transitions rejected with `ValueError("invalid_transition")`.
- [ ] Variant rows persist `pending|generated|validated|published|failed` with platform, content, errors, timestamps.
- [ ] Restart-safe: new store instance on same DB sees the package and its state.
- [ ] Audit events appended for create/state-change/variant-update/publish/error.
- [ ] Idempotency: same key + same payload returns cached result; same key + different payload raises.

### 5.2 P0-2 Content pipeline API
- [ ] `POST /api/v1/content-packages` 201 for valid source + platforms; 400 for empty platforms, unknown source; 409 for idempotency collision.
- [ ] `GET /api/v1/content-packages/{id}` 200 with state, variants[], timestamps, audit; 404 unknown.
- [ ] `POST .../generate` 200 triggers generation; 409 wrong state.
- [ ] `POST .../validate` 200 validates variants; 409 wrong state.
- [ ] `POST .../approve` 200 transitions to approved; 409 when variants not all validated.
- [ ] `POST .../publish` 200 triggers publishing; 409 wrong state.
- [ ] `GET .../history` 200 returns audit trail.
- [ ] All error bodies are JSON `{"detail": ...}` (no HTML).

### 5.3 P0-3 PlatformAdapter
- [ ] Given source text + platform + brand voice, returns `PlatformVariant` with adapted content within platform constraints.
- [ ] Brand voice profile resolved (explicit → project → user → default); adapter prompt includes tone guidance.
- [ ] Per-platform prompt adapts length, tone, CTA, hashtags (LinkedIn: professional, 1300 chars; Twitter: concise, 280 chars; email: subject + body; blog: long-form).
- [ ] Idempotent: same package+platform with existing `generated` variant returns cached result.
- [ ] Uses `LLMProvider` (no direct OpenAI import).

### 5.4 P0-4 Validation wiring
- [ ] Each variant validated against its target platform's constraints via `ConstraintValidator`.
- [ ] Variant `validation_status` set to `validated` (all checks pass) or `failed` (with error details).
- [ ] Package state transitions to `ready_to_approve` when all variants validated; `failed` when any variant fails.
- [ ] Validation is idempotent (re-validating an already validated variant is a no-op).

### 5.5 P0-5 Publish wiring
- [ ] Each approved variant published via `PublishService.publish()` to its target platform.
- [ ] Variant `publish_status` set to `published` (with `remote_id`) or `failed` (with error code).
- [ ] Package state transitions to `published` (all success) or `failed` (partial failure with per-variant errors).
- [ ] Publish is idempotent (re-publishing an already published variant returns cached result).

### 5.6 P0-7 Idempotency + error recovery
- [ ] `Idempotency-Key` header required on create and publish; missing → 400.
- [ ] Same key + same payload → cached response (no duplicate records, deliveries, or side effects).
- [ ] Same key + different payload → 409 `idempotency_key_reused`.
- [ ] `RECOVERABLE` errors (LLM timeout, publish transient) allow retry without data loss.
- [ ] `FATAL` errors (invalid input, unknown source) stop the pipeline with clear error.
- [ ] Partial completion: 3/4 platforms generated → package `failed` with per-variant errors; retry only failed variants.
- [ ] Every state transition and error recorded in audit log with timestamp and actor.

### 5.7 P0-6 Wizard UI (US-001 GUI flow)
- [ ] `#content-creation` route loads with no console errors; axe scan clean.
- [ ] 4 steps with progress indicator; "Next" unlocks only when current step valid; "Back" preserves all selections.
- [ ] Step 1: source selection (library or paste), platform checkboxes, brand voice dropdown.
- [ ] Step 2: per-platform progress cards (pending → generating → generated); auto-advance when done.
- [ ] Step 3: per-platform variant cards with char count, constraint badges, inline edit; "Approve" button.
- [ ] Step 4: per-platform publish status; correlation ID; history link.
- [ ] Playwright `content-creation.spec.ts` green (route loads, wizard steps render, no error overlay).

### 5.8 Cross-cutting
- [ ] `tests/test_content_creation.py`: interface tests pass immediately; behavioral tests fail cleanly pre-implementation (RED), pass post-implementation.
- [ ] Full suite green once via `PATH="$PWD/.venv/bin:$PATH" python -m pytest`; `ruff check` clean.
- [ ] Security: allowlists for platforms/source_types, length caps on text, parameterized SQL, no blocking calls in async.
- [ ] Docs: README + CHANGELOG + `docs/content-pipeline.md` updated.

---

## 6. Interface Contract Summary (for the pre-tester)

Canonical API:

```
POST /api/v1/content-packages
  header: Idempotency-Key: <string> (required)
  body: {source_type: "generation_id"|"text"|"url",
         source_ref: str,                    # Generation.id | raw text | URL
         platforms: list[str],               # ["linkedin", "twitter", "email", "blog"]
         brand_voice_id?: str}
  201 → {id, state: "draft", platforms, created_at}
  400 malformed/empty platforms/unknown source
  409 idempotency collision

GET /api/v1/content-packages/{id}
  200 → {id, source_type, source_ref, state, brand_voice_id,
         platforms, variants: [{id, platform, content, char_count,
                                validation_status, publish_status,
                                error?, remote_id?}],
         created_at, updated_at}
  404 unknown id

POST /api/v1/content-packages/{id}/generate
  200 → {state: "generating", variant_count: N}
  409 wrong state

POST /api/v1/content-packages/{id}/validate
  200 → {state: "validating"|"ready_to_approve"|"failed",
         variants: [{id, platform, validation_status, errors: [...]}]}
  409 wrong state

POST /api/v1/content-packages/{id}/approve
  200 → {state: "approved"}
  409 variants not all validated

POST /api/v1/content-packages/{id}/publish
  header: Idempotency-Key: <string> (required)
  200 → {state: "publishing", deliveries: [{platform, status}]}
  409 wrong state / idempotency collision

GET /api/v1/content-packages/{id}/history
  200 → {events: [{kind, payload, created_at, actor?}]}
```

State machine (P0): `draft → generating → validating → ready_to_approve → approved → publishing → published | failed`
Variant sub-states: `pending → generated → validated → published | failed`

Key module contracts for interface tests:
- `src/product_ops.py`: `class ContentPackageStore` — `create_package`, `get_package`, `update_state`, `save_variants`, `get_variants`, `update_variant`, `approve`, `audit`, `history`
- `src/services/platform_adapter.py`: `class PlatformAdapter` — `async adapt(source_text, platform, brand_voice) -> PlatformVariant`; `PLATFORM_PROMPTS: dict`
- `src/routers/content_packages.py`: `router = APIRouter(prefix="/api/v1/content-packages")` with endpoints above
- `src/schemas/content_packages.py`: `ContentPackageCreate`, `ContentPackageResponse`, `ContentVariantResponse`, `ContentPackageHistory` (pydantic v2)
- Frontend: `frontend/src/content-creation.tsx` exports `ContentCreationWizard` component; Route `"content-creation"` added to `navigation.ts`

---

## 7. Sources

- **Repo (primary):** /home/zoltan/contentforge @ 978298c (v0.15.0) — full module walk, pyproject, config, frontend, tests, product_ops.py store patterns.
- **Parent task:** t_ae66fe2c — BDD user stories US-001..US-004, GUI flow, acceptance criteria.
- **Sibling analysis:** `analysis/analysis-brief.md` (video pipeline, t_dfd6e7fc) — format convention for this brief.
- **Repo patterns:** `src/product_ops.py` (ContentOpsStore, TranscreationStore), `src/family/store.py` (FamilyStore idempotency/audit), `src/services/llm_provider.py` (provider abstraction), `src/services/constraint_validator.py` (platform validation), `src/routers/transcreation.py` (v1 API convention).

# Brand Kit — System Architecture & API Contracts Specification

**Feature:** Brand Kit (visual identity management)
**Repo:** /home/zoltan/contentforge (v0.13.0, commit `ad86b4a`)
**Date:** 2026-08-06
**Author:** analyst (t_453c223e)
**Status:** ARCHITECTURE SPEC — documents the implemented system as ground truth, with deltas where the implementation diverges from the original contract.

---

## 0. Executive Summary

Brand Kit is a visual-identity management subsystem of ContentForge. It lets a user define **colors, fonts, and logos** for one or more brands, upload font/logo assets, and generate a **self-contained HTML brand-guidelines document**. It complements the pre-existing **Brand Voice** module (text identity) without replacing it: Brand Kit owns *how content looks*, Brand Voice owns *how content sounds*.

The feature is **fully implemented** in the repo (backend + frontend + tests, commits `16cd9fa` … `ad86b4a`). This document describes the real implementation as ground truth and flags three deltas found during verification:

1. **API prefix drift** — the original contract and the frontend call `/api/v1/brand-kit`; the backend router registers `/brand-kit` (verified: `/api/v1/brand-kit` → 404, `/brand-kit` → 200).
2. **No PUT/PATCH/delete endpoint** — `BrandKitUpdate` schema exists but no route uses it; the frontend `updateBrandKit()` calls `PUT /api/v1/brand-kit/{id}` which does not exist (would 405/404).
3. **`/uploads` static mount is bound at import time** — two upload tests fail (404 on `GET /uploads/...`) when the app's `Settings` are overridden to a temp upload root in tests; production is unaffected.

Each delta has a recommendation in §9.

---

## 1. Current State Assessment

### 1.1 What Exists (implemented)

| Layer | Location | Pattern |
|-------|----------|---------|
| ORM model | `src/models/brand_kit.py` | SQLAlchemy 2.0 `Mapped`/`mapped_column`, UUID-string PK, PostgreSQL `JSON` columns for colors/fonts/logos, tz-aware timestamps, soft delete, version counter |
| Pydantic schemas | `src/schemas/brand_kit.py` | `ColorPalette` (hex + computed RGB/HSL properties), `FontSet`, `LogoSet`, `BrandKitCreate/Update/Response/ListResponse` |
| API router | `src/routers/brand_kit.py` | `APIRouter(prefix="/brand-kit")`, 5 endpoints, `Depends(get_db)` |
| Domain logic | `src/brand_kit/storage.py` | `BrandKitStorage` — extension whitelist, filename sanitization, bounded reads, size cap |
| Guidelines generator | `src/brand_kit/guidelines.py` | `BrandGuidelinesGenerator` — HTML-escaped self-contained document |
| Config | `src/config.py` | `UPLOAD_ROOT` (default `uploads`), `MAX_UPLOAD_SIZE_MB` (default 10) |
| Static mounts | `src/main.py` | `/static` (app assets) + `/uploads` (brand-kit assets, F4 finding) |
| Frontend | `frontend/src/brandkit.tsx` (482 lines) | `BrandKitWorkspace` → `BrandKitList` / `BrandKitDashboard` / `BrandGuidelinesView`, hash-routed at `#brand-kit` |
| Frontend tests | `frontend/src/brandkit.test.tsx` | Vitest + React Testing Library |
| Backend tests | `tests/test_brand_kit.py` (70), `test_brand_kit_crud.py` (29), `test_brand_kit_upload.py` (7) | Unit + integration; 2 upload tests currently failing (see §1.3) |
| Docs | `docs/brand-kit.md` (325 lines) | Feature guide, API reference, upload constraints, multi-brand usage |

### 1.2 What the Original Task Asked vs. Reality

| Task requirement | Implementation status |
|------------------|----------------------|
| BrandKit model with colors/fonts/logos/guidelines | ✅ `src/models/brand_kit.py` (guidelines_html column reserved, generated on demand) |
| Link to BrandVoiceProfile | ✅ `brand_voice_id` FK-style string column (no DB-level FK constraint; matches `Generation` pattern) |
| Multi-brand per user | ✅ `user_id` column; list endpoint returns all kits; docs show multi-brand usage |
| Color model hex/RGB/HSL | ✅ hex stored; `primary_rgb` / `primary_hsl` computed properties |
| Font custom uploads TTF/OTF/WOFF/WOFF2 | ✅ `FONT_EXTENSIONS` + upload endpoint |
| Curated Google Fonts | ⚠️ Font *names* are free-text strings (frontend has no Google Fonts picker); file uploads supported |
| Logo types primary/secondary/icon/watermark + format/size | ✅ `LogoSet` + upload writes `primary_format`/`primary_size`; UI drops slots for all four |
| POST/GET `/api/v1/brand-kit` | ⚠️ Implemented at `/brand-kit` (prefix drift, §0.1) |
| GET `/api/v1/brand-kit/guidelines` | ⚠️ Implemented at `/brand-kit/guidelines` |
| POST `/api/v1/brand-kit/upload` | ⚠️ Implemented at `/brand-kit/upload` |
| Secure file storage, no traversal | ✅ `validate_filename` (rejects `..`, `\`, strips dir components), extension whitelist, 413 cap |
| HTML/PDF guidelines combining visual + voice | ✅ HTML (self-contained, escaped); PDF not implemented (download as `.html`); voice section optional via `voice_profile` param |
| Integration with content generation | ⚠️ `brand_voice_id` is threaded into `/generate`; Brand Kit assets are not yet consumed by generation |
| Frontend dashboard (picker, selector, upload, preview, guidelines) | ✅ all five sections in `BrandKitDashboard` |

### 1.3 Test Baseline (verified 2026-08-06)

```
pytest tests/test_brand_kit.py tests/test_brand_kit_crud.py tests/test_brand_kit_upload.py
→ 104 passed, 2 failed
```

The 2 failures (`test_uploaded_font_is_servable_via_get_file_url`, `test_uploaded_logo_is_servable_via_get_file_url`) are a **test-environment coupling**, not a production bug:

- `src/main.py` mounts `app.mount("/uploads", StaticFiles(directory=str(_upload_root)))` at **import time** using the *default* `Settings.UPLOAD_ROOT` (`"uploads"`).
- The tests override `get_settings_dep` to a `tmp_path` root, and upload via `POST /brand-kit/upload` → file lands in `tmp_path`, but `GET /uploads/...` still serves the *import-time* root → 404.
- Verified with a live ASGI probe: upload succeeds (201, file on disk, JSON updated), only the static GET misses.

Fix options: bind the mount inside `lifespan` after settings load, or make the mount directory resolve lazily; a `StaticFiles(directory=...)` re-mount in lifespan with `app.mount(..., name="uploads")` replacement is the minimal change.

---

## 2. Data Models

### 2.1 ORM — `src/models/brand_kit.py`

```python
class BrandKit(Base):
    __tablename__ = "brand_kits"

    id: Mapped[str]            # String(36) PK, uuid4
    name: Mapped[str]          # String(255), NOT NULL
    description: Mapped[str]   # Text, default ""
    brand_type: Mapped[str]    # String(50), default "personal"
    user_id: Mapped[str | None]      # String(36), nullable → multi-brand per user
    brand_voice_id: Mapped[str | None]  # String(36), nullable → link to BrandVoice
    colors: Mapped[dict]       # JSON, default {}
    fonts: Mapped[dict]        # JSON, default {}
    logos: Mapped[dict]        # JSON, default {}
    guidelines_html: Mapped[str | None]  # Text, nullable (reserved, not persisted on write)
    version: Mapped[int]       # Integer, default 1; bumped by increment_version()
    deleted_at: Mapped[datetime | None]  # soft delete
    created_at / updated_at    # server_default func.now(), onupdate
```

Key design decisions:
- **JSON blob columns** for the three asset groups (mirrors `BrandVoice.profile_data` and the codebase's flexible-data convention). The schema layer (`ColorPalette` etc.) provides shape validation at the API boundary.
- **Soft delete** via `deleted_at` (consistent with `BrandVoice`, `Generation`); list/get/upload queries all filter `deleted_at.is_(None)`.
- **`version` counter** bumped on upload (and intended on update); the upload endpoint increments it — the CRUD tests assert `version == 2` after an upload.
- **No DB-level FK** to `brand_voices` — a plain string column, consistent with the existing `Generation.brand_voice_id` pattern and avoiding cross-table constraints at the SQLite-dev/Postgres-prod boundary.

### 2.2 Schemas — `src/schemas/brand_kit.py`

`ColorPalette` (hex with `^#?[0-9A-Fa-f]{6}$` pattern validation) exposes computed properties:

| Property | Derivation |
|----------|-----------|
| `primary_rgb: tuple[int,int,int]` | hex → RGB |
| `primary_hsl: tuple[int,int,int]` | RGB → HSL (0–360°, 0–100%, 0–100%) |

`FontSet`: `heading`, `body`, `accent` (default `"Arial"`) + optional `heading_file`, `body_file`, `accent_file` (uploaded font paths).

`LogoSet`: `primary`, `secondary`, `icon`, `watermark` (paths) + `primary_format` (e.g. `"png"`), `primary_size` (bytes).

`BrandKitCreate`: `name` (min_length=1), `description`, `brand_type`, optional `user_id`/`brand_voice_id`, nested `colors`/`fonts`/`logos` with defaults.
`BrandKitUpdate`: all-optional partial model — **currently unused by any route** (see §0.2).
`BrandKitResponse`: create payload + `id`, `version`, `created_at`, `updated_at`.
`BrandKitListResponse`: `{items, total, limit, offset}`.

### 2.3 Multi-brand

`user_id` is a plain nullable column; the list endpoint returns **all** kits (no user scoping filter — `get_current_user`/`scope_query_by_user` exist in `src/dependencies.py` but the brand-kit router does not use them). Docs (`docs/brand-kit.md`) demonstrate creating separate Personal and Business kits. Recommendation: wire `user_id` from the authenticated user and add a `WHERE user_id = :current` filter as a hardening step (§9.4).

---

## 3. API Contracts

### 3.1 Actual Endpoints (ground truth — router prefix `/brand-kit`)

| Method | Path | Status | Request | Response |
|--------|------|--------|---------|----------|
| POST | `/brand-kit` | 201 | `BrandKitCreate` JSON | `BrandKitResponse` |
| GET | `/brand-kit` | 200 | `?limit=` (1–100, default 20), `?offset=` (≥0) | `BrandKitListResponse` |
| GET | `/brand-kit/{brand_kit_id}` | 200 / 404 | — | `BrandKitResponse` |
| GET | `/brand-kit/guidelines` | 200 / 404 | `?brand_kit_id=` | HTML string (`text/html`) |
| POST | `/brand-kit/upload` | 201 / 400 / 404 / 413 | multipart: `file`, `brand_kit_id`, `file_type` (`font`\|`logo`) | `{path, filename, size, brand_kit_id, file_type}` |

Auth: **none of the brand-kit routes require authentication** (no `Depends(get_current_user)`). The router only uses `get_db` + `get_settings_dep`. This matches several other routers in the app but is flagged in §9.4.

### 3.2 Contract Drift — `/api/v1` prefix

- Original task body: `POST/GET /api/v1/brand-kit`, `GET /api/v1/brand-kit/guidelines`, `POST /api/v1/brand-kit/upload`.
- Frontend (`frontend/src/brandkit.tsx` lines 61–98): calls `/api/v1/brand-kit` everywhere.
- Backend (`src/routers/brand_kit.py` line 28): `APIRouter(prefix="/brand-kit")`, mounted in `main.py` without a global prefix.
- Verified empirically: `GET /api/v1/brand-kit` → **404**; `GET /brand-kit` → **200**.
- `docs/brand-kit.md` documents the real `/brand-kit` paths.
- Other routers mix conventions (e.g. `/api/v1/analytics`, `/api/v1/seo`, `/api/v1/languages` vs. `/generate`, `/schedule`, `/brand-voice`), so there is no app-wide prefix rule to lean on.

**Impact:** the Brand Kit dashboard in the frontend cannot list/create kits against the real backend as-is; in dev the Vite proxy forwards `/api/*` to `:8000` where it 404s. (In the deployed single-binary setup the frontend is served as static files from the same origin — same result.)

**Options (§9.1):**
- A) Change the router prefix to `/api/v1/brand-kit` (matches contract + frontend; most other v1 routers already embed `/api/v1`). Lowest-risk, one-line change.
- B) Add `app.include_router(brand_kit_router, prefix="/api/v1")` — but the router already has `prefix="/brand-kit"` so this yields `/api/v1/brand-kit` only if the router prefix is dropped.
- C) Keep `/brand-kit` and change the frontend + docs — contradicts the original contract and the majority of v1-style routers.

### 3.3 Missing PUT/delete

`BrandKitUpdate` exists but there is **no** `PUT /brand-kit/{id}` or `DELETE /brand-kit/{id}` route. The frontend's `updateBrandKit()` (PUT) and `handleSave()` in `BrandKitDashboard` depend on it; the dashboard's "Save brand kit" button therefore cannot persist edits against the real backend. The `BrandVoice` router, by contrast, implements full CRUD (`PUT` + `DELETE`, 204). Recommendation (§9.2): add `PUT /brand-kit/{brand_kit_id}` (200, `BrandKitResponse`, bump version) and `DELETE` (204, soft delete) following the `brand_voice` router pattern.

### 3.4 Upload Endpoint Behavior (verified)

- Extension whitelist: `FONT_EXTENSIONS = {.ttf, .otf, .woff, .woff2}`; `LOGO_EXTENSIONS = {.png, .jpg, .jpeg, .svg, .webp}`. Disallowed → 400 with allowed list.
- Filename sanitization: `validate_filename` rejects `..` and `\` (400), strips directory components (`Path(filename).name`), rejects empty result.
- Size cap: `MAX_UPLOAD_SIZE_MB` (default 10). Early 413 on `Content-Length` when present, then bounded 1 MiB chunk reads → 413 mid-stream (DoS protection, F5 finding).
- Storage layout: `<UPLOAD_ROOT>/brand_kit/<kit_id>/fonts|logos/<filename>`.
- On success: JSON fields updated (`fonts.heading_file` / `logos.primary` + `primary_format` + `primary_size`), `version` incremented, 201 `{path, filename, size, brand_kit_id, file_type}`. `path` is relative to `UPLOAD_ROOT`.
- `BrandKitStorage.get_file_url()` returns `/uploads/<relative-path>` — served by the `/uploads` mount in `main.py` (F4 finding).

---

## 4. File Storage Strategy

### 4.1 Directory Structure

```
<UPLOAD_ROOT>                      # default: ./uploads (env UPLOAD_ROOT)
└── brand_kit/
    └── <brand_kit_id>/            # uuid4
        ├── fonts/                 # heading.ttf, body.otf, accent.woff2, …
        └── logos/                 # primary.png, secondary.svg, icon.webp, …
```

### 4.2 Security Constraints (implemented)

| Constraint | Enforcement |
|-----------|-------------|
| Path traversal | `validate_filename` rejects `..` and backslash; uses `Path(filename).name` (strip dirs) |
| Extension whitelist | `validate_file_type` + `FONT_EXTENSIONS`/`LOGO_EXTENSIONS`; defense-in-depth before write |
| Size cap | `MAX_UPLOAD_SIZE_MB`; early Content-Length check + bounded chunked read (413) |
| MIME sniffing | Not implemented (extension-only validation) — acceptable for this scope, noted as enhancement |
| Multi-instance | Local filesystem is single-instance only; Railway single service OK; S3 migration path documented in sibling brief (§3.2 there) |

### 4.3 Naming Convention

- Original filename is preserved after sanitization (e.g. `primary.png`), not re-hashed. Collision risk is low per-kit since directories are per-kit; a timestamp/uuid prefix is a possible hardening (recommendation §9.3) to avoid overwrite on re-upload of same name.

---

## 5. Brand Guidelines Generator

### 5.1 Implementation — `src/brand_kit/guidelines.py`

`BrandGuidelinesGenerator.generate(kit: BrandKitResponse, voice_profile: dict | None = None) -> str` produces a **self-contained HTML document**:

- `<style>` block embedding brand fonts/colors via CSS.
- Sections: header (name, description, brand_type), **Color Palette** swatch grid (5 colors, inline-styled swatches), **Typography** (heading/body/accent), **Logos** (listed if present), optional **Brand Voice** section (escaped `brand_identity` dict string) when `voice_profile` is passed.
- **Stored-XSS hardening (F3 finding):** every user-derived value (`name`, `description`, `brand_type`, font names, colors — even though pattern-constrained) is run through `html.escape()` before interpolation, because the frontend renders the document via `dangerouslySetInnerHTML`.
- `generate_bytes()` UTF-8 encodes for download/PDF pipeline.

### 5.2 Rendering & Download

- `GET /brand-kit/guidelines?brand_kit_id=` returns the raw HTML string (FastAPI serializes `str` return as `text/html`).
- Frontend `BrandGuidelinesView` fetches it and renders via `dangerouslySetInnerHTML`, with a **Download guidelines** button (Blob → `brand-guidelines-<id>.html`).

### 5.3 PDF Gap

The original task asked for HTML/**PDF**. PDF is **not implemented** — download is the `.html` file. The generator's deterministic, self-contained HTML is directly printable (`@media print` friendly by construction: single column, inline styles) and is a clean input for a future PDF step (`weasyprint` or browser print-to-PDF). Recommendation §9.5: add a `?format=pdf` or a `/brand-kit/guidelines/{id}/pdf` endpoint using weasyprint when PDF becomes a requirement.

### 5.4 Voice Integration

The generator accepts an optional `voice_profile` dict, but **the router never loads it** — `generate_guidelines()` calls `gen.generate(_to_response(kit))` without a voice lookup. So the Brand Voice section is currently dead code at the API level. Recommendation §9.6: when `kit.brand_voice_id` is set, load the `BrandVoice` row and pass its `profile_data` into the generator so guidelines truly combine visual + text identity.

---

## 6. Integration Points

### 6.1 Brand Kit ↔ Brand Voice (complementary, not replacing)

| Dimension | Brand Voice | Brand Kit |
|-----------|-------------|-----------|
| Owns | Text identity (attributes, vocabulary, scenarios, formatting) | Visual identity (colors, fonts, logos) |
| Persistence | `brand_voices` table + JSON `profile_data` | `brand_kits` table + JSON colors/fonts/logos |
| Domain package | `src/brand_voice/` (VoiceProfile, VoiceManager, parser, presets, templates) | `src/brand_kit/` (storage, guidelines) |
| API | `/brand-voice` CRUD (full: POST/GET/PUT/DELETE) | `/brand-kit` (POST/GET ×3 + upload; **no PUT/DELETE yet**) |
| LLM use | `VoiceProfile.to_system_prompt()` injected into generation | not yet consumed by generation |
| Link | — | `BrandKit.brand_voice_id` → `brand_voices.id` |

The two modules are cleanly separable: Brand Voice feeds the **LLM prompt**; Brand Kit feeds **rendering/presentation** (guidelines HTML, preview, and eventually content templates).

### 6.2 Content Generation

`src/routers/content.py` (`POST /generate/{content_type}`) already accepts `brand_voice_id` and stores `Generation.brand_voice_id`. Brand Kit is **not referenced** there. Natural integration (recommendation §9.7):
- `POST /generate` accepts optional `brand_kit_id`; the generator could use brand colors/fonts for output formatting and brand voice for tone.
- Guidelines/rendering pipeline can pull both via the shared `brand_voice_id` link.

### 6.3 Frontend Wiring

- `navigation.ts`: `"brand-kit"` added to `Route` union + `NAV_ITEMS` (icon `◆`, label "Brand Kit").
- `main.tsx`: `Workspace` switch → `case "brand-kit": return <BrandKitWorkspace/>`.
- Vite dev proxy: `/api` → `127.0.0.1:8000` (so the prefix drift breaks the dashboard in dev too).

---

## 7. Frontend Component Architecture

### 7.1 Component Tree (implemented in `frontend/src/brandkit.tsx`)

```
BrandKitWorkspace                    # top-level switcher (route: #brand-kit)
├── BrandKitList                     # card grid + create form
│   ├── Toast (success)
│   └── .bk-grid/.bk-card            # per-kit swatch preview (5 mini swatches)
├── BrandKitDashboard                # per-brand editor
│   ├── Color palette editor         # 5 slots: color picker + hex input + RGB readout
│   ├── Font selector                # 3 slots: text input + "The quick brown fox" preview
│   ├── Logo upload                  # 4 drop zones (primary/secondary/icon/watermark)
│   ├── Live preview                 # CSS custom properties → styled sample card
│   └── Actions                      # Back / View guidelines / Save brand kit
└── BrandGuidelinesView              # fetch + dangerouslySetInnerHTML + Download (.html)
```

### 7.2 Key Implementation Notes

- **Types** mirror the Pydantic schemas (ColorPalette/FontSet/LogoSet/BrandKit/ListResponse) — single source of truth per side, manually duplicated.
- **API helpers** (`fetchBrandKits`, `createBrandKit`, `getBrandKit`, `updateBrandKit`, `uploadBrandKitFile`, `fetchBrandGuidelines`) wrap `fetch`; JSON requests set `Content-Type`, multipart upload uses `FormData`.
- **Live preview** drives brand colors/fonts through CSS custom properties (`--brand-primary`, `--brand-font-heading`, …) on the preview container.
- **Guidelines preview** uses `dangerouslySetInnerHTML` — the backend's HTML-escaping (F3) is the compensating control.
- **States**: loading, error (with Retry), empty (onboarding), success toast (3.5s auto-clear).
- **Test surface**: `frontend/src/brandkit.test.tsx` covers list rendering, create form, swatch data-testids, dashboard color/font editing, preview, guidelines container.

### 7.3 Design System Conformance

Uses the app's existing tokens: `.bk-*` classes layered on the global styles.css design system (Manrope headings, DM Sans body, `--green`/`--mint`/`--ink` palette, 10–20px radii, soft shadows).

---

## 8. Security Review (implemented controls)

| # | Threat | Control | Status |
|---|--------|---------|--------|
| F1 | Path traversal in upload | `validate_filename` (reject `..`, `\`, strip dirs) + whitelist | ✅ implemented, tested |
| F2 | Arbitrary file types | Extension whitelist per type (fonts vs logos) | ✅ implemented, tested |
| F3 | Stored XSS via guidelines HTML | `html.escape()` on all user-derived values before interpolation (frontend uses `dangerouslySetInnerHTML`) | ✅ implemented, tested (`test_benign_values_render_unescaped`) |
| F4 | Uploaded files not retrievable | `/uploads` static mount in `main.py` + `get_file_url()` | ✅ implemented (test-env coupling issue in §1.3) |
| F5 | Upload DoS (oversized) | `MAX_UPLOAD_SIZE_MB` + Content-Length check + bounded chunked read | ✅ implemented, tested |
| — | Unauthenticated access to brand data | None on brand-kit routes | ⚠️ gap (§9.4) |
| — | Filename collision on re-upload | None (preserves original name) | ⚠️ gap (§9.3) |
| — | MIME sniffing | Extension-only | ⚠️ enhancement |

---

## 9. Prioritized Recommendations (deltas + hardening)

### P0 — fixes required for the feature to work end-to-end

1. **§3.2 — Align the API prefix.** Change router to `APIRouter(prefix="/api/v1/brand-kit")` (and update `docs/brand-kit.md`), or add a global `/api/v1` include for this router. Matches contract + frontend + the `/api/v1/analytics|seo|languages` convention. *(1-line backend change + docs)*
2. **§3.3 — Add PUT (and DELETE) routes.** Implement `PUT /api/v1/brand-kit/{id}` honoring `BrandKitUpdate` (bump version, update JSON blobs) and `DELETE` → 204 soft-delete, following `src/routers/brand_voice.py` (lines 102–137). Unblocks the dashboard's Save button. *(~40 lines, mirrors existing pattern)*
3. **§1.3 — Fix `/uploads` mount vs. test overrides.** Bind the mount directory from `get_settings()` inside `lifespan` (or re-mount in a startup hook) so the two F4 servable tests pass with a temp upload root. *(small `main.py` change; makes the 2 failing tests green)*

### P1 — contract fidelity & integration

4. **§6.1 — Wire auth + user scoping.** Add `Depends(get_current_user)` to brand-kit routes and filter list/get by `user_id` (reuse `scope_query_by_user` in `src/dependencies.py`). Aligns with the multi-brand-per-user requirement.
5. **§5.4 — Load voice into guidelines.** In `generate_guidelines()`, when `kit.brand_voice_id` is set, fetch the `BrandVoice` and pass `profile_data` to `gen.generate(..., voice_profile=...)` so guidelines include the text identity.
6. **§6.2 — Consume brand kit in generation.** Accept optional `brand_kit_id` in `POST /generate/{content_type}` and expose colors/fonts to the prompt or output rendering.

### P2 — hardening / polish

7. **§4.3 — Unique filenames.** Prefix stored files with a short uuid/timestamp to avoid overwrite on same-name re-upload; update `logos.primary`/`fonts.heading_file` accordingly.
8. **§5.3 — PDF export.** Add `?format=pdf` via weasyprint when required; the self-contained HTML is already print-ready.
9. **§4.2 — MIME sniffing.** Validate magic bytes (PNG/JPEG/SVG/WebP signatures, TTF/OTF/WOFF/WOFF2 headers) in addition to extension whitelist.

### Acceptance criteria for the P0 fixes

- [ ] `GET /api/v1/brand-kit` returns 200 (list) and `POST /api/v1/brand-kit` returns 201 with the frontend path.
- [ ] `PUT /api/v1/brand-kit/{id}` persists `BrandKitUpdate` payload and bumps `version`; `DELETE` soft-deletes (404 on subsequent GET).
- [ ] `pytest tests/test_brand_kit.py tests/test_brand_kit_crud.py tests/test_brand_kit_upload.py` → **all pass** (currently 104 pass / 2 fail).
- [ ] Brand Kit dashboard (list → edit → save → guidelines → download) works against the real backend via the Vite proxy.

---

## 10. Appendix

### 10.1 Verified Probes (2026-08-06, live ASGI)

```
POST /brand-kit                          → 201 (created)
GET  /api/v1/brand-kit                   → 404   ← frontend path
GET  /brand-kit                          → 200   ← real path
GET  /brand-kit/{id}                     → 200
GET  /brand-kit/guidelines?brand_kit_id= → 404 (no kit) / 200 HTML (kit)
GET  /api/v1/brand-kit/guidelines        → 404   ← frontend path
```

### 10.2 Files Touched by the Feature (git log `16cd9fa`…`ad86b4a`)

- `src/models/brand_kit.py`, `src/schemas/brand_kit.py`, `src/routers/brand_kit.py`
- `src/brand_kit/__init__.py`, `src/brand_kit/storage.py`, `src/brand_kit/guidelines.py`
- `src/config.py` (UPLOAD_ROOT, MAX_UPLOAD_SIZE_MB), `src/main.py` (router + /uploads mount)
- `tests/test_brand_kit.py`, `tests/test_brand_kit_crud.py`, `tests/test_brand_kit_upload.py`
- `frontend/src/brandkit.tsx`, `frontend/src/brandkit.test.tsx`, `frontend/src/navigation.ts`, `frontend/src/main.tsx`, `frontend/src/styles.css`
- `docs/brand-kit.md`, `README.md`

### 10.3 Related Work

- Backend brief: `analysis/sibling-backend-brief.md` (t_94e7e2da) — design options for module layout, storage backend, color format.
- Frontend brief: `analysis/sibling-frontend-brief.md` (t_bf80ac43) — component plan, design tokens, API contract table.
- Review brief: `/home/zoltan/contentforge/analysis/review-brief-brand-kit.md` — F1–F5 findings referenced above.
- Task chain: t_453c223e (this spec) → t_73c70cdc (downstream).

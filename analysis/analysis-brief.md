# ContentForge — AI Video Content Generation Pipeline: Requirements Analysis & Task Specs

**Feature:** Video Generation (blog/script → scenes → voiceover → MP4), brand-voice aware
**Repo:** /home/zoltan/contentforge (branch master, HEAD 67720ca, v0.14.0)
**Date:** 2026-08-08
**Author:** analyst (t_dfd6e7fc)
**Idea:** contentforge-ai-video-7d11 (state/idea-vault.jsonl, US-001..US-004)
**Parent epic:** t_9d4f95b1
**Status:** ANALYSIS BRIEF — requirements + task specs for the pre-tester → developer → tester pipeline. No code written.

> **⚠ RESEARCH-BRIEF SUBSTITUTION NOTICE**
> The task expected `analysis/research-brief.md` for this feature. It does **not** exist — the
> task workspace (t_dfd6e7fc) was created empty, and no video-pipeline research brief exists among
> the board's attachments (verified by scan of `attachments/*/research-brief.md`; the two files that
> mention "video" are for other features — social constraints t_ce8fd117, analytics dashboard
> t_d20921ac). Per the task instructions, this brief substitutes **direct repo inspection**
> (contentforge HEAD 67720ca, v0.14.0 — full module walk, config, pyproject, frontend, e2e) plus
> **targeted web research** (OpenAI TTS, ElevenLabs, Coqui fork, MoviePy/FFmpeg, verified 2026-08-08)
> for the missing brief. Substitution is explicitly noted so reviewers can weight sources accordingly.

---

## 0. Executive Summary

ContentForge v0.14.0 (Brand Kit + transcreation export fix) has **zero video capability** — verified
by module walk: no video models, routers, services, or frontend route (`src/routers/*`, `src/models/*`,
`src/services/*`, `frontend/src/navigation.ts` all have no video surface; "video" appears only in
constraints/attachment-type validation). The gap was confirmed by the parent epic's research
(market USD 846–946M, 78% adoption, competitors Pictory/InVideo/Repurpose.io all closed SaaS).

This brief specifies a **self-hosted blog-to-video pipeline** built on the repo's existing patterns:
SQLAlchemy models + Pydantic schemas + FastAPI routers under `/api/v1/video/*` (matching
`transcreation`/`brand-kit` conventions), a `product_ops`-style SQLite job store, an
`LLMProvider`-style TTS provider abstraction, brand-voice inheritance via the existing
`BrandVoice.profile_data` resolution, and a 5-step wizard in the existing Vite+React SPA.

**Key decisions (rationale in §3):**
1. **Render engine: MoviePy 2.x + imageio-ffmpeg** (bundled FFmpeg binary, no system install) — not
   raw ffmpeg CLI, not headless browser. Render = per-scene image + TTS audio → H.264 MP4.
2. **TTS: `TTSProvider` ABC** with OpenAI TTS (default, key already in env pattern), ElevenLabs
   (HTTP), Coqui (`coqui-tts` idiap fork, local fallback, optional dep).
3. **Job store: `VideoJobStore`** in `src/product_ops.py` (SQLite, JSON columns, audit log) — matches
   `TranscreationStore`; state machine `queued → outline → scenes → render → ready|failed` with
   per-scene rows for progress + retry.
4. **API paths: `/api/v1/video/jobs`** (task body says `/api/video/jobs`; repo convention is
   `/api/v1/<module>` — see §3.2, the actual registered prefix is `/api/v1/video`).
5. **Segmentation:** 10k-char single-video cap; long posts split at section boundaries into
   sequential segment jobs with a `segment_order` field; combine = concatenated MP4 (US-002).
6. **Frontend:** `frontend/src/video.tsx` hash-routed `#video`, 5-step wizard, mirroring
   `transcreation.tsx` conventions (typed API contract header comment, `validationMessage` reuse).

**Priority split (effort-aware):**
- **P0 (core loop):** video job API + state machine, scene assembly (images, no segmentation), TTS
  abstraction (OpenAI only first), per-scene progress + retry + partial export, MP4 export, wizard
  UI (5 steps, US-001 + US-004), brand voice inheritance. → `tests/test_video_jobs.py` (part 1).
- **P1 (completeness):** long-post segmentation + combine (US-002), ElevenLabs + Coqui providers,
  style presets (explainer/documentary) + voice selection + aspect ratio, per-scene retry UI with
  render history (US-003). → `tests/test_video_jobs.py` (part 2) + frontend tests.
- **P2 (polish, optional in-cycle):** resolution presets beyond 720p, preview sample render,
  credits/usage accounting hooks, admin settings surface for TTS keys.

---

## 1. Current State Assessment

### 1.1 Verified repo state (contentforge @ 67720ca, v0.14.0, tree clean)

| Layer | Location | Verified pattern |
|---|---|---|
| ORM models | `src/models/*.py` | SQLAlchemy 2.0 `Mapped`/`mapped_column`, UUID-string PK, tz-aware timestamps, JSON columns; `Generation` has `brand_voice_id` FK |
| Brand voice | `src/models/brand_voice.py` + `src/brand_voice/*` | `BrandVoice.profile_data` JSON; `ContentGenerator` resolves voice: explicit id → project → user scope (see `src/services/generator.py` "Voice resolution order") |
| Schemas | `src/schemas/*.py` | Pydantic v2 (`BaseModel`, `Field`, `Literal`, `Enum`); `ContentParameters.length` uses `Literal["short","medium","long"]` pattern |
| Routers | `src/routers/*.py` | `APIRouter(prefix="/api/v1/<module>")` — transcreation (`/api/v1/transcreation`), brand-kit (`/api/v1/brand-kit`), analytics (`/api/v1/analytics`) are the modern pattern; legacy `/generate`, `/brand-voice` unprefixed |
| Router registration | `src/main.py` | explicit `from src.routers.X import router as X_router` + `app.include_router(...)`; tables registered via `from src.models import ... # noqa: F401` |
| Ops persistence | `src/product_ops.py` | `ContentOpsStore` + `TranscreationStore`: raw `sqlite3`, JSON columns, `_audit()` provenance, `_id()` = `uuid.uuid4().hex` |
| LLM provider | `src/services/llm_provider.py` | `LLMProvider` ABC + `OpenAIProvider` + factory `get_provider()`; lazy client, ImportError → helpful message. **This is the pattern to clone for TTS** |
| Config | `src/config.py` | Pydantic `BaseSettings`, env-file, `case_sensitive=True`; new keys (e.g. `ELEVENLABS_API_KEY`, `OPENAI_TTS_MODEL`) slot in cleanly |
| Content source | `src/models/generation.py` | `Generation` table IS the blog store (content_type="blog", generated_text, parameters JSON, brand_voice_id). Blog post id = Generation.id. No separate blog table |
| Frontend | `frontend/src/` | React 19 + TS + Vite SPA, hash routing; `navigation.ts` `Route` union + `NAV_ITEMS`; `transcreation.tsx` = closest pattern (typed API contract header, `apiMessage()` helper, `validationMessage` from `flow.ts`) |
| E2E | `frontend/e2e/transcreation.spec.ts` | Playwright, `#route` hash URLs against Vite :5173 proxying `/api` → backend :8099; `collectErrors()` console/pageerror guard; axe a11y expected by ui-gate |
| Tests | `tests/` | 2263 passed / 0 failed / 27 skipped (66 modules) at 99e07af (tester run t_2281c46b); patterns: `TestClient` + `pytest.mark.asyncio`, `tests/scratch/` for stubs |
| FFmpeg | **NOT installed** on host (verified `which ffmpeg`, `/usr/bin/ffmpeg`, `/usr/local/bin/ffmpeg` all absent) | → **must not hard-depend on system ffmpeg**; use `imageio-ffmpeg` bundled binary |
| Runtime deps | `pyproject.toml` | pinned deps; `openai==2.50.0` in extra `openai` (venv has 2.48.0 installed); **no** moviepy/imageio/elevenlabs/coqui yet |
| LLM | `LLM_API_KEY`/`LLM_PROVIDER`/`LLM_MODEL` (gpt-4o default) | OpenAI-compatible; used for outline/scene-script generation via `LLMProvider` |

### 1.2 Gap analysis (what does NOT exist)

- No `src/models/video*.py`, no `src/schemas/video*.py`, no `src/routers/video.py`, no
  `src/services/video*.py`, no `src/video/` package.
- No `VideoJobStore` in `product_ops.py`; no state machine; no job queue/worker.
- No TTS provider abstraction; no `ELEVENLABS_API_KEY`/`OPENAI_TTS_*`/`COQUI_*` settings.
- No render pipeline (no moviepy/imageio-ffmpeg deps, no export endpoint).
- No `#video` route in `frontend/src/navigation.ts`; no `video.tsx`; no `frontend/e2e/video.spec.ts`.
- No docs (`docs/video-pipeline.md`, README/CHANGELOG/api-reference entries).

### 1.3 Constraints & risks (verified)

| Risk | Detail | Mitigation |
|---|---|---|
| FFmpeg absent on host | system ffmpeg not installed; render hard-dep would fail e2e | `imageio-ffmpeg` (bundles static binary, pulled by moviepy) — pin it |
| Coqui is heavy (PyTorch) | ~2GB+, slow first load, not viable in CI/e2e | optional extra `video-coqui`; provider auto-disabled when import fails; fallback chain OpenAI → ElevenLabs → Coqui |
| External TTS APIs need keys | OpenAI key exists in env pattern; ElevenLabs/Coqui optional | provider registry keyed by availability; tests use fake provider / httpx MockTransport |
| Long posts | single-video char cap (10k) → US-002 segmentation | section-boundary splitter + sequential segment jobs + combine |
| Async blocking | moviepy/ffmpeg render + Coqui TTS are CPU/IO bound | run render in `asyncio.to_thread`/`run_in_executor` (repo rule: no blocking calls in async) |
| Race on retry | retry must not re-render completed scenes (US-003) | per-scene status persisted; retry only touches `failed` scenes; completed scene artifacts cached (file path in DB) |
| API prefix drift | task body says `/api/video/jobs`; repo convention `/api/v1/...` (brand-kit v1 drift was a real review finding) | **Register `/api/v1/video` and note the canonical path in the brief** — frontend + tests + docs must all use `/api/v1/video/jobs` |

---

## 2. Clustered Options

### 2.1 Render/MP4 approach

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. MoviePy 2.x + imageio-ffmpeg** | pure-pip, bundled ffmpeg binary (no system dep), Python-native scene composition, per-scene clips → concat; active project | adds numpy/Pillow/imageio deps; render CPU-bound | ✅ **Chosen** |
| B. Raw ffmpeg CLI subprocess | no new py deps | system ffmpeg **absent** (verified); brittle arg building; still needs images+audio prep | ❌ |
| C. Headless browser (Puppeteer/Playwright) render | rich typography/scene graphics | heavy; slow; overkill for image+audio slideshow; e2e already uses Playwright — don't couple | ❌ |
| D. External render API (e.g. Shotstack) | zero local CPU | SaaS cost, not self-hosted (contradicts product gap) | ❌ |

### 2.2 TTS provider strategy

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. `TTSProvider` ABC + registry (OpenAI/ElevenLabs/Coqui)** | matches `LLMProvider` pattern; key available (OpenAI); fallback chain gives self-host story | 3 adapters to write | ✅ **Chosen** (P0: OpenAI only; P1: ElevenLabs + Coqui) |
| B. OpenAI only | smallest scope | single-vendor, no fallback (US-003 retry story weaker), not self-hosted | ❌ |
| C. Coqui only | fully local | PyTorch dep, slow, quality lower | ❌ |

Provider facts (verified web, 2026-08-08): OpenAI `tts-1`/`tts-1-hd`/`gpt-4o-mini-tts`, 6 preset
voices (alloy/echo/fable/onyx/nova/shimmer), $15/1M chars (tts-1), $30/1M (hd). ElevenLabs v2 API,
~$0.0484/1k chars API (≈1 credit/char), models Flash v2.5 / Multilingual v2 / Eleven v3. Coqui
original repo unmaintained → **community fork `coqui-tts` (idiap/coqui-ai-TTS, v0.27.5, Jan 2026,
Python 3.10–3.14)** is the pip package to use.

### 2.3 Job state machine & persistence

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. SQLite `VideoJobStore` + per-scene rows + enum states** | matches `TranscreationStore`; survives restart; per-scene progress natural; partial export trivially queryable | sqlite write on every scene update (fine at this scale) | ✅ **Chosen** |
| B. In-memory job dict + background task | simplest | lost on restart; no audit; state machine hard to test | ❌ |
| C. Celery/RQ + Redis | robust queue | new infra, not self-host-friendly for single-node; overkill | ❌ |

States: `queued → outline → scenes → render → ready|failed`, plus terminal-with-partial
`failed` (scenes sub-states: `pending|generating|done|failed`). Retry endpoint re-queues only
`failed` scenes. Partial export = render MP4 from `done` scenes only when max retries exhausted.

### 2.4 API surface shape

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. `/api/v1/video/jobs` (POST/GET) + `/api/v1/video/jobs/{id}/export` + `/api/v1/video/jobs/{id}/retry`** | repo convention; RESTful; retry explicit | — | ✅ **Chosen** (retry = POST `/retry`; export = GET streams file) |
| B. Task-body literal `/api/video/jobs` (no v1) | matches task text | inconsistent with v1 modules; brand-kit v1 drift precedent says follow repo | ❌ |

### 2.5 Scene assembly & segmentation

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. Section-based scenes + image reuse from blog HTML/markdown + 10k-char cap with section-boundary split** | direct map to US-001/US-002; images in `Generation.parameters`/HTML reused; narrative preserved | needs a section extractor for plain-text scripts | ✅ **Chosen** |
| B. LLM full re-write of scenes | nicer copy | cost, drift from source sections, harder to map test assertions | ❌ |

---

## 3. Chosen Tech Stack (with rationale)

| Layer | Choice | Rationale |
|---|---|---|
| Backend framework | FastAPI (existing) | repo standard; async; pydantic validation |
| Persistence | SQLite via `VideoJobStore` (sqlite3, JSON cols) in `src/product_ops.py` | `TranscreationStore` precedent; restart-safe; zero new infra |
| ORM models | SQLAlchemy 2.0 (existing) for `VideoJob`/`VideoScene` if ORM; store may own tables | match `src/models/` convention; keep FK to `generations.id` (blog source) |
| TTS | `TTSProvider` ABC (clone `LLMProvider`); registry `get_tts_provider()`; OpenAI (`openai` extra, existing) → ElevenLabs (P1, httpx) → Coqui (P1, optional `video-coqui` extra) | pattern reuse; fallback chain; self-host story |
| Outline + scene script | existing `LLMProvider` (`LLM_API_KEY`/`LLM_MODEL`) — prompt for outline + per-scene narration + style preset | no new LLM dep; brand voice injected via `profile_data` |
| Audio | TTS adapter returns per-scene mp3/wav bytes → cached file per scene | retry reuses cached audio (US-003: no re-charge) |
| Render | **MoviePy 2.x + imageio-ffmpeg**; per-scene `ImageClip` + `AudioFileClip` → `concatenate_videoclips` → H.264 MP4; run in executor thread | system ffmpeg absent (verified); bundled binary; per-scene clip composition matches scene model |
| Resolutions | 720p default; `resolution` param allowlist `[480p, 720p, 1080p]` (1080p P2) | validated user input per security gate |
| Frontend | React 19 + TS + Vite (existing); `video.tsx` hash-routed `#video`; 5-step wizard | `transcreation.tsx` pattern; ui-gate + frontend-reference compliance |
| E2E | Playwright `frontend/e2e/video.spec.ts` (route loads, wizard steps, no console errors, axe) | existing e2e pattern; MANDATORY per parent epic |
| Config | `src/config.py` additions: `OPENAI_TTS_MODEL` (default `tts-1`), `OPENAI_TTS_VOICE` (default `alloy`), `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `VIDEO_MAX_SECTION_CHARS` (default 10000), `VIDEO_RENDER_DIR`, `VIDEO_RESOLUTION` | existing settings pattern; env overridable |
| Packaging | deps pinned in `pyproject.toml` `dependencies`; heavy TTS extras as `video-coqui` optional | pre-tester/dev standard: runtime deps must be pinned, not just in .venv |

---

## 4. Prioritized Task List (P0 / P1 / P2)

> Each task spec below includes **module name, expected behavior, interface description, and
> dependencies**. The pre-tester writes `tests/test_video_jobs.py` (P0 + P1 behavioral + interface
> tests) per the pre-tester card t_ba5cfcec; the developer implements per t_45f81716.

### P0 — Core generation loop (US-001, US-004 skeleton)

**P0-1. Video job model + store + state machine**
- **Module:** `src/models/video.py` (ORM) + `VideoJobStore` in `src/product_ops.py`
- **Expected behavior:** persist video jobs with state `queued|outline|scenes|render|ready|failed`;
  per-scene rows `pending|generating|done|failed` with `attempts`, `error`, `asset_path` (audio),
  `image_path`, `order`; audit log; restart-safe (state from DB).
- **Interfaces:**
  - `VideoJobStore(path)` → `create_job(source: VideoJobSource) -> str`, `get_job(id) -> VideoJobRecord`,
    `update_state(job_id, state)`, `list_scenes(job_id)`, `update_scene(job_id, scene_id, **fields)`,
    `scene(job_id, scene_id)`, `audit(job_id, kind, payload)`; `VideoJobRecord` dataclass/dict:
    `{id, source_type, source_ref, state, brand_voice_id, style_preset, voice, resolution,
    segment_order, error, created_at, updated_at, scenes: [SceneRecord]}`
- **Dependencies:** existing `src/product_ops.py`, `src/models/` convention; none new.

**P0-2. Video job API router**
- **Module:** `src/routers/video.py` (registered in `src/main.py`)
- **Expected behavior:**
  - `POST /api/v1/video/jobs` — body `{source_type: "generation_id"|"url"|"script",
    source_ref: str, brand_voice_id?: str, style_preset?: "explainer"|"documentary",
    voice?: str, resolution?: "480p"|"720p"|"1080p"}` → 201 `{job_id, state:"queued"}`;
    400 on malformed/oversized input (script length cap, allowlist enums); 404 unknown generation id.
  - `GET /api/v1/video/jobs/{id}` → job record incl. per-scene status + progress
    (`scenes:[{id,order,state,attempts,error?}]`, `overall_progress: float` 0–100).
  - `POST /api/v1/video/jobs/{id}/retry` → re-queues only `failed` scenes; 200 with retried scene ids;
    409 when job not in `failed`/`scenes` terminal state.
  - `GET /api/v1/video/jobs/{id}/export?resolution=720p` → streams MP4 (FileResponse) when `ready`
    or partial-export allowed; 409 when no scenes done; 404 unknown job.
  - Error contract: 400 malformed, 404 missing, 409 wrong state, 502/503 external provider — JSON bodies.
- **Dependencies:** P0-1 store, P0-3 assembly, P0-4 TTS, P0-5 render, schemas `src/schemas/video.py`.

**P0-3. Scene assembly from blog sections (images; no segmentation yet)**
- **Module:** `src/services/video_scenes.py`
- **Expected behavior:** given a `Generation` (blog) or raw script, split into sections (HTML
  headings/paragraphs or markdown `##`, else paragraph groups); produce ordered scenes each with
  narration text; **reuse blog images** — images referenced in the post's HTML/`parameters` are
  attached to the nearest section scene as `image_path` (download/copy to render dir; skip broken).
  Plain-text script → no images (scenes render with styled background/title card).
- **Interfaces:** `assemble_scenes(source: BlogSource|ScriptSource, llm, voice_profile) -> list[Scene]`;
  `Scene = {id, order, heading, narration, image_path|None, tts_text}`;
  `split_sections(text) -> list[Section]` (pure, testable).
- **Dependencies:** `src/models/generation.py`, LLM provider (outline/narration), brand voice profile.

**P0-4. TTS provider abstraction (OpenAI first)**
- **Module:** `src/services/tts.py` (clone `llm_provider.py` structure)
- **Expected behavior:** `TTSProvider` ABC with `async synthesize(text, voice, out_path) -> Path`
  (+ `available()`, `name`); `OpenAITTSProvider` (uses `openai` client audio.speech, model from
  settings, mp3 to out_path); `get_tts_provider()` factory returns first available by chain
  OpenAI → (P1: ElevenLabs → Coqui); missing key/import → provider unavailable (not crash).
  Per-scene audio written to `{render_dir}/{job_id}/scene_{n}.mp3`, cached (US-003).
- **Dependencies:** `src/config.py` additions; `openai` extra (already in pyproject, venv 2.48.0).
- **P1 extension:** `ElevenLabsTTSProvider` (httpx POST
  `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`), `CoquiTTSProvider` (`coqui-tts` optional).

**P0-5. MP4 render + export (MoviePy + imageio-ffmpeg)**
- **Module:** `src/services/video_render.py`
- **Expected behavior:** render each `done` scene to a clip (scene image or styled title card, sized
  to resolution, e.g. 720p = 1280×720) with its TTS audio; concat in order; write H.264 MP4 to
  `{render_dir}/{job_id}/export_{resolution}.mp4`; run in executor thread (no blocking in async);
  partial export renders only `done` scenes when allowed. Export endpoint streams the file.
- **Interfaces:** `render_job(job_id, scenes, resolution) -> Path`, `render_scene(scene) -> Path`,
  `combine_scenes(paths, resolution, out) -> Path`; `RESOLUTIONS = {"480p": (854,480),
  "720p": (1280,720), "1080p": (1920,1080)}`.
- **Dependencies:** **new pinned deps** `moviepy>=2.0,<3`, `imageio-ffmpeg` (bundles ffmpeg),
  `numpy`, `pillow` (imageio pulls); add to `pyproject.toml` `dependencies`.

**P0-6. Brand voice inheritance**
- **Module:** `src/services/video_scenes.py` (prompt side)
- **Expected behavior:** when `brand_voice_id` present, resolve profile via existing voice-resolution
  (explicit → project → user) and inject tone guidance into the outline/narration LLM prompts and
  the TTS narration text (e.g. formality, banned terms); `GET job` returns resolved
  `brand_voice_id` + `voice_profile_name` when inherited. Falls back silently when absent.
- **Dependencies:** `src/brand_voice/scoping.py`, `generator.py` voice resolution.

**P0-7. 5-step wizard UI (Video page) — US-001 + US-004**
- **Module:** `frontend/src/video.tsx` (+ `navigation.ts` Route `"video"`, label "Video", icon "▶"),
  `frontend/src/video.test.tsx`, `frontend/e2e/video.spec.ts`
- **Expected behavior (5 steps, progress indicator, back preserves state):**
  1. **Blog source** — pick Generation from content library (GET generations) or paste URL/script; "Next".
  2. **Scene outline** — auto-extracted scenes listed; reorder by drag (P0: up/down buttons OK);
     "Next".
  3. **Style & voice** — style preset (explainer/documentary), voice select, aspect ratio
     (16:9/9:16/1:1); "Preview" (P0: preview = static scene thumbnail strip; P1: sample render).
  4. **Generate** — POST job, poll `GET job` every ~2s, per-scene status chips + overall progress bar;
     on scene failure → "Retry failed scenes" button (P1: render history tab).
  5. **Preview & export** — HTML5 `<video>` preview (export URL), resolution select, "Download MP4".
  Empty state when no content library posts; friendly `validationMessage` on API errors; no console
  errors; axe a11y clean.
- **Dependencies:** P0-2 API; existing `flow.ts`, `styles.css`, frontend conventions.

### P1 — Segmentation, retry UX, provider completeness (US-002, US-003)

**P1-1. Long-post segmentation + combine**
- **Module:** `src/services/video_segments.py` (+ store fields `segment_order`, `parent_job_id`)
- **Expected behavior:** when source text > `VIDEO_MAX_SECTION_CHARS` (10k), split at section
  boundaries into sequential segment jobs (each ≤ cap) preserving order; `POST /api/v1/video/jobs`
  accepts `auto_segment: bool` (default true) and returns `{job_id, segments:[ids]}` when split;
  `POST /api/v1/video/jobs/{parent}/combine` concatenates segment MP4s (US-002: consistent voice/
  style — all segments inherit same voice+preset+brand voice; no duplicated transitions) → combined
  MP4; `GET` per-segment progress. Pure splitter `split_at_section_boundaries(text, cap) -> [str]`
  unit-testable; each segment contains only its assigned range.
- **Dependencies:** P0-3 assembly, P0-5 render.

**P1-2. Retry without re-render + partial export (US-003)**
- **Module:** `src/routers/video.py` + store
- **Expected behavior:** scene failure → job `failed` with `failed` scene marked + error stored;
  completed scenes remain `done` with cached audio/clips (never re-synthesized/re-rendered);
  `POST /retry` re-queues only `failed` scenes (attempts++, cap `max_retries=3`); after cap,
  `GET export?partial=true` renders from `done` scenes only and marks job `partial`; export still
  returns MP4 + `{partial: true, skipped_scenes:[ids]}` header/body flag.
- **Dependencies:** P0-1 store, P0-2 router, P0-5 render.

**P1-3. ElevenLabs + Coqui TTS providers + voice list endpoint**
- **Module:** `src/services/tts.py` (extend)
- **Expected behavior:** `GET /api/v1/video/voices?provider=...` → `{provider, voices:[{id,name}]}`
  (OpenAI 6 preset voices static; ElevenLabs fetched; Coqui model names); provider chain
  OpenAI → ElevenLabs → Coqui with per-provider `available()`; Coqui via optional extra
  `video-coqui` (NOT in base deps — PyTorch); graceful 503 with clear message when none available.
- **Dependencies:** P0-4; `httpx` (already pinned); optional `coqui-tts`.

**P1-4. Style presets & aspect ratio in render**
- **Module:** `src/services/video_styles.py` + render
- **Expected behavior:** `STYLE_PRESETS = {"explainer": {...title card, colors, font sizes, caption
  style...}, "documentary": {...serif/dark, lower-third captions...}}`; `aspect_ratio` maps to
  canvas dims per resolution; style applied to title cards/captions during render; stored on job.
- **Dependencies:** P0-5 render, P0-2 API schema.

**P1-5. Frontend retry + render history + preview sample**
- **Module:** `frontend/src/video.tsx` (extend)
- **Expected behavior:** step 4 error banner "Scene N failed — Retry failed scenes"; render history
  tab (attempts, error reasons); step 3 "Preview" triggers sample render of scene 1 (US-004
  "without charging a full generation credit" → P1: preview flag on job, no full concat);
  drag-reorder scenes.
- **Dependencies:** P1-2, P1-3, P1-4.

### P2 — Optional polish (in-cycle only if P0/P1 land clean)

- **P2-1** 1080p render presets verified on e2e; resolution in export query validated against allowlist.
- **P2-2** Credits/usage hooks: per-scene TTS char count + render duration recorded in audit
  (prep for subscription/credits model; no billing UI).
- **P2-3** Admin settings surface for TTS keys/voices in existing Admin page.
- **P2-4** Background worker: job execution as asyncio task with polling (P0 can run inline task
  loop; P2 moves to persistent worker + `queued` pickup).

---

## 5. Acceptance Criteria per Task

### 5.1 P0-1 VideoJobStore + state machine
- [ ] `create_job` returns stable id; `get_job` round-trips all fields incl. scenes.
- [ ] State transitions valid: `queued→outline→scenes→render→ready` and any state → `failed`;
  invalid transitions rejected (e.g. `ready→scenes`).
- [ ] Scene rows persist `pending|generating|done|failed`, `attempts`, `error`, `order`, asset paths.
- [ ] Restart-safe: new store instance on same DB sees the job and its state.
- [ ] Audit events appended for create/state-change/retry/export.

### 5.2 P0-2 Video job API
- [ ] `POST /api/v1/video/jobs` 201 for generation_id / url / script; 400 for bad enums, empty
      script > cap, oversize; 404 unknown generation_id.
- [ ] `GET /api/v1/video/jobs/{id}` 200 with `state`, `scenes[]` per-scene state, `overall_progress`;
      404 unknown id.
- [ ] `POST /api/v1/video/jobs/{id}/retry` re-queues only `failed` scenes; 409 in non-retryable state.
- [ ] `GET /api/v1/video/jobs/{id}/export` streams MP4 with `Content-Type: video/mp4` when ready;
      409 when nothing renderable; 404 unknown.
- [ ] All error bodies are JSON `{"detail": ...}` (no HTML).

### 5.3 P0-3 Scene assembly
- [ ] Blog (Generation) → scenes 1:1 with content sections (heading preserved).
- [ ] Blog images reused: scene with an image in its section gets `image_path`; broken/missing
      images skipped without failing the job (fallback to title card).
- [ ] Plain script → scenes from paragraph groups, no images, still renders.
- [ ] `split_sections` pure function tests (headings, paragraphs, empty input).

### 5.4 P0-4 TTS abstraction (OpenAI)
- [ ] `TTSProvider` ABC + `OpenAITTSProvider` synthesizes mp3 to `out_path` (fake client in tests).
- [ ] `get_tts_provider()` returns OpenAI when key set; falls back gracefully; raises/503s with
      clear message when no provider available.
- [ ] Per-scene audio cached on first success; subsequent job GET reports cached asset path.

### 5.5 P0-5 Render + export
- [ ] `render_job` produces a playable MP4 (probe: H.264, duration ≈ sum of scene audio lengths,
      ≥1 frame per scene) at chosen resolution.
- [ ] 720p default; `480p/720p/1080p` accepted; invalid resolution → 400.
- [ ] Runs without system ffmpeg (imageio-ffmpeg binary used) — verified in CI/e2e environment.
- [ ] Partial export (P1-2) renders only `done` scenes and flags `partial: true`.

### 5.6 P0-6 Brand voice inheritance
- [ ] Job created with `brand_voice_id` resolves profile (explicit → project → user precedence);
      narration prompt contains tone guidance; `GET job` returns `voice_profile_name`.
- [ ] No brand voice → generation proceeds with default tone, no error.

### 5.7 P0-7 Wizard UI (US-001, US-004)
- [ ] `#video` route loads with no console errors; axe scan clean.
- [ ] 5 steps with progress indicator; "Next" unlocks only when current step valid; "Back"
      preserves all selections (US-004 AC3).
- [ ] Step 2 scenes render from API; reorder persists to job (order field) before generate.
- [ ] Step 4 polls job, shows per-scene status + overall progress bar (US-001 GUI flow).
- [ ] Step 5 previews exported MP4 via `<video>` and downloads at chosen resolution (US-001 AC3).
- [ ] Playwright `video.spec.ts` green (route loads, wizard steps render, no error overlay).

### 5.8 P1-1 Segmentation (US-002)
- [ ] >10k-char post → `auto_segment` splits at section boundaries into sequential segments,
      each ≤ cap; `segments:[ids]` returned; narrative order preserved (US-002 AC1).
- [ ] Each segment job renders only its assigned content range (US-002 AC3).
- [ ] `combine` concatenates segments with consistent voice/style, no duplicated transitions
      (US-002 AC2) → combined MP4 downloadable.

### 5.9 P1-2 Retry + partial export (US-003)
- [ ] Scene failure pauses job, completed scenes cached, failure marked (US-003 AC1).
- [ ] Retry re-generates only failed scenes; cached scenes NOT re-synthesized/re-rendered
      (US-003 AC2 — assert via store: done scenes keep asset paths + attempt count unchanged).
- [ ] After `max_retries=3` on a scene, partial export succeeds with `partial: true` and skipped
      scene ids (US-003 AC3).

### 5.10 P1-3 TTS providers + voices
- [ ] ElevenLabs provider synthesizes via httpx (MockTransport test); unavailable without key.
- [ ] Coqui provider import-guarded; optional extra; unavailable without `video-coqui`.
- [ ] `GET /api/v1/video/voices` returns per-provider voice lists; 503 when none available.

### 5.11 P1-4 Style presets
- [ ] explainer vs documentary produce visually distinct title cards/captions (golden render check
      by dims/colors or snapshot); stored + returned on job.

### 5.12 P1-5 Frontend retry/preview
- [ ] Failed scene → red status + "Retry failed scenes" re-queues only that scene (US-003 GUI flow).
- [ ] Render history tab lists attempts + error reason; preview sample renders scene 1 without
      full-job credit semantics (US-004 AC2).

### 5.13 Cross-cutting (all P0/P1)
- [ ] `tests/test_video_jobs.py`: interface tests pass immediately; behavioral tests fail cleanly
      pre-implementation (RED), pass post-implementation; no `pytest.raises(NotImplementedError)`
      on feature's own public methods.
- [ ] Full suite green once via `.venv/bin/python -m pytest`; `ruff check` clean; deps pinned in
      `pyproject.toml` (moviepy, imageio-ffmpeg, numpy, pillow; elevenlabs via httpx; coqui as extra).
- [ ] Security: allowlists for enums/resolutions, length caps on script/voice/style, parameterized
      SQL, no blocking calls in async (render in executor), sanitized filename/path handling in render dir.
- [ ] Docs: README + CHANGELOG + `docs/video-pipeline.md` + `docs/api-reference` updated
      (documenter task t_f8f0166a); ui-gate passes (consumer/B2B).
- [ ] `git commit` + push (branch master, HTTPS remote), `git-push-verify.sh` passes.

---

## 6. Interface Contract Summary (for the pre-tester)

Canonical API (repo v1 convention — **use `/api/v1/video/...` in tests, frontend, and docs**):

```
POST /api/v1/video/jobs
  body: {source_type: "generation_id"|"url"|"script",
         source_ref: str,               # Generation.id | URL | raw text
         brand_voice_id?: str,
         style_preset?: "explainer"|"documentary",
         voice?: str,                   # provider voice id, default provider default
         resolution?: "480p"|"720p"|"1080p",   # default 720p
         auto_segment?: bool}           # default true (P1)
  201 → {job_id, state: "queued", segments?: [job_id]}   # segments when auto-segmented
  400 malformed/oversize/enum; 404 unknown generation_id

GET /api/v1/video/jobs/{id}
  200 → {id, source_type, source_ref, state, brand_voice_id, voice_profile_name?,
         style_preset, voice, resolution, segment_order?, error?,
         overall_progress: float, scenes: [{id, order, heading, state,
                                            attempts, error?, image_path?,
                                            audio_path?}], created_at, updated_at}
  404 unknown id

POST /api/v1/video/jobs/{id}/retry            # P0 (API), P1 (only-failed semantics hardened)
  200 → {retried: [scene_id]}                  # only failed scenes
  409 wrong state

GET /api/v1/video/jobs/{id}/export?resolution=720p&partial=true
  200 → MP4 stream (Content-Type: video/mp4; X-Partial: true when partial)
  409 nothing renderable; 404 unknown id

POST /api/v1/video/jobs/{parent}/combine       # P1 (US-002)
  200 → {combined_job_id, url: "/api/v1/video/jobs/{id}/export"}

GET /api/v1/video/voices?provider=openai|elevenlabs|coqui   # P1
  200 → {provider, voices: [{id, name}]}; 503 none available
```

State machine (P0): `queued → outline → scenes → render → ready | failed`
Scene sub-states: `pending → generating → done | failed` (attempts ≤ 3, then stays `failed`;
completed scenes never re-enter `generating` — retry targets `failed` only).

Key module contracts for interface tests (imports/signatures):
- `src/services/tts.py`: `class TTSProvider(ABC)` — `async synthesize(text: str, voice: str | None, out_path: str | Path) -> Path`, `available() -> bool`, `name: str`; `class OpenAITTSProvider(TTSProvider)`; `def get_tts_provider() -> TTSProvider`.
- `src/services/video_scenes.py`: `split_sections(text: str) -> list[str]`; `assemble_scenes(source, llm, voice_profile) -> list[Scene]` with `Scene` pydantic model (`id, order, heading, narration, tts_text, image_path: str | None`).
- `src/services/video_render.py`: `RESOLUTIONS: dict[str, tuple[int,int]]`; `render_job(job_id, scenes, resolution) -> Path`; `combine_scenes(paths, resolution, out) -> Path`.
- `src/product_ops.py`: `VideoJobStore(path)` — `create_job`, `get_job`, `update_state`, `list_scenes`, `update_scene`, `scene`, `audit` (see P0-1).
- `src/routers/video.py`: `router = APIRouter(prefix="/api/v1/video")` with the endpoints above.
- `src/schemas/video.py`: `VideoJobCreate`, `VideoJobResponse`, `VideoSceneResponse`, `VideoExportResponse`, `VoiceListResponse` (pydantic v2).
- Frontend: `frontend/src/video.tsx` exports `VideoWizard` component; Route `"video"` added to `navigation.ts`.

---

## 7. Sources

- **Repo (primary):** /home/zoltan/contentforge @ 67720ca (v0.14.0) — module walk, pyproject,
  config, frontend, e2e; idea vault `state/idea-vault.jsonl` (contentforge-ai-video-7d11, US-001..004).
- **OpenAI TTS:** platform.openai.com/docs/models/tts-1; pricing $15/1M chars tts-1, $30/1M hd,
  gpt-4o-mini-tts ≈ $0.015/min (cross-checked: costgoat.com, knowara.com, texttolab.com — Aug 2026).
- **ElevenLabs:** elevenlabs.io/docs (v2 TTS API, Flash v2.5/Multilingual v2/Eleven v3 models);
  API pricing ≈ $0.0484/1k chars, 1 credit ≈ 1 char (cross-checked: unifically.com, cekura.ai — Aug 2026).
- **Coqui:** coqui-ai/TTS unmaintained → idiap/coqui-ai-TTS community fork; pip `coqui-tts`
  v0.27.5 (2026-01-26), Python 3.10–3.14 (cross-checked: PyPI, localaimaster.com — Aug 2026).
- **MoviePy/FFmpeg:** pypi.org/project/moviepy (2.x), imageio-ffmpeg bundles ffmpeg binary;
  slideshow pattern (image+audio clips → concat → MP4) per community walkthroughs (Medium 2026).
- **Repo-standard references:** `micro-saas-lab/docs/DEVELOPMENT-STANDARDS.md`,
  `micro-saas-lab/shared/templates/frontend-reference.md`, `docs/api-overview.md`, prior
  analysis `analysis/architecture-spec.md` (Brand Kit, t_453c223e) — format convention.

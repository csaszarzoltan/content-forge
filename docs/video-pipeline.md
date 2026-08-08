# Video Generation Pipeline — Blog/Script → Scenes → Voiceover → MP4

ContentForge v0.15.0 adds an **AI video generation pipeline**: it turns a blog post (Generation row), a URL, or raw script text into a narrated MP4 video with per-scene progress, retry, and partial export. The pipeline is brand-voice aware and self-hosted — rendering uses MoviePy 2 + the `imageio-ffmpeg` bundled FFmpeg binary (no system FFmpeg install required).

## Features

| Tier | Module | Description |
|------|--------|-------------|
| P0 | **Video job API** | `POST/GET /api/v1/video/jobs`, `POST /jobs/{id}/retry`, `GET /jobs/{id}/export`, `POST /jobs/{parent}/combine`, `GET /voices` |
| P0 | **Job state machine** | `queued → outline → scenes → render → ready | failed | partial` with per-scene rows for progress and retry |
| P0 | **Scene assembly** | Blog sections → ordered scenes with narration; blog images reused per section; broken/missing images fall back to styled title cards |
| P0 | **TTS abstraction** | `TTSProvider` ABC — OpenAI TTS (default), ElevenLabs (HTTP), Coqui (`coqui-tts` optional extra) |
| P0 | **Style presets** | `explainer` (default) and `documentary` — title-card colors + narration tone guidance |
| P0 | **Voice selection** | OpenAI preset voices (alloy, echo, fable, onyx, nova, shimmer); provider-specific lists via `GET /voices` |
| P0 | **Retry without re-render** | Only failed scenes are re-queued; completed scenes keep cached `audio_path`/`image_path` and attempt counts (US-003) |
| P0 | **Partial export** | After max retries, `GET /export?partial=true` streams the renderable scenes with `x-partial: true` |
| P0 | **MP4 export** | H.264 + AAC, `yuv420p`, resolution selection (`480p`/`720p`/`1080p`, default `720p`) |
| P0 | **Brand voice inheritance** | Video jobs resolve the brand voice profile name (explicit → project → user scope) and surface `voice_profile_name` |
| P0 | **5-step wizard UI** | React + TypeScript hash-routed `#video` workspace: source → outline → style/voice → generate → export, selections preserved across steps (US-004) |
| P1 | **Long-post segmentation** | 10k-char cap; posts split at section boundaries into sequential segment jobs (`segment_order`), combined via `POST /jobs/{parent}/combine` (US-002) |

## Job State Machine

```
            ┌──────────────────────────────────────────────┐
queued ────► outline ────► scenes ────► render ────► ready │
                │             │             │              │
                └─────────────┴─────────────┴────► failed   │
                                          partial (max retries, some scenes done)
```

- `failed` is reachable from any state; backwards jumps (e.g. `ready → scenes`) are rejected with `ValueError` at the store level.
- Scene sub-states: `pending → generating → done | failed`, each row carrying `attempts`, `error`, and cached `image_path`/`audio_path`.
- `partial` state: jobs whose scenes exceeded max retries can still export the completed scenes (`x-partial: true`).

## API Endpoints

All endpoints live under `/api/v1/video` (repo v1 convention; the frontend proxies `/api` → backend).

### `POST /api/v1/video/jobs`

Create a video job from a blog generation id, a URL, or raw script text.

**Request body:**
```json
{
  "source_type": "generation_id | url | script",
  "source_ref": "gen-123 | https://example.com/blog/post | ## Intro\nHello.",
  "brand_voice_id": "bv-1",
  "style_preset": "explainer | documentary",
  "voice": "alloy",
  "resolution": "720p",
  "auto_segment": true
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `source_type` | enum | yes | — | `generation_id`, `url`, or `script` |
| `source_ref` | string | yes | — | Generation id, URL, or script text (≤ 200k chars) |
| `brand_voice_id` | string | no | `null` | Brand voice profile id (resolved → `voice_profile_name`) |
| `style_preset` | enum | no | `null` | `explainer` (default) or `documentary` |
| `voice` | string | no | `null` | TTS voice id (e.g. `alloy`) |
| `resolution` | enum | no | `"720p"` | `480p`, `720p`, or `1080p` |
| `auto_segment` | bool | no | `true` | Split long posts into sequential segment jobs |

**Responses:**
- `201` — `{"job_id": "…", "state": "queued", "segments": null | ["…"]}`
- `400` — malformed/oversize source
- `404` — unknown `generation_id`
- `422` — invalid enum / field validation (Pydantic)

### `GET /api/v1/video/jobs/{job_id}`

Fetch a job with per-scene status and overall progress.

**Response** (`200`):
```json
{
  "id": "j1", "source_type": "script", "source_ref": "…", "state": "scenes",
  "brand_voice_id": "bv-1", "voice_profile_name": "Acme Professional",
  "style_preset": "explainer", "voice": "alloy", "resolution": "720p",
  "segment_order": null, "error": null, "overall_progress": 50.0,
  "scenes": [{"id": "s1", "order": 1, "heading": "Intro", "state": "done",
              "attempts": 1, "error": null, "image_path": null, "audio_path": "/tmp/s1.mp3"}],
  "created_at": "…", "updated_at": "…"
}
```
- `404` — unknown job id (JSON `{"detail": "video job not found"}`).

### `POST /api/v1/video/jobs/{job_id}/retry`

Re-queue **only** failed scenes; completed scenes are never re-rendered (US-003). Attempts increment per retry; scenes at max retries (3) stay failed.

**Response** (`200`): `{"retried": ["scene-id", …]}` — only the failed scenes.
- `404` — unknown job; `409` — job state not retryable (e.g. `ready`).

### `GET /api/v1/video/jobs/{job_id}/export?resolution=720p&partial=true`

Stream the rendered MP4 (`Content-Type: video/mp4`). `partial=true` skips scenes that exhausted retries and adds `x-partial: true`.

- `409` — nothing renderable (no done scenes / job not ready and no partial allowed)
- `404` — unknown job; `422` — invalid resolution.

### `POST /api/v1/video/jobs/{parent_id}/combine`

Concatenate a segment family's rendered clips into one combined MP4 (US-002).

**Response** (`200`): `{"combined_job_id": "…", "url": "/api/v1/video/jobs/…"}`
- `404` — unknown/implausible parent id.

### `GET /api/v1/video/voices?provider=openai|elevenlabs|coqui`

**Response** (`200`): `{"provider": "openai", "voices": [{"id": "alloy", "name": "Alloy"}, …]}`
- `503` — provider unavailable (missing API key / optional extra not installed).

## Error Contract

Every error is a JSON body `{"detail": "…"}`:
- `400` malformed input · `404` missing resource · `409` wrong job/scene state · `422` Pydantic validation · `502`/`503` external provider failures (TTS unavailable/timeout, missing API key, optional extra not installed).

## TTS Providers

| Provider | Key | Notes |
|----------|-----|-------|
| OpenAI (default) | `OPENAI_API_KEY` (or `LLM_API_KEY`) | `tts-1` model, preset voices |
| ElevenLabs | `ELEVENLABS_API_KEY` | HTTP, voice list via API |
| Coqui | `coqui-tts` optional extra | Local fallback; voice names known once installed |

`get_tts_provider()` factory returns the first available provider. When no key is configured the pipeline writes a short silent MP3 placeholder so scene rendering and exports still work offline.

## Architecture

| Module | Role |
|--------|------|
| `src/schemas/video.py` | Pydantic v2 request/response models + enums |
| `src/routers/video.py` | FastAPI router (`/api/v1/video`), error mapping, async handlers |
| `src/product_ops.py` (`VideoJobStore`) | SQLite job store (TranscreationStore pattern): jobs, scenes, audit log |
| `src/services/video_scenes.py` | `split_sections` + `assemble_scenes` (blog image reuse) |
| `src/services/video_segments.py` | `split_at_section_boundaries` (10k cap, US-002) |
| `src/services/tts.py` | `TTSProvider` ABC + OpenAI/ElevenLabs/Coqui + factory |
| `src/services/video_render.py` | MoviePy 2 + imageio-ffmpeg: per-scene clips → H.264 MP4 |
| `frontend/src/video.tsx` | 5-step wizard (`#video` hash route) |

## Frontend

The 5-step wizard (React + TypeScript, `#video` route) mirrors the `transcreation.tsx` conventions:

1. **Source** — generation id / URL / script (validated before advancing)
2. **Outline** — extracted scenes with reorder controls
3. **Style & voice** — style preset, voice select, aspect ratio
4. **Generate** — per-scene status, overall progress bar, "Retry failed scenes" (US-003)
5. **Export** — MP4 preview + download, resolution select

Selections (voice, style) are preserved when navigating back (US-004). Run frontend tests with `npm test` (vitest), build with `npm run build` (tsc + vite).

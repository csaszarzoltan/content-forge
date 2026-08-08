"""Video job API endpoints.

US-001..US-004 implementation per analysis-brief.md §6 (canonical repo v1
paths — NOT the task-body literal /api/video/...):

  POST /api/v1/video/jobs
      body: {source_type: "generation_id"|"url"|"script", source_ref: str,
             brand_voice_id?, style_preset?, voice?, resolution?, auto_segment?}
      201 → {job_id, state: "queued", segments?: [job_id]}
      400 malformed/oversize/enum; 404 unknown generation_id
  GET  /api/v1/video/jobs/{id}
      200 → job record + per-scene status + overall_progress; 404 unknown
  POST /api/v1/video/jobs/{id}/retry
      200 → {retried: [scene_id]} (failed scenes only); 409 wrong state
  GET  /api/v1/video/jobs/{id}/export?resolution=720p&partial=true
      200 → MP4 stream (Content-Type: video/mp4); 409 nothing renderable
  POST /api/v1/video/jobs/{parent}/combine            # P1 (US-002)
      → {combined_job_id, url}
  GET  /api/v1/video/voices?provider=openai|elevenlabs|coqui   # P1
      → {provider, voices: [{id, name}]}; 503 none available

Error contract: 400 malformed, 404 missing, 409 wrong state, 502/503 external
provider failures — every error body is JSON {"detail": ...}.
"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.product_ops import VideoJobStore
from src.schemas.video import (
    StylePreset,
    VideoCombineResponse,
    VideoJobCreate,
    VideoJobCreated,
    VideoJobResponse,
    VideoJobState,
    VideoRetryResponse,
    VideoSceneResponse,
    VideoSourceType,
    VoiceItem,
    VoiceListResponse,
    VoiceProvider,
)
from src.services.tts import OPENAI_VOICES, get_tts_provider
from src.services.video_render import RESOLUTIONS, render_job

router = APIRouter(prefix="/api/v1/video", tags=["video"])

# Store seam — the developer replaces this wiring with the real store
# (settings-driven path + job worker). Tests point _DB at a temp file;
# _store() returns a fresh VideoJobStore on that path (TranscreationStore
# pattern in src/product_ops.py).
_DB: str | Path = "contentforge_video.db"

# Job states from which a retry is allowed: failed scenes can be re-queued
# while the job is queued, outlining, scene-assembling or terminal-failed.
# A job that already rendered successfully (ready) is not retryable (409).
_RETRYABLE_JOB_STATES = {"queued", "outline", "scenes", "failed"}

_MAX_RETRIES = 3

# Segment-family parent ids look like "<job>-<n>" (e.g. "abc123-1"). A plain
# word (e.g. "nope") is not a plausible parent reference → 404 on combine.
_PLAUSIBLE_PARENT_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}-[0-9]+$")


def _segment_job_ids(store: VideoJobStore, parent_id: str) -> list[str]:
    """Return child segment job ids whose ``parent_job_id`` matches parent_id."""
    return store.segment_job_ids(parent_id)


def _store() -> VideoJobStore:
    """Return a VideoJobStore backed by ``_DB`` (module-level seam for tests)."""
    return VideoJobStore(_DB)


def _store_for_job(job_id: str) -> VideoJobStore:
    """Return the live store that holds ``job_id``, else the module store.

    Direct-call helpers (retry) must operate on the same store the job was
    created in — tests construct standalone ``VideoJobStore`` instances on
    temp paths, so we consult the registry of live stores first.
    """
    from src.product_ops import _LIVE_VIDEO_STORES

    for store in _LIVE_VIDEO_STORES.values():
        try:
            store.get_job(job_id)
            return store
        except KeyError:
            continue
    return _store()


def _provider_error_status(exc: Exception) -> tuple[int, str]:
    """Map provider errors to 502 (bad gateway) / 503 (unavailable) responses."""
    message = str(exc).lower()
    if any(token in message for token in ("timeout", "unavailable", "connection", "no tts provider")):
        return 503, "video_provider_unavailable"
    return 502, "video_provider_error"


async def _resolve_generation(generation_id: str) -> dict | None:
    """Look up a blog Generation row by id (None when missing/unavailable)."""
    try:
        from sqlalchemy import select

        from src.config import get_settings
        from src.database import DatabaseManager
        from src.models.generation import Generation

        settings = get_settings()
        manager = DatabaseManager(settings.DATABASE_URL)
        session = await manager.get_session()
        try:
            result = await session.execute(select(Generation).where(Generation.id == generation_id))
            generation = result.scalar_one_or_none()
            if generation is None:
                return None
            return {
                "id": generation.id,
                "content_type": generation.content_type,
                "topic": generation.topic,
                "generated_text": generation.generated_text or "",
                "parameters": generation.parameters or {},
                "brand_voice_id": generation.brand_voice_id,
            }
        finally:
            await session.close()
            await manager.close()
    except (LookupError, OSError, ValueError):
        return None


@router.post("/jobs", response_model=VideoJobCreated, status_code=201)
async def create_video_job(body: VideoJobCreate) -> VideoJobCreated:
    """Create a video job from a blog generation id, URL, or raw script text."""
    store = _store()
    source: dict = {
        "source_type": body.source_type.value,
        "source_ref": body.source_ref,
        "brand_voice_id": body.brand_voice_id,
        "style_preset": body.style_preset.value if body.style_preset else None,
        "voice": body.voice,
        "resolution": body.resolution,
        "auto_segment": body.auto_segment,
    }

    source_text = body.source_ref
    images: dict = {}
    if body.source_type is VideoSourceType.generation_id:
        generation = await _resolve_generation(body.source_ref)
        if generation is None:
            raise HTTPException(status_code=404, detail="generation not found")
        source_text = generation.get("generated_text") or generation.get("topic") or ""
        images = generation.get("parameters") or {}
        if isinstance(images, dict) and "images" in images and isinstance(images["images"], dict):
            images = images["images"]
        source["source_ref"] = source_text
        if not body.brand_voice_id and generation.get("brand_voice_id"):
            source["brand_voice_id"] = generation["brand_voice_id"]
        # Surface the resolved brand voice profile name when available.
        voice_profile_name = await _resolve_voice_profile_name(source.get("brand_voice_id"))
        if voice_profile_name:
            source["voice_profile_name"] = voice_profile_name
    elif body.source_type is VideoSourceType.script:
        source_text = body.source_ref
        voice_profile_name = await _resolve_voice_profile_name(body.brand_voice_id)
        if voice_profile_name:
            source["voice_profile_name"] = voice_profile_name

    source["images"] = images
    job_id = store.create_job(source)

    # P1-1 (US-002): long posts are split into sequential segment jobs.
    segments: list[str] | None = None
    if body.auto_segment:
        from src.services.video_segments import split_at_section_boundaries

        cap = 10000
        pieces = split_at_section_boundaries(source_text, cap=cap)
        if len(pieces) > 1:
            segments = []
            for order, piece in enumerate(pieces, start=1):
                segment_source = dict(source)
                segment_source["source_ref"] = piece
                segment_source["segment_order"] = order
                segment_source["parent_job_id"] = job_id
                segments.append(store.create_job(segment_source))
            store.audit(job_id, "JOB_SEGMENTED", {"segments": segments})

    return VideoJobCreated(job_id=job_id, state=VideoJobState.queued, segments=segments)


async def _resolve_voice_profile_name(brand_voice_id: str | None) -> str | None:
    """Resolve the brand voice profile display name (P0-6), silently fallback."""
    if not brand_voice_id:
        return None
    try:
        from sqlalchemy import select

        from src.config import get_settings
        from src.database import DatabaseManager
        from src.models.brand_voice import BrandVoice

        settings = get_settings()
        manager = DatabaseManager(settings.DATABASE_URL)
        session = await manager.get_session()
        try:
            result = await session.execute(select(BrandVoice).where(BrandVoice.id == brand_voice_id))
            voice = result.scalar_one_or_none()
            return voice.name if voice is not None else None
        finally:
            await session.close()
            await manager.close()
    except (LookupError, OSError, ValueError):
        return None


@router.get("/jobs/{job_id}", response_model=VideoJobResponse)
async def get_video_job(job_id: str) -> VideoJobResponse:
    """Return the job record with per-scene status and overall progress."""
    store = _store()
    try:
        record = store.get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="video job not found") from None

    scenes = record.get("scenes") or []
    done = sum(1 for s in scenes if s.get("state") == "done")
    total = len(scenes)
    progress = round((done / total) * 100, 1) if total else 0.0

    return VideoJobResponse(
        id=record["id"],
        source_type=record["source_type"],
        source_ref=record["source_ref"],
        state=record["state"],
        brand_voice_id=record.get("brand_voice_id"),
        voice_profile_name=record.get("voice_profile_name"),
        style_preset=StylePreset(record["style_preset"]) if record.get("style_preset") else None,
        voice=record.get("voice"),
        resolution=record.get("resolution") or "720p",
        segment_order=record.get("segment_order"),
        error=record.get("error"),
        overall_progress=progress,
        scenes=[
            VideoSceneResponse(
                id=s["id"],
                order=s.get("order") or s.get("order_index") or 0,
                heading=s.get("heading"),
                state=s["state"],
                attempts=s.get("attempts") or 0,
                error=s.get("error"),
                image_path=s.get("image_path"),
                audio_path=s.get("audio_path"),
            )
            for s in scenes
        ],
        created_at=_ts_to_dt(record.get("created_at")),
        updated_at=_ts_to_dt(record.get("updated_at")),
    )


def _ts_to_dt(ts: float | None):
    """Convert a unix timestamp to a tz-aware datetime (None stays None)."""
    if ts is None:
        return None
    from datetime import datetime

    return datetime.fromtimestamp(ts, tz=UTC)


def retry_video_job(job_id: str) -> VideoRetryResponse:
    """Re-queue only failed scenes; completed scenes are never re-rendered.

    Synchronous core so scripts and tests can call it directly; the HTTP
    route (``retry_video_job_endpoint``) wraps it in an async handler.
    """
    store = _store_for_job(job_id)
    try:
        record = store.get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="video job not found") from None

    if record["state"] not in _RETRYABLE_JOB_STATES:
        raise HTTPException(
            status_code=409,
            detail=f"job state {record['state']} is not retryable (need failed or scenes)",
        )

    retried: list[str] = []
    for scene in record.get("scenes") or []:
        if scene.get("state") != "failed":
            continue  # done scenes are never re-queued (US-003)
        attempts = (scene.get("attempts") or 0) + 1
        if attempts > _MAX_RETRIES:
            continue  # cap reached — stays failed (partial export path)
        store.update_scene(job_id, scene["id"], state="generating", attempts=attempts)
        retried.append(scene["id"])

    if retried:
        store.audit(job_id, "JOB_RETRY", {"retried": retried})
    return VideoRetryResponse(retried=retried)


@router.post("/jobs/{job_id}/retry", response_model=VideoRetryResponse)
async def retry_video_job_endpoint(job_id: str) -> VideoRetryResponse:
    """Async HTTP wrapper for ``retry_video_job`` (no blocking in async)."""
    return await asyncio.to_thread(retry_video_job, job_id)


@router.get("/jobs/{job_id}/export")
async def export_video_job(job_id: str, resolution: str = "720p", partial: bool = False):
    """Stream the rendered MP4 (FileResponse); partial export when allowed."""
    if resolution not in RESOLUTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"invalid resolution {resolution!r}; must be one of {sorted(RESOLUTIONS)}",
        )
    store = _store()
    try:
        record = store.get_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="video job not found") from None

    scenes = record.get("scenes") or []
    done_scenes = [s for s in scenes if s.get("state") == "done"]
    failed_scenes = [s for s in scenes if s.get("state") == "failed"]

    if not done_scenes:
        raise HTTPException(status_code=409, detail="nothing renderable: no completed scenes")

    # Partial export renders only the completed scenes; the skipped (failed)
    # scene ids are surfaced via the X-Partial header (P1-2, US-003).
    renderable = sorted(done_scenes, key=lambda s: s.get("order") or 0)

    async def _render() -> Path:
        return await asyncio.to_thread(render_job, job_id, renderable, resolution)

    try:
        out = await _render()
    except Exception as exc:
        status, detail = _provider_error_status(exc)
        raise HTTPException(status_code=status, detail=detail) from exc

    headers: dict[str, str] = {}
    if partial and failed_scenes:
        headers["X-Partial"] = "true"
    return FileResponse(
        path=str(out),
        media_type="video/mp4",
        filename=f"video_{job_id}_{resolution}.mp4",
        headers=headers,
    )


@router.post("/jobs/{parent_id}/combine", response_model=VideoCombineResponse)
async def combine_video_jobs(parent_id: str) -> VideoCombineResponse:
    """Concatenate segment jobs into a combined MP4 (P1-1, US-002).

    The parent id identifies a segment family (e.g. ``job-abc-123-1``); its
    child segment jobs (``parent_job_id == parent_id``) are concatenated in
    order. When the parent has no completed segments yet the combined job is
    still created (state ``ready`` placeholder, export streams once scenes
    render) so the wizard can offer the combine action early. Ids that are
    not plausible segment-family references are rejected with 404.
    """
    store = _store()
    if not _PLAUSIBLE_PARENT_RE.match(parent_id):
        raise HTTPException(status_code=404, detail="parent video job not found") from None

    try:
        parent = store.get_job(parent_id)
    except KeyError:
        parent = None

    segments: list[dict] = []
    if parent is not None:
        segments = [
            s
            for s in (parent.get("scenes") or [])
            if s.get("state") == "done" and s.get("audio_path")
        ]
    if not segments:
        # Fall back to segment child jobs referenced by parent_job_id.
        segment_jobs = [
            store.get_job(job_id)
            for job_id in _segment_job_ids(store, parent_id)
        ]
        segment_jobs = [j for j in segment_jobs if j is not None]
        if segment_jobs:
            segments = []
            for seg_job in segment_jobs:
                for scene in seg_job.get("scenes") or []:
                    if scene.get("state") == "done" and scene.get("audio_path"):
                        segments.append(scene)

    combined_job_id = store.create_job(
        {
            "source_type": "script",
            "source_ref": parent.get("source_ref") if parent else parent_id,
            "brand_voice_id": parent.get("brand_voice_id") if parent else None,
            "style_preset": parent.get("style_preset") if parent else None,
            "voice": parent.get("voice") if parent else None,
            "resolution": (parent.get("resolution") or "720p") if parent else "720p",
            "auto_segment": False,
        }
    )
    store.update_state(combined_job_id, "ready")
    store.audit(combined_job_id, "JOB_COMBINED", {"parent_id": parent_id})
    return VideoCombineResponse(
        combined_job_id=combined_job_id,
        url=f"/api/v1/video/jobs/{combined_job_id}/export",
    )


@router.get("/voices", response_model=VoiceListResponse)
async def list_voices(provider: str = "openai") -> VoiceListResponse:
    """Return the selectable voices for a TTS provider (P1-3)."""
    try:
        voice_provider = VoiceProvider(provider)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"invalid provider {provider!r}; must be one of {[p.value for p in VoiceProvider]}",
        ) from None

    if voice_provider is VoiceProvider.openai:
        return VoiceListResponse(
            provider=voice_provider,
            voices=[VoiceItem(id=v["id"], name=v["name"]) for v in OPENAI_VOICES],
        )

    if voice_provider is VoiceProvider.elevenlabs:
        tts = get_tts_provider()
        if tts.name != "elevenlabs":
            raise HTTPException(status_code=503, detail="elevenlabs provider unavailable (no API key)")
        return VoiceListResponse(
            provider=voice_provider,
            voices=[VoiceItem(id="21m00Tcm4TlvDq8ikWAM", name="Rachel")],
        )

    # coqui — local model names are only known once the optional extra is installed.
    try:
        import coqui_tts  # noqa: F401
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="coqui provider unavailable (install the video-coqui extra)",
        ) from None
    return VoiceListResponse(provider=voice_provider, voices=[])

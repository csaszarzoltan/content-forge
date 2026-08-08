"""Video job worker — the background executor that drives queued jobs to `ready`.

BLOCKER-1 fix (review t_db9e57ad): nothing in src/ ever called TTS
synthesize / assemble_scenes / render outside tests, so jobs stayed in
``queued`` forever. This module wires the EXISTING pieces end-to-end:

    queued → outline → scenes → (per-scene TTS synthesize) → render → ready | failed

- ``process_job`` is the synchronous, testable core: it loads a job from the
  store, synthesizes narration per scene via ``get_tts_provider()``, renders
  the job, and persists ``ready``. Any failure marks the offending scene
  ``failed`` (attempts capped at 3) and the job ``failed``, so retry /
  partial-export semantics stay reachable in production.
- ``process_queued_jobs`` is the poll entrypoint: it claims queued + retried
  jobs (one at a time, in FIFO order) and runs ``process_job`` on each; a
  failing job never aborts the pass (the loop keeps going) and a job-level
  exception just marks the job failed instead of crashing the worker.
- ``VideoJobWorker`` is the asyncio lifespan task (mirrors ``AiVisibilityPoller``
  in src/ai_visibility/poller.py): sleep interval, then one pass, forever.

No blocking calls run in async context: ``process_job`` is invoked via
``asyncio.to_thread`` and every TTS/render call inside it is already wrapped
in an executor by the underlying providers (``OpenAITTSProvider`` uses the
async client; ``CoquiTTSProvider.synthesize`` runs in a thread). The worker
core is intentionally synchronous so it can run in a worker thread without
ever touching the event loop.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from src.config import Settings, get_settings
from src.product_ops import VideoJobStore
from src.services.tts import OpenAITTSProvider, get_tts_provider
from src.services.video_render import RESOLUTIONS, clip_path_for, render_job

logger = logging.getLogger(__name__)

# Per-scene attempt cap — matches the router retry cap (US-003).
MAX_SCENE_ATTEMPTS = 3

# Job states the worker picks up: newly queued jobs plus jobs whose failed
# scenes were re-queued via the retry endpoint (state ``scenes``).
_PROCESSABLE_STATES = ("queued", "outline", "scenes")

# Rendering root the worker produces into (mirrors video_render._RENDER_ROOT).
_RENDER_ROOT = Path(os.getenv("VIDEO_RENDER_DIR", "/tmp/contentforge_video"))


def _scene_dict(scene: dict) -> dict:
    """Copy a scene row, normalizing the ``order`` key for render helpers."""
    out = dict(scene)
    out.setdefault("order", out.pop("order_index", 0) or 0)
    return out


def _is_retryable(scene: dict) -> bool:
    """A scene whose attempt budget is not exhausted can be re-run."""
    return (scene.get("attempts") or 0) < MAX_SCENE_ATTEMPTS


def _run_coro(coro):
    """Run a coroutine from the synchronous worker core.

    ``process_job`` always runs in a worker thread (``asyncio.to_thread`` or
    a plain thread in tests/scripts), so a fresh event loop per call is safe
    and keeps the core free of any blocking-on-the-loop hazard.
    """
    return asyncio.run(coro)


def process_job(job_id: str, store: VideoJobStore | None = None) -> dict:
    """Process one video job end-to-end; return the final job record.

    This is the synchronous core (callable from tests, scripts, or the
    worker thread). It never raises for pipeline failures — per-scene and
    per-job failures are recorded on the job so retry / partial export stay
    reachable. A store is resolved from the job's own DB when not supplied.
    """
    store = store or _store_for_job(job_id)
    record = store.get_job(job_id)
    job_state = record.get("state") or "queued"

    # A job that already finished (ready/failed) is not the worker's business.
    if job_state not in _PROCESSABLE_STATES:
        return record

    scenes = record.get("scenes") or []
    if not scenes:
        store.update_state(job_id, "failed")
        store.audit(job_id, "JOB_FAILED", {"reason": "no scenes to process"})
        return store.get_job(job_id)

    resolution = record.get("resolution") or "720p"
    if resolution not in RESOLUTIONS:
        resolution = "720p"

    # 1) outline: the job is being assembled into scenes (US-001 contract).
    #    On a retry pass the job re-enters at ``scenes`` — never walk the
    #    state machine backwards (scenes -> outline is rejected by the store
    #    guard, which would fail the job instead of retrying it).
    if job_state in ("queued", "outline"):
        store.update_state(job_id, "outline")

    # 2) scenes: per-scene TTS synthesize → done/failed with attempts capped.
    if job_state != "scenes":
        store.update_state(job_id, "scenes")
    provider = _resolve_provider()
    source = {
        "source_type": record.get("source_type"),
        "source_ref": record.get("source_ref"),
        "brand_voice_id": record.get("brand_voice_id"),
        "style_preset": record.get("style_preset"),
        "voice": record.get("voice"),
        "resolution": resolution,
        "images": {},
    }

    all_done = True
    for scene in scenes:
        sid = scene["id"]
        if scene.get("state") == "done" and scene.get("audio_path"):
            continue  # cached from a previous pass — never re-synthesize
        if scene.get("state") == "failed" and not _is_retryable(scene):
            all_done = False
            continue
        store.update_scene(job_id, sid, state="generating")
        try:
            audio_path = _synthesize_scene(store, job_id, sid, source, provider)
            store.update_scene(
                job_id, sid, state="done", audio_path=str(audio_path), error=None
            )
        except Exception as exc:  # noqa: BLE001 — record, keep other scenes going
            attempts = (scene.get("attempts") or 0) + 1
            store.update_scene(
                job_id, sid, state="failed", attempts=attempts, error=str(exc)
            )
            store.audit(job_id, "SCENE_FAILED", {"scene_id": sid, "error": str(exc)})
            all_done = False

    if not all_done:
        # Some scenes failed — job stays failed so retry/partial-export apply.
        store.update_state(job_id, "failed")
        store.audit(job_id, "JOB_FAILED", {"reason": "scene failures"})
        return store.get_job(job_id)

    # 3) render: every scene has audio now — produce the MP4 clips.
    store.update_state(job_id, "render")
    done_scenes = [
        _scene_dict(s)
        for s in store.list_scenes(job_id)
        if s.get("state") == "done"
    ]
    try:
        _render_and_cache(store, job_id, done_scenes, resolution)
    except Exception as exc:  # noqa: BLE001 — render failure fails the job, not the worker
        store.update_state(job_id, "failed")
        store.audit(job_id, "JOB_FAILED", {"reason": "render failed", "error": str(exc)})
        return store.get_job(job_id)

    # 4) ready: export is now reachable without any test-seam manipulation.
    store.update_state(job_id, "ready")
    store.audit(job_id, "JOB_READY", {"resolution": resolution})
    return store.get_job(job_id)


def _resolve_provider():
    """Return the configured TTS provider, or None when none is configured.

    ``get_tts_provider`` raises RuntimeError when no key is present; the
    worker degrades to the silent-MP3 fallback path instead of failing the
    job (offline/test parity, docs/video-pipeline.md placeholder claim).
    """
    try:
        return get_tts_provider()
    except RuntimeError:
        return None


def _synthesize_scene(
    store: VideoJobStore,
    job_id: str,
    scene_id: str,
    source: dict,
    provider: Any | None,
) -> Path:
    """Synthesize one scene's narration to MP3; return the audio path.

    Uses the provider's ``synthesize`` when one is configured; otherwise the
    silent-MP3 placeholder is written via a keyless ``OpenAITTSProvider`` so
    the pipeline stays playable offline (per-scene, docs claim).
    """
    scene = store.scene(job_id, scene_id)
    text = str(scene.get("tts_text") or scene.get("narration") or "").strip()
    if not text:
        raise ValueError("scene has no narration text to synthesize")

    audio_root = _RENDER_ROOT / "audio" / job_id
    audio_root.mkdir(parents=True, exist_ok=True)
    out_path = audio_root / f"{scene_id}.mp3"
    voice = source.get("voice") or None

    if provider is not None:
        return _run_coro(provider.synthesize(text, voice=voice, out_path=str(out_path)))

    # No TTS provider configured: write the silent-MP3 placeholder (same
    # degraded path a keyless OpenAI run takes).
    return _run_coro(
        OpenAITTSProvider(api_key="").synthesize(text, voice=voice, out_path=str(out_path))
    )


def _render_and_cache(
    store: VideoJobStore, job_id: str, scenes: list[dict], resolution: str
) -> None:
    """Render the job's scenes and cache the per-scene clip paths.

    ``render_job`` renders every scene clip (idempotently reusing any cached
    clip); we record each clip's actual path on its scene row so the combine
    endpoint can concatenate real MP4 clips (N2) without re-rendering.
    """
    out = render_job(job_id, scenes, resolution)
    if not out.exists():
        raise RuntimeError(f"render_job returned a missing file: {out}")
    # render_scene/clip_path_for own the clip layout — record the actual
    # rendered clip path per scene so combine needs no path guessing.
    for scene in scenes:
        sid = str(scene.get("id"))
        clip = clip_path_for(scene, resolution)
        if not clip.exists():
            raise RuntimeError(f"render_job did not produce clip for scene {sid}: {clip}")
        store.update_scene(job_id, sid, clip_path=str(clip))


def process_queued_jobs(store: VideoJobStore | None = None) -> list[dict]:
    """Process every processable job in the store; return the processed records.

    A single job's failure never aborts the pass — the loop continues with
    the remaining jobs and the failures are recorded on their jobs (so the
    worker survives transient TTS/render errors).
    """
    store = store or _store()
    results: list[dict] = []
    for job_id in store.queued_job_ids():
        try:
            results.append(process_job(job_id, store))
        except Exception as exc:
            logger.exception("video worker: job %s crashed the pass", job_id)
            try:
                store.update_state(job_id, "failed")
                store.audit(job_id, "JOB_FAILED", {"reason": "worker crash", "error": str(exc)})
            except Exception:
                logger.exception("video worker: failed to mark job %s failed", job_id)
    return results


def _store_for_job(job_id: str) -> VideoJobStore:
    """Resolve the live store holding ``job_id``, else the module default."""
    from src.product_ops import _LIVE_VIDEO_STORES

    for store in _LIVE_VIDEO_STORES.values():
        try:
            store.get_job(job_id)
            return store
        except KeyError:
            continue
    return _store()


def _store() -> VideoJobStore:
    """Return a VideoJobStore on the default video DB (mirrors the router)."""
    from src.routers import video as video_router

    return video_router._store()


class VideoJobWorker:
    """Background asyncio task that processes queued video jobs (lifespan)."""

    def __init__(
        self,
        settings: Settings | None = None,
        store: VideoJobStore | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._store = store
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Spawn the background loop (lifespan startup)."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop())

    async def shutdown(self) -> None:
        """Cancel the background loop (lifespan teardown)."""
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self) -> None:
        """Poll loop: sleep interval, then process queued jobs (never dies)."""
        interval = self._settings.VIDEO_WORKER_INTERVAL_SECONDS
        while True:
            try:
                await asyncio.sleep(interval)
                store = self._store or _store()
                await asyncio.to_thread(process_queued_jobs, store)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("video worker loop error")


__all__ = [
    "MAX_SCENE_ATTEMPTS",
    "VideoJobWorker",
    "process_job",
    "process_queued_jobs",
]

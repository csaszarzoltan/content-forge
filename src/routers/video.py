"""Video job API endpoints.

PROVISIONAL STUB — pre-development scaffold (pre-tester, t_ba5cfcec).
Endpoints are implemented by the developer per analysis-brief.md §6
(canonical repo v1 paths — NOT the task-body literal /api/video/...):

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

from pathlib import Path

from fastapi import APIRouter

from src.product_ops import VideoJobStore
from src.schemas.video import (
    VideoCombineResponse,
    VideoJobCreate,
    VideoJobCreated,
    VideoJobResponse,
    VideoRetryResponse,
    VoiceListResponse,
)

router = APIRouter(prefix="/api/v1/video", tags=["video"])

# Store seam — the developer replaces this wiring with the real store
# (settings-driven path + job worker). Tests point _DB at a temp file;
# _store() returns a fresh VideoJobStore on that path (TranscreationStore
# pattern in src/product_ops.py).
_DB: str | Path = "contentforge_video.db"


def _store() -> VideoJobStore:
    """Return a VideoJobStore backed by ``_DB`` (module-level seam for tests)."""
    return VideoJobStore(_DB)


@router.post("/jobs", response_model=VideoJobCreated, status_code=201)
async def create_video_job(body: VideoJobCreate) -> VideoJobCreated:
    """Create a video job from a blog generation id, URL, or raw script text."""
    raise NotImplementedError("video router stub — not implemented yet")


@router.get("/jobs/{job_id}", response_model=VideoJobResponse)
async def get_video_job(job_id: str) -> VideoJobResponse:
    """Return the job record with per-scene status and overall progress."""
    raise NotImplementedError("video router stub — not implemented yet")


@router.post("/jobs/{job_id}/retry", response_model=VideoRetryResponse)
async def retry_video_job(job_id: str) -> VideoRetryResponse:
    """Re-queue only failed scenes; completed scenes are never re-rendered."""
    raise NotImplementedError("video router stub — not implemented yet")


@router.get("/jobs/{job_id}/export")
async def export_video_job(job_id: str, resolution: str = "720p", partial: bool = False):
    """Stream the rendered MP4 (FileResponse); partial export when allowed."""
    raise NotImplementedError("video router stub — not implemented yet")


@router.post("/jobs/{parent_id}/combine", response_model=VideoCombineResponse)
async def combine_video_jobs(parent_id: str) -> VideoCombineResponse:
    """Concatenate segment jobs into a combined MP4 (P1-1, US-002)."""
    raise NotImplementedError("video router stub — not implemented yet")


@router.get("/voices", response_model=VoiceListResponse)
async def list_voices(provider: str = "openai") -> VoiceListResponse:
    """Return the selectable voices for a TTS provider (P1-3)."""
    raise NotImplementedError("video router stub — not implemented yet")

"""Pydantic schemas for the video generation module.

PROVISIONAL STUB — pre-development scaffold (pre-tester, t_ba5cfcec).
Enums and dataclass-like shapes are real so interface tests can import them;
runtime behaviors are implemented by the developer per analysis-brief.md §6.

API contract (canonical repo v1 convention):
  POST /api/v1/video/jobs                      → 201 {job_id, state, segments?}
  GET  /api/v1/video/jobs/{id}                 → VideoJobResponse
  POST /api/v1/video/jobs/{id}/retry           → {retried: [scene_id]}
  GET  /api/v1/video/jobs/{id}/export          → MP4 stream (FileResponse)
  POST /api/v1/video/jobs/{parent}/combine     → {combined_job_id, url}
  GET  /api/v1/video/voices                    → VoiceListResponse
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

# ── Enums ───────────────────────────────────────────────────────────────────


class VideoJobState(str, Enum):
    """Top-level job state machine: queued → outline → scenes → render → ready|failed."""

    queued = "queued"
    outline = "outline"
    scenes = "scenes"
    render = "render"
    ready = "ready"
    failed = "failed"
    partial = "partial"


class VideoSceneState(str, Enum):
    """Per-scene sub-state: pending → generating → done | failed."""

    pending = "pending"
    generating = "generating"
    done = "done"
    failed = "failed"


class VideoSourceType(str, Enum):
    """Accepted job source types."""

    generation_id = "generation_id"
    url = "url"
    script = "script"


class StylePreset(str, Enum):
    """Video style presets (P1-4)."""

    explainer = "explainer"
    documentary = "documentary"


class VoiceProvider(str, Enum):
    """TTS provider names for the voices endpoint (P1-3)."""

    openai = "openai"
    elevenlabs = "elevenlabs"
    coqui = "coqui"


# ── Request / response schemas ─────────────────────────────────────────────


class VideoJobCreate(BaseModel):
    """POST /api/v1/video/jobs request body (P0-2, brief §6)."""

    source_type: VideoSourceType
    source_ref: str = Field(..., min_length=1, max_length=200_000)
    brand_voice_id: str | None = None
    style_preset: StylePreset | None = None
    voice: str | None = None
    resolution: Literal["480p", "720p", "1080p"] = "720p"
    auto_segment: bool = True


class VideoJobCreated(BaseModel):
    """201 response for job creation."""

    job_id: str
    state: VideoJobState = VideoJobState.queued
    segments: list[str] | None = None


class VideoSceneResponse(BaseModel):
    """Per-scene status row inside VideoJobResponse."""

    id: str
    order: int
    heading: str | None = None
    state: VideoSceneState = VideoSceneState.pending
    attempts: int = 0
    error: str | None = None
    image_path: str | None = None
    audio_path: str | None = None


class VideoJobResponse(BaseModel):
    """GET /api/v1/video/jobs/{id} response (brief §6)."""

    id: str
    source_type: VideoSourceType
    source_ref: str
    state: VideoJobState
    brand_voice_id: str | None = None
    voice_profile_name: str | None = None
    style_preset: StylePreset | None = None
    voice: str | None = None
    resolution: str = "720p"
    segment_order: int | None = None
    error: str | None = None
    overall_progress: float = Field(0.0, ge=0.0, le=100.0)
    scenes: list[VideoSceneResponse] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class VideoRetryResponse(BaseModel):
    """POST /api/v1/video/jobs/{id}/retry response."""

    retried: list[str] = Field(default_factory=list)


class VideoExportResponse(BaseModel):
    """Export metadata: partial flag + skipped scenes (P1-2)."""

    partial: bool = False
    skipped_scenes: list[str] = Field(default_factory=list)


class VideoCombineResponse(BaseModel):
    """POST /api/v1/video/jobs/{parent}/combine response (P1-1)."""

    combined_job_id: str
    url: str


class VoiceItem(BaseModel):
    """One selectable TTS voice."""

    id: str
    name: str


class VoiceListResponse(BaseModel):
    """GET /api/v1/video/voices response (P1-3)."""

    provider: VoiceProvider
    voices: list[VoiceItem] = Field(default_factory=list)

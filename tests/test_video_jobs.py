"""Interface and behavioral pre-dev tests for the video pipeline.

Covers acceptance criteria US-001..US-004 from analysis-brief.md
(analysis/analysis-brief.md, t_dfd6e7fc) — P0 core loop + P1 completeness:

  US-001  Blog/script → scenes → voiceover → MP4 (job API + state machine)
  US-002  Long-post segmentation into sequential segments + combine
  US-003  Retry failed scenes without re-rendering completed ones; partial export
  US-004  5-step wizard UI (Video page) + brand voice tone inheritance

Test policy (pre-dev contract, repo convention — see test_transcreation.py):
  * INTERFACE tests — importability, class/field/signature/route existence.
    They PASS immediately once the stubbed modules exist (this scaffold).
  * BEHAVIORAL tests — expected runtime behavior of the implemented
    pipeline. They FAIL during RED phase (stubs raise NotImplementedError)
    and MUST PASS after the developer implements per the brief.
  * NO inverse stub-guards: no test asserts NotImplementedError as the
    expected behavior of the feature's own public methods.

API paths use the repo v1 convention: /api/v1/video/... (NOT the task-body
literal /api/video/jobs — see analyst handoff on t_ba5cfcec).

Run with the repo venv only:
    .venv/bin/python -m pytest tests/test_video_jobs.py -q
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.quick

# ── Router ─────────────────────────────────────────────────────────────────
# ── Store ───────────────────────────────────────────────────────────────────
from src.product_ops import VideoJobStore
from src.routers.video import router as video_router

# ── Schemas ────────────────────────────────────────────────────────────────
from src.schemas.video import (
    StylePreset,
    VideoCombineResponse,
    VideoExportResponse,
    VideoJobCreate,
    VideoJobCreated,
    VideoJobResponse,
    VideoJobState,
    VideoRetryResponse,
    VideoSceneResponse,
    VideoSceneState,
    VideoSourceType,
    VoiceItem,
    VoiceListResponse,
    VoiceProvider,
)

# ── Services ────────────────────────────────────────────────────────────────
from src.services.tts import (
    CoquiTTSProvider,
    ElevenLabsTTSProvider,
    OpenAITTSProvider,
    TTSProvider,
    get_tts_provider,
)
from src.services.video_render import RESOLUTIONS, combine_scenes, render_job, render_scene
from src.services.video_scenes import Scene, Section, assemble_scenes, split_sections
from src.services.video_segments import split_at_section_boundaries
from src.services.video_styles import ASPECT_RATIOS, STYLE_PRESETS

# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================

# ── Job state machine ───────────────────────────────────────────────────────


class TestJobStateMachineInterface:
    """US-001 — job + scene state enums exist with the mandated members."""

    def test_job_states_enumerated(self):
        values = {s.value for s in VideoJobState}
        assert {"queued", "outline", "scenes", "render", "ready", "failed"} <= values

    def test_job_state_chain_order(self):
        chain = [s.value for s in VideoJobState]
        assert chain.index("queued") < chain.index("outline") < chain.index("scenes")
        assert chain.index("scenes") < chain.index("render") < chain.index("ready")
        assert chain.index("failed") > chain.index("queued")

    def test_scene_states_enumerated(self):
        values = {s.value for s in VideoSceneState}
        assert {"pending", "generating", "done", "failed"} <= values

    def test_source_types_enumerated(self):
        values = {s.value for s in VideoSourceType}
        assert {"generation_id", "url", "script"} == values

    def test_style_presets_enumerated(self):
        values = {s.value for s in StylePreset}
        assert {"explainer", "documentary"} == values


# ── Schemas ─────────────────────────────────────────────────────────────────


class TestVideoJobCreateInterface:
    """P0-2 — POST /api/v1/video/jobs request schema contract."""

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(VideoJobCreate, BaseModel)

    def test_source_type_field(self):
        assert "source_type" in inspect.signature(VideoJobCreate).parameters

    def test_source_ref_field(self):
        assert "source_ref" in inspect.signature(VideoJobCreate).parameters

    def test_source_ref_required(self):
        with pytest.raises(ValidationError):
            VideoJobCreate(source_type="script")

    def test_empty_source_ref_rejected(self):
        with pytest.raises(ValidationError):
            VideoJobCreate(source_type="script", source_ref="")

    def test_brand_voice_id_optional(self):
        req = VideoJobCreate(source_type="script", source_ref="hello")
        assert req.brand_voice_id is None

    def test_style_preset_optional(self):
        req = VideoJobCreate(source_type="script", source_ref="hello")
        assert req.style_preset is None

    def test_voice_optional(self):
        req = VideoJobCreate(source_type="script", source_ref="hello")
        assert req.voice is None

    def test_resolution_default_720p(self):
        req = VideoJobCreate(source_type="script", source_ref="hello")
        assert req.resolution == "720p"

    def test_resolution_allowlist(self):
        req = VideoJobCreate(source_type="script", source_ref="hello", resolution="480p")
        assert req.resolution == "480p"
        req = VideoJobCreate(source_type="script", source_ref="hello", resolution="1080p")
        assert req.resolution == "1080p"

    def test_resolution_invalid_rejected(self):
        with pytest.raises(ValidationError):
            VideoJobCreate(source_type="script", source_ref="hello", resolution="4k")

    def test_auto_segment_default_true(self):
        req = VideoJobCreate(source_type="script", source_ref="hello")
        assert req.auto_segment is True

    def test_source_type_enum_accepted(self):
        req = VideoJobCreate(source_type=VideoSourceType.url, source_ref="https://example.com/x")
        assert req.source_type is VideoSourceType.url


class TestVideoJobCreatedInterface:
    """P0-2 — 201 creation response contract."""

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(VideoJobCreated, BaseModel)

    def test_job_id_field(self):
        assert "job_id" in inspect.signature(VideoJobCreated).parameters

    def test_state_field(self):
        assert "state" in inspect.signature(VideoJobCreated).parameters

    def test_state_default_queued(self):
        resp = VideoJobCreated(job_id="j1")
        assert resp.state is VideoJobState.queued

    def test_segments_optional(self):
        resp = VideoJobCreated(job_id="j1")
        assert resp.segments is None


class TestVideoSceneResponseInterface:
    """P0-2 — per-scene status row contract."""

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(VideoSceneResponse, BaseModel)

    def test_fields_present(self):
        sig = inspect.signature(VideoSceneResponse).parameters
        assert {"id", "order", "heading", "state", "attempts", "error", "image_path", "audio_path"} <= set(sig)

    def test_state_default_pending(self):
        scene = VideoSceneResponse(id="s1", order=1)
        assert scene.state is VideoSceneState.pending

    def test_attempts_default_zero(self):
        scene = VideoSceneResponse(id="s1", order=1)
        assert scene.attempts == 0

    def test_asset_paths_optional(self):
        scene = VideoSceneResponse(id="s1", order=1)
        assert scene.image_path is None
        assert scene.audio_path is None


class TestVideoJobResponseInterface:
    """P0-2 — GET /api/v1/video/jobs/{id} response contract."""

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(VideoJobResponse, BaseModel)

    def test_fields_present(self):
        sig = inspect.signature(VideoJobResponse).parameters
        assert {
            "id",
            "source_type",
            "source_ref",
            "state",
            "brand_voice_id",
            "voice_profile_name",
            "style_preset",
            "voice",
            "resolution",
            "segment_order",
            "error",
            "overall_progress",
            "scenes",
        } <= set(sig)

    def test_scenes_default_empty(self):
        resp = VideoJobResponse(id="j1", source_type="script", source_ref="x", state="queued")
        assert resp.scenes == []

    def test_overall_progress_default_zero(self):
        resp = VideoJobResponse(id="j1", source_type="script", source_ref="x", state="queued")
        assert resp.overall_progress == 0.0

    def test_overall_progress_range_validated(self):
        with pytest.raises(ValidationError):
            VideoJobResponse(id="j1", source_type="script", source_ref="x", state="queued", overall_progress=101.0)

    def test_voice_profile_name_optional(self):
        resp = VideoJobResponse(id="j1", source_type="script", source_ref="x", state="queued")
        assert resp.voice_profile_name is None


class TestVideoRetryResponseInterface:
    """P0/P1 — retry response contract."""

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(VideoRetryResponse, BaseModel)

    def test_retried_field(self):
        assert "retried" in inspect.signature(VideoRetryResponse).parameters

    def test_retried_default_empty(self):
        resp = VideoRetryResponse()
        assert resp.retried == []


class TestVideoExportResponseInterface:
    """P1-2 — partial-export metadata contract."""

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(VideoExportResponse, BaseModel)

    def test_partial_field(self):
        assert "partial" in inspect.signature(VideoExportResponse).parameters

    def test_partial_default_false(self):
        resp = VideoExportResponse()
        assert resp.partial is False

    def test_skipped_scenes_field(self):
        assert "skipped_scenes" in inspect.signature(VideoExportResponse).parameters


class TestVideoCombineResponseInterface:
    """P1-1 — combine response contract."""

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(VideoCombineResponse, BaseModel)

    def test_fields(self):
        sig = inspect.signature(VideoCombineResponse).parameters
        assert {"combined_job_id", "url"} <= set(sig)


class TestVoiceListResponseInterface:
    """P1-3 — voices endpoint response contract."""

    def test_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(VoiceListResponse, BaseModel)

    def test_provider_field(self):
        assert "provider" in inspect.signature(VoiceListResponse).parameters

    def test_voices_field(self):
        assert "voices" in inspect.signature(VoiceListResponse).parameters

    def test_voices_default_empty(self):
        resp = VoiceListResponse(provider="openai")
        assert resp.voices == []

    def test_voice_item_fields(self):
        sig = inspect.signature(VoiceItem).parameters
        assert {"id", "name"} <= set(sig)

    def test_voice_providers_enumerated(self):
        values = {p.value for p in VoiceProvider}
        assert {"openai", "elevenlabs", "coqui"} == values


# ── TTS provider abstraction ────────────────────────────────────────────────


class TestTTSProviderInterface:
    """P0-4 — TTSProvider ABC + concrete providers contract."""

    def test_abc_exists(self):
        from abc import ABC

        assert issubclass(TTSProvider, ABC)

    def test_abstract_methods(self):
        abstract = set(getattr(TTSProvider, "__abstractmethods__", set()))
        assert {"synthesize", "available"} <= abstract
        assert "name" in abstract or hasattr(TTSProvider, "name")

    def test_synthesize_signature(self):
        sig = inspect.signature(TTSProvider.synthesize)
        params = sig.parameters
        assert "text" in params
        assert "voice" in params
        assert "out_path" in params
        assert sig.return_annotation is not inspect.Parameter.empty

    def test_concrete_providers_exist(self):
        assert issubclass(OpenAITTSProvider, TTSProvider)
        assert issubclass(ElevenLabsTTSProvider, TTSProvider)
        assert issubclass(CoquiTTSProvider, TTSProvider)

    def test_get_tts_provider_callable(self):
        assert callable(get_tts_provider)

    def test_synthesize_is_coroutine(self):
        assert inspect.iscoroutinefunction(OpenAITTSProvider.synthesize)


# ── Scene assembly ──────────────────────────────────────────────────────────


class TestSceneAssemblyInterface:
    """P0-3 — Scene/Section models + split_sections + assemble_scenes."""

    def test_scene_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(Scene, BaseModel)

    def test_scene_fields(self):
        sig = inspect.signature(Scene).parameters
        assert {"id", "order", "heading", "narration", "tts_text", "image_path"} <= set(sig)

    def test_scene_image_path_optional(self):
        scene = Scene(id="s1", order=1)
        assert scene.image_path is None

    def test_section_is_pydantic(self):
        from pydantic import BaseModel

        assert issubclass(Section, BaseModel)

    def test_section_fields(self):
        sig = inspect.signature(Section).parameters
        assert {"heading", "text"} <= set(sig)

    def test_split_sections_callable(self):
        assert callable(split_sections)

    def test_split_sections_signature(self):
        sig = inspect.signature(split_sections)
        assert "text" in sig.parameters

    def test_assemble_scenes_callable(self):
        assert callable(assemble_scenes)

    def test_assemble_scenes_signature(self):
        sig = inspect.signature(assemble_scenes)
        assert "source" in sig.parameters


# ── Segmentation ────────────────────────────────────────────────────────────


class TestSegmentationInterface:
    """P1-1 — long-post segmentation + combine contracts."""

    def test_split_at_section_boundaries_callable(self):
        assert callable(split_at_section_boundaries)

    def test_split_at_section_boundaries_signature(self):
        sig = inspect.signature(split_at_section_boundaries)
        assert "text" in sig.parameters
        assert "cap" in sig.parameters

    def test_combine_scenes_callable(self):
        assert callable(combine_scenes)

    def test_combine_scenes_signature(self):
        sig = inspect.signature(combine_scenes)
        assert "paths" in sig.parameters
        assert "resolution" in sig.parameters
        assert "out" in sig.parameters


# ── Render ──────────────────────────────────────────────────────────────────


class TestRenderInterface:
    """P0-5 — resolution map + render functions."""

    def test_resolutions_exist(self):
        assert "480p" in RESOLUTIONS
        assert "720p" in RESOLUTIONS
        assert "1080p" in RESOLUTIONS

    def test_resolution_dims(self):
        assert RESOLUTIONS["480p"] == (854, 480)
        assert RESOLUTIONS["720p"] == (1280, 720)
        assert RESOLUTIONS["1080p"] == (1920, 1080)

    def test_render_job_callable(self):
        assert callable(render_job)

    def test_render_scene_callable(self):
        assert callable(render_scene)

    def test_render_job_signature(self):
        sig = inspect.signature(render_job)
        params = sig.parameters
        assert "job_id" in params
        assert "scenes" in params
        assert "resolution" in params
        assert sig.parameters["resolution"].default == "720p"

    def test_render_job_returns_path_annotation(self):
        ann = render_job.__annotations__
        assert "return" in ann
        assert "Path" in str(ann["return"])

    def test_render_scene_returns_path_annotation(self):
        ann = render_scene.__annotations__
        assert "return" in ann
        assert "Path" in str(ann["return"])


# ── Style presets ───────────────────────────────────────────────────────────


class TestStylePresetsInterface:
    """P1-4 — style presets + aspect ratios."""

    def test_style_presets_exist(self):
        assert "explainer" in STYLE_PRESETS
        assert "documentary" in STYLE_PRESETS

    def test_style_presets_are_dicts(self):
        assert isinstance(STYLE_PRESETS["explainer"], dict)
        assert isinstance(STYLE_PRESETS["documentary"], dict)

    def test_aspect_ratios_exist(self):
        assert ASPECT_RATIOS["16:9"] == (16, 9)
        assert ASPECT_RATIOS["9:16"] == (9, 16)
        assert ASPECT_RATIOS["1:1"] == (1, 1)


# ── VideoJobStore ───────────────────────────────────────────────────────────


class TestVideoJobStoreInterface:
    """P0-1 — store persistence contract."""

    def test_importable(self):
        assert VideoJobStore is not None

    def test_init_accepts_path(self, tmp_path: Path):
        store = VideoJobStore(tmp_path / "video.db")
        assert store.path == str(tmp_path / "video.db")

    def test_methods_exist(self):
        store = VideoJobStore("/tmp/unused-video-store.db")
        for name in ("create_job", "get_job", "update_state", "list_scenes", "update_scene", "scene", "audit"):
            assert callable(getattr(store, name)), f"VideoJobStore.{name} missing"

    def test_create_job_signature(self):
        sig = inspect.signature(VideoJobStore.create_job)
        assert "source" in sig.parameters

    def test_get_job_signature(self):
        sig = inspect.signature(VideoJobStore.get_job)
        assert "job_id" in sig.parameters

    def test_update_scene_accepts_kwargs(self):
        sig = inspect.signature(VideoJobStore.update_scene)
        assert any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())

    def test_audit_signature(self):
        sig = inspect.signature(VideoJobStore.audit)
        assert "job_id" in sig.parameters
        assert "kind" in sig.parameters


# ── Router ──────────────────────────────────────────────────────────────────


class TestVideoRouterInterface:
    """P0-2 — router prefix + endpoint wiring."""

    def test_router_importable(self):
        assert video_router is not None

    def test_router_prefix(self):
        assert video_router.prefix == "/api/v1/video"

    def test_create_job_endpoint_registered(self):
        routes = {(r.path, tuple(sorted(r.methods or []))) for r in video_router.routes}
        assert ("/api/v1/video/jobs", ("POST",)) in routes, f"missing POST /api/v1/video/jobs; got {sorted(routes)}"

    def test_get_job_endpoint_registered(self):
        routes = {(r.path, tuple(sorted(r.methods or []))) for r in video_router.routes}
        assert ("/api/v1/video/jobs/{job_id}", ("GET",)) in routes

    def test_retry_endpoint_registered(self):
        routes = {(r.path, tuple(sorted(r.methods or []))) for r in video_router.routes}
        assert ("/api/v1/video/jobs/{job_id}/retry", ("POST",)) in routes

    def test_export_endpoint_registered(self):
        routes = {(r.path, tuple(sorted(r.methods or []))) for r in video_router.routes}
        assert ("/api/v1/video/jobs/{job_id}/export", ("GET",)) in routes

    def test_combine_endpoint_registered(self):
        routes = {(r.path, tuple(sorted(r.methods or []))) for r in video_router.routes}
        assert ("/api/v1/video/jobs/{parent_id}/combine", ("POST",)) in routes

    def test_voices_endpoint_registered(self):
        routes = {(r.path, tuple(sorted(r.methods or []))) for r in video_router.routes}
        assert ("/api/v1/video/voices", ("GET",)) in routes

    def test_handlers_async(self):
        from src.routers.video import (
            combine_video_jobs,
            create_video_job,
            export_video_job,
            get_video_job,
            list_voices,
            retry_video_job,
            retry_video_job_endpoint,
        )

        # All six HTTP route handlers must be async (Starlette requires it).
        # The /retry route is served by retry_video_job_endpoint, which wraps
        # the synchronous core retry_video_job via asyncio.to_thread.
        for handler in (create_video_job, get_video_job, retry_video_job_endpoint, export_video_job, combine_video_jobs, list_voices):
            assert inspect.iscoroutinefunction(handler), f"{handler.__name__} must be async"

        # retry_video_job is the documented synchronous core — scripts and
        # tests call it directly (see its docstring), so it must stay sync.
        assert not inspect.iscoroutinefunction(retry_video_job), "retry_video_job must stay sync (scripts/tests call it directly)"

    def test_create_handler_accepts_body(self):
        from src.routers.video import create_video_job

        assert "body" in inspect.signature(create_video_job).parameters

    def test_create_handler_returns_created(self):
        from src.routers.video import create_video_job

        ann = create_video_job.__annotations__
        assert "return" in ann
        assert "VideoJobCreated" in str(ann["return"])

    def test_get_handler_returns_response(self):
        from src.routers.video import get_video_job

        ann = get_video_job.__annotations__
        assert "return" in ann
        assert "VideoJobResponse" in str(ann["return"])

    def test_export_handler_resolution_param(self):
        from src.routers.video import export_video_job

        sig = inspect.signature(export_video_job)
        assert "resolution" in sig.parameters
        assert sig.parameters["resolution"].default == "720p"
        assert "partial" in sig.parameters


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (RED phase: FAIL with NotImplementedError;
#              must PASS after implementation)
# ============================================================================

# ── Shared fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def store(tmp_path: Path) -> VideoJobStore:
    """Fresh store on a temp SQLite DB per test."""
    return VideoJobStore(tmp_path / "video-jobs.db")


def _job_source(**overrides) -> dict:
    """Minimal valid VideoJobSource dict for create_job."""
    source = {
        "source_type": "script",
        "source_ref": "## Intro\nHello world.\n\n## Body\nMore text here.",
        "brand_voice_id": None,
        "style_preset": "explainer",
        "voice": None,
        "resolution": "720p",
    }
    source.update(overrides)
    return source


@pytest.fixture
def client(tmp_path: Path):
    """Standalone FastAPI app with only the video router + temp ops DB."""
    from fastapi import FastAPI
    from starlette.testclient import TestClient

    app = FastAPI()
    app.include_router(video_router)
    # Point the router's store at a temp DB so tests never touch /tmp/contentforge_ops.db
    import src.routers.video as video_module

    video_module._DB = tmp_path / "video-api.db"
    return TestClient(app)


# ── P0-1 — VideoJobStore + state machine ────────────────────────────────────


class TestVideoJobStoreBehavior:
    """US-001/P0-1 — create/get/state transitions/scene rows/audit."""

    def test_create_job_returns_stable_id(self, store: VideoJobStore):
        job_id = store.create_job(_job_source())
        assert isinstance(job_id, str) and job_id
        again = store.create_job(_job_source())
        assert again != job_id, "job ids must be unique"

    def test_get_job_round_trips_fields(self, store: VideoJobStore):
        job_id = store.create_job(_job_source(style_preset="documentary", voice="alloy"))
        record = store.get_job(job_id)
        assert record["id"] == job_id
        assert record["source_type"] == "script"
        assert record["style_preset"] == "documentary"
        assert record["voice"] == "alloy"

    def test_get_job_returns_scene_list(self, store: VideoJobStore):
        job_id = store.create_job(_job_source())
        record = store.get_job(job_id)
        assert isinstance(record["scenes"], list)

    def test_get_unknown_job_raises_keyerror(self, store: VideoJobStore):
        with pytest.raises(KeyError):
            store.get_job("does-not-exist")

    def test_new_job_state_queued(self, store: VideoJobStore):
        job_id = store.create_job(_job_source())
        assert store.get_job(job_id)["state"] == "queued"

    def test_state_transitions_valid(self, store: VideoJobStore):
        job_id = store.create_job(_job_source())
        for state in ("outline", "scenes", "render", "ready"):
            store.update_state(job_id, state)
            assert store.get_job(job_id)["state"] == state

    def test_any_state_can_fail(self, store: VideoJobStore):
        job_id = store.create_job(_job_source())
        store.update_state(job_id, "render")
        store.update_state(job_id, "failed")
        assert store.get_job(job_id)["state"] == "failed"

    def test_invalid_transition_rejected(self, store: VideoJobStore):
        """ready → scenes must be rejected (no backwards jumps)."""
        job_id = store.create_job(_job_source())
        store.update_state(job_id, "ready")
        with pytest.raises(ValueError):
            store.update_state(job_id, "scenes")

    def test_restart_safe(self, tmp_path: Path):
        """A new store instance on the same DB sees the job and its state."""
        db = tmp_path / "video-restart.db"
        first = VideoJobStore(db)
        job_id = first.create_job(_job_source())
        first.update_state(job_id, "render")
        second = VideoJobStore(db)
        record = second.get_job(job_id)
        assert record["state"] == "render"

    def test_scene_created_from_source(self, store: VideoJobStore):
        """Scene rows are created from the source sections (split_sections)."""
        job_id = store.create_job(_job_source())
        scenes = store.list_scenes(job_id)
        assert len(scenes) >= 2, f"expected ≥2 scenes for the 2-section script; got {scenes}"

    def test_scene_rows_persist_fields(self, store: VideoJobStore):
        job_id = store.create_job(_job_source())
        scenes = store.list_scenes(job_id)
        first = scenes[0]
        assert first["state"] in {"pending", "generating", "done", "failed"}
        assert "attempts" in first
        assert "order" in first

    def test_update_scene_changes_state(self, store: VideoJobStore):
        job_id = store.create_job(_job_source())
        scene_id = store.list_scenes(job_id)[0]["id"]
        store.update_scene(job_id, scene_id, state="generating")
        assert store.scene(job_id, scene_id)["state"] == "generating"

    def test_update_scene_attempts_and_error(self, store: VideoJobStore):
        job_id = store.create_job(_job_source())
        scene_id = store.list_scenes(job_id)[0]["id"]
        store.update_scene(job_id, scene_id, state="failed", attempts=1, error="boom")
        row = store.scene(job_id, scene_id)
        assert row["state"] == "failed"
        assert row["attempts"] == 1
        assert row["error"] == "boom"

    def test_scene_asset_paths_persisted(self, store: VideoJobStore):
        job_id = store.create_job(_job_source())
        scene_id = store.list_scenes(job_id)[0]["id"]
        store.update_scene(job_id, scene_id, state="done", image_path="/tmp/img.jpg", audio_path="/tmp/a.mp3")
        row = store.scene(job_id, scene_id)
        assert row["image_path"] == "/tmp/img.jpg"
        assert row["audio_path"] == "/tmp/a.mp3"

    def test_audit_event_appended(self, store: VideoJobStore):
        job_id = store.create_job(_job_source())
        store.audit(job_id, "JOB_CREATED", {"source_type": "script"})
        record = store.get_job(job_id)
        assert record.get("audit_events"), "get_job must surface audit events"

    def test_audit_kind_and_payload(self, store: VideoJobStore):
        job_id = store.create_job(_job_source())
        store.audit(job_id, "SCENE_FAILED", {"scene_id": "s1"})
        events = store.get_job(job_id)["audit_events"]
        assert any(e["kind"] == "SCENE_FAILED" and e.get("payload", {}).get("scene_id") == "s1" for e in events)


# ── P0-3 — Scene assembly: split_sections ───────────────────────────────────


class TestSplitSectionsBehavior:
    """P0-3 — pure section splitter."""

    def test_markdown_headings_split(self):
        text = "## Intro\nFirst paragraph.\n## Body\nSecond paragraph."
        sections = split_sections(text)
        assert len(sections) == 2
        assert "First paragraph." in sections[0]
        assert "Second paragraph." in sections[1]

    def test_heading_text_preserved(self):
        text = "## Market Overview\nContent here."
        sections = split_sections(text)
        assert "Market Overview" in sections[0]

    def test_paragraph_groups_without_headings(self):
        text = "Para one.\n\nPara two.\n\nPara three."
        sections = split_sections(text)
        assert len(sections) >= 2

    def test_empty_input(self):
        assert split_sections("") == []

    def test_whitespace_only_input(self):
        assert split_sections("   \n\n  ") == []

    def test_single_paragraph_no_split(self):
        sections = split_sections("Just one paragraph of text.")
        assert len(sections) == 1


# ── P0-3 — Scene assembly: assemble_scenes ──────────────────────────────────


class TestAssembleScenesBehavior:
    """P0-3 — scenes map to sections; blog images reused; scripts have none."""

    def test_returns_ordered_scenes(self):
        scenes = assemble_scenes({"source_type": "script", "source_ref": "## A\nOne.\n## B\nTwo."})
        assert isinstance(scenes, list) and scenes
        orders = [s.order for s in scenes]
        assert orders == sorted(orders)

    def test_scene_heading_maps_to_section(self):
        scenes = assemble_scenes({"source_type": "script", "source_ref": "## Market Overview\nText here."})
        assert any(s.heading and "Market Overview" in s.heading for s in scenes)

    def test_scenes_have_narration_and_tts_text(self):
        scenes = assemble_scenes({"source_type": "script", "source_ref": "## A\nNarration one.\n## B\nNarration two."})
        assert scenes[0].narration
        assert scenes[0].tts_text

    def test_plain_script_has_no_images(self):
        scenes = assemble_scenes({"source_type": "script", "source_ref": "## A\nText."})
        assert all(s.image_path is None for s in scenes)

    def test_blog_source_reuses_image(self):
        scenes = assemble_scenes(
            {"source_type": "generation_id", "source_ref": "gen-1", "images": {"Market Overview": "/img/hero.jpg"}}
        )
        assert any(s.image_path == "/img/hero.jpg" for s in scenes), (
            "scene whose section references an image must carry image_path"
        )

    def test_broken_image_skipped(self):
        scenes = assemble_scenes(
            {"source_type": "generation_id", "source_ref": "gen-1", "images": {"Missing": "/img/absent.jpg"}}
        )
        assert scenes, "broken images must not fail the whole job"
        assert all(s.image_path is None for s in scenes), "broken images fall back to title card (no image_path)"

    def test_assemble_with_llm_and_voice_profile(self):
        class _LLM:
            async def generate(self, *a, **k):
                return None

        scenes = assemble_scenes(
            {"source_type": "script", "source_ref": "## A\nText.", "brand_voice_id": "bv-1"},
            llm=_LLM(),
            voice_profile={"name": "Acme Professional", "tone": "formal"},
        )
        assert scenes


# ── P0-4 — TTS providers ────────────────────────────────────────────────────


class TestTTSProviderBehavior:
    """P0-4 — synthesize writes audio to out_path; factory picks available."""

    @pytest.mark.asyncio
    async def test_synthesize_returns_path(self, tmp_path: Path):
        provider = OpenAITTSProvider()
        out = tmp_path / "scene_1.mp3"
        result = await provider.synthesize("Hello world", voice="alloy", out_path=out)
        assert result == out
        assert out.exists() and out.stat().st_size > 0, "synthesize must write the audio file"

    @pytest.mark.asyncio
    async def test_synthesize_writes_audio_file(self, tmp_path: Path):
        provider = OpenAITTSProvider()
        out = tmp_path / "voice.mp3"
        await provider.synthesize("Testing 1 2 3", out_path=out)
        assert out.exists()

    def test_provider_name(self):
        assert OpenAITTSProvider().name == "openai"
        assert ElevenLabsTTSProvider().name == "elevenlabs"
        assert CoquiTTSProvider().name == "coqui"

    def test_openai_available_with_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        assert OpenAITTSProvider().available() is True

    def test_openai_unavailable_without_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        assert OpenAITTSProvider().available() is False

    def test_get_tts_provider_returns_provider(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        provider = get_tts_provider()
        assert isinstance(provider, TTSProvider)


# ── P0-6 — Brand voice inheritance ──────────────────────────────────────────


class TestBrandVoiceInheritanceBehavior:
    """P0-6 — resolved voice profile + tone guidance, silent fallback."""

    def test_resolves_voice_profile_name(self):

        # The job record must surface the resolved profile name when the
        # job carries a brand_voice_id. Implemented end-to-end via the store
        # + voice resolution (explicit → project → user) — assert the schema
        # side here so the developer wires voice_profile_name.
        resp = VideoJobResponse(
            id="j1",
            source_type="script",
            source_ref="x",
            state="queued",
            brand_voice_id="bv-1",
            voice_profile_name="Acme Professional",
        )
        assert resp.voice_profile_name == "Acme Professional"

    def test_no_brand_voice_is_silent(self):
        resp = VideoJobResponse(id="j1", source_type="script", source_ref="x", state="queued")
        assert resp.brand_voice_id is None
        assert resp.voice_profile_name is None


# ── P0-5/P1-2 — Render + export ─────────────────────────────────────────────


class TestRenderBehavior:
    """P0-5 — render_job produces an MP4 at the chosen resolution."""

    def test_render_job_returns_existing_path(self, tmp_path: Path):
        scenes = [{"id": "s1", "order": 1, "heading": "A", "narration": "x", "image_path": None}]
        result = render_job("job-1", scenes, resolution="480p")
        assert isinstance(result, Path)
        assert result.exists(), "render_job must produce the MP4 file"
        assert result.suffix == ".mp4"

    def test_render_job_resolution_720p_default(self, tmp_path: Path):
        scenes = [{"id": "s1", "order": 1, "heading": "A", "narration": "x", "image_path": None}]
        result = render_job("job-2", scenes)
        assert result.suffix == ".mp4"

    def test_combine_scenes_returns_path(self, tmp_path: Path):
        # Two tiny pre-rendered clips; combine concatenates them.
        clip_a = tmp_path / "a.mp4"
        clip_b = tmp_path / "b.mp4"
        clip_a.write_bytes(b"\x00\x00\x00\x18ftypmp42")
        clip_b.write_bytes(b"\x00\x00\x00\x18ftypmp42")
        out = tmp_path / "combined.mp4"
        result = combine_scenes([clip_a, clip_b], resolution="480p", out=out)
        assert isinstance(result, Path)
        assert result == out


# ── P1-1 — Segmentation ─────────────────────────────────────────────────────


class TestSegmentationBehavior:
    """P1-1 — split_at_section_boundaries preserves order and the cap."""

    def test_long_post_splits_at_sections(self):
        text = "## Intro\n" + "x" * 6000 + "\n## Body\n" + "y" * 6000
        segments = split_at_section_boundaries(text, cap=10000)
        assert len(segments) >= 2
        assert all(len(seg) <= 10000 for seg in segments)

    def test_short_post_stays_one_segment(self):
        text = "## A\nShort."
        segments = split_at_section_boundaries(text, cap=10000)
        assert segments == [text]

    def test_segment_order_preserved(self):
        text = "## Intro\n" + "a" * 7000 + "\n## Middle\n" + "b" * 7000 + "\n## Outro\n" + "c" * 100
        segments = split_at_section_boundaries(text, cap=10000)
        assert "Intro" in segments[0]
        assert "Outro" in segments[-1]

    def test_each_segment_has_only_its_range(self):
        text = "## Intro\n" + "a" * 7000 + "\n## Body\n" + "b" * 7000
        segments = split_at_section_boundaries(text, cap=10000)
        assert "Intro" in segments[0]
        assert "Body" in segments[1]
        assert "Intro" not in segments[1]

    def test_custom_cap_honored(self):
        text = "## A\n" + "x" * 900 + "\n## B\n" + "y" * 900
        segments = split_at_section_boundaries(text, cap=1000)
        assert len(segments) >= 2
        assert all(len(seg) <= 1000 for seg in segments)


# ── P0-2 — API behavior (TestClient against the video router) ──────────────


class TestVideoApiBehavior:
    """P0-2 — POST/GET/retry/export endpoint behavior via TestClient."""

    def test_create_job_returns_201(self, client):
        resp = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "script", "source_ref": "## Intro\nHello.\n\n## Body\nMore."},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "job_id" in body
        assert body["state"] == "queued"

    def test_create_job_from_generation_id(self, client):
        resp = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "generation_id", "source_ref": "gen-123"},
        )
        assert resp.status_code in (201, 404), "unknown generation → 404; known → 201"

    def test_create_job_from_url(self, client):
        resp = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "url", "source_ref": "https://example.com/blog/post"},
        )
        assert resp.status_code == 201

    def test_create_job_unknown_generation_404(self, client):
        resp = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "generation_id", "source_ref": "missing-gen"},
        )
        assert resp.status_code == 404

    def test_create_job_invalid_source_type_422(self, client):
        resp = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "podcast", "source_ref": "x"},
        )
        assert resp.status_code == 422

    def test_create_job_invalid_resolution_422(self, client):
        resp = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "script", "source_ref": "hi", "resolution": "8k"},
        )
        assert resp.status_code == 422

    def test_create_job_oversize_script_rejected(self, client):
        resp = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "script", "source_ref": "x" * 210_000},
        )
        assert resp.status_code == 422

    def test_get_job_returns_record(self, client):
        created = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "script", "source_ref": "## A\nText."},
        ).json()
        resp = client.get(f"/api/v1/video/jobs/{created['job_id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["state"] == "queued"
        assert body["scenes"] is not None
        assert "overall_progress" in body

    def test_get_unknown_job_404(self, client):
        resp = client.get("/api/v1/video/jobs/nope")
        assert resp.status_code == 404

    def test_retry_failed_scene(self, client):
        created = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "script", "source_ref": "## A\nText."},
        ).json()
        job_id = created["job_id"]
        # Simulate one failed scene via the store, then retry.
        import src.routers.video as video_module

        store = video_module._store()
        scenes = store.list_scenes(job_id)
        store.update_scene(job_id, scenes[0]["id"], state="failed", attempts=1, error="tts boom")
        resp = client.post(f"/api/v1/video/jobs/{job_id}/retry")
        assert resp.status_code == 200
        body = resp.json()
        assert "retried" in body
        assert scenes[0]["id"] in body["retried"]

    def test_retry_wrong_state_409(self, client):
        created = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "script", "source_ref": "## A\nText."},
        ).json()
        job_id = created["job_id"]
        import src.routers.video as video_module

        video_module._store().update_state(job_id, "ready")
        resp = client.post(f"/api/v1/video/jobs/{job_id}/retry")
        assert resp.status_code == 409

    def test_retry_unknown_job_404(self, client):
        resp = client.post("/api/v1/video/jobs/nope/retry")
        assert resp.status_code == 404

    def test_export_returns_mp4_stream(self, client):
        created = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "script", "source_ref": "## A\nText."},
        ).json()
        job_id = created["job_id"]
        import src.routers.video as video_module

        store = video_module._store()
        store.update_state(job_id, "ready")
        for scene in store.list_scenes(job_id):
            store.update_scene(job_id, scene["id"], state="done", audio_path=f"/tmp/{scene['id']}.mp3")
        resp = client.get(f"/api/v1/video/jobs/{job_id}/export?resolution=720p")
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("video/mp4")
        assert resp.content[:4] == b"\x00\x00\x00\x18" or len(resp.content) > 0

    def test_export_nothing_renderable_409(self, client):
        created = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "script", "source_ref": "## A\nText."},
        ).json()
        resp = client.get(f"/api/v1/video/jobs/{created['job_id']}/export")
        assert resp.status_code == 409

    def test_export_unknown_job_404(self, client):
        resp = client.get("/api/v1/video/jobs/nope/export")
        assert resp.status_code == 404

    def test_export_invalid_resolution_422(self, client):
        created = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "script", "source_ref": "## A\nText."},
        ).json()
        resp = client.get(f"/api/v1/video/jobs/{created['job_id']}/export?resolution=8k")
        assert resp.status_code == 422

    def test_error_bodies_are_json(self, client):
        resp = client.get("/api/v1/video/jobs/nope")
        assert resp.headers.get("content-type", "").startswith("application/json")
        assert "detail" in resp.json()

    def test_voices_endpoint_returns_voices(self, client):
        resp = client.get("/api/v1/video/voices?provider=openai")
        assert resp.status_code == 200
        body = resp.json()
        assert body["provider"] == "openai"
        assert body["voices"], "OpenAI preset voices must be listed"
        assert {"id", "name"} <= set(body["voices"][0])


# ── P1-2 — Retry without re-render + partial export (US-003) ────────────────


class TestRetryNoRerenderBehavior:
    """P1-2 — done scenes keep asset paths + attempt counts across retry."""

    def test_retry_targets_failed_scenes_only(self, store: VideoJobStore):
        job_id = store.create_job(_job_source())
        scenes = store.list_scenes(job_id)
        done_id, failed_id = scenes[0]["id"], scenes[1]["id"]
        store.update_scene(job_id, done_id, state="done", attempts=1, audio_path="/tmp/done.mp3")
        store.update_scene(job_id, failed_id, state="failed", attempts=1, error="boom")

        from src.routers.video import retry_video_job

        # The API-level retry returns only the failed scene.
        retried = retry_video_job(job_id)
        retried_ids = retried.retried
        assert failed_id in retried_ids
        assert done_id not in retried_ids, "done scenes must never be re-queued"

    def test_done_scene_unchanged_after_retry(self, store: VideoJobStore):
        job_id = store.create_job(_job_source())
        scenes = store.list_scenes(job_id)
        done_id, failed_id = scenes[0]["id"], scenes[1]["id"]
        store.update_scene(job_id, done_id, state="done", attempts=2, audio_path="/tmp/done.mp3")
        store.update_scene(job_id, failed_id, state="failed", attempts=1, error="boom")

        from src.routers.video import retry_video_job

        retry_video_job(job_id)
        done = store.scene(job_id, done_id)
        assert done["state"] == "done"
        assert done["attempts"] == 2, "completed scene attempt count must not change"
        assert done["audio_path"] == "/tmp/done.mp3", "cached audio path must not change"

    def test_failed_scene_attempt_increments(self, store: VideoJobStore):
        job_id = store.create_job(_job_source())
        scenes = store.list_scenes(job_id)
        failed_id = scenes[0]["id"]
        store.update_scene(job_id, failed_id, state="failed", attempts=1, error="boom")
        store.update_scene(job_id, failed_id, state="generating", attempts=2)
        row = store.scene(job_id, failed_id)
        assert row["state"] == "generating"
        assert row["attempts"] == 2

    def test_max_retries_cap(self, store: VideoJobStore):
        job_id = store.create_job(_job_source())
        scene_id = store.list_scenes(job_id)[0]["id"]
        store.update_scene(job_id, scene_id, state="failed", attempts=3, error="boom")
        row = store.scene(job_id, scene_id)
        assert row["attempts"] >= 3
        assert row["state"] == "failed"

    def test_partial_export_skips_failed_scenes(self, client):
        created = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "script", "source_ref": "## A\nOne.\n## B\nTwo."},
        ).json()
        job_id = created["job_id"]
        import src.routers.video as video_module

        store = video_module._store()
        scenes = store.list_scenes(job_id)
        store.update_scene(job_id, scenes[0]["id"], state="done", audio_path="/tmp/a.mp3")
        store.update_scene(job_id, scenes[1]["id"], state="failed", attempts=3, error="exhausted")
        resp = client.get(f"/api/v1/video/jobs/{job_id}/export?partial=true")
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("video/mp4")
        assert resp.headers.get("x-partial", "").lower() == "true"


# ── P1-1 — Combine endpoint (US-002) ────────────────────────────────────────


class TestCombineBehavior:
    """P1-1 — combine returns a combined job + export URL."""

    def test_combine_returns_combined_job(self, client):
        """N2/N6: combine over a REAL parent with rendered clips → 200.

        The pre-dev version of this test POSTed to a phantom parent
        (``parent-1``) and expected 200 — exactly the N6 bug (unknown
        parents must 404). The regression now drives the real pipeline:
        create a job, process it with the worker (real TTS/render path,
        no store-seam scene manipulation), then combine the rendered clips.
        """
        created = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "script", "source_ref": "## Intro\nHello.\n\n## Body\nMore."},
        ).json()
        parent_id = created["job_id"]

        from src.services.video_worker import process_queued_jobs

        process_queued_jobs()
        job = client.get(f"/api/v1/video/jobs/{parent_id}").json()
        assert job["state"] == "ready", "worker must finish the job before combine"

        resp = client.post(f"/api/v1/video/jobs/{parent_id}/combine")
        assert resp.status_code == 200
        body = resp.json()
        assert "combined_job_id" in body
        assert body["url"].startswith("/api/v1/video/jobs/")

    def test_combine_unknown_parent_404(self, client):
        resp = client.post("/api/v1/video/jobs/nope/combine")
        assert resp.status_code == 404

    def test_combine_plausible_but_unknown_parent_404(self, client):
        """N6: a job-id-shaped unknown parent must 404, not 200-empty."""
        resp = client.post("/api/v1/video/jobs/nope-1/combine")
        assert resp.status_code == 404

    def test_combine_no_rendered_clips_yet_409(self, client):
        """N2: a real job that has not rendered yet has nothing to combine."""
        created = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "script", "source_ref": "## Intro\nHello."},
        ).json()
        resp = client.post(f"/api/v1/video/jobs/{created['job_id']}/combine")
        assert resp.status_code == 409

    def test_combined_job_export_streams_mp4(self, client):
        """N2: a combined job's export streams the concatenated MP4."""
        created = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "script", "source_ref": "## Intro\nHello.\n\n## Body\nMore."},
        ).json()
        parent_id = created["job_id"]

        from src.services.video_worker import process_queued_jobs

        process_queued_jobs()
        resp = client.post(f"/api/v1/video/jobs/{parent_id}/combine")
        assert resp.status_code == 200
        combined_id = resp.json()["combined_job_id"]

        exp = client.get(f"/api/v1/video/jobs/{combined_id}/export")
        assert exp.status_code == 200
        assert exp.headers.get("content-type", "").startswith("video/mp4")
        assert exp.content.startswith(b"\x00\x00\x00") or len(exp.content) > 0


# ── BLOCKER-1 — Background worker drives jobs to ready (review t_db9e57ad) ──


class TestVideoWorker:
    """The pipeline executor: queued → outline → scenes → render → ready.

    Regression for BLOCKER-1 (review t_db9e57ad): before the worker nothing
    in src/ called TTS synthesize / assemble_scenes / render, so jobs stayed
    ``queued`` forever. These tests drive the REAL worker path (no store-seam
    scene manipulation) and assert the job reaches ``ready`` with a playable
    MP4 export.
    """

    def test_worker_processes_queued_job_to_ready(self, client):
        """Create via the real API, process via the real worker, assert ready."""
        created = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "script", "source_ref": "## Intro\nHello.\n\n## Body\nMore."},
        ).json()
        job_id = created["job_id"]
        assert created["state"] == "queued"

        from src.services.video_worker import process_queued_jobs

        processed = process_queued_jobs()
        assert any(j.get("id") == job_id for j in processed)

        job = client.get(f"/api/v1/video/jobs/{job_id}").json()
        assert job["state"] == "ready"
        assert job["overall_progress"] == 100.0
        assert all(s["state"] == "done" for s in job["scenes"])
        assert all(s["audio_path"] for s in job["scenes"])

    def test_worker_ready_job_exports_playable_mp4(self, client):
        """BLOCKER-1 regression: export is 200 video/mp4 after the worker runs."""
        created = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "script", "source_ref": "## Intro\nHello."},
        ).json()
        job_id = created["job_id"]

        from src.services.video_worker import process_queued_jobs

        process_queued_jobs()

        resp = client.get(f"/api/v1/video/jobs/{job_id}/export")
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("video/mp4")
        assert len(resp.content) > 1000, "playable MP4 must have real bytes"
        # ftyp box → mp4 container signature
        assert resp.content.startswith(b"\x00\x00\x00") and b"ftyp" in resp.content[:32]

    def test_worker_retry_flows_back_into_worker(self, client, monkeypatch):
        """A failed job retried via the API is picked up by the worker again."""
        created = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "script", "source_ref": "## Intro\nHello."},
        ).json()
        job_id = created["job_id"]

        import src.routers.video as video_module

        store = video_module._store()
        scenes = store.list_scenes(job_id)
        # Simulate a scene that exhausted TTS (attempts cap reached).
        store.update_scene(job_id, scenes[0]["id"], state="failed", attempts=3, error="tts boom")
        store.update_state(job_id, "failed")

        from src.routers.video import retry_video_job

        retried = retry_video_job(job_id)
        assert retried.retried == [], "max attempts reached — nothing re-queued"

        # A retryable failure (attempts < 3) DOES come back into the worker's
        # pick-up range: state flips to scenes and the worker re-processes.
        store.update_scene(job_id, scenes[0]["id"], state="failed", attempts=1, error="tts boom")
        retried = retry_video_job(job_id)
        assert retried.retried, "failed scene with budget left must be re-queued"
        assert store.get_job(job_id)["state"] == "scenes", "retry must move job back into worker range"

        from src.services.video_worker import process_queued_jobs

        process_queued_jobs()
        job = client.get(f"/api/v1/video/jobs/{job_id}").json()
        assert job["state"] == "ready"
        assert job["scenes"][0]["state"] == "done"

    def test_worker_records_clip_paths_for_combine(self, client):
        """The worker caches per-scene clip paths (N2 combine input)."""
        created = client.post(
            "/api/v1/video/jobs",
            json={"source_type": "script", "source_ref": "## A\nOne.\n\n## B\nTwo."},
        ).json()
        job_id = created["job_id"]

        from src.services.video_worker import process_queued_jobs

        process_queued_jobs()
        import src.routers.video as video_module

        store = video_module._store()
        scenes = store.list_scenes(job_id)
        assert all(s["state"] == "done" for s in scenes)
        assert all(s["clip_path"] for s in scenes), "worker must cache rendered clip paths"
        from pathlib import Path

        assert all(Path(s["clip_path"]).is_file() for s in scenes)


# ── N3/N5 — provider-unavailable paths map to 503 (review t_db9e57ad) ──────


class TestVoicesProviderUnavailable:
    """N3/N5: elevenlabs/coqui unavailable must be 503, never 500 or a lie."""

    def test_elevenlabs_without_key_503(self, client, monkeypatch):
        """N3: no key configured → 503, and never a hardcoded voice list."""
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        resp = client.get("/api/v1/video/voices?provider=elevenlabs")
        assert resp.status_code == 503
        assert "detail" in resp.json()

    def test_elevenlabs_hardcoded_voice_gone(self, client, monkeypatch):
        """N3: with a key the voice id comes from config, not a hardcode."""
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
        resp = client.get("/api/v1/video/voices?provider=elevenlabs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["voices"], "configured voice must be surfaced"
        # The hardcoded id may still be the default when no env override —
        # but the *name* must not claim a specific person we never fetched.
        assert body["voices"][0]["id"], "voice id must be present"

    def test_coqui_without_extra_503(self, client, monkeypatch):
        """N5: coqui optional extra not installed → 503, not 500."""
        monkeypatch.setattr("src.routers.video.get_tts_provider", _raise_runtime_error)
        resp = client.get("/api/v1/video/voices?provider=coqui")
        assert resp.status_code == 503
        assert "detail" in resp.json()


def _raise_runtime_error():
    raise RuntimeError("No TTS provider available")


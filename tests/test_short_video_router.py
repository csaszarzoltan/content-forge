"""RED contract tests for short-video P0-6: API Router, Worker, and Store.

All imports come from src.short_video.router / store / worker which do not exist yet.
Every test MUST fail with ModuleNotFoundError (RED) until the developer implements the modules.
"""

from __future__ import annotations

import inspect


# ---------------------------------------------------------------------------
# Layer 1 — Import / existence tests
# ---------------------------------------------------------------------------
class TestImports:
    """Verify that the expected public API exists in src.short_video.router/store/worker."""

    def test_import_router_module(self):
        from src.short_video import router  # noqa: F401

    def test_import_router(self):
        from src.short_video.router import router  # noqa: F401

    def test_import_store_module(self):
        from src.short_video import store  # noqa: F401

    def test_import_short_video_store(self):
        from src.short_video.store import ShortVideoStore  # noqa: F401

    def test_import_worker_module(self):
        from src.short_video import worker  # noqa: F401

    def test_import_short_video_worker(self):
        from src.short_video.worker import ShortVideoWorker  # noqa: F401

    def test_import_schemas_job(self):
        from src.short_video.schemas import ShortVideoJob  # noqa: F401

    def test_import_schemas_job_state(self):
        from src.short_video.schemas import ShortVideoJobState  # noqa: F401

    def test_import_schemas_clip(self):
        from src.short_video.schemas import ShortVideoClip  # noqa: F401


# ---------------------------------------------------------------------------
# Layer 2 — Interface / signature tests
# ---------------------------------------------------------------------------
class TestStoreInterface:
    """Verify ShortVideoStore interface."""

    def test_store_init_signature(self):
        from src.short_video.store import ShortVideoStore

        sig = inspect.signature(ShortVideoStore.__init__)
        assert "db_path" in sig.parameters

    def test_store_has_create_job(self):
        from src.short_video.store import ShortVideoStore

        assert hasattr(ShortVideoStore, "create_job")
        assert callable(ShortVideoStore.create_job)

    def test_store_has_get_job(self):
        from src.short_video.store import ShortVideoStore

        assert hasattr(ShortVideoStore, "get_job")
        assert callable(ShortVideoStore.get_job)

    def test_store_has_update_job_state(self):
        from src.short_video.store import ShortVideoStore

        assert hasattr(ShortVideoStore, "update_job_state")
        assert callable(ShortVideoStore.update_job_state)

    def test_store_has_add_clip(self):
        from src.short_video.store import ShortVideoStore

        assert hasattr(ShortVideoStore, "add_clip")
        assert callable(ShortVideoStore.add_clip)

    def test_store_has_get_clips_for_job(self):
        from src.short_video.store import ShortVideoStore

        assert hasattr(ShortVideoStore, "get_clips_for_job")
        assert callable(ShortVideoStore.get_clips_for_job)

    def test_store_has_update_clip_state(self):
        from src.short_video.store import ShortVideoStore

        assert hasattr(ShortVideoStore, "update_clip_state")
        assert callable(ShortVideoStore.update_clip_state)


class TestWorkerInterface:
    """Verify ShortVideoWorker interface."""

    def test_worker_init_signature(self):
        from src.short_video.worker import ShortVideoWorker

        sig = inspect.signature(ShortVideoWorker.__init__)
        assert "interval_seconds" in sig.parameters

    def test_worker_has_run_forever(self):
        from src.short_video.worker import ShortVideoWorker

        assert hasattr(ShortVideoWorker, "run_forever")
        assert callable(ShortVideoWorker.run_forever)

    def test_run_forever_is_coroutine(self):
        from src.short_video.worker import ShortVideoWorker

        assert inspect.iscoroutinefunction(ShortVideoWorker.run_forever)

    def test_worker_has_process_job(self):
        from src.short_video.worker import ShortVideoWorker

        assert hasattr(ShortVideoWorker, "process_job")
        assert callable(ShortVideoWorker.process_job)


class TestRouterInterface:
    """Verify router endpoint structure."""

    def test_router_has_prefix(self):
        from src.short_video.router import router

        assert "/api/v1/short-video" in router.prefix

    def test_router_has_tags(self):
        from src.short_video.router import router

        assert "short-video" in router.tags


class TestSchemasInterface:
    """Verify shared schema models."""

    def test_short_video_job_fields(self):
        from src.short_video.schemas import ShortVideoJob

        fields = ShortVideoJob.model_fields
        assert "id" in fields
        assert "state" in fields
        assert "source_path" in fields
        assert "source_filename" in fields
        assert "source_format" in fields
        assert "created_at" in fields
        assert "updated_at" in fields
        assert "error" in fields
        assert "metadata" in fields

    def test_short_video_job_state_enum(self):
        from src.short_video.schemas import ShortVideoJobState

        states = {s.value for s in ShortVideoJobState}
        assert "queued" in states
        assert "transcribing" in states
        assert "detecting" in states
        assert "cropping" in states
        assert "rendering" in states
        assert "ready" in states
        assert "failed" in states

    def test_short_video_clip_fields(self):
        from src.short_video.schemas import ShortVideoClip

        fields = ShortVideoClip.model_fields
        assert "id" in fields
        assert "job_id" in fields
        assert "start_time" in fields
        assert "end_time" in fields
        assert "score" in fields
        assert "title" in fields
        assert "subtitle_text" in fields
        assert "output_path" in fields
        assert "hls_path" in fields
        assert "state" in fields


# ---------------------------------------------------------------------------
# Layer 3 — Behavioral / future tests
# ---------------------------------------------------------------------------
class TestStoreBehavioral:
    """Behavioral expectations for ShortVideoStore."""

    def test_store_create_and_get_job(self, tmp_path):
        from src.short_video.schemas import ShortVideoJob, ShortVideoJobState
        from src.short_video.store import ShortVideoStore

        store = ShortVideoStore(db_path=str(tmp_path / "test.db"))
        job = ShortVideoJob(
            id="test123",
            source_path="/tmp/v.mp4",
            source_filename="v.mp4",
            source_format="mp4",
        )
        store.create_job(job)
        fetched = store.get_job("test123")
        assert fetched is not None
        assert fetched.id == "test123"
        assert fetched.state == ShortVideoJobState.queued

    def test_store_update_job_state(self, tmp_path):
        from src.short_video.schemas import ShortVideoJob, ShortVideoJobState
        from src.short_video.store import ShortVideoStore

        store = ShortVideoStore(db_path=str(tmp_path / "test.db"))
        job = ShortVideoJob(
            id="test456",
            source_path="/tmp/v.mp4",
            source_filename="v.mp4",
            source_format="mp4",
        )
        store.create_job(job)
        store.update_job_state("test456", ShortVideoJobState.transcribing)
        fetched = store.get_job("test456")
        assert fetched.state == ShortVideoJobState.transcribing

    def test_store_get_nonexistent_job(self, tmp_path):
        from src.short_video.store import ShortVideoStore

        store = ShortVideoStore(db_path=str(tmp_path / "test.db"))
        assert store.get_job("nonexistent") is None


class TestRouterBehavioral:
    """Behavioral expectations for router endpoints."""

    def test_router_endpoints_exist(self):
        from fastapi.testclient import TestClient
        from src.short_video.router import router

        client = TestClient(router)
        # GET /jobs/{id} should return 404 for unknown
        resp = client.get("/jobs/nonexistent")
        assert resp.status_code in (404, 422)


class TestWorkerBehavioral:
    """Behavioral expectations for ShortVideoWorker."""

    def test_worker_init(self):
        from src.short_video.worker import ShortVideoWorker

        worker = ShortVideoWorker(interval_seconds=5)
        assert worker._interval == 5

    def test_worker_default_interval(self):
        from src.short_video.worker import ShortVideoWorker

        worker = ShortVideoWorker()
        assert worker._interval == 10

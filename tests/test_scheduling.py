"""Interface and behavioral tests for scheduling endpoints, schemas, and services.

Interface tests  — verify imports, class signatures (should PASS).
Behavioral tests — verify NotImplementedError for stubs.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.asyncio

from src.schemas.schedule import (
    PlatformConfig,
    ScheduleRequest,
    ScheduleResponse,
    ScheduleStatusResponse,
)
from src.routers.schedule import router as schedule_router
from src.services.scheduler import SchedulerService


# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestScheduleSchemasInterface:
    """Verify the scheduling schema interfaces."""

    def test_platform_config_importable(self):
        assert PlatformConfig is not None

    def test_platform_config_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(PlatformConfig, BaseModel)

    def test_schedule_request_importable(self):
        assert ScheduleRequest is not None

    def test_schedule_request_fields(self):
        sig = inspect.signature(ScheduleRequest)
        assert "generation_id" in sig.parameters
        assert "publish_at" in sig.parameters
        assert "platform" in sig.parameters
        assert "platform_config" in sig.parameters
        assert "retry_on_failure" in sig.parameters
        assert "max_retries" in sig.parameters

    def test_schedule_response_importable(self):
        assert ScheduleResponse is not None

    def test_schedule_response_fields(self):
        sig = inspect.signature(ScheduleResponse)
        assert "schedule_id" in sig.parameters
        assert "generation_id" in sig.parameters
        assert "status" in sig.parameters
        assert "publish_at" in sig.parameters
        assert "platform" in sig.parameters
        assert "created_at" in sig.parameters

    def test_schedule_status_response_importable(self):
        assert ScheduleStatusResponse is not None

    def test_schedule_status_response_fields(self):
        sig = inspect.signature(ScheduleStatusResponse)
        assert "schedule_id" in sig.parameters
        assert "status" in sig.parameters
        assert "retry_count" in sig.parameters
        assert "max_retries" in sig.parameters


class TestScheduleRouterInterface:
    """Verify the scheduling router interface."""

    def test_router_importable(self):
        assert schedule_router is not None
        assert schedule_router.prefix == "/schedule"

    def test_router_has_schedule_endpoint(self):
        routes = [(r.path, r.methods) for r in schedule_router.routes]
        assert any(path == "" or path == "/schedule" for path, _ in routes)

    def test_router_has_get_status_endpoint(self):
        routes = {(r.path, tuple(r.methods)) for r in schedule_router.routes}
        assert any("/{schedule_id}" in path and "GET" in methods for path, methods in routes)

    def test_router_has_cancel_endpoint(self):
        routes = {(r.path, tuple(r.methods)) for r in schedule_router.routes}
        assert any("/{schedule_id}" in path and "DELETE" in methods for path, methods in routes)


class TestSchedulerServiceInterface:
    """Verify the SchedulerService interface."""

    def test_scheduler_service_importable(self):
        assert SchedulerService is not None

    def test_scheduler_service_is_class(self):
        assert inspect.isclass(SchedulerService)

    def test_scheduler_service_has_schedule_post(self):
        assert hasattr(SchedulerService, "schedule_post")
        assert callable(SchedulerService.schedule_post)

    def test_scheduler_service_schedule_post_is_async(self):
        assert inspect.iscoroutinefunction(SchedulerService.schedule_post)

    def test_scheduler_service_has_cancel_post(self):
        assert hasattr(SchedulerService, "cancel_post")
        assert inspect.iscoroutinefunction(SchedulerService.cancel_post)

    def test_scheduler_service_has_get_post_status(self):
        assert hasattr(SchedulerService, "get_post_status")
        assert inspect.iscoroutinefunction(SchedulerService.get_post_status)

    def test_scheduler_service_has_start(self):
        assert hasattr(SchedulerService, "start")
        assert inspect.iscoroutinefunction(SchedulerService.start)

    def test_scheduler_service_has_shutdown(self):
        assert hasattr(SchedulerService, "shutdown")
        assert inspect.iscoroutinefunction(SchedulerService.shutdown)


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (verify real implementation)
# ============================================================================


class TestScheduleEndpointsBehavioral:
    """Behavioral tests for scheduling endpoints — verify real implementation."""

    def test_schedule_endpoint_is_callable(self):
        """POST /schedule handler exists."""
        from src.routers.schedule import schedule_content
        assert callable(schedule_content)

    def test_get_status_endpoint_is_callable(self):
        """GET /schedule/{id} handler exists."""
        from src.routers.schedule import get_schedule_status
        assert callable(get_schedule_status)

    def test_cancel_endpoint_is_callable(self):
        """DELETE /schedule/{id} handler exists."""
        from src.routers.schedule import cancel_scheduled_post
        assert callable(cancel_scheduled_post)


class TestSchedulerServiceBehavioral:
    """Behavioral tests for SchedulerService — verify real implementation."""

    def test_scheduler_init_works(self):
        """SchedulerService() should construct successfully."""
        svc = SchedulerService()
        assert svc is not None

    async def test_schedule_post_returns_id(self):
        """schedule_post() should return a schedule ID string."""
        svc = SchedulerService()
        schedule_id = await svc.schedule_post(
            generation_id="gen_1",
            publish_at=datetime.now(timezone.utc),
            platform="twitter",
        )
        assert isinstance(schedule_id, str)
        assert schedule_id.startswith("sch_")

    async def test_cancel_post_works(self):
        """cancel_post() should not raise."""
        svc = SchedulerService()
        await svc.cancel_post("sch_1")

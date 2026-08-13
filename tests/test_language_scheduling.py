"""Interface and behavioral tests for multi-language scheduling integration (T8).

Interface tests  — verify imports, class signatures (should PASS once stubs exist).
Behavioral tests — verify NotImplementedError for unimplemented stubs.

Covers:
  - Language-aware ScheduleRequest fields (source_language, target_language, timezone)
  - SchedulerService multi-language method extensions
  - Language-aware schedule response fields
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime

import pytest

# Mark as quick (unit tests)
pytestmark = pytest.mark.quick

from src.schemas.schedule import (
    ScheduleRequest,
    ScheduleResponse,
)
from src.services.scheduler import SchedulerService

# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestLanguageAwareScheduleRequestInterface:
    """Verify ScheduleRequest schema has language/timezone fields."""

    def test_schedule_request_has_source_language(self):
        sig = inspect.signature(ScheduleRequest)
        assert "source_language" in sig.parameters

    def test_schedule_request_source_language_type(self):
        ann = inspect.signature(ScheduleRequest).parameters["source_language"].annotation
        ann_str = str(ann)
        assert "str" in ann_str or "None" in ann_str

    def test_schedule_request_source_language_optional(self):
        param = inspect.signature(ScheduleRequest).parameters["source_language"]
        assert param.default is None or param.default is not inspect.Parameter.empty

    def test_schedule_request_has_target_language(self):
        sig = inspect.signature(ScheduleRequest)
        assert "target_language" in sig.parameters

    def test_schedule_request_has_timezone(self):
        sig = inspect.signature(ScheduleRequest)
        assert "timezone" in sig.parameters

    def test_schedule_request_timezone_type(self):
        ann = inspect.signature(ScheduleRequest).parameters["timezone"].annotation
        ann_str = str(ann)
        assert "str" in ann_str or "None" in ann_str

    def test_schedule_request_timezone_optional(self):
        param = inspect.signature(ScheduleRequest).parameters["timezone"]
        assert param.default is None or param.default is not inspect.Parameter.empty


class TestLanguageAwareScheduleResponseInterface:
    """Verify ScheduleResponse schema has language/timezone fields."""

    def test_schedule_response_has_source_language(self):
        sig = inspect.signature(ScheduleResponse)
        assert "source_language" in sig.parameters

    def test_schedule_response_has_target_language(self):
        sig = inspect.signature(ScheduleResponse)
        assert "target_language" in sig.parameters

    def test_schedule_response_has_timezone(self):
        sig = inspect.signature(ScheduleResponse)
        assert "timezone" in sig.parameters


class TestSchedulerServiceLanguageInterface:
    """Verify SchedulerService has language-aware scheduling methods."""

    def test_scheduler_service_has_schedule_multilingual(self):
        """SchedulerService should support language params in schedule_post."""
        sig = inspect.signature(SchedulerService.schedule_post)
        params = list(sig.parameters.keys())
        has_language_params = "source_language" in params or "target_language" in params
        assert has_language_params, "schedule_post should accept language params"

    def test_scheduler_service_has_timezone_param(self):
        sig = inspect.signature(SchedulerService.schedule_post)
        assert "timezone" in sig.parameters or "timezone" in str(sig)


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (verify real implementation)
# ============================================================================


class TestLanguageScheduleRequestBehavioral:
    """Behavioral tests for language-aware scheduling requests."""

    def test_schedule_request_with_language_fields(self):
        """ScheduleRequest should construct with language fields."""
        req = ScheduleRequest(
            generation_id="gen-1",
            publish_at=datetime.now(UTC),
            platform="twitter",
            source_language="en",
            target_language="de",
            timezone="Europe/Berlin",
        )
        assert req.source_language == "en"
        assert req.target_language == "de"
        assert req.timezone == "Europe/Berlin"

    def test_schedule_request_language_fields_optional(self):
        """ScheduleRequest should work without language fields."""
        req = ScheduleRequest(
            generation_id="gen-1",
            publish_at=datetime.now(UTC),
            platform="twitter",
        )
        assert req.source_language is None or req.source_language == "en"

    def test_schedule_request_timezone_conversion(self):
        """Timezone should be IANA format (e.g., Europe/Berlin)."""
        tz = "America/New_York"
        req = ScheduleRequest(
            generation_id="gen-1",
            publish_at=datetime.now(UTC),
            platform="blog",
            timezone=tz,
        )
        assert "/" in req.timezone, "Timezone should be in IANA tz format"


class TestLanguageScheduleResponseBehavioral:
    """Behavioral tests for language-aware schedule responses."""

    def test_schedule_response_with_language_fields(self):
        """ScheduleResponse should expose language fields."""
        resp = ScheduleResponse(
            schedule_id="sch_1",
            generation_id="gen-1",
            status="scheduled",
            publish_at=datetime.now(UTC),
            platform="twitter",
            created_at=datetime.now(UTC),
            source_language="en",
            target_language="de",
            timezone="Europe/Berlin",
        )
        assert resp.source_language == "en"
        assert resp.target_language == "de"
        assert resp.timezone == "Europe/Berlin"


class TestLanguageSchedulerBehavioral:
    """Behavioral tests for scheduler with language support."""

    @pytest.mark.asyncio
    async def test_scheduler_schedule_post_with_language(self):
        """schedule_post should accept language params."""
        svc = SchedulerService()
        schedule_id = await svc.schedule_post(
            generation_id="gen_1",
            publish_at=datetime.now(UTC),
            platform="twitter",
            source_language="en",
            target_language="de",
        )
        assert isinstance(schedule_id, str)
        assert schedule_id.startswith("sch_")

    @pytest.mark.asyncio
    async def test_scheduler_schedule_post_with_timezone(self):
        """schedule_post should accept timezone param."""
        svc = SchedulerService()
        schedule_id = await svc.schedule_post(
            generation_id="gen_1",
            publish_at=datetime.now(UTC),
            platform="linkedin",
            timezone="Asia/Tokyo",
        )
        assert isinstance(schedule_id, str)

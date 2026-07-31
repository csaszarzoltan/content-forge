"""Interface and behavioral tests for M7 — analytics export.

Interface tests  — verify imports, signatures (should PASS).
Behavioral tests — verify expected behavior; against pre-dev stubs they FAIL
                   with NotImplementedError (TDD RED phase).
"""

from __future__ import annotations

import csv
import inspect
import io
import json
import re

import pytest
from pydantic import BaseModel

from tests.analytics_test_utils import (
    seed_event,
    seed_generation,
)
from src.routers.analytics import router as analytics_router
from src.schemas.analytics import ExportResponse
from src.services.analytics import AnalyticsService

pytestmark = pytest.mark.asyncio

CSV_HEADER = ["date", "generation_id", "content_type", "channel", "event_type", "value"]


# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestExportSchemasInterface:
    """Verify the ExportResponse schema (brief §5.3)."""

    def test_export_response_importable(self):
        assert ExportResponse is not None

    def test_export_response_is_pydantic(self):
        assert issubclass(ExportResponse, BaseModel)

    def test_export_response_fields(self):
        sig = inspect.signature(ExportResponse)
        for field in ("format", "filename", "content_type", "data"):
            assert field in sig.parameters

    def test_export_response_requires_all_fields(self):
        with pytest.raises(Exception):
            ExportResponse(format="csv")  # type: ignore[call-arg]


class TestExportServiceInterface:
    """Verify export_data on the service (brief §5.1)."""

    def test_service_has_export_data(self):
        assert hasattr(AnalyticsService, "export_data")
        assert inspect.iscoroutinefunction(AnalyticsService.export_data)

    def test_export_data_signature(self):
        sig = inspect.signature(AnalyticsService.export_data)
        assert "db" in sig.parameters
        assert sig.parameters["format"].default == "json"
        assert sig.parameters["date_from"].default is None
        assert sig.parameters["date_to"].default is None
        assert sig.parameters["channel"].default is None
        assert sig.parameters["content_type"].default is None

    def test_export_data_return_annotation(self):
        annotation = inspect.signature(AnalyticsService.export_data).return_annotation
        assert "ExportResponse" in str(annotation)


class TestExportRouterInterface:
    """Verify the /export route (brief §5.4)."""

    def test_router_has_export_endpoint(self):
        routes = [(r.path, sorted(r.methods or [])) for r in analytics_router.routes]
        assert ("/api/v1/analytics/export", ["GET"]) in routes


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (FAIL with NotImplementedError during RED)
# ============================================================================


class TestExportBehavioral:
    """M7 — GET /api/v1/analytics/export behavior (brief §4 T7)."""

    async def _seed_two_days(self, db_session) -> None:
        await seed_generation(db_session, "gen_a", content_type="blog")
        await seed_generation(db_session, "gen_b", content_type="email")
        await seed_event(db_session, "gen_a", "impression", "twitter", 10, days_ago=1)
        await seed_event(db_session, "gen_a", "click", "twitter", 2, days_ago=1)
        await seed_event(db_session, "gen_b", "impression", "web", 5, days_ago=3)
        await seed_event(db_session, "gen_b", "read_time", "web", 120, days_ago=3)

    async def test_export_csv_roundtrip(self, db_session):
        """CSV parses back to the same data (stdlib csv, brief §4 T7)."""
        await self._seed_two_days(db_session)
        svc = AnalyticsService()
        response = await svc.export_data(db_session, format="csv")
        assert isinstance(response, ExportResponse)
        assert response.format == "csv"

        rows = list(csv.reader(io.StringIO(response.data)))
        assert rows[0] == CSV_HEADER
        data_rows = [r for r in rows[1:] if r]
        # One row per daily aggregate; seeded events collapse to 2 daily rows.
        assert len(data_rows) >= 2
        joined = "\n".join(response.data.splitlines())
        assert "gen_a" in joined
        assert "gen_b" in joined

    async def test_export_json_is_list_of_dicts(self, db_session):
        """JSON export is a serializable list of row dicts (§4 T7)."""
        await self._seed_two_days(db_session)
        svc = AnalyticsService()
        response = await svc.export_data(db_session, format="json")
        assert response.format == "json"
        parsed = json.loads(response.data)
        assert isinstance(parsed, list)
        assert all(isinstance(row, dict) for row in parsed)
        row_keys = {"date", "generation_id", "content_type", "channel", "event_type", "value"}
        assert row_keys.issubset(set(parsed[0].keys()))

    async def test_export_invalid_format_raises(self, db_session):
        """Invalid format -> 422 (service raises ValueError)."""
        svc = AnalyticsService()
        with pytest.raises(ValueError):
            await svc.export_data(db_session, format="xml")

    async def test_export_filename_pattern(self, db_session):
        """Filename analytics_export_<YYYYmmdd>.<fmt> (§4 T7)."""
        await self._seed_two_days(db_session)
        svc = AnalyticsService()
        for fmt in ("csv", "json"):
            response = await svc.export_data(db_session, format=fmt)
            assert re.fullmatch(rf"analytics_export_\d{{8}}\.{fmt}", response.filename)
            assert response.filename.endswith(f".{fmt}")

    async def test_export_channel_filter(self, db_session):
        """channel filter limits exported rows to that channel (§4 T7)."""
        await self._seed_two_days(db_session)
        svc = AnalyticsService()
        response = await svc.export_data(db_session, format="json", channel="twitter")
        parsed = json.loads(response.data)
        assert len(parsed) >= 1
        assert all(row["channel"] == "twitter" for row in parsed)
        assert all(row["generation_id"] == "gen_a" for row in parsed)

    async def test_export_content_type_filter(self, db_session):
        """content_type filter limits exported rows (§4 T7)."""
        await self._seed_two_days(db_session)
        svc = AnalyticsService()
        response = await svc.export_data(db_session, format="json", content_type="email")
        parsed = json.loads(response.data)
        assert all(row["content_type"] == "email" for row in parsed)
        assert all(row["generation_id"] == "gen_b" for row in parsed)

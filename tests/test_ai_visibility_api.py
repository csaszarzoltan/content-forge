"""Interface + behavioral tests for M6 — REST endpoints.

Interface tests verify route registration: prefix, paths, methods, response
models, and — critically — that ``/trends`` and ``/referral`` are registered
BEFORE ``/{content_id}`` (brief §5 M6, explicit acceptance test). These PASS
immediately. Behavioral tests call the handlers directly (per repo precedent)
and verify the 404/422 error mapping and response shapes; against the stubs
they FAIL with ``NotImplementedError`` (TDD RED phase).
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.quick]

from fastapi import HTTPException

from src.ai_visibility.router import (
    get_content_visibility,
    get_trends,
    ingest_referral,
    router,
)
from src.ai_visibility.schemas import (
    AIVisibilityTrendsResponse,
    ContentVisibilityResponse,
    ReferralIngestRequest,
    ReferralIngestResponse,
)

PREFIX = "/api/v1/ai-visibility"


# ============================================================================
# SECTION 1 — INTERFACE TESTS (PASS immediately)
# ============================================================================


class TestRouterInterface:
    """Verify the M6 route registration contract."""

    def test_router_prefix(self):
        assert router.prefix == PREFIX

    def test_router_tags(self):
        assert router.tags == ["ai-visibility"]

    def test_route_paths_registered(self):
        paths = [r.path for r in router.routes]
        assert f"{PREFIX}/trends" in paths
        assert f"{PREFIX}/referral" in paths
        assert f"{PREFIX}/{{content_id}}" in paths

    def test_route_methods(self):
        methods = {(r.path, next(iter(r.methods))) for r in router.routes}
        assert (f"{PREFIX}/trends", "GET") in methods
        assert (f"{PREFIX}/referral", "POST") in methods
        assert (f"{PREFIX}/{{content_id}}", "GET") in methods

    def test_route_order_trends_and_referral_before_content_id(self):
        """/trends and /referral must NOT be captured by /{content_id} —
        they are registered first (brief §5 M6 risk note)."""
        paths = [r.path for r in router.routes]
        idx_trends = paths.index(f"{PREFIX}/trends")
        idx_referral = paths.index(f"{PREFIX}/referral")
        idx_content = paths.index(f"{PREFIX}/{{content_id}}")
        assert idx_trends < idx_content
        assert idx_referral < idx_content

    def test_referral_route_status_code(self):
        route = next(r for r in router.routes if r.path == f"{PREFIX}/referral")
        assert route.status_code == 201

    def test_response_models(self):
        by_path = {r.path: r for r in router.routes}
        assert by_path[f"{PREFIX}/trends"].response_model is AIVisibilityTrendsResponse
        assert by_path[f"{PREFIX}/referral"].response_model is ReferralIngestResponse
        assert by_path[f"{PREFIX}/{{content_id}}"].response_model is ContentVisibilityResponse

    def test_content_handler_signature(self):
        sig = inspect.signature(get_content_visibility)
        assert tuple(sig.parameters) == (
            "content_id", "days", "db", "current_user",
        )
        assert sig.parameters["days"].default == 30

    def test_trends_handler_signature(self):
        sig = inspect.signature(get_trends)
        params = sig.parameters
        assert tuple(params) == ("days", "engine", "metric", "db", "current_user")
        assert params["days"].default == 30
        assert params["engine"].default is None
        assert params["metric"].default is None


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (FAIL with NotImplementedError during RED)
# ============================================================================


class TestContentVisibilityEndpointBehavioral:
    """GET /api/v1/ai-visibility/{content_id} behavior."""

    async def test_unknown_content_404(self, db_session):
        """Unknown generation_id -> HTTP 404 (ValueError mapping)."""
        with pytest.raises(HTTPException) as exc_info:
            await get_content_visibility(content_id="missing", days=30,
                                         db=db_session, current_user=None)
        assert exc_info.value.status_code == 404

    async def test_valid_content_returns_response(self, db_session):
        """Known content -> ContentVisibilityResponse with four engines."""
        from tests.ai_visibility_test_utils import seed_generation

        await seed_generation(db_session, "gen_a")
        resp = await get_content_visibility(content_id="gen_a", days=30,
                                            db=db_session, current_user=None)
        assert isinstance(resp, ContentVisibilityResponse)
        assert resp.content_id == "gen_a"
        assert len(resp.engines) == 4


class TestTrendsEndpointBehavioral:
    """GET /api/v1/ai-visibility/trends behavior."""

    async def test_invalid_days_422(self, db_session):
        """days not in {7,30,90} -> HTTP 422 (ValueError mapping)."""
        with pytest.raises(HTTPException) as exc_info:
            await get_trends(days=5, db=db_session, current_user=None)
        assert exc_info.value.status_code == 422

    async def test_invalid_engine_422(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            await get_trends(days=30, engine="claude", db=db_session,
                             current_user=None)
        assert exc_info.value.status_code == 422

    async def test_valid_trends_returns_response(self, db_session):
        resp = await get_trends(days=30, db=db_session, current_user=None)
        assert isinstance(resp, AIVisibilityTrendsResponse)
        assert resp.period == "30d" and resp.days == 30


class TestReferralEndpointBehavioral:
    """POST /api/v1/ai-visibility/referral behavior."""

    async def test_ingest_referral_returns_ok(self, db_session):
        from tests.ai_visibility_test_utils import seed_generation

        await seed_generation(db_session, "gen_ref")
        request = ReferralIngestRequest(
            generation_id="gen_ref",
            engine="chatgpt",
            referrer_url="https://chatgpt.com/c/xyz",
            landing_path="/pricing",
        )
        resp = await ingest_referral(request, db=db_session)
        assert isinstance(resp, ReferralIngestResponse)
        assert resp.status == "ok"
        assert resp.referral_id

    async def test_ingest_referral_unknown_generation_404(self, db_session):
        request = ReferralIngestRequest(
            generation_id="missing",
            engine="gemini",
            referrer_url="https://gemini.google.com/app/x",
        )
        with pytest.raises(HTTPException) as exc_info:
            await ingest_referral(request, db=db_session)
        assert exc_info.value.status_code == 404

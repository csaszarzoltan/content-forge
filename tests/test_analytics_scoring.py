"""Interface and behavioral tests for M8 — content scoring engine.

Interface tests  — verify imports, signatures (should PASS).
Behavioral tests — verify expected behavior; against pre-dev stubs they FAIL
                   with NotImplementedError (TDD RED phase).

Score formula (brief §4 T8): 0.35*engagement + 0.25*seo + 0.20*readability
+ 0.20*compliance (0-100); grades A>=90, B>=75, C>=60, D>=45, F<45; missing
sub-scores drop out and weights renormalize.
"""

from __future__ import annotations

import inspect

import pytest

# Mark as quick (unit tests)
pytestmark = [pytest.mark.asyncio, pytest.mark.quick]

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select

from src.models.analytics import AnalyticsEvent
from src.routers.analytics import get_content_score as score_endpoint
from src.routers.analytics import router as analytics_router
from src.schemas.analytics import ContentScoreResponse, ScoreBreakdown
from src.services.content_scoring import ContentScoringService
from tests.analytics_test_utils import (
    seed_event,
    seed_generation,
)

GRADE_BOUNDARIES = {"A": 90.0, "B": 75.0, "C": 60.0, "D": 45.0, "F": 0.0}


def _expected_grade(score: float) -> str:
    """Documented grade mapping: A>=90, B>=75, C>=60, D>=45, F<45."""
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 45:
        return "D"
    return "F"


# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestScoringSchemasInterface:
    """Verify the scoring schemas (brief §5.3)."""

    def test_content_score_response_importable(self):
        assert ContentScoreResponse is not None

    def test_content_score_response_is_pydantic(self):
        assert issubclass(ContentScoreResponse, BaseModel)

    def test_score_breakdown_importable(self):
        assert ScoreBreakdown is not None

    def test_score_breakdown_is_pydantic(self):
        assert issubclass(ScoreBreakdown, BaseModel)

    def test_content_score_response_fields(self):
        sig = inspect.signature(ContentScoreResponse)
        for field in ("generation_id", "score", "grade", "breakdown"):
            assert field in sig.parameters

    def test_score_breakdown_fields(self):
        sig = inspect.signature(ScoreBreakdown)
        for field in ("engagement", "seo", "readability", "compliance"):
            assert field in sig.parameters


class TestContentScoringServiceInterface:
    """Verify ContentScoringService (brief §5.2)."""

    def test_service_importable(self):
        assert ContentScoringService is not None

    def test_service_is_class(self):
        assert inspect.isclass(ContentScoringService)

    def test_service_has_score(self):
        assert hasattr(ContentScoringService, "score")
        assert inspect.iscoroutinefunction(ContentScoringService.score)

    def test_service_has_score_many(self):
        assert hasattr(ContentScoringService, "score_many")
        assert inspect.iscoroutinefunction(ContentScoringService.score_many)

    def test_score_signature(self):
        sig = inspect.signature(ContentScoringService.score)
        assert "db" in sig.parameters
        assert "generation_id" in sig.parameters

    def test_score_many_signature(self):
        sig = inspect.signature(ContentScoringService.score_many)
        assert "db" in sig.parameters
        assert "generation_ids" in sig.parameters

    def test_score_return_annotation(self):
        annotation = inspect.signature(ContentScoringService.score).return_annotation
        assert "ContentScoreResponse" in str(annotation)

    def test_score_many_return_annotation(self):
        annotation = inspect.signature(
            ContentScoringService.score_many
        ).return_annotation
        assert "ContentScoreResponse" in str(annotation)


class TestScoringRouterInterface:
    """Verify the /score/{generation_id} route (brief §5.4)."""

    def test_router_has_score_endpoint(self):
        routes = [(r.path, sorted(r.methods or [])) for r in analytics_router.routes]
        assert ("/api/v1/analytics/score/{generation_id}", ["GET"]) in routes


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (FAIL with NotImplementedError during RED)
# ============================================================================


class TestContentScoringBehavioral:
    """M8 — content scoring engine behavior (brief §4 T8)."""

    async def test_score_returns_response(self, db_session):
        """score returns ContentScoreResponse with 0-100 score and A-F grade."""
        await seed_generation(db_session, "gen_1")
        await seed_event(db_session, "gen_1", "impression", "web", 100)
        await seed_event(db_session, "gen_1", "click", "web", 10)

        svc = ContentScoringService()
        response = await svc.score(db_session, "gen_1")
        assert isinstance(response, ContentScoreResponse)
        assert response.generation_id == "gen_1"
        assert 0.0 <= response.score <= 100.0
        assert response.grade in ("A", "B", "C", "D", "F")
        assert isinstance(response.breakdown, ScoreBreakdown)

    async def test_score_deterministic(self, db_session):
        """Same input -> same score (deterministic, §4 T8)."""
        await seed_generation(db_session, "gen_1")
        await seed_event(db_session, "gen_1", "impression", "web", 100)

        svc = ContentScoringService()
        first = await svc.score(db_session, "gen_1")
        second = await svc.score(db_session, "gen_1")
        assert first.score == second.score
        assert first.grade == second.grade
        assert first.breakdown == second.breakdown

    async def test_score_missing_text_still_scores(self, db_session):
        """Missing text (e.g. social) still scores using available terms (§4 T8)."""
        await seed_generation(db_session, "gen_1", generated_text="")
        await seed_event(db_session, "gen_1", "impression", "twitter", 50)
        svc = ContentScoringService()
        response = await svc.score(db_session, "gen_1")
        assert 0.0 <= response.score <= 100.0
        assert response.grade in ("A", "B", "C", "D", "F")

    async def test_score_grade_matches_documented_boundaries(self, db_session):
        """Grade must match the documented A>=90/B>=75/C>=60/D>=45/F<45 mapping."""
        await seed_generation(db_session, "gen_1")
        await seed_event(db_session, "gen_1", "impression", "web", 100)
        svc = ContentScoringService()
        response = await svc.score(db_session, "gen_1")
        assert response.grade == _expected_grade(response.score)

    async def test_score_unknown_generation_raises(self, db_session):
        """Unknown generation -> service ValueError (router maps to 404)."""
        svc = ContentScoringService()
        with pytest.raises(ValueError):
            await svc.score(db_session, "does-not-exist")

    async def test_score_unknown_generation_404(self, db_session):
        """Handler maps unknown generation to HTTP 404."""
        with pytest.raises(HTTPException) as exc_info:
            await score_endpoint("does-not-exist", db=db_session)
        assert exc_info.value.status_code == 404

    async def test_score_many_returns_ordered_list(self, db_session):
        """score_many returns one ContentScoreResponse per id, order preserved."""
        await seed_generation(db_session, "gen_a")
        await seed_generation(db_session, "gen_b")
        await seed_event(db_session, "gen_a", "impression", "web", 10)
        await seed_event(db_session, "gen_b", "impression", "web", 20)

        svc = ContentScoringService()
        results = await svc.score_many(db_session, ["gen_a", "gen_b"])
        assert isinstance(results, list)
        assert len(results) == 2
        assert [r.generation_id for r in results] == ["gen_a", "gen_b"]
        assert all(isinstance(r, ContentScoreResponse) for r in results)

    async def test_score_many_raises_on_unknown(self, db_session):
        """score_many with an unknown id raises ValueError."""
        await seed_generation(db_session, "gen_a")
        svc = ContentScoringService()
        with pytest.raises(ValueError):
            await svc.score_many(db_session, ["gen_a", "does-not-exist"])

    async def test_score_does_not_write_events(self, db_session):
        """score performs no DB writes (§4 T8)."""
        await seed_generation(db_session, "gen_1")
        await seed_event(db_session, "gen_1", "impression", "web", 10)
        before = (
            await db_session.execute(select(func.count()).select_from(AnalyticsEvent))
        ).scalar_one()

        svc = ContentScoringService()
        await svc.score(db_session, "gen_1")

        after = (
            await db_session.execute(select(func.count()).select_from(AnalyticsEvent))
        ).scalar_one()
        assert after == before

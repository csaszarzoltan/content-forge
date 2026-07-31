"""Content scoring service (v0.9.0, analysis brief §4 T8 / §5.2).

Deterministic weighted formula: ``0.35*engagement + 0.25*seo + 0.20*readability
+ 0.20*compliance`` (each 0-100). Grades: A>=90, B>=75, C>=60, D>=45, F<45.
Missing sub-scores (e.g. no text for social content) drop out and the
remaining weights renormalize. Pure reads — never writes to the DB.
"""

from __future__ import annotations

from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.analytics import AnalyticsEvent, ContentAnalytics
from src.models.generation import Generation
from src.schemas.analytics import ContentScoreResponse, ScoreBreakdown
from src.services.analytics import _aggregate
from src.services.readability import ReadabilityScorer
from src.services.seo_analyzer import SEOAnalyzer

# Canonical term weights (brief §4 T8).
TERM_WEIGHTS: dict[str, float] = {
    "engagement": 0.35,
    "seo": 0.25,
    "readability": 0.20,
    "compliance": 0.20,
}

# SEO word-count quality tiers -> 0-100 base scores.
_QUALITY_SCORES: dict[str, float] = {
    "empty": 0.0,
    "thin": 30.0,
    "adequate": 70.0,
    "comprehensive": 90.0,
}

# Ideal keyword density (%) for the keyword-focus component.
_IDEAL_KEYWORD_DENSITY = 1.5

# Impressions needed for the full engagement impressions component.
_FULL_IMPRESSIONS = 2000


def _grade(score: float) -> Literal["A", "B", "C", "D", "F"]:
    """Map a 0-100 score to a letter grade (brief §4 T8 boundaries)."""
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 45:
        return "D"
    return "F"


class ContentScoringService:
    """Compute deterministic content quality scores from events + content."""

    async def score(
        self, db: AsyncSession, generation_id: str
    ) -> ContentScoreResponse:
        """Score one generation; raise ValueError -> 404 when unknown."""
        generation = await db.get(Generation, generation_id)
        if generation is None:
            raise ValueError("Generation not found")
        events = (
            await db.execute(
                select(AnalyticsEvent).where(
                    AnalyticsEvent.generation_id == generation_id
                )
            )
        ).scalars().all()
        analytics_row = (
            await db.execute(
                select(ContentAnalytics).where(
                    ContentAnalytics.generation_id == generation_id
                )
            )
        ).scalar_one_or_none()
        return self._compute(generation, list(events), analytics_row)

    async def score_many(
        self, db: AsyncSession, generation_ids: list[str]
    ) -> list[ContentScoreResponse]:
        """Score multiple generations in one pass, preserving order."""
        generations = (
            (
                await db.execute(
                    select(Generation).where(Generation.id.in_(generation_ids))
                )
            )
            .scalars()
            .all()
        )
        by_id = {generation.id: generation for generation in generations}
        for generation_id in generation_ids:
            if generation_id not in by_id:
                raise ValueError(f"Generation not found: {generation_id}")
        events = (
            (
                await db.execute(
                    select(AnalyticsEvent).where(
                        AnalyticsEvent.generation_id.in_(generation_ids)
                    )
                )
            )
            .scalars()
            .all()
        )
        events_by_generation: dict[str, list[AnalyticsEvent]] = {}
        for event in events:
            events_by_generation.setdefault(event.generation_id, []).append(event)
        analytics_rows = (
            (
                await db.execute(
                    select(ContentAnalytics).where(
                        ContentAnalytics.generation_id.in_(generation_ids)
                    )
                )
            )
            .scalars()
            .all()
        )
        analytics_by_generation = {
            row.generation_id: row for row in analytics_rows
        }
        return [
            self._compute(
                by_id[generation_id],
                events_by_generation.get(generation_id, []),
                analytics_by_generation.get(generation_id),
            )
            for generation_id in generation_ids
        ]

    @staticmethod
    def _engagement_score(events: list[AnalyticsEvent]) -> float:
        """Normalize engagement events into a 0-100 sub-score."""
        metrics = _aggregate(events)
        impressions_component = min(metrics.impressions / _FULL_IMPRESSIONS, 1.0) * 50
        engagement_component = min(metrics.engagement_rate, 1.0) * 50
        return min(100.0, impressions_component + engagement_component)

    @staticmethod
    def _seo_score(text: str) -> float:
        """Map SEOAnalyzer output to a 0-100 sub-score."""
        result = SEOAnalyzer().content_score(text, "")
        word_count_score = _QUALITY_SCORES.get(result.content_quality, 0.0)
        keyword_score = max(
            0.0, 100.0 - abs(result.keyword_density - _IDEAL_KEYWORD_DENSITY) * 40.0
        )
        return min(100.0, 0.7 * word_count_score + 0.3 * keyword_score)

    @staticmethod
    def _readability_score(text: str) -> float:
        """Map Flesch Reading Ease to a clamped 0-100 sub-score."""
        metrics = ReadabilityScorer().readability_metrics(text)
        return min(100.0, max(0.0, metrics.flesch_reading_ease))

    @staticmethod
    def _compliance_score(
        generation: Generation, analytics_row: ContentAnalytics | None
    ) -> float | None:
        """Extract the overall compliance sub-score, or None when unavailable."""
        scores = generation.compliance_scores or {}
        overall = scores.get("overall")
        if overall is None and analytics_row is not None:
            overall = analytics_row.compliance_overall
        if overall is None:
            return None
        return min(100.0, max(0.0, float(overall)))

    def _compute(
        self,
        generation: Generation,
        events: list[AnalyticsEvent],
        analytics_row: ContentAnalytics | None,
    ) -> ContentScoreResponse:
        """Compute the weighted score, dropping + renormalizing missing terms."""
        text = generation.generated_text or ""
        has_text = bool(text.strip())

        engagement = self._engagement_score(events)
        seo = self._seo_score(text) if has_text else None
        readability = self._readability_score(text) if has_text else None
        compliance = self._compliance_score(generation, analytics_row)

        terms: list[tuple[float, float]] = [
            (TERM_WEIGHTS["engagement"], engagement)
        ]
        if seo is not None:
            terms.append((TERM_WEIGHTS["seo"], seo))
        if readability is not None:
            terms.append((TERM_WEIGHTS["readability"], readability))
        if compliance is not None:
            terms.append((TERM_WEIGHTS["compliance"], compliance))

        total_weight = sum(weight for weight, _ in terms)
        score = (
            sum(weight * sub_score for weight, sub_score in terms) / total_weight
            if total_weight > 0
            else 0.0
        )

        return ContentScoreResponse(
            generation_id=generation.id,
            score=round(score, 2),
            grade=_grade(score),
            breakdown=ScoreBreakdown(
                engagement=round(engagement, 2),
                seo=round(seo, 2) if seo is not None else 0.0,
                readability=round(readability, 2) if readability is not None else 0.0,
                compliance=round(compliance, 2) if compliance is not None else 0.0,
            ),
        )

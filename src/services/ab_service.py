"""A/B testing service — business logic for the ContentForge A/B framework.

Orchestrates test creation, variant generation via ContentGenerator,
event tracking, statistical analysis, and test lifecycle management.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.ab_test import ABEvent, ABTest, ABVariant
from src.schemas.ab_test import (
    ABConcludeRequest,
    ABCreateRequest,
    ABDashboardResponse,
    ABResultsResponse,
    ABTestListResponse,
    ABTestResponse,
    ABTrackRequest,
    ABVariantResponse,
    ABVariantResult,
)
from src.services.ab_stats import AbStatsService


class ABTestService:
    """Service for managing A/B test lifecycle and variant generation."""

    @staticmethod
    def _to_ab_test_response(test: ABTest) -> ABTestResponse:
        """Convert an ABTest ORM instance to a response schema."""
        return ABTestResponse(
            id=test.id,
            name=test.name,
            description=test.description or "",
            content_type=test.content_type,
            topic=test.topic,
            brand_voice_id=test.brand_voice_id,
            status=test.status,
            variants=[
                ABVariantResponse(
                    id=v.id,
                    name=v.name,
                    variant_type=v.variant_type,
                    generation_id=v.generation_id,
                    variant_params=v.variant_params or {},
                    impressions=v.impressions,
                    conversions=v.conversions,
                    conversion_rate=v.conversions / v.impressions if v.impressions > 0 else 0.0,
                    created_at=v.created_at,
                )
                for v in (test.variants or [])
            ],
            winner_variant_id=test.winner_variant_id,
            created_by=test.created_by,
            created_at=test.created_at,
            concluded_at=test.concluded_at,
        )

    async def create_test(
        self,
        request: ABCreateRequest,
        db: AsyncSession,
        user_id: str | None = None,
    ) -> ABTest:
        """Create an A/B test and generate content variants.

        Args:
            request: Test creation parameters.
            db: Database session.
            user_id: Optional user identifier.

        Returns:
            The newly created ABTest ORM object.
        """
        test_id = str(uuid4())
        now = datetime.now(UTC)

        # Create the main test record
        ab_test = ABTest(
            id=test_id,
            name=request.name,
            description=request.description,
            content_type=request.content_type,
            topic=request.topic,
            brand_voice_id=request.brand_voice_id,
            status="draft",
            created_by=user_id,
            created_at=now,
        )
        db.add(ab_test)

        # Create variants with dimension-specific labels
        variant_dimensions = self._get_variant_dimensions(request)
        for i, (variant_name, variant_type, variant_params) in enumerate(variant_dimensions):
            variant = ABVariant(
                id=str(uuid4()),
                ab_test_id=test_id,
                name=variant_name,
                variant_type=variant_type,
                variant_params=variant_params,
                impressions=0,
                conversions=0,
                created_at=now,
            )
            db.add(variant)

        await db.flush()
        return ab_test

    @staticmethod
    def _get_variant_dimensions(
        request: ABCreateRequest,
    ) -> list[tuple[str, str, dict]]:
        """Generate variant names and params based on the request.

        Returns:
            List of (name, variant_type, variant_params) tuples.
        """
        dimension = request.variant_dimension or "tone"
        count = request.variant_count
        dimensions: list[tuple[str, str, dict]] = []

        # First variant is always the control
        dimensions.append(("Control", "control", {"dimension": dimension, "variation": "control"}))

        # Treatment variants based on the dimension
        treatment_labels: dict[str, list[str]] = {
            "tone": ["Professional", "Casual", "Authoritative", "Friendly"],
            "cta": ["Urgent CTA", "Soft CTA", "Benefit CTA", "Risk CTA"],
            "headline": [
                "Question Headline", "How-To Headline",
                "Listicle Headline", "Bold Headline",
            ],
            "structure": ["AIDA", "PAS", "Storytelling", "Inverted Pyramid"],
            "mixed": ["Tone A", "CTA A", "Structure A", "Hybrid"],
        }
        default_labels = [
            "Variant A", "Variant B",
            "Variant C", "Variant D",
        ]
        labels = treatment_labels.get(dimension, default_labels)
        for i in range(count - 1):
            label = labels[i] if i < len(labels) else f"Variant {chr(65 + i)}"
            variation = label.lower().replace(" ", "_")
            dimensions.append((
                label, "treatment",
                {"dimension": dimension, "variation": variation},
            ))

        return dimensions

    async def track_event(
        self,
        request: ABTrackRequest,
        db: AsyncSession,
    ) -> None:
        """Record an impression or conversion event for a variant.

        Args:
            request: Event tracking payload.
            db: Database session.
        """
        # Look up the variant to get its ab_test_id
        result = await db.execute(
            select(ABVariant).where(ABVariant.id == request.variant_id)
        )
        variant = result.scalar_one_or_none()
        if variant is None:
            raise ValueError(f"Variant {request.variant_id} not found")

        now = datetime.now(UTC)

        # Create the event record
        event = ABEvent(
            id=str(uuid4()),
            variant_id=request.variant_id,
            ab_test_id=variant.ab_test_id,
            event_type=request.event_type,
            user_identifier=request.user_identifier,
            event_data=request.metadata or {},
            created_at=now,
        )
        db.add(event)

        # Update variant counters
        if request.event_type == "impression":
            variant.impressions += 1
        elif request.event_type == "conversion":
            variant.conversions += 1

        await db.flush()

    async def get_results(
        self,
        test_id: str,
        db: AsyncSession,
    ) -> ABResultsResponse:
        """Get A/B test results with statistical significance analysis.

        Args:
            test_id: The A/B test identifier.
            db: Database session.

        Returns:
            Full results response with significance data.
        """
        # Fetch the test with variants eagerly loaded
        result = await db.execute(
            select(ABTest).where(ABTest.id == test_id)
        )
        test = result.scalar_one_or_none()
        if test is None:
            raise ValueError(f"AB test {test_id} not found")

        # Reload with variants
        await db.refresh(test, ["variants"])

        test_response = self._to_ab_test_response(test)

        # Build counts for statistical analysis
        counts: list[tuple[int, int]] = []
        for v in (test.variants or []):
            counts.append((v.impressions, v.conversions))

        # Calculate significance
        insufficient_data = AbStatsService.needs_more_data(counts)
        significance_level: float | None = None
        confidence_level: float | None = None
        winner_variant_id: str | None = None
        method: str = "chi-squared"

        if len(counts) >= 2 and not insufficient_data:
            sig_result = AbStatsService.calculate_significance(counts)
            significance_level = sig_result.p_value
            confidence_level = 1 - sig_result.p_value
            method = sig_result.method

            # Determine winner if statistically significant (p < 0.05)
            if sig_result.p_value < 0.05:
                # Winner = variant with highest conversion rate
                best_variant = max(
                    test.variants or [],
                    key=lambda v: v.conversions / v.impressions if v.impressions > 0 else 0,
                )
                winner_variant_id = best_variant.id

        # Build variant results
        variant_results: list[ABVariantResult] = []
        if test.variants:
            # Get the significance result for z-scores if available
            sig_result_for_z = None
            if not insufficient_data and len(counts) >= 2:
                sig_result_for_z = AbStatsService.calculate_significance(counts)

            for i, v in enumerate(test.variants):
                conversion_rate = v.conversions / v.impressions if v.impressions > 0 else 0.0
                z_score: float | None = None
                p_value: float | None = None
                if sig_result_for_z and i < len(counts):
                    # For 2-variant tests, derive z-scores per variant
                    if len(counts) == 2 and sig_result_for_z.z_score is not None:
                        if i == 0:
                            z_score = abs(sig_result_for_z.z_score)
                        else:
                            z_score = abs(sig_result_for_z.z_score)
                    p_value = sig_result_for_z.p_value

                variant_results.append(
                    ABVariantResult(
                        id=v.id,
                        name=v.name,
                        variant_type=v.variant_type,
                        impressions=v.impressions,
                        conversions=v.conversions,
                        conversion_rate=conversion_rate,
                        z_score=z_score,
                        p_value=p_value,
                        is_winner=v.id == winner_variant_id,
                    )
                )

        return ABResultsResponse(
            test=test_response,
            significance_level=significance_level,
            confidence_level=confidence_level,
            winner_variant_id=winner_variant_id,
            insufficient_data=insufficient_data,
            variants=variant_results,
            method=method,
        )

    async def conclude_test(
        self,
        test_id: str,
        request: ABConcludeRequest,
        db: AsyncSession,
    ) -> ABTest:
        """Conclude an A/B test by declaring a winner.

        Args:
            test_id: The A/B test identifier.
            request: Conclusion request with winner_variant_id.
            db: Database session.

        Returns:
            The updated ABTest ORM object with concluded status.
        """
        result = await db.execute(
            select(ABTest).where(ABTest.id == test_id)
        )
        test = result.scalar_one_or_none()
        if test is None:
            raise ValueError(f"AB test {test_id} not found")

        test.status = "concluded"
        test.winner_variant_id = request.winner_variant_id
        test.concluded_at = datetime.now(UTC)

        if request.note:
            test.description = (test.description or "") + f"\nConclusion note: {request.note}"

        await db.flush()
        return test

    async def get_dashboard(
        self,
        db: AsyncSession,
        limit: int = 20,
        offset: int = 0,
    ) -> ABDashboardResponse:
        """Get dashboard summary of all tests grouped by status.

        Args:
            db: Database session.
            limit: Maximum number of items per group.
            offset: Pagination offset.

        Returns:
            Dashboard response with active and concluded test groupings.
        """
        # Get active tests (draft + running)
        active_stmt = (
            select(ABTest)
            .options(selectinload(ABTest.variants))
            .where(ABTest.status.in_(["draft", "running"]))
            .offset(offset)
            .limit(limit)
        )
        active_result = await db.execute(active_stmt)
        active_tests = active_result.unique().scalars().all()

        # Get concluded tests
        concluded_stmt = (
            select(ABTest)
            .options(selectinload(ABTest.variants))
            .where(ABTest.status == "concluded")
            .offset(offset)
            .limit(limit)
        )
        concluded_result = await db.execute(concluded_stmt)
        concluded_tests = concluded_result.unique().scalars().all()

        # Total count
        total_stmt = select(func.count(ABTest.id))
        total_result = await db.execute(total_stmt)
        total_tests = total_result.scalar() or 0

        return ABDashboardResponse(
            active_tests=[self._to_ab_test_response(t) for t in active_tests],
            concluded_tests=[self._to_ab_test_response(t) for t in concluded_tests],
            total_tests=total_tests,
            active_count=len(active_tests),
            concluded_count=len(concluded_tests),
        )

    async def list_tests(
        self,
        db: AsyncSession,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ABTestListResponse:
        """List A/B tests with optional status filter and pagination.

        Args:
            db: Database session.
            status: Optional status filter.
            limit: Maximum results.
            offset: Pagination offset.

        Returns:
            Paginated list response.
        """
        stmt = select(ABTest)

        if status:
            stmt = stmt.where(ABTest.status == status)

        # Get total count
        total_count_stmt = select(func.count()).select_from(ABTest)
        if status:
            total_count_stmt = total_count_stmt.where(ABTest.status == status)
        count_result = await db.execute(total_count_stmt)
        total = count_result.scalar() or 0

        # Get paginated results with eager loaded variants
        stmt = stmt.options(selectinload(ABTest.variants)).offset(offset).limit(limit)
        result = await db.execute(stmt)
        tests = result.unique().scalars().all()

        return ABTestListResponse(
            items=[self._to_ab_test_response(t) for t in tests],
            total=total,
            limit=limit,
            offset=offset,
        )

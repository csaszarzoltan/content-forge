"""Shared seeding helpers for analytics pre-dev behavioral tests (RED phase).

During the RED phase the service methods raise ``NotImplementedError``, so any
test that calls ``seed_event`` fails exactly there — which is the intended
failure signal. After implementation these helpers exercise the real paths.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.generation import Generation
from src.schemas.analytics import TrackEventRequest
from src.services.analytics import AnalyticsService


async def seed_generation(
    session: AsyncSession, generation_id: str, **overrides
) -> Generation:
    """Insert a Generation row (required by track_event's 404 validation)."""
    gen = Generation(
        id=generation_id,
        content_type=overrides.get("content_type", "blog"),
        topic=overrides.get("topic", f"topic-{generation_id}"),
        generated_text=overrides.get(
            "generated_text",
            "We are excited to announce our new scalable platform. "
            "This enterprise-grade solution is proven to deliver robust results.",
        ),
        compliance_scores=overrides.get(
            "compliance_scores",
            {"overall": 85.0, "vocabulary": 80.0, "readability": 75.0, "tone": 90.0},
        ),
        model_used=overrides.get("model_used", "gpt-4o"),
        tokens_used=overrides.get("tokens_used", 1200),
    )
    session.add(gen)
    await session.commit()
    return gen


async def seed_event(
    session: AsyncSession,
    generation_id: str,
    event_type: str = "impression",
    channel: str = "web",
    value: int = 1,
    days_ago: int = 0,
) -> str:
    """Track one event via the canonical service path (raises during RED)."""
    request = TrackEventRequest(
        generation_id=generation_id,
        channel=channel,
        event_type=event_type,  # type: ignore[arg-type]
        value=value,
        occurred_at=datetime.now(UTC) - timedelta(days=days_ago),
    )
    response = await AnalyticsService().track_event(session, request)
    return response.event_id

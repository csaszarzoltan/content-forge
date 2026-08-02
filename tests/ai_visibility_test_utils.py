"""Shared seeding helpers for AI visibility pre-dev tests (RED phase).

Mirrors ``tests/analytics_test_utils.py``: ``seed_generation`` re-uses the
analytics helper; ``seed_mention`` / ``seed_referral`` go through the canonical
service path. During the RED phase the service methods raise
``NotImplementedError``, so any test that calls a seed helper fails exactly
there — the intended failure signal. After implementation these helpers
exercise the real persistence paths.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.ai_visibility.providers import EngineVisibilityResult
from src.ai_visibility.service import AiVisibilityService
from tests.analytics_test_utils import seed_generation  # noqa: F401

# Canonical tracked engines (brief §4.5) — used by seed helpers and tests.
ENGINES = ("chatgpt", "perplexity", "gemini", "google_ai_overviews")


async def seed_mention(
    session: AsyncSession,
    generation_id: str,
    engine: str = "chatgpt",
    mentioned: bool = True,
    cited: bool = False,
    sentiment: str = "neutral",
) -> int:
    """Record one visibility check result via the service path.

    Returns rows written. Raises NotImplementedError during the RED phase.
    """
    result = EngineVisibilityResult(
        engine=engine,
        query=f"what is {generation_id}?",
        mentioned=mentioned,
        cited=cited,
        cited_url="https://example.com/x" if cited else None,
        snippet="sample answer snippet",
        sentiment=sentiment,  # type: ignore[arg-type]
        raw_payload={"ok": True},
    )
    return await AiVisibilityService().record_mentions(
        session, generation_id, engine, [result]
    )


async def seed_referral(
    session: AsyncSession,
    generation_id: str,
    engine: str = "chatgpt",
    converted: bool = False,
    conversion_value: float = 0.0,
) -> str:
    """Record one AI-referred visit via the service path.

    Returns the referral id. Raises NotImplementedError during the RED phase.
    """
    return await AiVisibilityService().record_referral(
        session,
        generation_id=generation_id,
        engine=engine,
        referrer_url=f"https://{engine}.example.com/ref",
        landing_path="/pricing",
        converted=converted,
        conversion_value=conversion_value,
        occurred_at=datetime.now(UTC),
    )

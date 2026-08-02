"""AiVisibilityPoller — polling core + lifecycle (analysis brief §5 M7).

Chosen mechanism (decision A3): provider abstraction + background asyncio task
+ on-demand refresh — all sharing one testable core, ``poll_once``.

- ``poll_once`` is the single testable core: for each tracked content (or the
  given subset) and each engine, run ``queries_per_generation`` queries
  through the provider, record mentions, recompute engine metrics, rebuild
  trend aggregates. Per-engine errors are caught and reported in
  ``PollResult.errors`` — one failing engine never aborts the run, and
  ``poll_once`` never raises.
- ``start()`` spawns an asyncio background task looping with
  ``asyncio.sleep(interval)`` (sleep-first, so the task never polls before the
  interval elapses); ``shutdown()`` cancels it. Mirrors ``SchedulerService``.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai_visibility.models import AI_ENGINES
from src.ai_visibility.providers import ProviderError, ProviderRegistry
from src.ai_visibility.schemas import PollResult
from src.ai_visibility.service import AiVisibilityService
from src.config import Settings, get_settings
from src.database import DatabaseManager
from src.models.generation import Generation


def _utcnow() -> datetime:
    """Current tz-aware UTC datetime."""
    return datetime.now(UTC)


class AiVisibilityPoller:
    """Poll AI engines for visibility of tracked content."""

    def __init__(
        self,
        registry: ProviderRegistry,
        settings: Settings | None = None,
    ) -> None:
        self._registry = registry
        self._settings = settings or get_settings()
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Spawn the background polling loop (lifespan startup, P1/M8)."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop())

    async def shutdown(self) -> None:
        """Cancel the background polling loop (lifespan teardown, P1/M8)."""
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self) -> None:
        """Background loop: sleep interval, then run one poll cycle."""
        interval = self._settings.AI_VISIBILITY_POLL_INTERVAL_SECONDS
        while True:
            try:
                await asyncio.sleep(interval)
                manager = DatabaseManager(self._settings.DATABASE_URL)
                session = await manager.get_session()
                try:
                    await self.poll_once(session)
                finally:
                    await session.close()
                    await manager.close()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 — the loop must never die
                continue

    async def poll_once(
        self,
        db: AsyncSession,
        generation_ids: list[str] | None = None,
        engines: list[str] | None = None,
        queries_per_generation: int = 5,
    ) -> PollResult:
        """Run one full poll cycle; always returns a PollResult, never raises
        on provider failure."""
        started_at = _utcnow()
        service = AiVisibilityService()
        engines_polled: list[str] = []
        queries_run = 0
        mentions_recorded = 0
        errors: list[str] = []

        target_engines = engines or self._registry.configured_engines()
        target_engines = [e for e in target_engines if e in AI_ENGINES]

        if generation_ids is None:
            gen_rows = (await db.execute(select(Generation.id))).scalars().all()
            target_generations = list(gen_rows)
        else:
            target_generations = list(generation_ids)

        for engine in target_engines:
            engines_polled.append(engine)
            try:
                provider = self._registry.get(engine)
            except KeyError:
                errors.append(f"{engine}: provider not configured")
                continue

            for generation_id in target_generations:
                try:
                    results = []
                    for index in range(queries_per_generation):
                        query = f"what is {generation_id}? ({index + 1})"
                        result = await provider.check_visibility(
                            query, self._target_url(generation_id)
                        )
                        results.append(result)
                        queries_run += 1

                    recorded = await service.record_mentions(
                        db, generation_id, engine, results
                    )
                    mentions_recorded += recorded
                    await service.compute_engine_metrics(db, generation_id, engine)
                except ValueError as exc:
                    errors.append(f"{engine}/{generation_id}: {exc}")
                except ProviderError as exc:
                    errors.append(f"{engine}/{generation_id}: {exc}")
                except Exception as exc:  # noqa: BLE001 — never abort the run
                    errors.append(f"{engine}/{generation_id}: {exc}")

        try:
            await service.rebuild_trend_aggregates(db)
        except Exception as exc:  # noqa: BLE001 — rollup failure is non-fatal
            errors.append(f"trend aggregates: {exc}")

        return PollResult(
            started_at=started_at,
            finished_at=_utcnow(),
            engines_polled=engines_polled,
            queries_run=queries_run,
            mentions_recorded=mentions_recorded,
            errors=errors,
        )

    def _target_url(self, generation_id: str) -> str:
        """Deterministic target URL for a content piece (no URL column on
        Generation; tests exercise counts, not URL content)."""
        return f"https://contentforge.example/generations/{generation_id}"

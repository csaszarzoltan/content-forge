"""Interface + behavioral tests for M7 — AiVisibilityPoller.

Interface tests verify the class and the exact signatures from brief §5 M7 —
these PASS immediately. Behavioral tests verify ``poll_once`` semantics
(always returns PollResult, never raises on provider failure) and the
start/shutdown lifecycle; against the stubs they FAIL with
``NotImplementedError`` (TDD RED phase).
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.quick]

from src.ai_visibility.poller import AiVisibilityPoller
from src.ai_visibility.providers import ProviderRegistry
from src.ai_visibility.schemas import PollResult
from src.config import Settings

# ============================================================================
# SECTION 1 — INTERFACE TESTS (PASS immediately)
# ============================================================================


class TestPollerInterface:
    """Verify the M7 public surface."""

    def test_poller_class_exists(self):
        assert AiVisibilityPoller is not None

    def test_init_signature(self):
        sig = inspect.signature(AiVisibilityPoller.__init__)
        assert tuple(sig.parameters) == ("self", "registry", "settings")
        assert sig.parameters["settings"].default is None

    def test_poll_once_signature(self):
        sig = inspect.signature(AiVisibilityPoller.poll_once)
        params = sig.parameters
        assert tuple(params) == (
            "self", "db", "generation_ids", "engines", "queries_per_generation",
        )
        assert params["generation_ids"].default is None
        assert params["engines"].default is None
        assert params["queries_per_generation"].default == 5

    def test_lifecycle_methods(self):
        assert callable(AiVisibilityPoller.start)
        assert callable(AiVisibilityPoller.shutdown)
        sig_start = inspect.signature(AiVisibilityPoller.start)
        assert tuple(sig_start.parameters) == ("self",)
        sig_stop = inspect.signature(AiVisibilityPoller.shutdown)
        assert tuple(sig_stop.parameters) == ("self",)


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (FAIL with NotImplementedError during RED)
# ============================================================================


class TestPollerBehavioral:
    """Poller behavior once the developer implements M7."""

    async def test_poll_once_returns_poll_result(self, db_session):
        """poll_once always returns a PollResult (never raises on failure)."""
        poller = AiVisibilityPoller(registry=ProviderRegistry(Settings()))
        result = await poller.poll_once(db_session, generation_ids=["gen_1"])
        assert isinstance(result, PollResult)

    async def test_poll_once_counts_queries_and_mentions(self, db_session):
        poller = AiVisibilityPoller(registry=ProviderRegistry(Settings()))
        result = await poller.poll_once(
            db_session, generation_ids=["gen_1"], queries_per_generation=3
        )
        assert result.queries_run >= 1
        assert result.mentions_recorded >= 0
        assert result.engines_polled

    async def test_poll_once_reports_errors_not_raises(self, db_session):
        """A failing engine lands in PollResult.errors, never aborts the run."""
        poller = AiVisibilityPoller(registry=ProviderRegistry(Settings()))
        result = await poller.poll_once(db_session, generation_ids=["gen_1"])
        assert isinstance(result.errors, list)

    async def test_start_and_shutdown_cycle(self):
        """start() then shutdown() completes without error."""
        poller = AiVisibilityPoller(registry=ProviderRegistry(Settings()))
        await poller.start()
        await poller.shutdown()

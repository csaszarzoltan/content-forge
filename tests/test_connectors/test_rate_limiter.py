"""Interface and behavioral tests for TokenBucketRateLimiter.

Interface tests  — verify imports, constructor, method signatures (should PASS with stubs).
Behavioral tests — verify token bucket behaviour (RED until implementation).
Edge-case tests  — verify boundary conditions, zero capacity, concurrency, fairness.
"""

from __future__ import annotations

import inspect

import pytest


class TestRateLimiterInterface:
    """Verify the TokenBucketRateLimiter interface."""

    def test_rate_limiter_importable(self):
        """TokenBucketRateLimiter should be importable."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        assert TokenBucketRateLimiter is not None

    def test_rate_limiter_is_class(self):
        """TokenBucketRateLimiter should be a class."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        assert inspect.isclass(TokenBucketRateLimiter)

    def test_rate_limiter_constructor_accepts_capacity_and_refill_rate(self):
        """Constructor should accept capacity and refill_rate."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        sig = inspect.signature(TokenBucketRateLimiter)
        assert "capacity" in sig.parameters
        assert "refill_rate" in sig.parameters

    def test_rate_limiter_has_acquire_method(self):
        """TokenBucketRateLimiter should have an acquire method."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        assert hasattr(TokenBucketRateLimiter, "acquire")
        assert callable(TokenBucketRateLimiter.acquire)
        assert inspect.iscoroutinefunction(TokenBucketRateLimiter.acquire)

    def test_rate_limiter_has_try_acquire_method(self):
        """TokenBucketRateLimiter should have a try_acquire method."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        assert hasattr(TokenBucketRateLimiter, "try_acquire")
        assert callable(TokenBucketRateLimiter.try_acquire)

    def test_rate_limiter_has_remaining_property(self):
        """TokenBucketRateLimiter should have a remaining property."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        assert hasattr(TokenBucketRateLimiter, "remaining")

    def test_rate_limiter_has_capacity_property(self):
        """TokenBucketRateLimiter should have a capacity property."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        assert hasattr(TokenBucketRateLimiter, "capacity")

    def test_rate_limiter_accepts_name_param(self):
        """Constructor should accept name parameter."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        sig = inspect.signature(TokenBucketRateLimiter)
        assert "name" in sig.parameters


class TestRateLimiterBehavioral:
    """Behavioral tests for TokenBucketRateLimiter — RED until implemented."""

    @pytest.mark.asyncio
    async def test_constructor_sets_capacity(self):
        """Constructor should set the bucket capacity."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=1.0)
        assert limiter.capacity == 10
        assert limiter.remaining <= 10

    @pytest.mark.asyncio
    async def test_try_acquire_returns_true_when_tokens_available(self):
        """try_acquire() should return True when tokens are available."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(capacity=5, refill_rate=10.0)
        result = limiter.try_acquire()
        assert result is True

    @pytest.mark.asyncio
    async def test_try_acquire_returns_false_when_exhausted(self):
        """try_acquire() should return False when all tokens are consumed."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(capacity=2, refill_rate=0.0)
        # Consume all tokens
        limiter.try_acquire()
        limiter.try_acquire()
        # Next attempt should fail
        result = limiter.try_acquire()
        assert result is False

    @pytest.mark.asyncio
    async def test_remaining_decreases_on_acquire(self):
        """The remaining count should decrease after acquiring a token."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=0.0)
        remaining_before = limiter.remaining
        limiter.try_acquire()
        assert limiter.remaining == remaining_before - 1

    @pytest.mark.asyncio
    async def test_acquire_blocks_until_token_available(self):
        """acquire() should block until a token is available, then succeed."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(capacity=1, refill_rate=0.0)
        # Consume the only token
        limiter.try_acquire()
        assert limiter.remaining == 0

        # acquire() should eventually get a token after refill
        import asyncio

        # Create a limiter that refills quickly
        fast_limiter = TokenBucketRateLimiter(capacity=1, refill_rate=10.0)
        fast_limiter.try_acquire()  # consume it
        await asyncio.sleep(0.11)  # wait for refill
        await fast_limiter.acquire()
        assert fast_limiter.remaining >= 0

    @pytest.mark.asyncio
    async def test_tokens_refill_over_time(self):
        """Tokens should refill according to the refill_rate."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        import asyncio

        limiter = TokenBucketRateLimiter(capacity=5, refill_rate=5.0)  # 5 tokens/sec
        # Consume 3 tokens
        for _ in range(3):
            limiter.try_acquire()
        depleted = limiter.remaining

        # Wait for refill
        await asyncio.sleep(0.3)  # ~1.5 tokens should refill
        assert limiter.remaining > depleted

    @pytest.mark.asyncio
    async def test_rate_limiter_capacity_constant(self):
        """The capacity property should always return the initial capacity."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=1.0)
        assert limiter.capacity == 10
        # Consume some tokens — capacity should still be 10
        for _ in range(5):
            limiter.try_acquire()
        assert limiter.capacity == 10
        assert limiter.remaining <= 10


class TestRateLimiterEdgeCases:
    """Edge-case tests for TokenBucketRateLimiter — boundary conditions."""

    @pytest.mark.asyncio
    async def test_capacity_one_acquire_exact(self):
        """Capacity=1, acquire exact capacity should work."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(capacity=1, refill_rate=0.0)
        result = limiter.try_acquire(tokens=1)
        assert result is True
        assert limiter.remaining == 0

    @pytest.mark.asyncio
    async def test_capacity_one_over_capacity_fails(self):
        """Capacity=1, try_acquire when exhausted should return False."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(capacity=1, refill_rate=0.0)
        limiter.try_acquire()  # consume
        assert limiter.try_acquire() is False

    @pytest.mark.asyncio
    async def test_acquire_after_refill_eventually_succeeds(self):
        """Acquire after refill should eventually succeed."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        import asyncio

        limiter = TokenBucketRateLimiter(capacity=2, refill_rate=4.0)
        # Drain
        limiter.try_acquire(tokens=2)
        assert limiter.remaining < 2
        # Wait for refill
        await asyncio.sleep(0.3)  # ~1.2 tokens refilled
        result = limiter.try_acquire()
        assert result is True

    @pytest.mark.asyncio
    async def test_try_acquire_zero_tokens_returns_true(self):
        """try_acquire(tokens=0) should return True without consuming tokens."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(capacity=5, refill_rate=1.0)
        before = limiter.remaining
        result = limiter.try_acquire(tokens=0)
        assert result is True
        assert limiter.remaining == before  # no tokens consumed

    @pytest.mark.asyncio
    async def test_acquire_zero_tokens_returns_zero(self):
        """acquire(tokens=0) should return 0.0 immediately."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        import asyncio

        limiter = TokenBucketRateLimiter(capacity=5, refill_rate=1.0)
        wait = await limiter.acquire(tokens=0)
        assert wait == 0.0

    @pytest.mark.asyncio
    async def test_negative_tokens_try_acquire_returns_true(self):
        """try_acquire(tokens=-1) should return True (treated as non-positive)."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(capacity=5, refill_rate=1.0)
        result = limiter.try_acquire(tokens=-1)
        assert result is True

    @pytest.mark.asyncio
    async def test_negative_tokens_acquire_returns_zero(self):
        """acquire(tokens=-1) should return 0.0 immediately."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        import asyncio

        limiter = TokenBucketRateLimiter(capacity=5, refill_rate=1.0)
        wait = await limiter.acquire(tokens=-1)
        assert wait == 0.0

    @pytest.mark.asyncio
    async def test_remaining_never_exceeds_capacity(self):
        """The remaining property should never exceed capacity."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        import asyncio

        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=100.0)
        # Wait for significant refill time
        await asyncio.sleep(0.5)
        # Remaining should be capped at capacity
        assert limiter.remaining <= limiter.capacity

    @pytest.mark.asyncio
    async def test_acquire_blocks_when_exhausted(self):
        """acquire() should block when no tokens available, then succeed after refill."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        import asyncio

        limiter = TokenBucketRateLimiter(capacity=3, refill_rate=6.0)  # 6 tokens/s
        # Drain
        limiter.try_acquire(tokens=3)
        assert limiter.remaining < 1
        # acquire should wait for refill (~0.17s for 1 token at 6/sec)
        wait = await limiter.acquire(tokens=1)
        assert wait >= 0.0
        assert limiter.remaining >= 0

    @pytest.mark.asyncio
    async def test_acquire_multiple_tokens(self):
        """acquire() should support consuming multiple tokens."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        import asyncio

        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=0.0)
        wait = await limiter.acquire(tokens=3)
        assert wait >= 0.0
        assert limiter.remaining == 7

    @pytest.mark.asyncio
    async def test_try_acquire_multiple_tokens(self):
        """try_acquire() should support consuming multiple tokens."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=0.0)
        result = limiter.try_acquire(tokens=7)
        assert result is True
        assert limiter.remaining == 3

    @pytest.mark.asyncio
    async def test_try_acquire_multiple_tokens_exhaust(self):
        """try_acquire() multiple tokens should fail when insufficient."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(capacity=5, refill_rate=0.0)
        result = limiter.try_acquire(tokens=10)
        assert result is False
        assert limiter.remaining == 5  # unchanged

    @pytest.mark.asyncio
    async def test_zero_refill_rate_acquire_blocks_indefinitely(self):
        """acquire() with refill_rate=0 should block (no refill possible)."""
        from src.connectors.rate_limiter import TokenBucketRateLimiter

        import asyncio

        limiter = TokenBucketRateLimiter(capacity=3, refill_rate=0.0)
        # Drain
        limiter.try_acquire(tokens=3)
        # Acquire with timeout so test doesn't hang
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(limiter.acquire(tokens=1), timeout=0.5)

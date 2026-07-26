"""Interface and behavioral tests for TokenBucketRateLimiter.

Interface tests  — verify imports, constructor, method signatures (should PASS with stubs).
Behavioral tests — verify token bucket behaviour (RED until implementation).
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

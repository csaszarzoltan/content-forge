"""Token-bucket rate limiter for social media API rate limits.

Thread-safe using asyncio.Lock. Tokens refill at a configurable rate
up to a maximum capacity.
"""

from __future__ import annotations

import asyncio
import time


class TokenBucketRateLimiter:
    """Token-bucket rate limiter with async acquire and non-blocking check.

    Args:
        capacity: Maximum number of tokens the bucket can hold.
        refill_rate: Tokens added per second.
        name: Optional name for logging/debugging.
    """

    def __init__(self, capacity: int, refill_rate: float, name: str = "") -> None:
        self._capacity = float(capacity)
        self._tokens = float(capacity)
        self._refill_rate = refill_rate
        self._name = name
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    @property
    def capacity(self) -> float:
        """Return the bucket's maximum capacity."""
        return self._capacity

    @property
    def remaining(self) -> float:
        """Return the current number of tokens available (refills first)."""
        self._refill()
        return self._tokens

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now

    def try_acquire(self, tokens: int = 1) -> bool:
        """Non-blocking token acquisition.

        Args:
            tokens: Number of tokens to consume (default 1).

        Returns:
            True if tokens were available and consumed, False otherwise.
        """
        if tokens <= 0:
            return True
        self._refill()
        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False

    async def acquire(self, tokens: int = 1) -> float:
        """Block until tokens are available, then consume them.

        Args:
            tokens: Number of tokens to consume (default 1).

        Returns:
            The wait time in seconds before tokens were acquired.
        """
        if tokens <= 0:
            return 0.0
        start = time.monotonic()
        async with self._lock:
            self._refill()
            while self._tokens < tokens:
                self._refill()
                if self._tokens >= tokens:
                    break
                # Calculate time until at least one token is available
                deficit = tokens - self._tokens
                sleep_time = max(deficit / self._refill_rate, 0.01) if self._refill_rate > 0 else 0.1
                await asyncio.sleep(sleep_time)
                self._refill()
            self._tokens -= tokens
        return time.monotonic() - start

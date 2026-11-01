"""Token bucket rate limiter with an injectable clock."""
import time


class TokenBucket:
    """Allows bursts of up to `capacity` requests and refills `rate` tokens per second.

    The bucket starts full. `clock` returns the current time in seconds.
    """

    def __init__(self, capacity: int, rate: float, clock=time.monotonic):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if rate <= 0:
            raise ValueError("rate must be positive")
        self.capacity = capacity
        self.rate = rate
        self._clock = clock
        self._tokens = float(capacity)
        self._last = clock()

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last
        self._last = now
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)

    def allow(self, cost: int = 1) -> bool:
        """Consume `cost` tokens if available and return True, otherwise False
        (and consume nothing)."""
        if cost <= 0:
            raise ValueError("cost must be positive")
        self._refill()
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False

    def wait_time(self, cost: int = 1) -> float:
        """Seconds until `cost` tokens will be available (0.0 if available now)."""
        self._refill()
        missing = cost - self._tokens
        return max(0.0, missing / self.rate)

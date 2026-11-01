"""Retry delay schedules."""


def backoff_delays(retries: int, base: float = 0.5, factor: float = 2.0,
                   max_delay: float = 30.0) -> list[float]:
    """Delays before each retry: base, base*factor, base*factor**2, ... capped at max_delay.

    backoff_delays(4) == [0.5, 1.0, 2.0, 4.0]. retries == 0 gives [].
    Raises ValueError if retries < 0, base <= 0, factor < 1 or max_delay < base.
    """
    if retries < 0:
        raise ValueError("retries must not be negative")
    if base <= 0:
        raise ValueError("base must be positive")
    if factor < 1:
        raise ValueError("factor must be at least 1")
    if max_delay < base:
        raise ValueError("max_delay must be at least base")
    return [min(max_delay, base * factor ** i) for i in range(retries)]


def total_wait(retries: int, **kwargs) -> float:
    """Total time spent waiting across all retries."""
    return sum(backoff_delays(retries, **kwargs))


def should_retry(status_code: int, attempt: int, retries: int) -> bool:
    """Retry on 429 and 5xx (except 501), while attempt < retries (attempt is 0-based)."""
    if attempt >= retries:
        return False
    return status_code == 429 or (500 <= status_code <= 599 and status_code != 501)

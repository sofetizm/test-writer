import math
import pytest
from hypothesis import given, strategies as st

from retry_backoff import backoff_delays, total_wait, should_retry


# ---------- Tests for backoff_delays ----------

def test_backoff_delays_basic():
    # Basic example from docstring
    assert backoff_delays(4) == [0.5, 1.0, 2.0, 4.0]
    # Zero retries returns empty list
    assert backoff_delays(0) == []


@pytest.mark.parametrize(
    "retries,base,factor,max_delay,expected",
    [
        (3, 1.0, 2.0, 10.0, [1.0, 2.0, 4.0]),
        (5, 0.2, 3.0, 5.0, [0.2, 0.6, 1.8, 5.0, 5.0]),  # capped at max_delay
        (2, 2.5, 1.0, 3.0, [2.5, 2.5]),  # factor == 1 yields constant delay
    ],
)
def test_backoff_delays_various_parameters(retries, base, factor, max_delay, expected):
    assert backoff_delays(retries, base=base, factor=factor, max_delay=max_delay) == expected


@pytest.mark.parametrize(
    "retries,base,factor,max_delay,exc_msg",
    [
        (-1, 0.5, 2.0, 30.0, "retries must not be negative"),
        (1, 0.0, 2.0, 30.0, "base must be positive"),
        (1, -0.1, 2.0, 30.0, "base must be positive"),
        (1, 0.5, 0.9, 30.0, "factor must be at least 1"),
        (1, 0.5, 1.0, 0.4, "max_delay must be at least base"),
    ],
)
def test_backoff_delays_invalid_inputs(retries, base, factor, max_delay, exc_msg):
    with pytest.raises(ValueError) as e:
        backoff_delays(retries, base=base, factor=factor, max_delay=max_delay)
    assert exc_msg in str(e.value)


@given(
    retries=st.integers(min_value=0, max_value=20),
    base=st.floats(min_value=0.01, max_value=10.0, allow_nan=False, allow_infinity=False),
    factor=st.floats(min_value=1.0, max_value=5.0, allow_nan=False, allow_infinity=False),
    max_delay=st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_backoff_delays_properties(retries, base, factor, max_delay):
    # Ensure max_delay is at least base to avoid ValueError
    max_delay = max(max_delay, base)

    delays = backoff_delays(retries, base=base, factor=factor, max_delay=max_delay)

    # Length matches retries
    assert len(delays) == retries

    # All delays are positive and not greater than max_delay
    for d in delays:
        assert d > 0
        assert d <= max_delay + 1e-12  # tolerance for floating point

    # Delays are non‑decreasing
    assert all(earlier <= later for earlier, later in zip(delays, delays[1:]))


# ---------- Tests for total_wait ----------

def test_total_wait_matches_sum_of_delays():
    kwargs = {"base": 0.7, "factor": 2.5, "max_delay": 20.0}
    for retries in range(6):
        expected = sum(backoff_delays(retries, **kwargs))
        assert math.isclose(total_wait(retries, **kwargs), expected, rel_tol=1e-12)


def test_total_wait_zero_retries():
    assert total_wait(0) == 0.0


# ---------- Tests for should_retry ----------

@pytest.mark.parametrize(
    "status_code,attempt,retries,expected",
    [
        (429, 0, 3, True),   # 429 always retry if attempts left
        (429, 2, 3, True),   # still within limit
        (429, 3, 3, False),  # attempt == retries -> no retry
        (500, 1, 5, True),   # generic 5xx
        (501, 1, 5, False),  # 501 is excluded
        (599, 0, 1, True),   # upper bound of 5xx
        (400, 0, 2, False),  # non‑retryable status
        (200, 0, 2, False),  # success code never retries
    ],
)
def test_should_retry_logic(status_code, attempt, retries, expected):
    assert should_retry(status_code, attempt, retries) is expected


def test_should_retry_attempt_boundary():
    # When attempt equals retries, should always be False regardless of status
    for status in [429, 500, 501, 200]:
        assert not should_retry(status, attempt=5, retries=5)


def test_should_retry_negative_attempts():
    # Negative attempt values are treated as less than retries, so only status matters
    assert should_retry(429, attempt=-1, retries=0) is False  # no retries allowed
    assert should_retry(429, attempt=-1, retries=1) is True
    assert should_retry(500, attempt=-2, retries=1) is True
    assert should_retry(501, attempt=-2, retries=1) is False


# ---------- Edge case: large exponent causing overflow handling ----------
def test_backoff_delays_overflow_handling():
    # Use a huge factor to ensure the raw value would overflow a float,
    # but the function caps it at max_delay before overflow occurs.
    delays = backoff_delays(3, base=1.0, factor=1e308, max_delay=1e5)
    # All values should be capped at max_delay
    assert delays == [1.0, 1e5, 1e5]

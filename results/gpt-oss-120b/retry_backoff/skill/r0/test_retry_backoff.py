import pytest
from retry_backoff import backoff_delays, total_wait, should_retry

# ----------------------------------------------------------------------
# Test plan for backoff_delays
# ----------------------------------------------------------------------
# Behaviours:
# - Returns list of length `retries` with exponential backoff capped at max_delay.
# - Empty list when retries == 0.
# - Raises ValueError for:
#   * retries < 0
#   * base <= 0
#   * factor < 1
#   * max_delay < base
# - Default arguments produce the documented sequence and default max_delay is 30.0.
# Branches / boundaries:
#   * retries = 0, 1, typical >0
#   * factor = 1 (no exponential growth)
#   * max_delay exactly equal to a computed delay
#   * max_delay just below a computed delay (capping occurs)
#   * max_delay == base (edge case – should be allowed)
#   * large retries to ensure capping works repeatedly.
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "retries,base,factor,max_delay,expected",
    [
        (0, 0.5, 2.0, 30.0, []),
        (1, 0.5, 2.0, 30.0, [0.5]),
        (4, 0.5, 2.0, 30.0, [0.5, 1.0, 2.0, 4.0]),
        (5, 0.5, 2.0, 4.0, [0.5, 1.0, 2.0, 4.0, 4.0]),  # capping at max_delay
        (3, 1.0, 1.0, 10.0, [1.0, 1.0, 1.0]),  # factor == 1, no growth
        (3, 2.0, 3.0, 20.0, [2.0, 6.0, 18.0]),  # normal growth, no cap
        (4, 2.0, 3.0, 15.0, [2.0, 6.0, 15.0, 15.0]),  # cap hits on third element
        (3, 5.0, 2.0, 5.0, [5.0, 5.0, 5.0]),  # max_delay == base, all values capped
    ],
    ids=lambda val: str(val),
)
def test_backoff_delays_correctness(retries, base, factor, max_delay, expected):
    """Check that backoff_delays returns the expected sequence."""
    assert backoff_delays(retries, base=base, factor=factor, max_delay=max_delay) == expected


def test_backoff_delays_defaults():
    """Calling with no explicit parameters must use the documented defaults."""
    # Defaults are base=0.5, factor=2.0, max_delay=30.0
    assert backoff_delays(4) == [0.5, 1.0, 2.0, 4.0]
    # Verify that the default max_delay caps as expected:
    # 6th delay = 0.5 * 2**5 = 16.0 (below 30)
    # 7th delay = 0.5 * 2**6 = 32.0 -> capped to 30.0
    assert backoff_delays(7) == [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 30.0]


@pytest.mark.parametrize(
    "retries,base,factor,max_delay,exc_msg",
    [
        (-1, 0.5, 2.0, 30.0, "retries must not be negative"),
        (1, 0.0, 2.0, 30.0, "base must be positive"),
        (1, -0.1, 2.0, 30.0, "base must be positive"),
        (1, 0.5, 0.9, 30.0, "factor must be at least 1"),
        (1, 0.5, 0.5, 30.0, "factor must be at least 1"),
        (1, 0.5, 2.0, 0.4, "max_delay must be at least base"),
        (1, 1.0, 2.0, 0.9, "max_delay must be at least base"),
    ],
    ids=lambda val: str(val),
)
def test_backoff_delays_invalid_arguments(retries, base, factor, max_delay, exc_msg):
    """Invalid arguments must raise ValueError with the correct message."""
    with pytest.raises(ValueError, match=exc_msg):
        backoff_delays(retries, base=base, factor=factor, max_delay=max_delay)


def test_total_wait_matches_sum():
    """total_wait should equal the sum of the individual delays."""
    retries = 6
    kwargs = {"base": 0.3, "factor": 2.5, "max_delay": 5.0}
    delays = backoff_delays(retries, **kwargs)
    assert total_wait(retries, **kwargs) == sum(delays)


# ----------------------------------------------------------------------
# Test plan for should_retry
# ----------------------------------------------------------------------
# Behaviours:
# - Returns False when attempt >= retries (no more attempts allowed).
# - Returns True for status 429.
# - Returns True for 5xx except 501.
# - Returns False for other status codes.
# Branches / boundaries:
# - attempt exactly retries-1 (last allowed attempt)
# - attempt equal to retries (should be False)
# - status codes: 429, 500, 501, 502, 599, 600, 200
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "status_code,attempt,retries,expected",
    [
        (429, 0, 3, True),   # retry on 429, first attempt
        (429, 2, 3, True),   # retry on 429, last allowed attempt
        (429, 3, 3, False),  # attempt == retries -> no retry
        (500, 0, 2, True),   # 5xx allowed
        (501, 0, 2, False),  # 501 excluded
        (502, 1, 2, True),   # other 5xx allowed
        (599, 1, 2, True),   # upper bound of 5xx
        (600, 0, 2, False),  # just above 5xx range
        (200, 0, 2, False),  # normal success code
        (404, 0, 2, False),  # client error not 429
    ],
    ids=lambda val: str(val),
)
def test_should_retry_logic(status_code, attempt, retries, expected):
    assert should_retry(status_code, attempt, retries) is expected


def test_should_retry_attempt_boundary():
    """When attempt equals retries, should_retry must be False regardless of status."""
    for status in [429, 500, 501, 200]:
        assert not should_retry(status, attempt=5, retries=5)

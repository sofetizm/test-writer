# tests/test_rate_limiter.py
import pytest
from hypothesis import given, strategies as st

from rate_limiter import TokenBucket


# Helper clock that can be manually advanced
class ManualClock:
    def __init__(self, start=0.0):
        self.time = float(start)

    def __call__(self):
        return self.time

    def advance(self, seconds):
        self.time += seconds


def test_initial_state_full_bucket():
    clock = ManualClock()
    tb = TokenBucket(capacity=5, rate=2.0, clock=clock)
    # bucket starts full, allow up to capacity immediately
    for _ in range(5):
        assert tb.allow() is True
    # next request should be denied
    assert tb.allow() is False


def test_allow_consumes_tokens_and_refills_over_time():
    clock = ManualClock()
    tb = TokenBucket(capacity=3, rate=1.0, clock=clock)

    # consume two tokens
    assert tb.allow(cost=2) is True
    # only one token left
    assert tb.allow() is True
    # now empty
    assert tb.allow() is False

    # advance half a second, should have 0.5 token (not enough for cost=1)
    clock.advance(0.5)
    assert tb.allow() is False

    # advance another 0.5 second, now 1 token available
    clock.advance(0.5)
    assert tb.allow() is True


def test_wait_time_calculation():
    clock = ManualClock()
    tb = TokenBucket(capacity=4, rate=2.0, clock=clock)

    # consume all tokens
    assert tb.allow(cost=4) is True
    # no tokens left, wait_time for 1 token should be 0.5 seconds
    assert tb.wait_time() == pytest.approx(0.5)

    # after 0.25 seconds, half token available, wait_time should be 0.25
    clock.advance(0.25)
    assert tb.wait_time() == pytest.approx(0.25)

    # after another 0.25 seconds, token available, wait_time 0
    clock.advance(0.25)
    assert tb.wait_time() == pytest.approx(0.0)


def test_invalid_initialisation():
    with pytest.raises(ValueError, match="capacity must be positive"):
        TokenBucket(capacity=0, rate=1.0)
    with pytest.raises(ValueError, match="rate must be positive"):
        TokenBucket(capacity=5, rate=0.0)


def test_invalid_cost():
    clock = ManualClock()
    tb = TokenBucket(capacity=2, rate=1.0, clock=clock)
    with pytest.raises(ValueError, match="cost must be positive"):
        tb.allow(cost=0)
    with pytest.raises(ValueError, match="cost must be positive"):
        tb.allow(cost=-1)


@given(
    capacity=st.integers(min_value=1, max_value=10),
    rate=st.floats(min_value=0.1, max_value=5.0),
    cost=st.integers(min_value=1, max_value=10),
    advance=st.floats(min_value=0.0, max_value=5.0),
)
def test_property_refill_never_exceeds_capacity(capacity, rate, cost, advance):
    """After any amount of time, tokens never exceed capacity."""
    clock = ManualClock()
    tb = TokenBucket(capacity=capacity, rate=rate, clock=clock)

    # consume some tokens if possible
    tb.allow(cost=min(cost, capacity))

    # advance time arbitrarily
    clock.advance(advance)
    # trigger refill
    tb.wait_time()

    # Count how many successful allows we can get consecutively.
    successes = 0
    while tb.allow():
        successes += 1
        # guard against infinite loop in case of bug
        if successes > capacity:
            break
    assert successes <= capacity  # never more than capacity tokens


def test_refill_respects_rate_and_capacity():
    """Explicitly check token count after known elapsed time."""
    clock = ManualClock()
    tb = TokenBucket(capacity=5, rate=2.0, clock=clock)

    # use 3 tokens
    assert tb.allow(cost=3) is True
    # advance 1 second: should add 2 tokens, reaching 4 tokens total
    clock.advance(1.0)
    # wait_time for 1 token should be 0 (since we have 4 tokens)
    assert tb.wait_time(cost=1) == pytest.approx(0.0)

    # consume remaining 4 tokens
    assert tb.allow(cost=4) is True
    # bucket empty now
    assert tb.allow() is False

    # advance 3 seconds: should refill to capacity (5)
    clock.advance(3.0)
    assert tb.wait_time() == pytest.approx(0.0)
    for _ in range(5):
        assert tb.allow() is True
    assert tb.allow() is False

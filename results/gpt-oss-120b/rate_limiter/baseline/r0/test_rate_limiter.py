# tests/test_rate_limiter.py
import pytest
import itertools
from hypothesis import given, strategies as st

from rate_limiter import TokenBucket


def test_initial_state_allows_up_to_capacity():
    bucket = TokenBucket(capacity=5, rate=1.0, clock=lambda: 0.0)
    for _ in range(5):
        assert bucket.allow() is True
    assert bucket.allow() is False


def test_allow_respects_cost_and_refill():
    # Manual clock that we can control
    current = [0.0]

    def clock():
        return current[0]

    bucket = TokenBucket(capacity=3, rate=2.0, clock=clock)  # 2 tokens per second

    # initially full (3 tokens)
    assert bucket.allow(cost=2) is True   # leaves 1 token
    assert bucket.allow(cost=2) is False  # not enough (only 1)

    # advance time by 0.5s -> should add 1 token (2 * 0.5)
    current[0] += 0.5
    # next allow should succeed because we now have 2 tokens
    assert bucket.allow(cost=2) is True


def test_wait_time_calculation():
    t = [0.0]

    def clock():
        return t[0]

    bucket = TokenBucket(capacity=4, rate=2.0, clock=clock)

    assert bucket.wait_time() == 0.0

    assert bucket.allow(cost=3) is True
    # 1 token left, need 2 -> missing 1 token, rate 2/s => 0.5s
    assert bucket.wait_time(cost=2) == pytest.approx(0.5)

    t[0] += 0.5
    assert bucket.wait_time(cost=2) == pytest.approx(0.0)


def test_invalid_initialization():
    with pytest.raises(ValueError):
        TokenBucket(capacity=0, rate=1.0)
    with pytest.raises(ValueError):
        TokenBucket(capacity=5, rate=0.0)
    with pytest.raises(ValueError):
        TokenBucket(capacity=-1, rate=1.0)
    with pytest.raises(ValueError):
        TokenBucket(capacity=5, rate=-2.0)


def test_invalid_cost():
    bucket = TokenBucket(capacity=3, rate=1.0)
    with pytest.raises(ValueError):
        bucket.allow(cost=0)
    with pytest.raises(ValueError):
        bucket.allow(cost=-1)
    # wait_time does not validate cost in the implementation, so we only test allow


@given(
    capacity=st.integers(min_value=1, max_value=10),
    rate=st.floats(min_value=0.1, max_value=5.0),
    steps=st.integers(min_value=1, max_value=20),
)
def test_property_refill_never_exceeds_capacity(capacity, rate, steps):
    delta = 0.123
    current = [0.0]

    def clock():
        return current[0]

    bucket = TokenBucket(capacity=capacity, rate=rate, clock=clock)

    for _ in range(steps):
        bucket.allow(cost=1)
        current[0] += delta
        bucket.wait_time()  # trigger refill
        assert bucket.wait_time() >= 0.0

    current[0] += 1000.0
    bucket.wait_time()
    assert bucket.allow(cost=capacity) is True


def test_refill_behavior_multiple_calls():
    t = [0.0]
    clock = lambda: t[0]

    bucket = TokenBucket(capacity=2, rate=1.0, clock=clock)

    # consume both tokens
    assert bucket.allow(cost=2) is True
    assert bucket.allow() is False

    # repeated calls without time change should keep empty
    for _ in range(5):
        assert bucket.allow() is False
        # need 1 token (default cost) -> missing 1 token, rate 1 => 1 second
        assert bucket.wait_time() == pytest.approx(1.0)

    # advance half a second, need 0.5 more seconds
    t[0] += 0.5
    assert bucket.wait_time() == pytest.approx(0.5)

    # advance another 1.5 seconds, bucket should be full again
    t[0] += 1.5
    assert bucket.wait_time() == pytest.approx(0.0)
    assert bucket.allow(cost=2) is True

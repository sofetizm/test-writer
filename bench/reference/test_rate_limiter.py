import pytest
from rate_limiter import TokenBucket


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def make(capacity=2, rate=1.0):
    clock = Clock()
    return TokenBucket(capacity, rate, clock=clock), clock


def test_starts_full_and_blocks_when_empty():
    b, _ = make(capacity=3)
    assert [b.allow() for _ in range(4)] == [True, True, True, False]


def test_refill_over_time():
    b, clock = make(capacity=2, rate=2.0)
    b.allow()
    b.allow()
    assert not b.allow()
    clock.t += 0.5
    assert b.allow()
    assert not b.allow()


def test_partial_refill_not_enough():
    b, clock = make(capacity=1, rate=1.0)
    b.allow()
    clock.t += 0.9
    assert not b.allow()
    clock.t += 0.1
    assert b.allow()


def test_never_exceeds_capacity():
    b, clock = make(capacity=2, rate=1.0)
    clock.t += 1000
    assert [b.allow() for _ in range(3)] == [True, True, False]


def test_cost():
    b, _ = make(capacity=5)
    assert b.allow(cost=5)
    assert not b.allow(cost=1)


def test_failed_allow_consumes_nothing():
    b, _ = make(capacity=3)
    assert not b.allow(cost=4)
    assert b.allow(cost=3)


@pytest.mark.parametrize("cost", [0, -1])
def test_invalid_cost(cost):
    b, _ = make()
    with pytest.raises(ValueError, match="cost"):
        b.allow(cost)


def test_wait_time():
    b, clock = make(capacity=2, rate=2.0)
    assert b.wait_time() == 0.0
    b.allow()
    b.allow()
    assert b.wait_time() == pytest.approx(0.5)
    assert b.wait_time(cost=2) == pytest.approx(1.0)
    clock.t += 0.25
    assert b.wait_time() == pytest.approx(0.25)


@pytest.mark.parametrize(("capacity", "rate", "match"), [
    (0, 1.0, "capacity"), (-1, 1.0, "capacity"), (1, 0, "rate"), (1, -2.0, "rate"),
])
def test_invalid_args(capacity, rate, match):
    with pytest.raises(ValueError, match=match):
        TokenBucket(capacity, rate, clock=Clock())


def test_attributes():
    b, _ = make(capacity=4, rate=1.5)
    assert (b.capacity, b.rate) == (4, 1.5)

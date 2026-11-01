import pytest
from retry_backoff import backoff_delays, should_retry, total_wait


def test_default_schedule():
    assert backoff_delays(4) == [0.5, 1.0, 2.0, 4.0]


def test_zero_retries():
    assert backoff_delays(0) == []


def test_custom_base_and_factor():
    assert backoff_delays(3, base=1.0, factor=3.0) == [1.0, 3.0, 9.0]


def test_cap():
    assert backoff_delays(5, base=1.0, factor=2.0, max_delay=5.0) == [1.0, 2.0, 4.0, 5.0, 5.0]


def test_cap_equal_to_value_is_kept():
    assert backoff_delays(3, base=1.0, max_delay=4.0) == [1.0, 2.0, 4.0]


def test_default_cap_is_30():
    assert backoff_delays(8)[-1] == 30.0
    assert backoff_delays(7)[-1] == 30.0
    assert backoff_delays(7)[-2] == 16.0


def test_factor_one_is_constant():
    assert backoff_delays(3, base=2.0, factor=1.0) == [2.0, 2.0, 2.0]


def test_max_delay_equal_to_base_allowed():
    assert backoff_delays(2, base=3.0, max_delay=3.0) == [3.0, 3.0]


@pytest.mark.parametrize(("kwargs", "match"), [
    ({"retries": -1}, "retries"),
    ({"retries": 1, "base": 0}, "base"),
    ({"retries": 1, "base": -1}, "base"),
    ({"retries": 1, "factor": 0.5}, "factor"),
    ({"retries": 1, "base": 2.0, "max_delay": 1.0}, "max_delay"),
])
def test_invalid(kwargs, match):
    with pytest.raises(ValueError, match=match):
        backoff_delays(**kwargs)


def test_total_wait():
    assert total_wait(4) == 7.5
    assert total_wait(3, base=1.0, factor=3.0) == 13.0
    assert total_wait(0) == 0


@pytest.mark.parametrize(("status", "attempt", "retries", "expected"), [
    (429, 0, 3, True), (500, 0, 3, True), (503, 2, 3, True), (599, 0, 3, True),
    (501, 0, 3, False), (404, 0, 3, False), (499, 0, 3, False), (600, 0, 3, False),
    (200, 0, 3, False), (500, 3, 3, False), (429, 4, 3, False), (500, 0, 0, False),
])
def test_should_retry(status, attempt, retries, expected):
    assert should_retry(status, attempt, retries) is expected

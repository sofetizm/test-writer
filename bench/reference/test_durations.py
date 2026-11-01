import pytest
from durations import format_duration, parse_duration


@pytest.mark.parametrize(("text", "expected"), [
    ("1s", 1), ("1m", 60), ("1h", 3600), ("1d", 86400),
    ("1h30m", 5400), ("2d 4h", 2 * 86400 + 4 * 3600), ("1D 2H 3M 4S", 93784),
    ("  5m  ", 300), ("30s 1m", 90), ("0h 7s", 7), ("1 h 2 s", 3602), ("12m", 720),
])
def test_parse_valid(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize(("text", "match"), [
    ("", "empty"), ("   ", "empty"),
    ("1x", "unexpected"), ("abc", "unexpected"), ("x1h", "unexpected"), ("1h x", "unexpected"),
    ("1h 2h", "repeated"), ("0s", "positive"), ("0h 0m", "positive"),
])
def test_parse_invalid(text, match):
    with pytest.raises(ValueError, match=match):
        parse_duration(text)


@pytest.mark.parametrize(("seconds", "expected"), [
    (0, "0s"), (1, "1s"), (59, "59s"), (60, "1m"), (61, "1m 1s"), (3600, "1h"),
    (3661, "1h 1m 1s"), (86400, "1d"), (93784, "1d 2h 3m 4s"), (86401, "1d 1s"),
    (7200, "2h"),
])
def test_format(seconds, expected):
    assert format_duration(seconds) == expected


def test_format_negative():
    with pytest.raises(ValueError, match="negative"):
        format_duration(-1)


def test_round_trip():
    for s in (1, 59, 60, 3599, 3600, 86399, 90061):
        assert parse_duration(format_duration(s)) == s

import pytest
from durations import parse_duration, format_duration, UNITS

def manual_seconds(**kwargs):
    """Calculate total seconds from unit keyword arguments."""
    return sum(UNITS[unit] * value for unit, value in kwargs.items())

# ---------- Valid parsing ----------
@pytest.mark.parametrize(
    "input_str,expected",
    [
        ("1d", UNITS["d"]),
        ("2h", 2 * UNITS["h"]),
        ("30m", 30 * UNITS["m"]),
        ("45s", 45 * UNITS["s"]),
        ("1d 2h 3m 4s", manual_seconds(d=1, h=2, m=3, s=4)),
        ("4s3m2h1d", manual_seconds(d=1, h=2, m=3, s=4)),  # any order, no spaces
        ("  5h   10m  ", manual_seconds(h=5, m=10)),      # extra whitespace tolerated
        ("0d 0h 0m 5s", 5),                               # zero units allowed if total > 0
        ("1h30m", manual_seconds(h=1, m=30)),
        ("2d4h", manual_seconds(d=2, h=4)),
    ],
)
def test_parse_valid(input_str, expected):
    assert parse_duration(input_str) == expected


def test_parse_zero_total_raises():
    with pytest.raises(ValueError, match="duration must be positive"):
        parse_duration("0s")


def test_parse_empty_string_raises():
    with pytest.raises(ValueError, match="empty duration"):
        parse_duration("   ")


# ---------- Invalid parsing ----------
@pytest.mark.parametrize(
    "bad_input,expected_msg",
    [
        ("1x", r"unexpected text: 'x'"),
        ("1h 2h", r"unit 'h' repeated"),
        ("1h 2m extra", r"unexpected text: 'extra'"),
        ("1h2", r"unexpected text: '2'"),
        ("h1", r"unexpected text: 'h1'"),
        ("1hh", r"unexpected text: 'h'"),
        ("-5m", r"unexpected text: '-'"),
    ],
)
def test_parse_invalid_inputs(bad_input, expected_msg):
    with pytest.raises(ValueError, match=expected_msg):
        parse_duration(bad_input)


# ---------- Valid formatting ----------
@pytest.mark.parametrize(
    "seconds,expected",
    [
        (0, "0s"),
        (UNITS["s"], "1s"),
        (UNITS["m"], "1m"),
        (UNITS["h"], "1h"),
        (UNITS["d"], "1d"),
        (UNITS["d"] + UNITS["h"] + UNITS["m"] + UNITS["s"], "1d 1h 1m 1s"),
        (2 * UNITS["h"] + 30 * UNITS["m"], "2h 30m"),
        (3 * UNITS["d"] + 5 * UNITS["m"], "3d 5m"),
        (45, "45s"),
        (60 + 5, "1m 5s"),
    ],
)
def test_format_valid(seconds, expected):
    assert format_duration(seconds) == expected


def test_format_negative_raises():
    with pytest.raises(ValueError, match="negative duration"):
        format_duration(-10)


# ---------- Round‑trip property tests ----------
def test_round_trip_fixed():
    """Formatting then parsing should return the original seconds for a set of non‑zero values."""
    for seconds in [1, 59, 60, 61, 3599, 3600, 86400, 123456, 987654321]:
        formatted = format_duration(seconds)
        assert parse_duration(formatted) == seconds


# Hypothesis‑driven round‑trip (skip zero because parse_duration rejects it)
from hypothesis import given, strategies as st

@given(st.integers(min_value=1, max_value=10**9))
def test_round_trip_hypothesis(seconds):
    formatted = format_duration(seconds)
    assert parse_duration(formatted) == seconds

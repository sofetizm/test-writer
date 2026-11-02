# tests/test_durations.py
import pytest
from durations import parse_duration, format_duration, UNITS

# ---------- parse_duration tests ----------

def test_parse_simple_units():
    assert parse_duration("1d") == 86400
    assert parse_duration("2h") == 7200
    assert parse_duration("3m") == 180
    assert parse_duration("4s") == 4

def test_parse_multiple_units_no_spaces():
    assert parse_duration("1d2h3m4s") == 86400 + 7200 + 180 + 4

def test_parse_multiple_units_with_spaces():
    assert parse_duration("1d 2h 3m 4s") == 86400 + 7200 + 180 + 4
    assert parse_duration("  1d   2h   3m   4s  ") == 86400 + 7200 + 180 + 4

def test_parse_units_any_order():
    assert parse_duration("4s3m2h1d") == 86400 + 7200 + 180 + 4
    assert parse_duration("2h1d4s3m") == 86400 + 7200 + 180 + 4

def test_parse_case_insensitivity_and_whitespace():
    assert parse_duration("1D 2H 3M 4S") == 86400 + 7200 + 180 + 4
    assert parse_duration("\t1d\n2h\r3m 4s") == 86400 + 7200 + 180 + 4

def test_parse_raises_on_empty():
    with pytest.raises(ValueError, match="empty duration"):
        parse_duration("   ")

def test_parse_raises_on_unknown_characters():
    with pytest.raises(ValueError, match=r"unexpected text: '5x'"):
        parse_duration("5x")
    # allow optional whitespace before the unexpected token
    with pytest.raises(ValueError, match=r"unexpected text: '\s*5x'"):
        parse_duration("1h 5x")

def test_parse_raises_on_repeated_units():
    with pytest.raises(ValueError, match=r"unit 'h' repeated"):
        parse_duration("1h2h")
    with pytest.raises(ValueError, match=r"unit 'd' repeated"):
        parse_duration("1d 2d")

def test_parse_raises_on_zero_total():
    with pytest.raises(ValueError, match="duration must be positive"):
        parse_duration("0s")
    with pytest.raises(ValueError, match="duration must be positive"):
        parse_duration("0d 0h")

def test_parse_ignores_extra_spaces_between_tokens():
    assert parse_duration("10   h   5   m") == 10 * UNITS["h"] + 5 * UNITS["m"]

def test_parse_detects_trailing_garbage():
    with pytest.raises(ValueError, match=r"unexpected text: '\s*abc'"):
        parse_duration("1h abc")

def test_parse_detects_leading_garbage():
    with pytest.raises(ValueError, match=r"unexpected text: '\s*xyz'"):
        parse_duration("xyz 1h")

# ---------- format_duration tests ----------

@pytest.mark.parametrize(
    "seconds,expected",
    [
        (0, "0s"),
        (1, "1s"),
        (59, "59s"),
        (60, "1m"),
        (61, "1m 1s"),
        (3600, "1h"),
        (3661, "1h 1m 1s"),
        (86400, "1d"),
        (90061, "1d 1h 1m 1s"),
        (2*86400 + 3*3600 + 4*60 + 5, "2d 3h 4m 5s"),
    ],
    ids=[
        "0s","1s","59s","60s","61s","3600s","3661s","86400s","90061s","complex"
    ],
)
def test_format_basic(seconds, expected):
    assert format_duration(seconds) == expected

def test_format_omits_zero_units():
    assert format_duration(3600 + 5) == "1h 5s"
    assert format_duration(2 * UNITS["h"]) == "2h"

def test_format_negative_raises():
    with pytest.raises(ValueError, match="negative duration"):
        format_duration(-1)

def test_format_roundtrip_fixed():
    for seconds in [0, 1, 59, 60, 61, 3599, 3600, 86400, 90061, 123456]:
        assert parse_duration(format_duration(seconds)) == seconds

# Property‑based round‑trip test
from hypothesis import given, strategies as st

@given(st.integers(min_value=0, max_value=10**6))
def test_roundtrip_hypothesis(seconds):
    formatted = format_duration(seconds)
    assert parse_duration(formatted) == seconds

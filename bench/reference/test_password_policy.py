import pytest
from password_policy import check_password, strength

GOOD = "Abcdefg1!x"


def test_good_password_passes():
    assert check_password(GOOD) == []


@pytest.mark.parametrize(("pwd", "expected"), [
    ("Abcdef1!x", ["too_short"]),
    ("ABCDEFG1!X", ["no_lower"]),
    ("abcdefg1!x", ["no_upper"]),
    ("Abcdefgh!x", ["no_digit"]),
    ("Abcdefg12x", ["no_special"]),
    ("Abc defg1!x", ["whitespace"]),
    ("Abcccdefg1!", ["repeats"]),
    ("Abccdefg1!x", []),
    ("", ["too_short", "no_lower", "no_upper", "no_digit", "no_special"]),
    ("password", ["too_short", "no_upper", "no_digit", "no_special", "common"]),
    ("PASSWORD", ["too_short", "no_lower", "no_digit", "no_special", "common"]),
    ("aaa", ["too_short", "no_upper", "no_digit", "no_special", "repeats"]),
])
def test_rules(pwd, expected):
    assert check_password(pwd) == expected


def test_repeats_at_end_of_string():
    assert check_password("Abcdefg1!xxx") == ["repeats"]


def test_custom_min_length():
    assert check_password("Ab1!", min_length=4) == []
    assert check_password("Ab1!", min_length=5) == ["too_short"]


@pytest.mark.parametrize("special", list("!@#$%^&*()-_=+[]{};:,.?/"))
def test_each_special_char_counts(special):
    assert "no_special" not in check_password("Abcdefgh1" + special)


@pytest.mark.parametrize(("pwd", "expected"), [
    (GOOD, "strong"),
    ("Abcdef1!x", "medium"),
    ("abcdef1!x", "medium"),
    ("abcdef1xx", "weak"),
    ("", "weak"),
])
def test_strength(pwd, expected):
    assert strength(pwd) == expected


def test_alternating_chars_are_not_repeats():
    assert check_password("Abcbdefg1!") == []

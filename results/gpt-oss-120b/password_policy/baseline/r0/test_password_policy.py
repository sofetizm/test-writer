import pytest
from password_policy import check_password, strength

# Helper that disables the length check unless explicitly needed
def assert_problems(password, expected, *, min_length=0):
    """Assert that check_password returns exactly the expected list of problems."""
    assert check_password(password, min_length=min_length) == expected


# ----------------------------------------------------------------------
# Individual rule tests (length check disabled)
# ----------------------------------------------------------------------
def test_missing_lowercase():
    # No lowercase letters
    assert_problems("ABCDEF123!", ["no_lower"], min_length=0)


def test_missing_uppercase():
    # No uppercase letters
    assert_problems("abcdef123!", ["no_upper"], min_length=0)


def test_missing_digit():
    # No digits at all
    assert_problems("AbcdefGh!@", ["no_digit"], min_length=0)


def test_missing_special():
    # No special characters from the defined set
    assert_problems("AbcdefGh12", ["no_special"], min_length=0)


def test_whitespace():
    # Contains a space, should trigger only the whitespace rule (length disabled)
    assert_problems("Abcdef Gh1!", ["whitespace"], min_length=0)


def test_repeats_simple():
    # Three identical characters in a row
    assert_problems("Abc111def!", ["repeats"], min_length=0)


def test_repeats_overlapping():
    # Overlapping repeats (e.g., "aaa") should still be reported once
    assert_problems("AaAaaaB1!", ["repeats"], min_length=0)


def test_common_password_case_insensitive():
    # Common passwords are detected case‑insensitively
    assert_problems("PaSsWoRd", ["common"], min_length=0)


# ----------------------------------------------------------------------
# Length‑related tests (use default min_length=10)
# ----------------------------------------------------------------------
def test_too_short():
    # Shorter than the default minimum length (10)
    assert_problems("Abc1!", ["too_short"], min_length=10)


def test_multiple_issues_including_length():
    # Fails length, digit and special checks
    assert_problems("AbcdefGh", ["too_short", "no_digit", "no_special"], min_length=10)


# ----------------------------------------------------------------------
# Strength classification tests
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "pwd,expected",
    [
        # Strong: no problems
        ("AbcdefGh1!", "strong"),
        # Medium: exactly one problem (missing special)
        ("AbcdefGh12", "medium"),
        # Medium: exactly two problems (missing digit and special)
        ("AbcdefGh!!", "medium"),
        # Weak: three or more problems (too short, missing digit, missing special)
        ("Abc1!", "weak"),
        # Weak: three problems (whitespace, missing digit, missing special)
        ("Abc def!", "weak"),
    ],
)
def test_strength_classification(pwd, expected):
    assert strength(pwd) == expected

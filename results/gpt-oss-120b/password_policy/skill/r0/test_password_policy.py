# tests/test_password_policy.py
import pytest
from password_policy import check_password, strength, COMMON, SPECIAL

def make_password(
    *,
    base: str = "Aa1!",
    length: int = 10,
    add_special: bool = True,
    add_lower: bool = True,
    add_upper: bool = True,
    add_digit: bool = True,
    whitespace: str = "",
    repeats: str = "",
) -> str:
    """Create a password that satisfies the policy, then optionally tweak it."""
    pwd = base
    if not add_lower:
        pwd = pwd.replace("a", "A")
    if not add_upper:
        pwd = pwd.replace("A", "a")
    if not add_digit:
        pwd = pwd.replace("1", "b")
    if not add_special:
        pwd = pwd.replace("!", "b")
    pwd += whitespace + repeats
    if len(pwd) < length:
        pwd += "b" * (length - len(pwd))
    return pwd


@pytest.mark.parametrize(
    "password,expected",
    [
        ("Aa1!bbbbbb", ["repeats"]),  # three b's in a row
        ("Aa1!   ", ["too_short", "whitespace", "repeats"]),  # short, whitespace, repeats
        ("aaaaaaaaaa", ["no_upper", "no_digit", "no_special", "repeats", "common"]),  # common lower
        ("AAAAAAAAAA", ["no_lower", "no_digit", "no_special", "repeats", "common"]),  # common upper
        ("1234567890", ["no_lower", "no_upper", "no_special", "repeats", "common"]),  # common digits
        ("Password1!", []),  # valid, not in COMMON
        ("admin123", ["too_short", "no_upper", "no_special", "common"]),  # common and short
    ],
    ids=[
        "repeats",
        "short+whitespace",
        "common_lower",
        "common_upper",
        "common_digits",
        "valid",
        "common_short",
    ],
)
def test_check_password_various_issues(password, expected):
    """Each rule should be reported correctly and in order."""
    assert check_password(password) == expected


def test_check_password_all_rules_pass():
    """A fully compliant password returns an empty list."""
    pwd = make_password(length=12)
    assert check_password(pwd) == []


def test_check_password_order_of_issues():
    """Multiple issues must appear in the documented order."""
    pwd = "   "  # whitespace, too short, no lower, no upper, no digit, no special
    expected = ["too_short", "no_lower", "no_upper", "no_digit", "no_special", "whitespace"]
    assert check_password(pwd) == expected


@pytest.mark.parametrize(
    "violations,expected_strength",
    [
        (0, "strong"),
        (1, "medium"),
        (2, "medium"),
        (3, "weak"),
        (4, "weak"),
    ],
    ids=["0", "1", "2", "3", "4"],
)
def test_strength_based_on_number_of_violations(violations, expected_strength):
    """strength() maps the count of distinct rule violations to the correct label."""
    pwd = make_password(length=12)
    # Functions that introduce a new distinct problem
    breakers = [
        lambda p: p.lower(),                     # break no_upper
        lambda p: p.upper(),                     # break no_lower
        lambda p: p.replace("1", "b"),           # break no_digit
        lambda p: p + " ",                       # add whitespace
        lambda p: p + "aaa",                     # add repeats
        lambda p: list(COMMON)[0],               # common password
        lambda p: p.replace("!", "b"),           # break no_special
    ]
    applied = 0
    for br in breakers:
        if applied >= violations:
            break
        new_pwd = br(pwd)
        if set(check_password(new_pwd)) != set(check_password(pwd)):
            pwd = new_pwd
            applied += 1
    # Ensure we hit the intended number of distinct violations
    assert len(check_password(pwd)) == violations
    assert strength(pwd) == expected_strength


def test_strength_weak_when_three_or_more_issues():
    """Boundary test: three distinct violations yields 'weak'."""
    pwd = make_password(length=12, add_special=False)  # missing special -> 1 issue
    pwd = pwd + "   "  # whitespace -> 2 issues
    pwd = pwd + "aaa"  # repeats -> 3 issues
    problems = check_password(pwd)
    assert "no_special" in problems
    assert "whitespace" in problems
    assert "repeats" in problems
    assert strength(pwd) == "weak"


def test_common_password_detection_is_case_insensitive():
    """Common passwords should be flagged regardless of case."""
    for common in COMMON:
        pwd = common.upper() + "Aa1!"  # ensure length >= min_length
        assert "common" in check_password(pwd)


def test_special_characters_set_contains_expected_symbols():
    """Validate that SPECIAL set includes typical punctuation."""
    for ch in "!@#$%^&*()-_=+[]{};:,.?/":
        assert ch in SPECIAL

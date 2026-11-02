import pytest
from semver import parse, compare, bump

# ---------- parse ----------
@pytest.mark.parametrize(
    "version,expected",
    [
        ("0.0.0", (0, 0, 0, ())),
        ("1.2.3", (1, 2, 3, ())),
        ("10.20.30", (10, 20, 30, ())),
        ("1.2.3-alpha", (1, 2, 3, ("alpha",))),
        ("1.2.3-1.2beta.3", (1, 2, 3, (1, "2beta", 3))),
        ("  2.3.4-rc.1  ", (2, 3, 4, ("rc", 1))),
    ],
)
def test_parse_various(version, expected):
    assert parse(version) == expected


def test_parse_invalid():
    with pytest.raises(ValueError, match="invalid version"):
        parse("not.a.version")
    with pytest.raises(ValueError, match="invalid version"):
        parse("1.2")          # missing patch
    with pytest.raises(ValueError, match="invalid version"):
        parse("1.2.3-")       # dangling hyphen


# ---------- compare ----------
@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("1.2.3", "1.2.3", 0),
        ("1.2.3", "1.2.4", -1),
        ("2.0.0", "1.9.9", 1),
        ("1.2.3-alpha", "1.2.3-beta", -1),
        ("1.2.3-beta", "1.2.3-alpha", 1),
        ("1.2.3-alpha.1", "1.2.3-alpha", 1),
    ],
)
def test_compare_various(a, b, expected):
    assert compare(a, b) == expected


def test_compare_prerelease_vs_release():
    assert compare("1.0.0-alpha", "1.0.0") == -1
    assert compare("1.0.0", "1.0.0-alpha") == 1


def test_compare_numeric_vs_alpha():
    # numeric identifiers sort before alphanumeric ones
    assert compare("1.0.0-1", "1.0.0-alpha") == -1
    assert compare("1.0.0-alpha", "1.0.0-1") == 1


def test_compare_multiple_identifiers():
    # compare each identifier in order
    assert compare("1.0.0-1.2", "1.0.0-1.10") == -1
    assert compare("1.0.0-1.10", "1.0.0-1.2") == 1
    # alphanumeric after numeric
    assert compare("1.0.0-1.alpha", "1.0.0-1.0") == 1


def test_compare_strict_equality():
    # same prerelease strings are equal
    assert compare("1.0.0-alpha", "1.0.0-alpha") == 0
    # longer prerelease is greater
    assert compare("1.0.0-alpha", "1.0.0-alpha.0") == -1


def test_compare_all_components():
    base = "2.5.3-alpha.1"
    assert compare(base, "3.0.0") == -1   # major higher
    assert compare(base, "2.6.0") == -1   # minor higher
    assert compare(base, "2.5.4") == -1   # patch higher
    assert compare(base, "2.5.3-alpha.2") == -1  # prerelease higher


# ---------- bump ----------
@pytest.mark.parametrize(
    "original,part,expected",
    [
        ("0.0.0", "major", "1.0.0"),
        ("1.2.3", "major", "2.0.0"),
        ("1.2.3", "minor", "1.3.0"),
        ("1.2.3", "patch", "1.2.4"),
        ("1.2.3-rc.1", "major", "2.0.0"),
        ("1.2.3-rc.1", "minor", "1.3.0"),
        ("1.2.3-rc.1", "patch", "1.2.4"),
    ],
)
def test_bump_basic(original, part, expected):
    assert bump(original, part) == expected


def test_bump_invalid_part():
    with pytest.raises(ValueError, match="unknown part"):
        bump("1.2.3", "foo")


# ---------- edge cases for numeric parsing ----------
def test_parse_numeric_boundary():
    version = "9.8.7"
    major, minor, patch, pre = parse(version)
    assert (major, minor, patch) == (9, 8, 7)
    assert pre == ()


# ---------- ensure prerelease handling ----------
def test_prerelease_vs_no_prerelease():
    # version without prerelease is greater than any with prerelease
    assert compare("1.0.0", "1.0.0-0") == 1
    assert compare("1.0.0-0", "1.0.0-0") == 0

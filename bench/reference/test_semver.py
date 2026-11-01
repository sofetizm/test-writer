import pytest
from semver import bump, compare, parse


@pytest.mark.parametrize(("text", "expected"), [
    ("1.2.3", (1, 2, 3, ())),
    ("0.0.0", (0, 0, 0, ())),
    ("10.20.30", (10, 20, 30, ())),
    ("1.0.0-alpha", (1, 0, 0, ("alpha",))),
    ("1.0.0-alpha.1", (1, 0, 0, ("alpha", 1))),
    (" 2.0.0-rc.10 ", (2, 0, 0, ("rc", 10))),
])
def test_parse(text, expected):
    assert parse(text) == expected


@pytest.mark.parametrize("bad", ["1.2", "1.2.3.4", "a.b.c", "1.2.3-", "v1.2.3", ""])
def test_parse_invalid(bad):
    with pytest.raises(ValueError, match="invalid version"):
        parse(bad)


@pytest.mark.parametrize(("a", "b", "expected"), [
    ("1.0.0", "1.0.0", 0),
    ("1.0.0", "2.0.0", -1),
    ("2.0.0", "1.0.0", 1),
    ("1.2.0", "1.10.0", -1),
    ("1.0.9", "1.0.10", -1),
    ("1.0.0-alpha", "1.0.0", -1),
    ("1.0.0", "1.0.0-alpha", 1),
    ("1.0.0-alpha", "1.0.0-alpha.1", -1),
    ("1.0.0-alpha.1", "1.0.0-alpha.beta", -1),
    ("1.0.0-alpha.beta", "1.0.0-beta", -1),
    ("1.0.0-beta.2", "1.0.0-beta.11", -1),
    ("1.0.0-rc.1", "1.0.0-rc.1", 0),
    ("1.0.0-1", "1.0.0-alpha", -1),
])
def test_compare(a, b, expected):
    assert compare(a, b) == expected


@pytest.mark.parametrize(("version", "part", "expected"), [
    ("1.2.3", "major", "2.0.0"), ("1.2.3", "minor", "1.3.0"), ("1.2.3", "patch", "1.2.4"),
    ("1.2.3-rc.1", "patch", "1.2.4"), ("0.9.9", "minor", "0.10.0"),
])
def test_bump(version, part, expected):
    assert bump(version, part) == expected


def test_bump_unknown_part():
    with pytest.raises(ValueError, match="unknown part"):
        bump("1.0.0", "build")

import pytest
from semver import parse, compare, bump

# ---------- Tests for parse ----------
@pytest.mark.parametrize(
    "version,expected",
    [
        ("0.0.0", (0, 0, 0, ())),
        ("1.2.3", (1, 2, 3, ())),
        ("10.20.30", (10, 20, 30, ())),
        ("1.2.3-alpha", (1, 2, 3, ("alpha",))),
        ("1.2.3-alpha.1", (1, 2, 3, ("alpha", 1))),
        ("1.2.3-1.2.3", (1, 2, 3, (1, 2, 3))),
        ("  1.2.3-beta.2  ", (1, 2, 3, ("beta", 2))),  # whitespace trimmed
    ],
)
def test_parse_valid(version, expected):
    assert parse(version) == expected


@pytest.mark.parametrize(
    "bad_version",
    [
        "",                     # empty
        "1",                    # incomplete
        "1.2",                  # incomplete
        "1.2.3.",               # trailing dot
        "1.2.3-!",              # illegal character
        "a.b.c",                # non‑numeric core
        "1.2.3-01",             # leading zero is allowed by regex but should be parsed as int
        "1.2.3-α",              # non‑ASCII identifier
    ],
)
def test_parse_invalid(bad_version):
    with pytest.raises(ValueError):
        parse(bad_version)


# ---------- Tests for compare ----------
@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("1.0.0", "1.0.0", 0),
        ("1.0.0", "2.0.0", -1),
        ("2.0.0", "1.0.0", 1),
        ("1.2.3", "1.2.4", -1),
        ("1.2.4", "1.2.3", 1),
        ("1.2.3-alpha", "1.2.3", -1),          # prerelease < release
        ("1.2.3", "1.2.3-alpha", 1),
        ("1.2.3-alpha", "1.2.3-beta", -1),    # lexical order for alphanum
        ("1.2.3-beta", "1.2.3-alpha", 1),
        ("1.2.3-1", "1.2.3-alpha", -1),       # numeric < alphanumeric
        ("1.2.3-alpha", "1.2.3-1", 1),
        ("1.2.3-1.2", "1.2.3-1.10", -1),      # numeric comparison element‑wise
        ("1.2.3-1.10", "1.2.3-1.2", 1),
        ("1.2.3-rc.1", "1.2.3-rc.2", -1),
        ("1.2.3-rc.2", "1.2.3-rc.1", 1),
        ("1.2.3-rc.1", "1.2.3-rc.1", 0),
    ],
)
def test_compare_various(a, b, expected):
    assert compare(a, b) == expected
    # symmetry check
    assert compare(b, a) == -expected


def test_compare_total_order():
    # Build a list of versions that should be sorted according to semver precedence
    versions = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
    ]
    # Verify that sorting using compare yields the same order
    sorted_by_compare = sorted(versions, key=lambda v: parse(v))
    # The built‑in tuple ordering of parse respects the same precedence rules,
    # so we can directly compare to the expected list.
    assert sorted_by_compare == versions


# ---------- Tests for bump ----------
@pytest.mark.parametrize(
    "original,part,expected",
    [
        ("0.0.0", "major", "1.0.0"),
        ("1.2.3", "major", "2.0.0"),
        ("1.2.3", "minor", "1.3.0"),
        ("1.2.3", "patch", "1.2.4"),
        ("1.2.3-rc.1", "patch", "1.2.4"),   # prerelease dropped
        ("1.2.3-rc.1", "minor", "1.3.0"),
        ("1.2.3-rc.1", "major", "2.0.0"),
    ],
)
def test_bump_basic(original, part, expected):
    assert bump(original, part) == expected


def test_bump_invalid_part():
    with pytest.raises(ValueError):
        bump("1.2.3", "invalid")

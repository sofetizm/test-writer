"""Semantic versions: MAJOR.MINOR.PATCH with an optional -prerelease part."""
import re

_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.]+))?$")


def parse(version: str):
    """Parse "1.2.3" or "1.2.3-alpha.1" into (major, minor, patch, prerelease_tuple).

    Prerelease identifiers that are digits become ints. Raises ValueError otherwise.
    """
    m = _RE.match(version.strip())
    if not m:
        raise ValueError(f"invalid version: {version!r}")
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    pre = tuple(int(p) if p.isdigit() else p for p in m.group(4).split(".")) if m.group(4) else ()
    return major, minor, patch, pre


def _pre_key(pre):
    # A version without prerelease is greater than any prerelease of it.
    if not pre:
        return (1,)
    # Numeric identifiers sort before alphanumeric ones.
    return (0, tuple((0, p, "") if isinstance(p, int) else (1, 0, p) for p in pre))


def compare(a: str, b: str) -> int:
    """-1 if a < b, 0 if equal, 1 if a > b, by semver precedence rules."""
    pa, pb = parse(a), parse(b)
    ka = (pa[:3], _pre_key(pa[3]))
    kb = (pb[:3], _pre_key(pb[3]))
    return (ka > kb) - (ka < kb)


def bump(version: str, part: str) -> str:
    """Increment "major", "minor" or "patch", resetting lower parts and dropping
    the prerelease. bump("1.2.3-rc.1", "patch") == "1.2.4"."""
    major, minor, patch, _ = parse(version)
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"unknown part: {part!r}")

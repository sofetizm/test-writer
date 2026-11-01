"""Parse and format human-readable durations such as "1h30m" or "2d 4h"."""
import re

UNITS = {"d": 86400, "h": 3600, "m": 60, "s": 1}
_TOKEN = re.compile(r"(\d+)\s*([dhms])")


def parse_duration(text: str) -> int:
    """Return the total number of seconds in `text`.

    Units: d, h, m, s, in any order, optionally separated by spaces ("1h 30m").
    Each unit may appear at most once. Raises ValueError for empty input,
    unknown characters, repeated units or a total of zero seconds.
    """
    cleaned = text.strip().lower()
    if not cleaned:
        raise ValueError("empty duration")
    total = 0
    seen = set()
    pos = 0
    for match in _TOKEN.finditer(cleaned):
        if cleaned[pos:match.start()].strip():
            raise ValueError(f"unexpected text: {cleaned[pos:match.start()]!r}")
        value, unit = int(match.group(1)), match.group(2)
        if unit in seen:
            raise ValueError(f"unit {unit!r} repeated")
        seen.add(unit)
        total += value * UNITS[unit]
        pos = match.end()
    if cleaned[pos:].strip():
        raise ValueError(f"unexpected text: {cleaned[pos:]!r}")
    if total == 0:
        raise ValueError("duration must be positive")
    return total


def format_duration(seconds: int) -> str:
    """Format seconds as "1d 2h 3m 4s", omitting zero units. 0 -> "0s".

    Raises ValueError for negative input.
    """
    if seconds < 0:
        raise ValueError("negative duration")
    if seconds == 0:
        return "0s"
    parts = []
    for unit, size in UNITS.items():
        amount, seconds = divmod(seconds, size)
        if amount:
            parts.append(f"{amount}{unit}")
    return " ".join(parts)

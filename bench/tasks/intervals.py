"""Operations on closed integer intervals [start, end]."""


def _check(interval):
    start, end = interval
    if start > end:
        raise ValueError(f"invalid interval {interval}: start > end")


def merge(intervals):
    """Merge overlapping or touching intervals ([1, 3] + [3, 5] -> [1, 5];
    [1, 2] + [3, 4] -> [1, 4] because integer intervals are adjacent).

    Input order does not matter; the result is sorted by start. The input list
    is not modified.
    """
    for iv in intervals:
        _check(iv)
    result = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1] + 1:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return [tuple(iv) for iv in result]


def total_length(intervals):
    """Number of distinct integers covered by the intervals ([1, 3] covers 3)."""
    return sum(end - start + 1 for start, end in merge(intervals))


def intersect(a, b):
    """Intersection of two intervals, or None if they do not overlap."""
    _check(a)
    _check(b)
    start = max(a[0], b[0])
    end = min(a[1], b[1])
    if start > end:
        return None
    return (start, end)

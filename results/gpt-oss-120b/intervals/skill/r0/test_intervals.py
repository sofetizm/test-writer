import pytest
from intervals import merge, total_length, intersect

# ---------- merge ----------
@pytest.mark.parametrize(
    "intervals,expected",
    [
        ([], []),
        ([(1, 3)], [(1, 3)]),
        ([(1, 3), (5, 7)], [(1, 3), (5, 7)]),  # disjoint
        ([(1, 3), (3, 5)], [(1, 5)]),          # touching at a point
        ([(1, 2), (3, 4)], [(1, 4)]),          # adjacent integers
        ([(5, 7), (1, 3)], [(1, 3), (5, 7)]),  # order independence
        ([(1, 4), (2, 6), (8, 10), (9, 12)], [(1, 6), (8, 12)]),  # overlapping groups
        ([(1, 10), (2, 3), (4, 5)], [(1, 10)]),  # inner intervals
        ([(0, 0), (1, 1), (2, 2)], [(0, 2)]),  # singletons adjacent -> merge
        ([(0, 0), (1, 1)], [(0, 1)]),          # singletons adjacent -> merge
        ([(1, 3), (2, 5)], [(1, 5)]),          # later interval extends end
    ],
    ids=lambda val: str(val),
)
def test_merge_various(intervals, expected):
    # Ensure original list is not mutated
    original = list(intervals)
    result = merge(intervals)
    assert result == expected
    assert intervals == original  # input unchanged


def test_merge_invalid_interval():
    with pytest.raises(ValueError, match="invalid interval"):
        merge([(5, 3)])  # start > end


# ---------- total_length ----------
@pytest.mark.parametrize(
    "intervals,expected",
    [
        ([], 0),
        ([(1, 3)], 3),
        ([(1, 3), (5, 7)], 6),
        ([(1, 3), (3, 5)], 5),   # merged to (1,5) => 5 integers
        ([(0, 0), (1, 1), (2, 2)], 3),  # merged to (0,2)
        ([(0, 2), (4, 4)], 4),   # 0-2 (3) + 4 (1) = 4
    ],
)
def test_total_length(intervals, expected):
    assert total_length(intervals) == expected


# ---------- intersect ----------
@pytest.mark.parametrize(
    "a,b,expected",
    [
        ((1, 5), (3, 7), (3, 5)),
        ((1, 2), (3, 4), None),
        ((5, 5), (5, 5), (5, 5)),
        ((-3, 0), (-1, 2), (-1, 0)),
    ],
    ids=lambda val: str(val),
)
def test_intersect_various(a, b, expected):
    assert intersect(a, b) == expected


def test_intersect_invalid():
    with pytest.raises(ValueError, match="invalid interval"):
        intersect((5, 3), (1, 2))
    with pytest.raises(ValueError, match="invalid interval"):
        intersect((1, 2), (5, 3))

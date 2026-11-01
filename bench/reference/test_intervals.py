import pytest
from intervals import intersect, merge, total_length


@pytest.mark.parametrize(("given", "expected"), [
    ([], []),
    ([(1, 3)], [(1, 3)]),
    ([(1, 3), (2, 5)], [(1, 5)]),
    ([(1, 3), (3, 5)], [(1, 5)]),
    ([(1, 2), (3, 4)], [(1, 4)]),
    ([(1, 2), (4, 5)], [(1, 2), (4, 5)]),
    ([(5, 6), (1, 2)], [(1, 2), (5, 6)]),
    ([(1, 10), (2, 3)], [(1, 10)]),
    ([(4, 4), (1, 1), (2, 2)], [(1, 2), (4, 4)]),
    ([(-5, -3), (-2, 0)], [(-5, 0)]),
])
def test_merge(given, expected):
    assert merge(given) == expected


def test_merge_returns_tuples_and_keeps_input():
    data = [(3, 4), (1, 2)]
    result = merge(data)
    assert data == [(3, 4), (1, 2)]
    assert all(type(iv) is tuple for iv in result)


def test_merge_rejects_invalid():
    with pytest.raises(ValueError, match="start > end"):
        merge([(1, 2), (5, 4)])


def test_merge_accepts_single_point():
    assert merge([(2, 2)]) == [(2, 2)]


@pytest.mark.parametrize(("given", "expected"), [
    ([], 0), ([(1, 1)], 1), ([(1, 3)], 3), ([(1, 3), (2, 4)], 4), ([(1, 2), (5, 6)], 4),
])
def test_total_length(given, expected):
    assert total_length(given) == expected


@pytest.mark.parametrize(("a", "b", "expected"), [
    ((1, 5), (3, 8), (3, 5)),
    ((3, 8), (1, 5), (3, 5)),
    ((1, 3), (3, 6), (3, 3)),
    ((1, 2), (3, 4), None),
    ((1, 10), (4, 6), (4, 6)),
])
def test_intersect(a, b, expected):
    assert intersect(a, b) == expected


@pytest.mark.parametrize(("a", "b"), [((2, 1), (1, 3)), ((1, 3), (5, 4))])
def test_intersect_rejects_invalid(a, b):
    with pytest.raises(ValueError):
        intersect(a, b)


def test_merge_into_last_of_several():
    assert merge([(1, 2), (5, 6), (6, 8)]) == [(1, 2), (5, 8)]
    assert merge([(1, 2), (5, 9), (6, 7)]) == [(1, 2), (5, 9)]
    assert merge([(1, 2), (5, 6), (7, 8)]) == [(1, 2), (5, 8)]

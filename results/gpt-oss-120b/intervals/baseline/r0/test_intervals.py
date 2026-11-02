import pytest
from intervals import merge, total_length, intersect, _check

# ----------------------------------------------------------------------
# Tests for the internal validator _check
def test_check_valid_and_invalid():
    # Valid intervals should not raise
    for iv in [(0, 0), (-5, 5), (10, 20)]:
        _check(iv)  # no exception

    # Invalid intervals must raise ValueError
    with pytest.raises(ValueError):
        _check((5, 4))
    with pytest.raises(ValueError):
        _check((10, -1))


# ----------------------------------------------------------------------
# Tests for merge
@pytest.mark.parametrize(
    "input_intervals, expected",
    [
        # Empty input
        ([], []),
        # Single interval stays unchanged
        ([(1, 3)], [(1, 3)]),
        # Non‑overlapping, non‑adjacent intervals stay separate
        ([(1, 2), (4, 5)], [(1, 2), (4, 5)]),
        # Adjacent intervals are merged (integer adjacency)
        ([(1, 2), (3, 4)], [(1, 4)]),
        # Overlapping intervals are merged
        ([(1, 5), (3, 7)], [(1, 7)]),
        # Mixed overlapping and adjacent intervals – all become one because they chain together
        ([(5, 8), (1, 3), (4, 4), (9, 10)], [(1, 10)]),
        # Unordered input must be sorted in result
        ([(10, 12), (1, 3), (5, 7)], [(1, 3), (5, 7), (10, 12)]),
        # Touching at a single point (e.g., [1,3] and [5,6]) are NOT merged because they are not adjacent integers
        ([(1, 3), (5, 6)], [(1, 3), (5, 6)]),
        # Large range with many small intervals
        ([(0, 0), (1, 1), (2, 2), (3, 5)], [(0, 5)]),
    ],
)
def test_merge_various_cases(input_intervals, expected):
    # Ensure original list is not mutated
    original = list(input_intervals)
    result = merge(input_intervals)
    assert result == expected
    assert input_intervals == original


def test_merge_invalid_interval_raises():
    with pytest.raises(ValueError):
        merge([(5, 3), (1, 2)])


# ----------------------------------------------------------------------
# Tests for total_length
@pytest.mark.parametrize(
    "intervals, expected_len",
    [
        ([], 0),
        ([(1, 3)], 3),                     # 1,2,3
        ([(1, 2), (4, 5)], 4),             # 1,2,4,5
        ([(1, 2), (3, 5)], 5),             # merged to (1,5) => 5 numbers
        ([(0, 0), (2, 2), (4, 4)], 3),     # three isolated points
        ([(1, 10), (5, 15)], 15),          # merged to (1,15)
        ([(1, 1), (2, 2), (3, 3)], 3),     # consecutive points become one interval
    ],
)
def test_total_length(intervals, expected_len):
    assert total_length(intervals) == expected_len


# ----------------------------------------------------------------------
# Tests for intersect
def test_intersect_basic():
    assert intersect((1, 5), (3, 7)) == (3, 5)
    assert intersect((1, 3), (4, 6)) is None
    assert intersect((5, 5), (5, 10)) == (5, 5)
    assert intersect((-10, -5), (-8, -3)) == (-8, -5)


def test_intersect_invalid_raises():
    with pytest.raises(ValueError):
        intersect((5, 3), (1, 2))
    with pytest.raises(ValueError):
        intersect((1, 2), (4, 3))


# ----------------------------------------------------------------------
# Property‑based tests using hypothesis
from hypothesis import given, strategies as st

@given(
    st.lists(
        st.tuples(
            st.integers(min_value=-1000, max_value=1000),
            st.integers(min_value=-1000, max_value=1000),
        ),
        min_size=0,
        max_size=20,
    )
)
def test_merge_idempotent_and_sorted(intervals):
    # Keep only valid intervals for the function under test
    valid = [iv for iv in intervals if iv[0] <= iv[1]]
    merged = merge(valid)

    # 1. Result must be sorted by start
    starts = [iv[0] for iv in merged]
    assert starts == sorted(starts)

    # 2. Merging again yields the same list (idempotence)
    assert merge(merged) == merged

    # 3. No overlapping or adjacent intervals remain
    for i in range(len(merged) - 1):
        a = merged[i]
        b = merged[i + 1]
        assert a[1] + 1 < b[0]  # at least one integer gap


@given(
    st.lists(
        st.tuples(st.integers(), st.integers()),
        min_size=0,
        max_size=10,
    )
)
def test_total_length_consistency_with_merge(intervals):
    valid = [iv for iv in intervals if iv[0] <= iv[1]]
    merged = merge(valid)
    expected = sum(end - start + 1 for start, end in merged)
    assert total_length(valid) == expected

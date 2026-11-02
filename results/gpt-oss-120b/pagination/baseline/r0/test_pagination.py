import pytest
from pagination import paginate
from hypothesis import given, strategies as st

# Basic deterministic tests covering typical scenarios and edge cases
def test_basic_pagination():
    meta = paginate(total=95, page=1, per_page=20)
    assert meta["page"] == 1
    assert meta["pages"] == 5  # 95/20 -> 5 pages (last page has 15 items)
    assert meta["per_page"] == 20
    assert meta["offset"] == 0
    assert meta["has_prev"] is False
    assert meta["has_next"] is True

def test_last_page():
    meta = paginate(total=95, page=5, per_page=20)
    assert meta["page"] == 5
    assert meta["pages"] == 5
    assert meta["offset"] == 80
    assert meta["has_prev"] is True
    assert meta["has_next"] is False

def test_page_clamping():
    # Requesting a page beyond the last should clamp to the last page
    meta = paginate(total=30, page=10, per_page=10)
    assert meta["page"] == 3  # only 3 pages exist
    assert meta["pages"] == 3
    assert meta["has_next"] is False

def test_zero_total():
    meta = paginate(total=0, page=1, per_page=10)
    assert meta["pages"] == 1
    assert meta["page"] == 1
    assert meta["offset"] == 0
    assert meta["has_prev"] is False
    assert meta["has_next"] is False

def test_per_page_capped_by_max():
    meta = paginate(total=500, page=1, per_page=150, max_per_page=100)
    assert meta["per_page"] == 100
    assert meta["pages"] == 5  # 500/100
    assert meta["offset"] == 0

def test_invalid_arguments():
    with pytest.raises(ValueError):
        paginate(total=-1, page=1)
    with pytest.raises(ValueError):
        paginate(total=10, page=0)
    with pytest.raises(ValueError):
        paginate(total=10, page=1, per_page=0)

# Property‑based tests using hypothesis
@given(
    total=st.integers(min_value=0, max_value=10_000),
    per_page=st.integers(min_value=1, max_value=200),
    max_per_page=st.integers(min_value=1, max_value=200),
    page_offset=st.integers(min_value=0, max_value=50),
)
def test_hypothesis_properties(total, per_page, max_per_page, page_offset):
    # Ensure per_page is respected and capped
    capped = min(per_page, max_per_page)
    pages = max(1, -(-total // capped))

    # Choose a page number possibly out of range to test clamping
    page = 1 + page_offset
    meta = paginate(total=total, page=page, per_page=per_page, max_per_page=max_per_page)

    # Page should be clamped to [1, pages]
    assert 1 <= meta["page"] <= pages
    assert meta["pages"] == pages
    assert meta["per_page"] == capped

    # Offset must equal (page-1)*per_page
    assert meta["offset"] == (meta["page"] - 1) * capped

    # Navigation flags consistency
    assert meta["has_prev"] == (meta["page"] > 1)
    assert meta["has_next"] == (meta["page"] < pages)

    # When total is zero, there is exactly one empty page
    if total == 0:
        assert meta["pages"] == 1
        assert meta["page"] == 1
        assert meta["offset"] == 0
        assert meta["has_prev"] is False
        assert meta["has_next"] is False

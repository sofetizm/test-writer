import pytest
from pagination import paginate

# Helper to compute expected pagination manually
def manual_paginate(total, page, per_page, max_per_page):
    if total < 0:
        raise ValueError("total must not be negative")
    if page < 1:
        raise ValueError("page must be at least 1")
    if per_page < 1:
        raise ValueError("per_page must be at least 1")
    per_page = min(per_page, max_per_page)
    pages = max(1, -(-total // per_page))
    page = min(page, pages)
    return {
        "page": page,
        "pages": pages,
        "per_page": per_page,
        "offset": (page - 1) * per_page,
        "has_prev": page > 1,
        "has_next": page < pages,
    }

@pytest.mark.parametrize(
    "total, page, per_page, max_per_page, expected",
    [
        (0, 1, 20, 100, {"page": 1, "pages": 1, "per_page": 20, "offset": 0, "has_prev": False, "has_next": False}),
        (5, 1, 2, 100, {"page": 1, "pages": 3, "per_page": 2, "offset": 0, "has_prev": False, "has_next": True}),
        (5, 2, 2, 100, {"page": 2, "pages": 3, "per_page": 2, "offset": 2, "has_prev": True, "has_next": True}),
        (5, 3, 2, 100, {"page": 3, "pages": 3, "per_page": 2, "offset": 4, "has_prev": True, "has_next": False}),
        (5, 10, 2, 100, {"page": 3, "pages": 3, "per_page": 2, "offset": 4, "has_prev": True, "has_next": False}),
        (50, 1, 30, 100, {"page": 1, "pages": 2, "per_page": 30, "offset": 0, "has_prev": False, "has_next": True}),
        (50, 2, 30, 100, {"page": 2, "pages": 2, "per_page": 30, "offset": 30, "has_prev": True, "has_next": False}),
        (50, 3, 30, 100, {"page": 2, "pages": 2, "per_page": 30, "offset": 30, "has_prev": True, "has_next": False}),
        # per_page exceeding max_per_page
        (250, 1, 150, 100, {"page": 1, "pages": 3, "per_page": 100, "offset": 0, "has_prev": False, "has_next": True}),
        (250, 2, 150, 100, {"page": 2, "pages": 3, "per_page": 100, "offset": 100, "has_prev": True, "has_next": True}),
        (250, 3, 150, 100, {"page": 3, "pages": 3, "per_page": 100, "offset": 200, "has_prev": True, "has_next": False}),
    ],
    ids=lambda val: str(val),
)
def test_paginate_various_cases(total, page, per_page, max_per_page, expected):
    result = paginate(total, page, per_page, max_per_page)
    assert result == expected

def test_default_parameters():
    # defaults: per_page=20, max_per_page=100
    result = paginate(45, 2)  # page 2, default per_page
    expected = manual_paginate(45, 2, 20, 100)
    assert result == expected

@pytest.mark.parametrize(
    "total, page, per_page, max_per_page, error_msg",
    [
        (-1, 1, 20, 100, "total must not be negative"),
        (10, 0, 20, 100, "page must be at least 1"),
        (10, 1, 0, 100, "per_page must be at least 1"),
    ],
    ids=lambda val: str(val),
)
def test_invalid_arguments_raise(total, page, per_page, max_per_page, error_msg):
    with pytest.raises(ValueError, match=error_msg):
        paginate(total, page, per_page, max_per_page)

def test_per_page_of_one_is_allowed():
    # This checks the mutant where per_page < 1 is changed to <= 1
    result = paginate(3, 1, per_page=1, max_per_page=100)
    expected = {
        "page": 1,
        "pages": 3,
        "per_page": 1,
        "offset": 0,
        "has_prev": False,
        "has_next": True,
    }
    assert result == expected

def test_offset_and_navigation_flags_consistency():
    # Random sample of values to ensure offset matches page and per_page
    for total, per_page in [(23, 5), (100, 20), (7, 3)]:
        pages = max(1, -(-total // per_page))
        for page in range(1, pages + 1):
            result = paginate(total, page, per_page)
            assert result["offset"] == (page - 1) * result["per_page"]
            assert result["has_prev"] == (page > 1)
            assert result["has_next"] == (page < pages)

import pytest
from pagination import paginate


def test_first_page():
    assert paginate(45, 1, per_page=20) == {
        "page": 1, "pages": 3, "per_page": 20, "offset": 0,
        "has_prev": False, "has_next": True,
    }


def test_middle_page():
    assert paginate(45, 2, per_page=20) == {
        "page": 2, "pages": 3, "per_page": 20, "offset": 20,
        "has_prev": True, "has_next": True,
    }


def test_last_page():
    assert paginate(45, 3, per_page=20) == {
        "page": 3, "pages": 3, "per_page": 20, "offset": 40,
        "has_prev": True, "has_next": False,
    }


@pytest.mark.parametrize(("total", "per_page", "pages"), [
    (0, 10, 1), (1, 10, 1), (10, 10, 1), (11, 10, 2), (20, 10, 2), (21, 10, 3), (7, 3, 3),
])
def test_page_count(total, per_page, pages):
    assert paginate(total, 1, per_page)["pages"] == pages


def test_page_beyond_last_is_clamped():
    assert paginate(45, 99, per_page=20)["page"] == 3
    assert paginate(45, 99, per_page=20)["offset"] == 40


def test_empty_list():
    assert paginate(0, 1) == {
        "page": 1, "pages": 1, "per_page": 20, "offset": 0,
        "has_prev": False, "has_next": False,
    }


def test_default_per_page_is_20():
    assert paginate(100, 2)["offset"] == 20


def test_per_page_capped():
    r = paginate(1000, 2, per_page=500)
    assert r["per_page"] == 100 and r["offset"] == 100 and r["pages"] == 10


def test_custom_max_per_page():
    assert paginate(1000, 1, per_page=500, max_per_page=250)["per_page"] == 250
    assert paginate(1000, 1, per_page=100, max_per_page=100)["per_page"] == 100


@pytest.mark.parametrize(("total", "page", "per_page", "match"), [
    (-1, 1, 10, "total"), (10, 0, 10, "page"), (10, 1, 0, "per_page"),
])
def test_invalid(total, page, per_page, match):
    with pytest.raises(ValueError, match=match):
        paginate(total, page, per_page)


def test_single_page_flags():
    r = paginate(5, 1, per_page=5)
    assert r["has_prev"] is False and r["has_next"] is False


def test_per_page_one_is_valid():
    assert paginate(3, 2, per_page=1) == {
        "page": 2, "pages": 3, "per_page": 1, "offset": 1,
        "has_prev": True, "has_next": True,
    }

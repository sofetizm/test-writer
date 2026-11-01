import pytest
from money import apply_discount, format_cents, split_amount


@pytest.mark.parametrize(("total", "parts", "expected"), [
    (100, 3, [34, 33, 33]), (100, 1, [100]), (0, 3, [0, 0, 0]), (5, 2, [3, 2]),
    (2, 3, [1, 1, 0]), (9, 3, [3, 3, 3]), (11, 4, [3, 3, 3, 2]),
])
def test_split(total, parts, expected):
    assert split_amount(total, parts) == expected


@pytest.mark.parametrize(("total", "parts", "match"), [(10, 0, "parts"), (-1, 2, "negative")])
def test_split_invalid(total, parts, match):
    with pytest.raises(ValueError, match=match):
        split_amount(total, parts)


@pytest.mark.parametrize(("price", "percent", "expected"), [
    (999, 15, 849), (10, 25, 8), (1000, 0, 1000), (1000, 100, 0), (1, 50, 1),
    (3, 50, 2), (7, 10, 6), (199, 1, 197), (100, 33, 67), (1234, 7, 1148),
    (8, 95, 0), (9, 95, 0), (10, 95, 1),
])
def test_discount(price, percent, expected):
    assert apply_discount(price, percent) == expected


@pytest.mark.parametrize("percent", [-1, 101])
def test_discount_invalid(percent):
    with pytest.raises(ValueError, match="between 0 and 100"):
        apply_discount(100, percent)


@pytest.mark.parametrize(("cents", "expected"), [
    (0, "0.00 ₽"), (5, "0.05 ₽"), (150, "1.50 ₽"), (123450, "1 234.50 ₽"),
    (100000000, "1 000 000.00 ₽"), (-500, "-5.00 ₽"), (-5, "-0.05 ₽"),
])
def test_format(cents, expected):
    assert format_cents(cents) == expected


def test_format_currency():
    assert format_cents(250, "$") == "2.50 $"

import pytest
from money import split_amount, apply_discount, format_cents

# ---------- split_amount tests ----------
@pytest.mark.parametrize(
    "total, parts, expected",
    [
        (0, 1, [0]),
        (5, 1, [5]),
        (5, 5, [1, 1, 1, 1, 1]),
        (5, 2, [3, 2]),
        (100, 3, [34, 33, 33]),
        (101, 3, [34, 34, 33]),
        (10, 3, [4, 3, 3]),
    ],
)
def test_split_amount_basic(total, parts, expected):
    assert split_amount(total, parts) == expected


def test_split_amount_invalid():
    with pytest.raises(ValueError):
        split_amount(10, 0)
    with pytest.raises(ValueError):
        split_amount(-1, 1)


def test_split_amount_sum():
    for total in range(0, 200, 13):
        for parts in range(1, 10):
            shares = split_amount(total, parts)
            assert len(shares) == parts
            assert sum(shares) == total
            # shares differ by at most 1
            assert max(shares) - min(shares) <= 1


# ---------- apply_discount tests ----------
@pytest.mark.parametrize(
    "price, percent, expected",
    [
        (999, 15, 849),   # 999 * 0.85 = 849.15 -> 849
        (10, 25, 8),      # 10 * 0.75 = 7.5 -> 8
        (100, 0, 100),
        (100, 100, 0),
        (12345, 50, 6173),  # 12345 * 0.5 = 6172.5 -> 6173
    ],
)
def test_apply_discount_examples(price, percent, expected):
    assert apply_discount(price, percent) == expected


def test_apply_discount_invalid():
    for p in (-1, 101):
        with pytest.raises(ValueError):
            apply_discount(100, p)


def test_apply_discount_rounding():
    # values that sit exactly on .5 should round up
    assert apply_discount(1, 50) == 1  # 0.5 -> 1
    assert apply_discount(3, 50) == 2  # 1.5 -> 2
    # values just below .5 should round down
    assert apply_discount(99, 1) == 98  # 99*0.99 = 98.01 -> 98


# ---------- format_cents tests ----------
@pytest.mark.parametrize(
    "cents, currency, expected",
    [
        (0, "₽", "0.00 ₽"),
        (5, "$", "0.05 $"),
        (12345, "€", "123.45 €"),
        (1234567, "£", "12 345.67 £"),
        (-5, "₽", "-0.05 ₽"),
        (-1234567, "¥", "-12 345.67 ¥"),
    ],
)
def test_format_cents_examples(cents, currency, expected):
    assert format_cents(cents, currency) == expected


def test_format_cents_thousands_separator():
    # large positive number
    assert format_cents(1_234_567, "₽") == "12 345.67 ₽"
    # large negative number
    assert format_cents(-1_234_567, "₽") == "-12 345.67 ₽"


def test_format_cents_default_currency():
    assert format_cents(100) == "1.00 ₽"


def test_format_cents_no_currency():
    # empty string as currency should still format correctly
    assert format_cents(2500, "") == "25.00 "


def test_format_cents_negative_zero():
    # -0 should be formatted as 0.00 (no negative sign)
    assert format_cents(-0, "₽") == "0.00 ₽"

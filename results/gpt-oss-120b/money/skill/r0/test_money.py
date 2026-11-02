import pytest
from money import split_amount, apply_discount, format_cents

# ----------------------------------------------------------------------
# split_amount tests
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "total, parts, expected",
    [
        (0, 1, [0]),
        (5, 1, [5]),
        (5, 5, [1, 1, 1, 1, 1]),
        (5, 2, [3, 2]),  # remainder 1 goes to first share
        (100, 3, [34, 33, 33]),
        (101, 3, [34, 34, 33]),  # remainder two goes to first two shares
        (1, 2, [1, 0]),  # remainder 1, second share gets 0
        (99, 100, [1] * 99 + [0]),  # many parts, first 99 get a cent
    ],
    ids=[
        "zero_total_one_part",
        "single_part",
        "equal_parts",
        "two_parts_remainder",
        "example_from_doc",
        "remainder_two",
        "more_parts_than_cents_one_extra",
        "many_parts",
    ],
)
def test_split_amount_basic(total, parts, expected):
    """Check that split_amount distributes cents correctly."""
    result = split_amount(total, parts)
    assert result == expected
    # Invariant: sum of parts equals total
    assert sum(result) == total
    # Invariant: difference between any two parts is at most 1
    assert max(result) - min(result) <= 1


@pytest.mark.parametrize(
    "total, parts, exc_msg",
    [
        (-1, 1, "total must not be negative"),
        (10, 0, "parts must be at least 1"),
        (10, -5, "parts must be at least 1"),
    ],
    ids=["negative_total", "zero_parts", "negative_parts"],
)
def test_split_amount_errors(total, parts, exc_msg):
    """split_amount should raise ValueError for invalid arguments."""
    with pytest.raises(ValueError, match=exc_msg):
        split_amount(total, parts)


# ----------------------------------------------------------------------
# apply_discount tests
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "price, percent, expected",
    [
        (999, 15, 849),  # example from docstring
        (10, 25, 8),  # 7.5 rounds up to 8
        (100, 0, 100),  # no discount
        (100, 100, 0),  # full discount
        (1, 50, 1),  # 0.5 rounds up
        (1, 49, 1),  # 0.51 rounds up
        (1, 51, 0),  # 0.49 rounds down
        (12345, 33, 8271),  # computed correctly
    ],
    ids=[
        "doc_example",
        "half_up",
        "no_discount",
        "full_discount",
        "tiny_price_half_up",
        "tiny_price_half_up_49",
        "tiny_price_half_down",
        "random_case",
    ],
)
def test_apply_discount_basic(price, percent, expected):
    """apply_discount must compute discounted price with half‑up rounding."""
    assert apply_discount(price, percent) == expected


@pytest.mark.parametrize(
    "price, percent, exc_msg",
    [
        (100, -1, "percent must be between 0 and 100"),
        (100, 101, "percent must be between 0 and 100"),
    ],
    ids=["percent_below_zero", "percent_above_hundred"],
)
def test_apply_discount_invalid_percent(price, percent, exc_msg):
    """apply_discount should reject percentages outside 0..100."""
    with pytest.raises(ValueError, match=exc_msg):
        apply_discount(price, percent)


def test_apply_discount_rounding_boundary():
    """Check the exact half‑up boundary where the remainder is exactly 50."""
    # price * (100 - percent) = 199 -> cents=1, rest=99 -> rounds up
    assert apply_discount(199, 0) == 199
    # Construct a case where rest == 50 (exact half)
    # price=25, percent=50 => numerator=25*50=1250, cents=12, rest=50 -> should round up to 13
    assert apply_discount(25, 50) == 13


# ----------------------------------------------------------------------
# format_cents tests
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "cents, currency, expected",
    [
        (0, "₽", "0.00 ₽"),
        (5, "€", "0.05 €"),
        (12345, "₽", "123.45 ₽"),
        (1234567, "₽", "12 345.67 ₽"),
        (123456789, "$", "1 234 567.89 $"),
        (-5, "₽", "-0.05 ₽"),
        (-1234567, "₽", "-12 345.67 ₽"),
    ],
    ids=[
        "zero",
        "small_positive",
        "regular",
        "thousands_separator",
        "large_with_dollar",
        "negative_small",
        "negative_large",
    ],
)
def test_format_cents_basic(cents, currency, expected):
    """format_cents should format amounts with correct separators and sign."""
    assert format_cents(cents, currency) == expected


def test_format_cents_default_currency():
    """Default currency symbol should be ₽."""
    assert format_cents(12345) == "123.45 ₽"


def test_format_cents_consistency():
    """Round‑trip: parsing the formatted string back to cents yields original."""
    def parse(s: str) -> int:
        amount, _ = s.rsplit(" ", 1)
        whole, frac = amount.replace(" ", "").split(".")
        sign = -1 if whole.startswith("-") else 1
        whole = int(whole.lstrip("-"))
        return sign * (whole * 100 + int(frac))

    for cents in [0, 5, 99, 100, 101, 12345, -12345, 1234567, -1234567]:
        formatted = format_cents(cents)
        assert parse(formatted) == cents

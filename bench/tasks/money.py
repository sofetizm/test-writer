"""Money helpers. Amounts are integers in cents to avoid floating point errors."""


def split_amount(total_cents: int, parts: int) -> list[int]:
    """Split `total_cents` into `parts` shares that differ by at most one cent.

    The first shares receive the extra cents: split_amount(100, 3) == [34, 33, 33].
    Raises ValueError if parts < 1 or total_cents < 0.
    """
    if parts < 1:
        raise ValueError("parts must be at least 1")
    if total_cents < 0:
        raise ValueError("total must not be negative")
    base, remainder = divmod(total_cents, parts)
    return [base + 1 if i < remainder else base for i in range(parts)]


def apply_discount(price_cents: int, percent: int) -> int:
    """Price after a percentage discount, rounded half up to whole cents.

    apply_discount(999, 15) == 849 (999 * 0.85 = 849.15).
    apply_discount(10, 25) == 8 (7.5 rounds up). percent must be in 0..100.
    """
    if not 0 <= percent <= 100:
        raise ValueError("percent must be between 0 and 100")
    numerator = price_cents * (100 - percent)
    cents, rest = divmod(numerator, 100)
    if rest * 2 >= 100:
        cents += 1
    return cents


def format_cents(cents: int, currency: str = "₽") -> str:
    """Format cents as "1 234.50 ₽" with a space as thousands separator.

    Negative amounts get a leading minus: "-5.00 ₽".
    """
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    grouped = f"{whole:,}".replace(",", " ")
    return f"{sign}{grouped}.{frac:02d} {currency}"

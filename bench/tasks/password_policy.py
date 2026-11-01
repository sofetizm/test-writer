"""Password policy checks."""

COMMON = {"password", "qwerty123", "12345678", "iloveyou", "admin123"}
SPECIAL = set("!@#$%^&*()-_=+[]{};:,.?/")


def check_password(password: str, min_length: int = 10) -> list[str]:
    """Return the list of violated rules (empty list = password accepted).

    Rules, reported in this order:
    "too_short"   fewer than min_length characters
    "no_lower"    no lowercase letter
    "no_upper"    no uppercase letter
    "no_digit"    no digit
    "no_special"  no character from SPECIAL
    "whitespace"  contains whitespace
    "repeats"     the same character three or more times in a row
    "common"      matches a common password, case-insensitively
    """
    problems = []
    if len(password) < min_length:
        problems.append("too_short")
    if not any(c.islower() for c in password):
        problems.append("no_lower")
    if not any(c.isupper() for c in password):
        problems.append("no_upper")
    if not any(c.isdigit() for c in password):
        problems.append("no_digit")
    if not any(c in SPECIAL for c in password):
        problems.append("no_special")
    if any(c.isspace() for c in password):
        problems.append("whitespace")
    if any(password[i] == password[i + 1] == password[i + 2] for i in range(len(password) - 2)):
        problems.append("repeats")
    if password.lower() in COMMON:
        problems.append("common")
    return problems


def strength(password: str) -> str:
    """"weak" if 3+ rules are violated, "medium" if 1-2, "strong" if none."""
    n = len(check_password(password))
    if n >= 3:
        return "weak"
    if n > 0:
        return "medium"
    return "strong"

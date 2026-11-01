"""Turn titles (Russian or English) into URL slugs."""
import re

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
}


def slugify(text: str, max_length: int = 50, separator: str = "-") -> str:
    """Lowercase, transliterate Cyrillic, replace runs of other characters with
    `separator`, strip separators at the ends.

    If the slug is longer than `max_length`, it is cut at the last separator that
    keeps it within the limit (words are not split); a single long word is cut hard.
    Returns "" when nothing is left. Raises ValueError if max_length < 1.
    """
    if max_length < 1:
        raise ValueError("max_length must be positive")
    text = "".join(_TRANSLIT.get(ch, ch) for ch in text.lower())
    slug = re.sub(r"[^a-z0-9]+", separator, text).strip(separator)
    if len(slug) <= max_length:
        return slug
    cut = slug[:max_length + 1]
    idx = cut.rfind(separator)
    if idx > 0:
        return slug[:idx]
    return slug[:max_length]

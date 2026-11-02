import pytest
from slugify import slugify

@pytest.mark.parametrize(
    "input_text,expected",
    [
        ("Hello World!", "hello-world"),
        ("Привет мир", "privet-mir"),
        ("Café au lait", "caf-au-lait"),  # accent removed by regex
        ("   Multiple   spaces   ", "multiple-spaces"),
        ("---Leading and trailing---", "leading-and-trailing"),
        ("", ""),
        ("!!!", ""),
    ],
    ids=[
        "basic english",
        "cyrillic transliteration",
        "unicode accent",
        "multiple spaces",
        "leading/trailing separators",
        "empty string",
        "only symbols",
    ],
)
def test_basic_slugify(input_text, expected):
    assert slugify(input_text) == expected


def test_max_length_cut_at_separator():
    # slug length 23, max_length 10 -> cut at last separator before limit
    assert slugify("one two three four", max_length=10) == "one-two"


def test_max_length_hard_cut_long_word():
    # single long word longer than max_length should be hard cut
    assert slugify("supercalifragilisticexpialidocious", max_length=10) == "supercalif"


def test_max_length_equal_boundary():
    # When slug length equals max_length, it should be returned unchanged
    slug = slugify("a b c d e f g h i j", max_length=19)  # "a-b-c-d-e-f-g-h-i-j" length 19
    assert len(slug) == 19
    assert slug == "a-b-c-d-e-f-g-h-i-j"


def test_idx_zero_fallback():
    # Create a slug where the only separator is at position 0 after cutting
    # e.g., slug = "-a-b", max_length=2 -> cut = "-a-"
    # idx will be 0, so fallback to hard cut
    result = slugify("-a-b", max_length=2, separator="-")
    # Hard cut of first 2 chars: "-a", stripped -> "a"
    assert result == "a"


def test_default_max_length_boundary():
    # Build a slug whose length is exactly 51 after processing.
    # With default max_length=50 it should be cut, with max_length=51 it should stay.
    text = "word " * 11  # "word-word-...-"  (11 words)
    # After slugify: "word-word-word-word-word-word-word-word-word-word-word"
    # Length = 4*11 + 10 separators = 54, >51
    default_slug = slugify(text)  # max_length=50
    longer_slug = slugify(text, max_length=51)
    assert len(default_slug) < len(longer_slug)
    assert len(default_slug) <= 50
    assert len(longer_slug) > 50


def test_max_length_one_is_allowed():
    # max_length=1 should not raise and should return at most one character (or empty)
    assert slugify("A", max_length=1) in ("a", "")
    # With a separator present, it should be stripped
    assert slugify("A B", max_length=1) == "a"


def test_invalid_max_length():
    with pytest.raises(ValueError, match="max_length must be positive"):
        slugify("test", max_length=0)

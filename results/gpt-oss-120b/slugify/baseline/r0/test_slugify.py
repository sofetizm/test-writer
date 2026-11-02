import pytest
from slugify import slugify

# Basic functionality tests
@pytest.mark.parametrize(
    "input_text,expected",
    [
        ("Hello World!", "hello-world"),
        ("  Multiple   spaces  ", "multiple-spaces"),
        ("Café au lait", "caf-au-lait"),  # accent removed by regex
        ("Python_3.8+rocks", "python-3-8-rocks"),
        ("---Leading and trailing---", "leading-and-trailing"),
        ("", ""),
        ("!!!", ""),
    ],
)
def test_basic_slugify(input_text, expected):
    assert slugify(input_text) == expected


def test_cyrillic_transliteration():
    # Mixed Russian and English, with punctuation
    text = "Привет, мир! Hello, world!"
    # Expected transliteration: privet-mir-hello-world
    assert slugify(text) == "privet-mir-hello-world"


def test_max_length_cut_at_separator():
    # Create a slug longer than max_length with several separators
    text = "one two three four five six seven eight nine ten"
    # Default separator is '-', max_length 20 should cut after "one-two-three-four"
    assert slugify(text, max_length=20) == "one-two-three-four"


def test_max_length_hard_cut_single_long_word():
    # A single long word without separators should be hard cut
    long_word = "a" * 30
    assert slugify(long_word, max_length=10) == "aaaaaaaaaa"


def test_max_length_respects_separator_boundary():
    # Ensure that when the cut point lands exactly on a separator, it is not included
    text = "word1 word2 word3"
    # slug becomes "word1-word2-word3"
    # max_length 11 includes "word1-word2" (len 11) but trailing separator should be stripped
    assert slugify(text, max_length=11) == "word1-word2"


def test_custom_separator():
    # Use underscore as separator
    text = "Hello World! This is a test."
    assert slugify(text, separator="_") == "hello_world_this_is_a_test"


def test_invalid_max_length():
    with pytest.raises(ValueError):
        slugify("test", max_length=0)
    with pytest.raises(ValueError):
        slugify("test", max_length=-5)


# Property-based tests using hypothesis
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=100))
def test_slugify_is_lowercase_and_no_invalid_chars(s):
    result = slugify(s)
    # Result should be lowercase
    assert result == result.lower()
    # Should contain only a-z, 0-9 and hyphens (or be empty)
    assert all(ch.islower() or ch.isdigit() or ch == "-" for ch in result)


@given(
    st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll")), min_size=1, max_size=20),
    st.integers(min_value=1, max_value=100),
)
def test_slugify_respects_max_length(text, max_len):
    result = slugify(text, max_length=max_len)
    # Result length should never exceed max_len
    assert len(result) <= max_len
    # If result is non-empty and longer than 1, it should not start or end with separator
    if result:
        assert not result.startswith("-")
        assert not result.endswith("-")

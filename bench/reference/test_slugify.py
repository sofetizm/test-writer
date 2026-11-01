import pytest
from slugify import slugify


@pytest.mark.parametrize(("text", "expected"), [
    ("Hello World", "hello-world"),
    ("  Hello,   World!  ", "hello-world"),
    ("Привет, мир", "privet-mir"),
    ("Щука и ёж", "schuka-i-ezh"),
    ("Объявление", "obyavlenie"),
    ("C++ & Python 3", "c-python-3"),
    ("---", ""),
    ("", ""),
    ("Юла Цирк Чай Шум Хлеб Ящик", "yula-tsirk-chay-shum-hleb-yaschik"),
])
def test_basic(text, expected):
    assert slugify(text) == expected


def test_custom_separator():
    assert slugify("Hello big World", separator="_") == "hello_big_world"


def test_no_truncation_at_exact_limit():
    assert slugify("abc def", max_length=7) == "abc-def"


def test_truncates_at_word_boundary():
    assert slugify("abc def ghi", max_length=9) == "abc-def"
    assert slugify("abc def ghi", max_length=8) == "abc-def"
    assert slugify("abc def ghi", max_length=6) == "abc"


def test_boundary_where_cut_lands_on_separator():
    assert slugify("ab cd ef", max_length=5) == "ab-cd"


def test_single_long_word_cut_hard():
    assert slugify("abcdefghij", max_length=4) == "abcd"


def test_default_max_length_is_50():
    words = " ".join(["word"] * 20)
    result = slugify(words)
    assert len(result) <= 50
    assert result == "-".join(["word"] * 10)
    assert slugify("a" * 50) == "a" * 50
    assert slugify("a" * 51) == "a" * 50


def test_max_length_one():
    assert slugify("ab", max_length=1) == "a"


@pytest.mark.parametrize("bad", [0, -3])
def test_invalid_max_length(bad):
    with pytest.raises(ValueError, match="max_length"):
        slugify("x", max_length=bad)


def test_short_first_word_before_cut():
    assert slugify("a bcdef", max_length=3) == "a"

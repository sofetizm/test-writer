import pytest
from lru_cache import LRUCache


def test_put_get_and_len():
    c = LRUCache(2)
    c.put("a", 1)
    assert c.get("a") == 1
    assert len(c) == 1


def test_missing_returns_default():
    c = LRUCache(1)
    assert c.get("x") is None
    assert c.get("x", 42) == 42


def test_evicts_least_recently_used():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    assert "a" not in c
    assert c.get("b") == 2 and c.get("c") == 3
    assert len(c) == 2


def test_get_refreshes_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")
    c.put("c", 3)
    assert "b" not in c
    assert "a" in c


def test_put_existing_updates_value_and_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("a", 10)
    c.put("c", 3)
    assert c.get("a") == 10
    assert "b" not in c
    assert len(c) == 2


def test_capacity_one():
    c = LRUCache(1)
    c.put("a", 1)
    c.put("b", 2)
    assert "a" not in c and c.get("b") == 2


def test_contains_does_not_refresh():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    assert "a" in c
    c.put("c", 3)
    assert "a" not in c


def test_stats():
    c = LRUCache(2)
    assert c.hit_rate() == 0.0
    c.put("a", 1)
    c.get("a")
    c.get("a")
    c.get("zzz")
    assert c.hits == 2 and c.misses == 1
    assert c.hit_rate() == pytest.approx(2 / 3)


def test_stats_all_misses():
    c = LRUCache(1)
    c.get("x")
    assert c.hit_rate() == 0.0


@pytest.mark.parametrize("cap", [0, -1])
def test_invalid_capacity(cap):
    with pytest.raises(ValueError, match="capacity"):
        LRUCache(cap)


def test_capacity_attribute():
    assert LRUCache(3).capacity == 3

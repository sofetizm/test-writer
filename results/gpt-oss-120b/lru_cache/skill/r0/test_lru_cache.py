import pytest
from lru_cache import LRUCache


@pytest.fixture
def cache():
    """Cache with capacity 3 for most tests."""
    return LRUCache(3)


def test_constructor_invalid_capacity():
    with pytest.raises(ValueError, match="capacity must be at least 1"):
        LRUCache(0)
    with pytest.raises(ValueError, match="capacity must be at least 1"):
        LRUCache(-5)


@pytest.mark.parametrize(
    "capacity,expected",
    [(1, 1), (5, 5), (10, 10)],
    ids=lambda v: f"capacity_{v}",
)
def test_constructor_valid_capacity(capacity, expected):
    c = LRUCache(capacity)
    assert c.capacity == expected
    assert len(c) == 0
    assert c.hits == 0
    assert c.misses == 0
    assert c.hit_rate() == 0.0


def test_put_and_len(cache):
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert len(cache) == 3
    # Adding a fourth key evicts the least recently used ("a")
    cache.put("d", 4)
    assert len(cache) == 3
    assert "a" not in cache
    assert set(cache._data.keys()) == {"b", "c", "d"}


def test_put_updates_existing_key_and_recency(cache):
    cache.put("x", 10)
    cache.put("y", 20)
    cache.put("z", 30)
    # Access "x" to make it most recent
    assert cache.get("x") == 10
    # Now put a new key, causing eviction of the least recent ("y")
    cache.put("new", 99)
    assert "y" not in cache
    # Existing key "x" should still be present and most recent
    assert "x" in cache
    # Order should be z, x, new (z is now least recent)
    assert list(cache._data.keys()) == ["z", "x", "new"]


def test_get_hits_and_misses(cache):
    # Miss first
    assert cache.get("missing", default="def") == "def"
    assert cache.misses == 1
    assert cache.hits == 0
    assert cache.hit_rate() == 0.0

    # Put and hit
    cache.put("k", 100)
    assert cache.get("k") == 100
    assert cache.hits == 1
    assert cache.misses == 1
    assert cache.hit_rate() == 0.5

    # Another miss
    assert cache.get("nope") is None
    assert cache.misses == 2
    assert cache.hit_rate() == 1 / 3


def test_get_moves_key_to_end(cache):
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    # Access "a" makes it most recent
    assert cache.get("a") == 1
    assert list(cache._data.keys()) == ["b", "c", "a"]
    # Access "b"
    assert cache.get("b") == 2
    assert list(cache._data.keys()) == ["c", "a", "b"]


def test_contains_does_not_change_recency(cache):
    cache.put("first", 1)
    cache.put("second", 2)
    cache.put("third", 3)
    # Record order
    original_order = list(cache._data.keys())
    assert ("second" in cache) is True
    # Order must be unchanged
    assert list(cache._data.keys()) == original_order


def test_hit_rate_before_any_get():
    c = LRUCache(2)
    assert c.hit_rate() == 0.0
    c.put("x", 1)
    c.put("y", 2)
    # Still no get calls
    assert c.hit_rate() == 0.0


def test_eviction_respects_recency_after_puts(cache):
    # Fill cache
    cache.put(1, "a")
    cache.put(2, "b")
    cache.put(3, "c")
    # Access 2 to make it recent, order: 1,3,2
    assert cache.get(2) == "b"
    # Put new key, should evict 1
    cache.put(4, "d")
    assert 1 not in cache
    assert set(cache._data.keys()) == {3, 2, 4}
    # Verify order: 3 (least), 2, 4 (most)
    assert list(cache._data.keys()) == [3, 2, 4]


def test_put_same_key_does_not_increase_size(cache):
    cache.put("k", 1)
    cache.put("k", 2)  # update same key
    assert len(cache) == 1
    assert cache.get("k") == 2
    # Adding two more distinct keys reaches capacity
    cache.put("a", 10)
    cache.put("b", 20)
    assert len(cache) == 3
    # Adding another distinct key evicts the least recent (which is "k")
    cache.put("c", 30)
    assert "k" not in cache
    assert set(cache._data.keys()) == {"a", "b", "c"}

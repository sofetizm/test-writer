import pytest
from hypothesis import given, strategies as st

from lru_cache import LRUCache


def test_initialization_invalid_capacity():
    """Capacity must be at least 1."""
    with pytest.raises(ValueError):
        LRUCache(0)
    with pytest.raises(ValueError):
        LRUCache(-5)


def test_basic_put_and_get():
    cache = LRUCache(2)
    # initially empty
    assert len(cache) == 0
    assert cache.get("a") is None
    assert cache.misses == 1
    assert cache.hits == 0

    # put a value and retrieve it
    cache.put("a", 1)
    assert len(cache) == 1
    assert "a" in cache
    assert cache.get("a") == 1
    assert cache.hits == 1
    assert cache.misses == 1  # only the earlier miss

    # default value handling
    sentinel = object()
    assert cache.get("missing", default=sentinel) is sentinel
    assert cache.misses == 2


def test_eviction_policy():
    """When capacity is exceeded, the least-recently-used key is evicted."""
    cache = LRUCache(3)
    for i in range(3):
        cache.put(f"k{i}", i)

    # order is k0, k1, k2 (k0 is LRU)
    assert list(cache._data.keys()) == ["k0", "k1", "k2"]

    # Access k0 makes it most recent
    assert cache.get("k0") == 0
    assert list(cache._data.keys()) == ["k1", "k2", "k0"]

    # Insert new key, should evict k1 (now LRU)
    cache.put("k3", 3)
    assert "k1" not in cache
    assert set(cache._data.keys()) == {"k2", "k0", "k3"}
    # order should be k2, k0, k3
    assert list(cache._data.keys()) == ["k2", "k0", "k3"]


def test_put_updates_existing_key_without_eviction():
    """Putting an existing key updates its value and recency but does not evict."""
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    # cache is full now
    cache.put("a", 10)  # update existing key
    # No eviction should happen
    assert len(cache) == 2
    assert cache.get("a") == 10
    # 'a' should now be most recent, order: b, a
    assert list(cache._data.keys()) == ["b", "a"]


def test_hit_rate_calculation():
    cache = LRUCache(2)
    # No gets yet
    assert cache.hit_rate() == 0.0

    cache.put("x", 42)
    cache.get("x")          # hit
    cache.get("y")          # miss
    cache.get("x")          # hit
    cache.get("z", 99)      # miss with default
    assert cache.hits == 2
    assert cache.misses == 2
    assert cache.hit_rate() == pytest.approx(0.5)


@given(
    st.lists(st.tuples(st.integers(min_value=0, max_value=20), st.integers()), min_size=1, max_size=30),
    st.integers(min_value=1, max_value=10),
)
def test_random_operations_consistency(ops, capacity):
    """
    Perform a sequence of put/get operations on both LRUCache and a reference
    implementation (a simple dict with manual LRU tracking) and compare
    behaviours: length, membership, values returned, and eviction order.
    """
    # reference structures
    ref_data = {}
    ref_order = []  # most recent at end

    cache = LRUCache(capacity)

    for key, value in ops:
        # randomly decide to put or get
        if key % 2 == 0:
            # put operation
            cache.put(key, value)
            if key in ref_data:
                # move to most recent
                ref_order.remove(key)
            ref_data[key] = value
            ref_order.append(key)
            # enforce capacity
            while len(ref_order) > capacity:
                evicted = ref_order.pop(0)
                del ref_data[evicted]
        else:
            # get operation
            default = -1
            got = cache.get(key, default=default)
            # reference get
            if key in ref_data:
                ref_order.remove(key)
                ref_order.append(key)
                expected = ref_data[key]
            else:
                expected = default
            assert got == expected

        # after each step, compare internal state
        assert len(cache) == len(ref_data)
        assert set(cache._data.keys()) == set(ref_data.keys())
        # order of keys in cache should match ref_order (LRU -> MRU)
        assert list(cache._data.keys()) == ref_order

    # final hit rate sanity check (should be between 0 and 1)
    hr = cache.hit_rate()
    assert 0.0 <= hr <= 1.0


def test_contains_does_not_affect_recency():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    # initial order a, b
    assert list(cache._data.keys()) == ["a", "b"]
    # membership check should not move key
    assert "a" in cache
    assert list(cache._data.keys()) == ["a", "b"]
    # get should move it
    cache.get("a")
    assert list(cache._data.keys()) == ["b", "a"]

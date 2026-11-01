"""A small least-recently-used cache."""
from collections import OrderedDict


class LRUCache:
    """Keeps at most `capacity` items; when full, putting a new key evicts the
    least recently used one. Both `get` and `put` mark a key as recently used.
    """

    def __init__(self, capacity: int):
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self.capacity = capacity
        self._data = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key, default=None):
        if key not in self._data:
            self.misses += 1
            return default
        self.hits += 1
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key, value) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key) -> bool:
        """Membership check does not change recency."""
        return key in self._data

    def hit_rate(self) -> float:
        """Share of `get` calls that found the key; 0.0 before any `get`."""
        total = self.hits + self.misses
        return self.hits / total if total else 0.0

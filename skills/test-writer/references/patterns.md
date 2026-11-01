# Test patterns

## Boundary table with parametrize
```python
import pytest
from pagination import paginate

@pytest.mark.parametrize(
    ("total", "per_page", "expected_pages"),
    [
        pytest.param(0, 10, 0, id="empty"),
        pytest.param(1, 10, 1, id="one-item"),
        pytest.param(10, 10, 1, id="exactly-full-page"),
        pytest.param(11, 10, 2, id="one-over"),
    ],
)
def test_page_count(total, per_page, expected_pages):
    assert paginate(total, page=1, per_page=per_page)["pages"] == expected_pages
```

## Errors: type *and* message
```python
def test_rejects_negative_per_page():
    with pytest.raises(ValueError, match="per_page must be positive"):
        paginate(10, page=1, per_page=-1)
```

## Whole-structure assertions
```python
def test_second_page_metadata():
    assert paginate(25, page=2, per_page=10) == {
        "page": 2, "pages": 3, "offset": 10, "limit": 10,
        "has_prev": True, "has_next": True,
    }
```
Comparing the whole dict checks every field at once and shows a clear diff on failure.

## Floating point
```python
assert result == pytest.approx(0.3)            # not ==
assert result == pytest.approx(2.5, abs=1e-9)
```
Money: use integers (cents) or `decimal.Decimal`, and assert exact values.

## Injected clock instead of sleep
```python
class FakeClock:
    def __init__(self, t=0.0):
        self.t = t
    def __call__(self):
        return self.t
    def advance(self, seconds):
        self.t += seconds

def test_bucket_refills_over_time():
    clock = FakeClock()
    bucket = TokenBucket(capacity=2, rate=1.0, clock=clock)
    assert bucket.allow() and bucket.allow()
    assert not bucket.allow()
    clock.advance(1.0)
    assert bucket.allow()
```
If the code has no clock parameter, use `monkeypatch.setattr(module.time, "monotonic", fake)`.

## Stateful objects: sequence + full state check
```python
def test_get_refreshes_recency():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")          # "a" becomes most recent
    cache.put("c", 3)       # evicts "b", not "a"
    assert cache.get("b") is None
    assert cache.get("a") == 1
    assert len(cache) == 2
```

## Property-based tests (Hypothesis)
Use when the code has an invariant that should hold for *all* inputs.
```python
from hypothesis import given, strategies as st

@given(st.integers(min_value=0, max_value=10**9), st.integers(min_value=1, max_value=50))
def test_split_conserves_total(total, parts):
    shares = split_amount(total, parts)
    assert sum(shares) == total
    assert len(shares) == parts
    assert max(shares) - min(shares) <= 1
```
Property tests complement example tests; they do not replace exact-value examples.

## Temporary files
```python
def test_writes_report(tmp_path):
    out = tmp_path / "report.csv"
    write_report(rows, out)
    assert out.read_text(encoding="utf-8") == "name,score\nann,5\n"
```

## Real bug found: keep the test, mark it
```python
@pytest.mark.xfail(reason="BUG: docstring says end is inclusive, code excludes it", strict=True)
def test_range_includes_end():
    assert list(date_range(d1, d3)) == [d1, d2, d3]
```
`strict=True` makes the test fail loudly once the bug is fixed, so the marker is removed.

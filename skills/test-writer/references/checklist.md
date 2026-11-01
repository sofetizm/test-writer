# What to test: checklist

Go through the code line by line. Each item below is a place where bugs hide and
where mutation testing will inject a change.

## Comparisons (`<`, `<=`, `==`, `in`, `is`)
- For `x < limit`: test `limit - 1`, `limit`, `limit + 1`. Off-by-one survives otherwise.
- For `==` / `!=`: test the equal case and a different case.
- For `in`: test an element that is present, one that is absent, and an empty container.

## Arithmetic (`+ - * / // % **`)
- Use inputs where swapping the operator changes the result. `x + 0` and `x - 0` are
  the same; `1 * 1` and `1 / 1` are the same. Avoid 0 and 1 as the *only* test values.
- Integer vs float division: test values that do not divide evenly.
- Rounding: test .5 cases, negative numbers, and values just below/above a boundary.

## Constants
- Every literal (`0`, `1`, `60`, `100`, default arguments) should be observable in some
  test result. If changing `60` to `61` breaks no test, the unit conversion is untested.

## Boolean logic (`and`, `or`, `not`)
- For `a and b`: cases (True, False) and (False, True) distinguish it from `or`.
- For `not x`: test both values of `x`.

## Branches and early returns
- Every `if`/`elif`/`else` body executed at least once with its effect asserted.
- Every `raise`: the input that triggers it, the exception type and message (`match=`).
- Loops: zero iterations, one iteration, many iterations; `break`/`continue` paths.

## Return values
- Assert the exact value, every field of a dict/tuple/dataclass, and the type when it
  matters (`int` vs `float`, `list` vs `tuple`).
- A function that returns `None` on purpose: assert `is None`.

## Side effects and state
- Calls that are statements (`items.append(x)`, `cache.move_to_end(k)`, `self._count += 1`)
  must have a visible effect checked by some test, or the call can be deleted unnoticed.
- After a method call, check the state that should change *and* the state that should not.
- Order of operations: e.g. eviction order in caches, which element wins on ties.

## Inputs
- Empty: `""`, `[]`, `{}`, `0`.
- Single element; duplicates; already sorted / reverse sorted / unsorted.
- Unicode and case (`"Ё"`, `"ß"`, mixed case), whitespace at the edges.
- Large values; negative values; `float('nan')`, `inf` if numeric code accepts floats.
- Invalid types or values the function promises to reject.

## Invariants (property-based candidates)
- Round-trip: `parse(format(x)) == x`.
- Conservation: parts sum to the whole, no elements lost or duplicated.
- Ordering: output is sorted; output order is stable.
- Idempotence: `f(f(x)) == f(x)`.
- Bounds: result always within `[lo, hi]`.

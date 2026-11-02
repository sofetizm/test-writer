---
name: test-writer
description: Write pytest tests that actually catch bugs, verified by mutation testing. Use when asked to write, add, improve or review unit tests for Python code, or to raise test quality or coverage.
---

# Test writer

Tests that pass are easy to write. Tests that **fail when the code is wrong** are the
goal. Line coverage does not measure that; mutation testing does: inject small bugs
into the code and check that the tests catch them. This skill writes tests in a loop
that ends only when the tests catch (almost) every injected bug.

## Workflow

### 1. Understand the contract before writing anything
Read the module and write down, as a short test plan:
- **Behaviours**: what each public function/method promises (docstring, names, types).
- **Branches**: every `if`/`elif`/`else`, loop exit, early `return`, `raise`.
- **Boundaries**: for every comparison `a < b` the cases `b-1`, `b`, `b+1`; empty
  inputs, zero, one element, maximum sizes, negative numbers, `None` where allowed.
- **Error paths**: each `raise` and which inputs trigger it.
- **Invariants**: properties that hold for all inputs (round-trips, ordering,
  conservation such as "parts sum to the total", idempotence).
- **State**: for classes, the sequence of calls that changes state (and what must
  *not* change).

See `references/checklist.md` for the full list of what to look for.

### 2. Write the tests
- Test **public behaviour**, never private helpers or implementation details.
- Assert **exact expected values** computed by hand from the specification.
  Never `assert result`, `assert result is not None`, `assert len(x) > 0`
  when the exact value is known.
- One behaviour per test, named after it: `test_merge_touching_intervals_joins_them`.
- Use `@pytest.mark.parametrize` for boundary tables: input, expected, and an `id`.
- Error cases: `with pytest.raises(ValueError, match="...")`. The match matters: it
  proves the *right* error was raised.
- Check **every** field of a returned structure, not just one.
- For state: assert both what changed and what did not.
- Invariants: add a property-based test with Hypothesis if it is installed
  (`references/patterns.md`).
- Inject time, randomness and I/O (clock functions, seeds, `tmp_path`) instead of
  sleeping or touching real resources.

Patterns: `references/patterns.md`. Mistakes to avoid: `references/anti-patterns.md`.

### 3. Run the tests on the original code
Always run plain pytest before mutation testing. All tests must pass. If one fails:
- read the **actual** value in the failure (`assert 849 == 850`) and trace the code by
  hand to see which one is right. Do not guess a new expected value;
- the **expectation** is wrong → fix the test;
- the **code** contradicts its own docstring/contract → this is a real bug. Do not
  change the code under test. Keep the test, mark it
  `@pytest.mark.xfail(reason="BUG: ...", strict=True)` and report the bug to the user;
- still unsure after two attempts on the same case → remove that case and mention it
  in the report. Do not loop.

### 4. Measure with mutation testing
```bash
python <skill-dir>/scripts/mutation_score.py --module path/to/module.py --tests path/to/test_module.py
```
Run it from the project root. The script copies the project to a temporary directory,
so the user's files are never modified. It prints the mutation score and every
**surviving mutant**: a line number and the change (e.g. `` `<` -> `<=` ``) that no
test detected.

For each surviving mutant, either:
- **add or sharpen a test** that would fail with this change (usually a missing
  boundary, an unchecked return field, or an unchecked side effect), or
- **mark it equivalent** if the change cannot alter observable behaviour
  (e.g. `<` vs `<=` where equality is impossible). Say so explicitly; do not
  pretend it is covered.

Repeat steps 3–4. Stop when the score is **≥ 90%** and every remaining survivor is
explained, or after 4 iterations. If the script cannot run (no Python, no pytest),
do the same review by hand: go through each comparison, arithmetic operator,
constant and `return` and ask "which test fails if this changes?".

### 5. Report
Finish with a short summary for the user:
- what is covered (behaviours, boundaries, errors);
- the final mutation score and which survivors are equivalent;
- **bugs found** in the code under test (xfail tests), if any.

## Rules
- Never modify the code under test to make tests pass.
- Never weaken an assertion to make a test pass.
- Never delete a failing test without explaining why it was wrong.
- Keep tests deterministic and fast (no `sleep`, no network, no real clock).

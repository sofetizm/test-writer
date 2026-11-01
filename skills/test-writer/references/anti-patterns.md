# Anti-patterns: tests that pass but catch nothing

| Anti-pattern | Why it is weak | Instead |
|---|---|---|
| `assert result` / `assert result is not None` | Any non-empty value passes, including wrong ones | `assert result == expected` |
| `assert len(items) > 0` | Wrong items of any count pass | Compare the list itself |
| `assert isinstance(x, int)` as the only check | Every wrong integer passes | Check the value; type check only in addition |
| Expected value computed by the same formula as the code | Repeats the bug in the test | Hand-computed constants from the spec |
| Only "happy path" with typical values | Boundaries and errors untested, `<` vs `<=` survives | Boundary table + error cases |
| Test values 0 and 1 only | `+`/`-` with 0, `*`/`/` with 1 give identical results | Use values like 3, 7, 12 |
| `pytest.raises(Exception)` | Any crash passes, including a `TypeError` from a bug | Exact exception type + `match=` |
| Mocking the unit under test or everything around it | Tests the mocks, not the code | Mock only slow/external boundaries (network, clock) |
| Checking one field of a returned dict | Other fields can be wrong | Compare the whole structure |
| `try: ... except: pass` in a test | Swallows the failure | Let it fail, or `pytest.raises` |
| `time.sleep()` in tests | Slow and flaky | Inject a fake clock |
| Tests depending on execution order or shared mutable state | Pass alone, fail together (or vice versa) | Fresh objects per test, fixtures |
| Changing the code under test so the test passes | Hides real bugs | Mark `xfail(strict=True)` and report the bug |
| Weakening an assertion after a failure | The failure was information | Decide whether the code or the expectation is wrong |
| Giant test checking ten behaviours | First failure hides the rest, unclear what broke | One behaviour per test, descriptive name |

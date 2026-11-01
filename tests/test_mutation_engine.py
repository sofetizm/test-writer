"""The mutation engine is the measuring instrument: it gets the strictest tests."""
import ast
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from twbench import SKILL_DIR
from twbench.mutation import apply_mutation, collect_mutations, mutation_score, run

SCRIPT = SKILL_DIR / "scripts" / "mutation_score.py"

SAMPLE = textwrap.dedent('''
    """Module docstring."""


    def f(a: int, b: int = 2) -> int:
        """Docstring with numbers 1 2 3."""
        if a < b and a != 0:
            a += 1
        items = []
        items.append(a)
        return max(a * b, -1) if not a else a - b


    if __name__ == "__main__":
        print(f(1, 3))
''')


def kinds(source):
    return sorted(m.kind for m in collect_mutations(source))


def test_operators_found():
    assert kinds(SAMPLE) == sorted([
        "constant",
        "negate_if", "boolop", "compare", "compare", "constant",
        "augassign", "constant",
        "drop_call",
        "return_none", "unary", "func_swap", "binop", "unary", "constant", "binop",
    ])


def test_skips_docstrings_annotations_and_main_guard():
    descriptions = [(m.lineno, m.description) for m in collect_mutations(SAMPLE)]
    lines = {ln for ln, _ in descriptions}
    docstring_lines, main_guard_lines = {2, 6}, {14, 15}
    assert not lines & docstring_lines
    assert not lines & main_guard_lines
    assert (5, "`2` -> `3`") in descriptions


@pytest.mark.parametrize("m", collect_mutations(SAMPLE), ids=lambda m: f"{m.kind}-{m.lineno}-{m.col}")
def test_each_mutant_is_valid_python_and_differs(m):
    mutated = apply_mutation(SAMPLE, m)
    ast.parse(mutated)
    assert ast.dump(ast.parse(mutated)) != ast.dump(ast.parse(SAMPLE))


def test_specific_rewrites():
    src = "def g(x):\n    return x < 3\n"
    by_kind = {m.kind: m for m in collect_mutations(src)}
    assert "x <= 3" in apply_mutation(src, by_kind["compare"])
    assert "x < 4" in apply_mutation(src, by_kind["constant"])
    assert "return None" in apply_mutation(src, by_kind["return_none"])


def test_constant_variants():
    src = "A = 0\nB = 1\nC = 7\nD = True\nE = 2.5\nF = 'text'\nG = None\n"
    assert [m.description for m in collect_mutations(src)] == [
        "`0` -> `1`", "`1` -> `0`", "`7` -> `8`", "`True` -> `False`", "`2.5` -> `5.0`"]


def test_import_name():
    imp = mutation_score.import_name_for
    assert imp(Path("mod.py")) == "mod"
    assert imp(Path("src/pkg/mod.py")) == "pkg.mod"
    assert imp(Path("pkg/sub/__init__.py")) == "pkg.sub"


def _project(tmp_path, tests):
    (tmp_path / "calc.py").write_text(
        "def clamp(x, lo, hi):\n"
        "    if lo > hi:\n"
        "        raise ValueError('lo > hi')\n"
        "    return max(lo, min(x, hi))\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_calc.py").write_text(tests)
    return tmp_path


WEAK = "from calc import clamp\n\ndef test_it():\n    assert clamp(5, 0, 10)\n"
STRONG = textwrap.dedent("""
    import pytest
    from calc import clamp

    @pytest.mark.parametrize("x,exp", [(-1, 0), (0, 0), (5, 5), (10, 10), (11, 10)])
    def test_clamp(x, exp):
        assert clamp(x, 0, 10) == exp

    def test_equal_bounds():
        assert clamp(7, 3, 3) == 3

    def test_invalid():
        with pytest.raises(ValueError, match="lo > hi"):
            clamp(1, 3, 2)
""")


def test_weak_tests_leave_survivors(tmp_path):
    rep = run(_project(tmp_path, WEAK), Path("calc.py"), ["tests/test_calc.py"], workers=2)
    assert rep.error is None and rep.baseline_ok
    assert rep.survived >= 2 and rep.score < 70
    assert any(s["mutation"] == "`>` -> `>=`" and s["line"] == 2 for s in rep.survivors)


def test_strong_tests_kill_everything(tmp_path):
    rep = run(_project(tmp_path, STRONG), Path("calc.py"), ["tests/test_calc.py"], workers=2)
    assert (rep.score, rep.survived) == (100.0, 0)


def test_original_files_untouched(tmp_path):
    proj = _project(tmp_path, WEAK)
    before = (proj / "calc.py").read_text()
    run(proj, Path("calc.py"), ["tests/test_calc.py"], workers=2)
    assert (proj / "calc.py").read_text() == before


def test_failing_baseline_is_an_error(tmp_path):
    proj = _project(tmp_path, "from calc import clamp\n\ndef test_x():\n    assert clamp(1, 0, 2) == 5\n")
    rep = run(proj, Path("calc.py"), ["tests/test_calc.py"])
    assert rep.error and "do not pass" in rep.error and rep.score is None


def test_deselect_failing(tmp_path):
    tests = STRONG + "\n\ndef test_wrong():\n    assert clamp(1, 0, 2) == 5\n"
    rep = run(_project(tmp_path, tests), Path("calc.py"), ["tests/test_calc.py"],
              deselect_failing=True, workers=2)
    assert rep.deselected == ["tests/test_calc.py::test_wrong"]
    assert rep.score == 100.0


def test_infinite_loop_mutant_times_out(tmp_path):
    (tmp_path / "loop.py").write_text(
        "def countdown(n):\n    steps = 0\n    while n > 0:\n        n -= 1\n"
        "        steps += 1\n    return steps\n")
    (tmp_path / "test_loop.py").write_text(
        "from loop import countdown\n\ndef test_it():\n    assert countdown(3) == 3\n")
    rep = run(tmp_path, Path("loop.py"), ["test_loop.py"], workers=2)
    assert rep.timeouts >= 1
    assert rep.survived == 0


def test_cli_json(tmp_path):
    proj = _project(tmp_path, WEAK)
    out = subprocess.run([sys.executable, str(SCRIPT), "--module", "calc.py", "--tests",
                          "tests/test_calc.py", "--json"], cwd=proj, capture_output=True,
                         text=True, check=True).stdout
    data = json.loads(out)
    assert data["total"] == data["killed"] + data["survived"]
    assert data["survivors"]


def test_cli_text_and_exit_code(tmp_path):
    proj = _project(tmp_path, "def test_x():\n    assert False\n")
    res = subprocess.run([sys.executable, str(SCRIPT), "--module", "calc.py", "--tests",
                          "tests/test_calc.py"], cwd=proj, capture_output=True, text=True)
    assert res.returncode == 2
    assert res.stdout.startswith("ERROR:")

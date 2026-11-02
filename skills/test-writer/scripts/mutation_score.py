#!/usr/bin/env python3
"""Mutation testing for one Python module: how many injected bugs do the tests catch?

Each "mutant" is a copy of the module with exactly one small bug (`<` -> `<=`,
`+` -> `-`, `and` -> `or`, a constant off by one, a dropped call, `return None`...).
A mutant is *killed* if the tests fail on it and *survives* if they still pass.
Mutation score = killed / total. Surviving mutants point at behaviour no test checks.

Only the standard library and pytest are required.

Usage (from the project root):
    python mutation_score.py --module src/pkg/mod.py --tests tests/test_mod.py
    python mutation_score.py --module mod.py --tests test_mod.py --json

The project is copied to a temporary directory, so your files are never modified.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from queue import Queue

IGNORE_DIRS = {".git", ".hg", ".venv", "venv", "env", "node_modules", "__pycache__",
               ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", "build", "dist",
               ".hypothesis", ".idea", ".vscode"}

_BINOP_SWAP = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult,
               ast.FloorDiv: ast.Div, ast.Mod: ast.FloorDiv, ast.Pow: ast.Mult}
_CMP_SWAP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
             ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.In: ast.NotIn, ast.NotIn: ast.In,
             ast.Is: ast.IsNot, ast.IsNot: ast.Is}
_OP_TEXT = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "//",
            ast.Mod: "%", ast.Pow: "**", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">",
            ast.GtE: ">=", ast.Eq: "==", ast.NotEq: "!=", ast.In: "in", ast.NotIn: "not in",
            ast.Is: "is", ast.IsNot: "is not", ast.And: "and", ast.Or: "or"}
_FUNC_SWAP = {"min": "max", "max": "min", "any": "all", "all": "any"}


@dataclass
class Mutation:
    index: int
    kind: str
    lineno: int
    description: str
    variant: int = 0
    col: int = 0


@dataclass
class MutantResult:
    mutation: Mutation
    status: str
    seconds: float = 0.0


def _walk(tree: ast.AST):
    """Deterministic DFS yielding (node, parent, field, index_in_list). Skips annotations,
    docstrings and f-string internals, where mutations only produce noise."""
    stack = [(tree, None, None, None)]
    while stack:
        node, parent, fname, idx = stack.pop()
        yield node, parent, fname, idx
        children = []
        for name, value in ast.iter_fields(node):
            if name in ("annotation", "returns", "type_comment"):
                continue
            if isinstance(node, ast.JoinedStr):
                continue
            if isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, ast.AST):
                        if (name == "body" and i == 0 and _is_docstring(item)):
                            continue
                        children.append((item, node, name, i))
            elif isinstance(value, ast.AST):
                children.append((value, node, name, None))
        stack.extend(reversed(children))


def _is_docstring(node: ast.AST) -> bool:
    return (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str))


def _is_main_guard(node: ast.AST) -> bool:
    return (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__")


def _const_variant(value):
    if isinstance(value, bool):
        return not value, f"`{value}` -> `{not value}`"
    if isinstance(value, int):
        new = 1 if value == 0 else (0 if value == 1 else value + 1)
        return new, f"`{value}` -> `{new}`"
    if isinstance(value, float):
        new = value * 2 if value else 1.0
        return new, f"`{value}` -> `{new}`"
    return None


def collect_mutations(source: str) -> list[Mutation]:
    tree = ast.parse(source)
    skip: set[int] = set()
    for node in ast.walk(tree):
        if _is_main_guard(node):
            skip.update(id(n) for n in ast.walk(node))
    out: list[Mutation] = []
    for i, (node, _parent, _f, _idx) in enumerate(_walk(tree)):
        if id(node) in skip:
            continue
        line = getattr(node, "lineno", 0)
        start = len(out)
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOP_SWAP:
            new = _BINOP_SWAP[type(node.op)]
            out.append(Mutation(i, "binop", line,
                                f"`{_OP_TEXT[type(node.op)]}` -> `{_OP_TEXT[new]}`"))
        elif isinstance(node, ast.AugAssign) and type(node.op) in _BINOP_SWAP:
            new = _BINOP_SWAP[type(node.op)]
            out.append(Mutation(i, "augassign", line,
                                f"`{_OP_TEXT[type(node.op)]}=` -> `{_OP_TEXT[new]}=`"))
        elif isinstance(node, ast.Compare):
            for k, op in enumerate(node.ops):
                if type(op) in _CMP_SWAP:
                    new = _CMP_SWAP[type(op)]
                    out.append(Mutation(i, "compare", line,
                                        f"`{_OP_TEXT[type(op)]}` -> `{_OP_TEXT[new]}`", k))
        elif isinstance(node, ast.BoolOp):
            new = ast.Or if isinstance(node.op, ast.And) else ast.And
            out.append(Mutation(i, "boolop", line,
                                f"`{_OP_TEXT[type(node.op)]}` -> `{_OP_TEXT[new]}`"))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.Not, ast.USub)):
            sym = "not " if isinstance(node.op, ast.Not) else "-"
            out.append(Mutation(i, "unary", line, f"removed `{sym.strip()}`"))
        elif isinstance(node, ast.If):
            out.append(Mutation(i, "negate_if", line, "condition negated (`if not (...)`)"))
        elif isinstance(node, ast.Constant) and _const_variant(node.value) is not None:
            out.append(Mutation(i, "constant", line, _const_variant(node.value)[1]))
        elif isinstance(node, ast.Return) and node.value is not None and not (
                isinstance(node.value, ast.Constant) and node.value.value is None):
            out.append(Mutation(i, "return_none", line, "`return ...` -> `return None`"))
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            out.append(Mutation(i, "drop_call", line, "call statement removed"))
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id in _FUNC_SWAP):
            out.append(Mutation(i, "func_swap", line,
                                f"`{node.func.id}()` -> `{_FUNC_SWAP[node.func.id]}()`"))
        for m in out[start:]:
            m.col = getattr(node, "col_offset", -1) + 1
    return out


def apply_mutation(source: str, m: Mutation) -> str:
    tree = ast.parse(source)
    for i, (node, parent, fname, idx) in enumerate(_walk(tree)):
        if i != m.index:
            continue
        if m.kind in ("binop", "augassign"):
            node.op = _BINOP_SWAP[type(node.op)]()
        elif m.kind == "compare":
            node.ops[m.variant] = _CMP_SWAP[type(node.ops[m.variant])]()
        elif m.kind == "boolop":
            node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
        elif m.kind == "unary":
            _replace(parent, fname, idx, node.operand)
        elif m.kind == "negate_if":
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
        elif m.kind == "constant":
            node.value = _const_variant(node.value)[0]
        elif m.kind == "return_none":
            node.value = ast.Constant(value=None)
        elif m.kind == "drop_call":
            _replace(parent, fname, idx, ast.Pass())
        elif m.kind == "func_swap":
            node.func = ast.Name(id=_FUNC_SWAP[node.func.id], ctx=ast.Load())
        break
    else:
        raise ValueError(f"mutation index {m.index} not found")
    return ast.unparse(ast.fix_missing_locations(tree)) + "\n"


def _replace(parent, fname, idx, new):
    if idx is None:
        setattr(parent, fname, new)
    else:
        getattr(parent, fname)[idx] = new


def import_name_for(module_rel: Path) -> str:
    parts = list(module_rel.with_suffix("").parts)
    if parts and parts[0] in ("src", "lib"):
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _env(root: Path) -> dict:
    env = dict(os.environ)
    paths = [str(root), str(root / "src")]
    if env.get("PYTHONPATH"):
        paths.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(paths)
    env["PYTHONDONTWRITEBYTECODE"] = "1"   # stale .pyc would hide mutations
    env.pop("PYTEST_ADDOPTS", None)
    return env


def _pytest_cmd(tests: list[str], deselect: list[str], extra: list[str],
                cache_dir: Path | None = None) -> list[str]:
    cmd = [sys.executable, "-m", "pytest", "-q", "--no-header"]
    if cache_dir is None:
        cmd += ["-x", "-p", "no:cacheprovider"]
    else:
        cmd += ["-o", f"cache_dir={cache_dir}"]
    if _HAS_HYPOTHESIS:
        cmd.append("--hypothesis-seed=0")
    cmd += [*tests, *extra]
    for d in deselect:
        cmd += ["--deselect", d]
    return cmd


_HAS_HYPOTHESIS = importlib.util.find_spec("hypothesis") is not None


def _failed_ids(cache_dir: Path) -> list[str]:
    path = cache_dir / "v" / "cache" / "lastfailed"
    if not path.exists():
        return []
    return sorted(json.loads(path.read_text(encoding="utf-8")))


def _run(cmd, cwd: Path, timeout: float):
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, cwd=cwd, env=_env(cwd), capture_output=True, text=True,
                              timeout=timeout)
        return proc.returncode, proc.stdout + proc.stderr, time.monotonic() - started
    except subprocess.TimeoutExpired:
        return None, "timeout", time.monotonic() - started


def _copy_project(root: Path, dest: Path) -> Path:
    shutil.copytree(root, dest, ignore=lambda d, names: [n for n in names if n in IGNORE_DIRS
                                                           or n.endswith(".pyc")])
    return dest


@dataclass
class Report:
    module: str
    tests: list[str]
    total: int = 0
    killed: int = 0
    survived: int = 0
    timeouts: int = 0
    score: float | None = None
    baseline_ok: bool = False
    baseline_output: str = ""
    deselected: list[str] = field(default_factory=list)
    survivors: list[dict] = field(default_factory=list)
    seconds: float = 0.0
    error: str | None = None


def run(project: Path, module: Path, tests: list[str], workers: int = 0,
        deselect_failing: bool = False, extra_pytest_args: list[str] | None = None,
        max_mutants: int | None = None) -> Report:
    started = time.monotonic()
    project = project.resolve()
    module_abs = (project / module).resolve() if not module.is_absolute() else module
    module_rel = module_abs.relative_to(project)
    report = Report(module=str(module_rel), tests=tests)
    extra = extra_pytest_args or []
    source = module_abs.read_text(encoding="utf-8")

    tmp = Path(tempfile.mkdtemp(prefix="mutscore-"))
    try:
        base_dir = _copy_project(project, tmp / "base")

        name = import_name_for(module_rel)
        code, out, _ = _run([sys.executable, "-c",
                             f"import importlib; print(importlib.import_module({name!r}).__file__)"],
                            base_dir, 60)
        if code == 0:
            resolved = Path(out.strip().splitlines()[-1]).resolve()
            if base_dir.resolve() not in resolved.parents:
                report.error = (f"`import {name}` resolves to {resolved}, not to the project copy. "
                                "Another copy of the package (e.g. a non-editable install) shadows "
                                "your source, so mutations would be invisible. Reinstall with "
                                "`pip install -e .` or uninstall the package.")
                return report

        cache_dir = tmp / "pytest-cache"
        code, out, base_t = _run(_pytest_cmd(tests, [], extra + ["-rfE", "--tb=short"], cache_dir),
                                 base_dir, 600)
        failing = _failed_ids(cache_dir)
        if code == 1 and deselect_failing:
            report.deselected = failing
            code, out, base_t = _run(_pytest_cmd(tests, report.deselected, extra), base_dir, 600)
        report.baseline_output = out[-3000:]
        if code != 0:
            what = (f"{len(failing)} test(s) fail on the original code: "
                    + ", ".join(failing[:8]) if code == 1 and failing
                    else f"pytest could not run the tests (exit code {code}, e.g. a syntax "
                         "error, an import error or invalid parametrize arguments)")
            report.error = f"{what}. Fix the tests before measuring mutation score"
            return report
        report.baseline_ok = True

        mutations = collect_mutations(source)
        if max_mutants:
            mutations = mutations[:max_mutants]
        timeout = max(10.0, base_t * 5 + 5)
        workers = workers or min(4, os.cpu_count() or 1)
        pool: Queue = Queue()
        for w in range(workers):
            pool.put(_copy_project(project, tmp / f"w{w}"))

        def one(m: Mutation) -> MutantResult:
            wdir = pool.get()
            target = wdir / module_rel
            try:
                target.write_text(apply_mutation(source, m), encoding="utf-8")
                rc, _, secs = _run(_pytest_cmd(tests, report.deselected, extra), wdir, timeout)
            except Exception:  # a mutant that cannot be built counts as killed
                return MutantResult(m, "error")
            finally:
                target.write_text(source, encoding="utf-8")
                shutil.rmtree(wdir / ".hypothesis", ignore_errors=True)
                pool.put(wdir)
            if rc is None:
                return MutantResult(m, "timeout", secs)
            return MutantResult(m, "survived" if rc == 0 else "killed", secs)

        with ThreadPoolExecutor(max_workers=workers) as ex:
            results = list(ex.map(one, mutations))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    lines = source.splitlines()
    report.total = len(results)
    report.survived = sum(r.status == "survived" for r in results)
    report.timeouts = sum(r.status == "timeout" for r in results)
    report.killed = report.total - report.survived
    report.score = round(100 * report.killed / report.total, 1) if report.total else None
    for r in results:
        if r.status == "survived":
            m = r.mutation
            code_line = lines[m.lineno - 1].strip() if 0 < m.lineno <= len(lines) else ""
            report.survivors.append({"line": m.lineno, "col": m.col, "code": code_line,
                                     "mutation": m.description, "kind": m.kind})
    report.seconds = round(time.monotonic() - started, 1)
    return report


def format_report(r: Report, max_survivors: int = 20) -> str:
    if r.error:
        msg = f"ERROR: {r.error}"
        if r.baseline_output and not r.baseline_ok:
            msg += "\n\n--- pytest output ---\n" + r.baseline_output[-1500:]
        return msg
    out = [f"Mutation score: {r.score}%  ({r.killed}/{r.total} mutants killed, "
           f"{r.survived} survived, {r.timeouts} timeouts) in {r.seconds}s"]
    if r.deselected:
        out.append(f"Note: {len(r.deselected)} test(s) failing on the original code were "
                   f"excluded: {', '.join(r.deselected[:5])}")
    if r.survivors:
        out.append("\nSurviving mutants (behaviour that no test checks):")
        for s in r.survivors[:max_survivors]:
            where = f"line {s['line']}:{s['col']}"
            out.append(f"  {where:<12} {s['mutation']:<34} | {s['code']}")
        if len(r.survivors) > max_survivors:
            out.append(f"  ... and {len(r.survivors) - max_survivors} more")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--module", required=True, help="path to the module under test")
    p.add_argument("--tests", required=True, nargs="+", help="test file(s) or directories")
    p.add_argument("--project", default=".", help="project root (default: current directory)")
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--deselect-failing", action="store_true",
                   help="ignore tests that already fail on the original code")
    p.add_argument("--max-survivors", type=int, default=20)
    p.add_argument("--json", action="store_true", help="machine-readable output")
    args = p.parse_args(argv)

    rep = run(Path(args.project), Path(args.module), args.tests, args.workers,
              args.deselect_failing)
    if args.json:
        print(json.dumps(asdict(rep), ensure_ascii=False, indent=2))
    else:
        print(format_report(rep, args.max_survivors))
    return 0 if rep.error is None else 2


if __name__ == "__main__":
    sys.exit(main())

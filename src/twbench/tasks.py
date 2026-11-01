"""Benchmark tasks: a module to test, an empty workspace, a reference test suite."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from . import REFERENCE_DIR, TASKS_DIR


@dataclass
class Task:
    name: str
    module_path: Path
    reference_tests: Path

    @property
    def source(self) -> str:
        return self.module_path.read_text(encoding="utf-8")

    @property
    def test_rel(self) -> str:
        return f"tests/test_{self.name}.py"


def all_tasks() -> list[Task]:
    return [Task(p.stem, p, REFERENCE_DIR / f"test_{p.stem}.py")
            for p in sorted(TASKS_DIR.glob("*.py"))]


def select(names: str) -> list[Task]:
    tasks = all_tasks()
    if names in ("", "all"):
        return tasks
    wanted = [n.strip() for n in names.split(",")]
    by_name = {t.name: t for t in tasks}
    missing = [n for n in wanted if n not in by_name]
    if missing:
        raise SystemExit(f"unknown task(s): {missing}; available: {sorted(by_name)}")
    return [by_name[n] for n in wanted]


def make_workspace(task: Task, dest: Path, tests: str | None = None) -> Path:
    """Workspace = the module + tests/ folder. Optionally pre-filled with a test file."""
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "tests").mkdir(parents=True)
    shutil.copy(task.module_path, dest / task.module_path.name)
    if tests is not None:
        (dest / task.test_rel).write_text(tests, encoding="utf-8")
    return dest


_COUNT = re.compile(r"(\d+) (passed|failed|error|errors|xfailed|xpassed|skipped)")


def run_pytest(workspace: Path, test_rel: str, timeout: float = 120) -> tuple[int | None, str, dict]:
    """Run the tests against the original module. Returns (exit code, output, counts)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(workspace)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTEST_ADDOPTS", None)
    cmd = [sys.executable, "-m", "pytest", "-q", "-rfE", "--no-header", "-p", "no:cacheprovider",
           "--tb=short", test_rel]
    try:
        proc = subprocess.run(cmd, cwd=workspace, env=env, capture_output=True, text=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, f"pytest timed out after {timeout}s", {}
    out = proc.stdout + proc.stderr
    counts: dict[str, int] = {}
    tail = out.strip().splitlines()[-1] if out.strip() else ""
    for n, kind in _COUNT.findall(tail):
        key = "error" if kind.startswith("error") else kind
        counts[key] = counts.get(key, 0) + int(n)
    return proc.returncode, out, counts

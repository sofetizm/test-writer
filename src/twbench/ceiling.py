"""Ceiling: mutation score of the hand-written reference suites (bench/reference/).

Some mutants are *equivalent*: they do not change observable behaviour and cannot be
killed by any test, so 100% is not always reachable. Scores are also reported relative
to this ceiling.

  python -m twbench.ceiling          # recompute bench/ceiling.json
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from . import ROOT
from .mutation import run as run_mutation
from .tasks import all_tasks, make_workspace

CEILING_FILE = ROOT / "bench" / "ceiling.json"


def compute() -> dict:
    result = {}
    for task in all_tasks():
        with tempfile.TemporaryDirectory() as tmp:
            ws = make_workspace(task, Path(tmp) / "ws",
                                tests=task.reference_tests.read_text(encoding="utf-8"))
            rep = run_mutation(ws, Path(task.module_path.name), [task.test_rel])
        if rep.error:
            raise RuntimeError(f"{task.name}: {rep.error}")
        result[task.name] = {"score": rep.score, "killed": rep.killed, "total": rep.total,
                             "equivalent_survivors": rep.survivors}
        print(f"{task.name:<16} {rep.score:5.1f}%  ({rep.killed}/{rep.total})")
    return result


def load_ceiling() -> dict:
    if not CEILING_FILE.exists():
        return {}
    return {k: v["score"] for k, v in json.loads(CEILING_FILE.read_text()).items()}


def main() -> None:
    data = compute()
    CEILING_FILE.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"saved {CEILING_FILE}")


if __name__ == "__main__":
    main()

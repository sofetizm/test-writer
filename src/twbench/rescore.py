"""Re-score saved test files without calling the model again.

Use after a change in the scoring code: every results/**/metrics.json is re-evaluated
from the test file saved next to it; the episode data (turns, tokens) is kept.

  python -m twbench.rescore --results results
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from .ceiling import load_ceiling
from .run import evaluate_tests
from .tasks import make_workspace, select


def rescore(results: Path) -> list[tuple[str, float, float]]:
    ceiling = load_ceiling()
    changes = []
    for metrics_path in sorted(results.rglob("metrics.json")):
        m = json.loads(metrics_path.read_text(encoding="utf-8"))
        task = select(m["task"])[0]
        saved = metrics_path.parent / Path(task.test_rel).name
        tests = saved.read_text(encoding="utf-8") if saved.exists() else None
        ws = make_workspace(task, metrics_path.parent / "ws", tests=tests)
        try:
            fresh = evaluate_tests(task, ws)
        finally:
            shutil.rmtree(ws, ignore_errors=True)
        old = m.get("score", 0.0)
        for key in ("valid", "score", "reason", "killed", "total", "survivors", "tests_passed",
                    "tests_failed", "tests_error", "pytest_exit", "excluded_tests"):
            m.pop(key, None)
        m.update(fresh)
        m["ceiling"] = ceiling.get(task.name)
        metrics_path.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
        changes.append((str(metrics_path.parent.relative_to(results)), old, m["score"]))
        print(f"{changes[-1][0]:<45} {old:5.1f}% -> {m['score']:5.1f}%")
    return changes


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results", default="results")
    rescore(Path(p.parse_args().results))


if __name__ == "__main__":
    main()

"""Run the benchmark: every task × condition × repeat, with resume.

Example (free Groq tier):
  export OPENAI_API_KEY=... OPENAI_BASE_URL=https://api.groq.com/openai/v1
  python -m twbench.run --backend openai --model openai/gpt-oss-120b --name gpt-oss-120b \\
      --conditions baseline,skill --reasoning-effort low --rpm 10

Each episode is saved to results/<name>/<task>/<condition>/r<k>/. Finished episodes are
skipped when the command is run again, so a run interrupted by rate limits can be resumed.
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from .agent import run_episode
from .backends import HFLocal, OpenAICompatible
from .ceiling import load_ceiling
from .conditions import parse_conditions
from .mutation import run as run_mutation
from .tasks import run_pytest, select


def evaluate_tests(task, workspace: Path) -> dict:
    """Score the final test file: pass/fail on the original code, then mutation score.
    Tests failing on the original code are excluded (they would 'kill' every mutant)."""
    test_path = workspace / task.test_rel
    if not test_path.exists():
        return {"valid": False, "score": 0.0, "reason": "no test file"}
    code, out, counts = run_pytest(workspace, task.test_rel)
    rep = run_mutation(workspace, Path(task.module_path.name), [task.test_rel],
                       deselect_failing=True)
    result = {"tests_passed": counts.get("passed", 0), "tests_failed": counts.get("failed", 0),
              "tests_error": counts.get("error", 0), "pytest_exit": code,
              "excluded_tests": len(rep.deselected)}
    if rep.error or not rep.total:
        return {**result, "valid": False, "score": 0.0, "reason": rep.error or "no mutants"}
    return {**result, "valid": True, "score": rep.score, "killed": rep.killed,
            "total": rep.total, "survivors": rep.survivors}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--backend", choices=["openai", "hf"], default="openai")
    p.add_argument("--model", required=True)
    p.add_argument("--name", help="run name in reports (default: model name)")
    p.add_argument("--conditions", default="baseline,skill")
    p.add_argument("--tasks", default="all", help="comma-separated task names or 'all'")
    p.add_argument("--repeats", type=int, default=1)
    p.add_argument("--max-turns", type=int, default=6)
    p.add_argument("--out", default="results")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--max-tokens", type=int, default=4096)
    p.add_argument("--reasoning-effort", choices=["low", "medium", "high"])
    p.add_argument("--rpm", type=float, default=0.0, help="max requests per minute")
    p.add_argument("--price-in", type=float, default=0.0, help="USD per 1M input tokens")
    p.add_argument("--price-out", type=float, default=0.0, help="USD per 1M output tokens")
    p.add_argument("--no-4bit", action="store_true", help="hf backend: load in full precision")
    args = p.parse_args()

    name = args.name or args.model.split("/")[-1]
    tasks = select(args.tasks)
    conditions = parse_conditions(args.conditions)
    if args.backend == "openai":
        backend = OpenAICompatible(args.model, args.price_in, args.price_out, args.max_tokens,
                                   args.temperature, args.rpm, args.reasoning_effort)
    else:
        backend = HFLocal(args.model, load_in_4bit=not args.no_4bit,
                          max_new_tokens=args.max_tokens)
    ceiling = load_ceiling()
    root = Path(args.out) / name
    root.mkdir(parents=True, exist_ok=True)
    (root / "run_config.json").write_text(json.dumps(
        {**backend.describe(), "max_turns": args.max_turns,
         "conditions": [c.name for c in conditions]}, indent=2))

    total = len(tasks) * len(conditions) * args.repeats
    done = 0
    # repeat -> task -> condition: a partial run stays balanced between conditions
    for r in range(args.repeats):
        for task in tasks:
            for cond in conditions:
                done += 1
                out = root / task.name / cond.name / f"r{r}"
                if (out / "metrics.json").exists():
                    print(f"[{done}/{total}] {task.name:<16} {cond.name:<11} r{r}: already done")
                    continue
                out.mkdir(parents=True, exist_ok=True)
                started = time.monotonic()
                ws = out / "ws"
                try:
                    ep = run_episode(backend, task, cond, ws, args.max_turns)
                except Exception as e:
                    print(f"[{done}/{total}] {task.name:<16} {cond.name:<11} r{r}: "
                          f"ERROR {type(e).__name__}: {str(e)[:200]}")
                    shutil.rmtree(ws, ignore_errors=True)
                    continue
                metrics = evaluate_tests(task, ws)
                test_file = ws / task.test_rel
                if test_file.exists():
                    shutil.copy(test_file, out / test_file.name)
                shutil.rmtree(ws, ignore_errors=True)
                metrics.update({"task": task.name, "condition": cond.name, "repeat": r,
                                "run": name, "ceiling": ceiling.get(task.name),
                                "episode": ep.summary(),
                                "wall_seconds": round(time.monotonic() - started, 1)})
                (out / "transcript.json").write_text(
                    json.dumps(ep.transcript, ensure_ascii=False, indent=1), encoding="utf-8")
                (out / "metrics.json").write_text(
                    json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")
                print(f"[{done}/{total}] {task.name:<16} {cond.name:<11} r{r}: "
                      f"score {metrics['score']:5.1f}%  turns {ep.turns}  "
                      f"actions {','.join(ep.actions) or '-'}  "
                      f"tokens {ep.input_tokens + ep.output_tokens}", flush=True)
    print(f"Done. Report: python -m twbench.report --results {args.out}")


if __name__ == "__main__":
    main()

"""Aggregate results/**/metrics.json into results/RESULTS.md and a chart.

The headline number is the *paired* difference skill − baseline on the same task and
repeat, with a bootstrap 95% confidence interval: tasks differ a lot in difficulty, and
pairing removes that variance from the comparison.

  python -m twbench.report --results results
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path


def load(results: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(results.rglob("metrics.json"))]


def bootstrap_ci(values: list[float], n: int = 5000, seed: int = 0) -> tuple[float, float]:
    if len(values) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    means = sorted(statistics.fmean(rng.choices(values, k=len(values))) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n) - 1]


def _rel(m: dict) -> float:
    c = m.get("ceiling") or 100.0
    return min(100.0, 100.0 * m["score"] / c) if c else 0.0


def summarize(rows: list[dict]) -> dict:
    by = defaultdict(list)
    for m in rows:
        by[(m["run"], m["condition"])].append(m)
    summary = {}
    for (run, cond), ms in sorted(by.items()):
        eps = [m["episode"] for m in ms]
        summary[(run, cond)] = {
            "n": len(ms),
            "score": statistics.fmean(m["score"] for m in ms),
            "rel": statistics.fmean(_rel(m) for m in ms),
            "valid": 100 * sum(m["valid"] for m in ms) / len(ms),
            "tests": statistics.fmean(m.get("tests_passed", 0) for m in ms),
            "failing": statistics.fmean(m.get("excluded_tests", 0) for m in ms),
            "turns": statistics.fmean(e["turns"] for e in eps),
            "tokens": statistics.fmean(e["input_tokens"] + e["output_tokens"] for e in eps),
            "cost": sum(e["cost_usd"] for e in eps),
        }
    return summary


def paired(rows: list[dict], a: str = "baseline", b: str = "skill") -> dict:
    idx = {(m["run"], m["task"], m["repeat"], m["condition"]): m for m in rows}
    out = {}
    for run in sorted({m["run"] for m in rows}):
        deltas = []
        for (r, task, rep, cond), m in idx.items():
            if r == run and cond == b and (run, task, rep, a) in idx:
                deltas.append(m["score"] - idx[(run, task, rep, a)]["score"])
        if deltas:
            lo, hi = bootstrap_ci(deltas)
            out[run] = {"n": len(deltas), "mean": statistics.fmean(deltas), "lo": lo, "hi": hi,
                        "wins": sum(d > 0 for d in deltas), "ties": sum(d == 0 for d in deltas),
                        "losses": sum(d < 0 for d in deltas)}
    return out


def per_task(rows: list[dict]) -> tuple[list[str], list[str], dict]:
    cols = sorted({(m["run"], m["condition"]) for m in rows})
    tasks = sorted({m["task"] for m in rows})
    cell = defaultdict(list)
    for m in rows:
        cell[(m["task"], (m["run"], m["condition"]))].append(m["score"])
    return tasks, cols, {k: statistics.fmean(v) for k, v in cell.items()}


def plot(rows: list[dict], path: Path, a: str = "baseline", b: str = "skill") -> bool:
    """Per-task dumbbell chart: one row per task, a dot per condition, a line between them."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    runs = sorted({m["run"] for m in rows})
    score = defaultdict(list)
    for m in rows:
        score[(m["run"], m["task"], m["condition"])].append(m["score"])
    if not any(k[2] == b for k in score) or not any(k[2] == a for k in score):
        return False
    fig, axes = plt.subplots(1, len(runs), figsize=(5.2 * len(runs), 4.6), squeeze=False)
    for ax, run in zip(axes[0], runs, strict=True):
        tasks = sorted({t for r, t, _ in score if r == run},
                       key=lambda t: statistics.fmean(score.get((run, t, a), [0])))
        for y, t in enumerate(tasks):
            va = statistics.fmean(score[(run, t, a)]) if (run, t, a) in score else None
            vb = statistics.fmean(score[(run, t, b)]) if (run, t, b) in score else None
            if va is not None and vb is not None:
                color = "#1f6feb" if vb > va else "#cf222e" if vb < va else "#9aa5b1"
                ax.plot([va, vb], [y, y], color=color, lw=2, zorder=1)
            if va is not None:
                ax.scatter(va, y, color="#9aa5b1", s=40, zorder=2, label=a if y == 0 else None)
            if vb is not None:
                ax.scatter(vb, y, color="#1f6feb", s=40, zorder=3, label=b if y == 0 else None)
        ax.set_yticks(range(len(tasks)))
        ax.set_yticklabels(tasks)
        ax.set_xlabel("Mutation score, %")
        ax.set_title(run, fontsize=11)
        ax.grid(axis="x", alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return True


def render(rows: list[dict], results: Path) -> str:
    s = summarize(rows)
    lines = ["# Results", "",
             "| Run | Condition | Episodes | Mutation score, % | % of ceiling | Valid suites, % "
             "| Passing tests | Tests failing on correct code | Turns | Tokens / episode | Cost, $ |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for (run, cond), v in s.items():
        lines.append(f"| {run} | {cond} | {v['n']} | **{v['score']:.1f}** | {v['rel']:.1f} | "
                     f"{v['valid']:.0f} | {v['tests']:.1f} | {v['failing']:.1f} | {v['turns']:.1f} "
                     f"| {v['tokens']:.0f} | {v['cost']:.3f} |")
    for a, b in (("baseline", "skill"), ("baseline", "skill-text"), ("skill-text", "skill")):
        pr = paired(rows, a, b)
        if not pr:
            continue
        lines += ["", f"## Paired difference: {b} − {a}", "",
                  "| Run | Pairs | Mean Δ, p.p. | 95% CI (bootstrap) | Better / same / worse |",
                  "|---|---|---|---|---|"]
        for run, v in pr.items():
            lines.append(f"| {run} | {v['n']} | **{v['mean']:+.1f}** | "
                         f"[{v['lo']:+.1f}; {v['hi']:+.1f}] | "
                         f"{v['wins']} / {v['ties']} / {v['losses']} |")
    tasks, cols, cell = per_task(rows)
    lines += ["", "## By task (mutation score, %)", "",
              "| Task | " + " | ".join(f"{r} · {c}" for r, c in cols) + " |",
              "|---|" + "---|" * len(cols)]
    for t in tasks:
        vals = [f"{cell[(t, c)]:.0f}" if (t, c) in cell else "—" for c in cols]
        lines.append(f"| {t} | " + " | ".join(vals) + " |")
    if plot(rows, results / "scores.png"):
        lines += ["", "![scores](scores.png)"]
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results", default="results")
    args = p.parse_args()
    results = Path(args.results)
    rows = load(results)
    if not rows:
        raise SystemExit(f"no metrics.json under {results}")
    text = render(rows, results)
    (results / "RESULTS.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

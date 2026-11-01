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


def plot(summary: dict, path: Path) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    runs = sorted({r for r, _ in summary})
    conds = [c for c in ("baseline", "skill-text", "skill") if any((r, c) in summary for r in runs)]
    colors = {"baseline": "#9aa5b1", "skill-text": "#7fb3d5", "skill": "#1f6feb"}
    width = 0.8 / max(len(conds), 1)
    fig, ax = plt.subplots(figsize=(1.8 + 1.6 * len(runs) * max(len(conds), 1) / 2, 4))
    for i, c in enumerate(conds):
        xs = [j + i * width for j in range(len(runs))]
        ys = [summary.get((r, c), {}).get("score", 0) for r in runs]
        bars = ax.bar(xs, ys, width, label=c, color=colors.get(c))
        ax.bar_label(bars, fmt="%.0f", fontsize=8, padding=2)
    ax.set_xticks([j + width * (len(conds) - 1) / 2 for j in range(len(runs))])
    ax.set_xticklabels(runs)
    ax.set_ylabel("Mutation score, %")
    ax.set_ylim(0, 105)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, ncols=len(conds), loc="upper center", bbox_to_anchor=(0.5, 1.12))
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
    if plot(s, results / "scores.png"):
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

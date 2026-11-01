import math

import pytest

from twbench.report import bootstrap_ci, paired, render, summarize


def row(task, cond, score, run="m", rep=0, ceiling=100.0):
    return {"task": task, "condition": cond, "score": score, "run": run, "repeat": rep,
            "ceiling": ceiling, "valid": score > 0, "tests_passed": 5, "excluded_tests": 0,
            "episode": {"turns": 3, "input_tokens": 1000, "output_tokens": 200, "cost_usd": 0.01}}


ROWS = [row("a", "baseline", 40), row("a", "skill", 90), row("b", "baseline", 60),
        row("b", "skill", 60), row("c", "baseline", 80), row("c", "skill", 70, ceiling=87.5)]


def test_summary():
    s = summarize(ROWS)
    assert s[("m", "baseline")]["score"] == pytest.approx(60)
    assert s[("m", "skill")]["score"] == pytest.approx(220 / 3)
    assert s[("m", "skill")]["rel"] == pytest.approx((90 + 60 + 80) / 3)
    assert s[("m", "skill")]["cost"] == pytest.approx(0.03)


def test_paired():
    p = paired(ROWS)["m"]
    assert p["n"] == 3 and p["mean"] == pytest.approx((50 + 0 - 10) / 3)
    assert (p["wins"], p["ties"], p["losses"]) == (1, 1, 1)
    assert p["lo"] <= p["mean"] <= p["hi"]


def test_bootstrap_ci_constant_and_small():
    assert bootstrap_ci([5.0, 5.0, 5.0]) == (5.0, 5.0)
    lo, hi = bootstrap_ci([1.0])
    assert math.isnan(lo) and math.isnan(hi)


def test_render(tmp_path):
    text = render(ROWS, tmp_path)
    assert "| m | skill | 3 | **73.3**" in text
    assert "Paired difference: skill − baseline" in text
    assert "| a | 40 | 90 |" in text

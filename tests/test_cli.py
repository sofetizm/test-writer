"""End-to-end: run -> resume -> report, with a fake model instead of an API."""
import json
import sys

from twbench import REFERENCE_DIR, report
from twbench import run as run_mod
from twbench.backends import Scripted

WEAK = ("```python\nfrom retry_backoff import backoff_delays\n\n"
        "def test_it():\n    assert backoff_delays(2)\n```\nACTION: finish")
STRONG = ("```python\n" + (REFERENCE_DIR / "test_retry_backoff.py").read_text()
          + "```\nACTION: finish")


class FakeModel(Scripted):
    """Weak tests without the skill, strong tests when the skill is in the prompt."""

    def __init__(self, *args, **kwargs):
        super().__init__([])

    def chat(self, messages):
        self.seen.append(messages)
        reply = STRONG if "Installed skill: test-writer" in messages[0]["content"] else WEAK
        return type("R", (), {"text": reply, "input_tokens": 100, "output_tokens": 50,
                              "cost_usd": 0.001})()

    def describe(self):
        return {"backend": "fake"}


def test_run_resume_report(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run_mod, "OpenAICompatible", FakeModel)
    argv = ["run", "--model", "fake/model", "--tasks", "retry_backoff",
            "--conditions", "baseline,skill", "--out", str(tmp_path)]
    monkeypatch.setattr(sys, "argv", argv)
    run_mod.main()
    base = json.loads((tmp_path / "model/retry_backoff/baseline/r0/metrics.json").read_text())
    skill = json.loads((tmp_path / "model/retry_backoff/skill/r0/metrics.json").read_text())
    assert base["score"] < 50 < skill["score"] == 100.0
    assert (tmp_path / "model/retry_backoff/skill/r0/test_retry_backoff.py").exists()
    assert not (tmp_path / "model/retry_backoff/skill/r0/ws").exists()

    run_mod.main()
    assert capsys.readouterr().out.count("already done") == 2

    monkeypatch.setattr(sys, "argv", ["report", "--results", str(tmp_path)])
    report.main()
    text = (tmp_path / "RESULTS.md").read_text()
    assert "| model | skill | 1 | **100.0**" in text

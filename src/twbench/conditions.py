"""Experimental conditions. Everything except the skill is identical between them.

baseline    — the agent can write tests and run them. No skill.
skill       — the skill is installed: SKILL.md in context, references on demand,
              and the skill's mutation script available as a tool.
skill-text  — ablation: the same SKILL.md and references, but the mutation script
              cannot run. Shows how much of the effect comes from the instructions alone.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import SKILL_DIR

PROTOCOL = """You are working in a sandbox. Each of your replies may contain:
1. Optionally, the COMPLETE content of the test file in ONE ```python code block.
   It replaces the previous version of the file entirely.
2. Exactly one action on the LAST line of the reply, chosen from the list below.

Available actions:
{actions}

The action result is returned to you in the next message. Do not modify the module
under test; you can only write the test file."""

ACTIONS = {
    "run_tests": "ACTION: run_tests              — run pytest with your current test file",
    "run_mutation": ("ACTION: run_mutation           — run the skill's mutation_score.py on the "
                     "module with your test file; shows the score and surviving mutants"),
    "read_reference": ("ACTION: read_reference <file>  — read a reference file of the skill: "
                       "checklist.md, patterns.md, anti-patterns.md"),
    "finish": "ACTION: finish                 — you are done; the current test file is final",
}

TASK = """Write a high-quality pytest test suite for the module `{module}` shown below.
The test file is `{test_rel}`; it imports the module with `from {name} import ...`.
Available libraries: pytest, hypothesis.

```python
{source}
```"""


@dataclass
class Condition:
    name: str
    actions: tuple[str, ...]
    with_skill: bool
    note: str = ""

    def system_prompt(self) -> str:
        text = "You are an experienced Python engineer.\n\n" + PROTOCOL.format(
            actions="\n".join(ACTIONS[a] for a in self.actions))
        if self.with_skill:
            text += ("\n\n# Installed skill: test-writer\n"
                     "The following skill is installed and applies to this task. Follow it.\n\n"
                     + skill_text())
            text += "\n\n# How the skill's tools map to this sandbox\n" + self.note
        return text


def skill_text() -> str:
    return (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")


def reference(name: str) -> str | None:
    path = SKILL_DIR / "references" / name
    if path.parent != SKILL_DIR / "references" or not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


CONDITIONS = {
    "baseline": Condition("baseline", ("run_tests", "finish"), with_skill=False),
    "skill": Condition(
        "skill", ("run_tests", "run_mutation", "read_reference", "finish"), with_skill=True,
        note=("`python <skill-dir>/scripts/mutation_score.py --module ... --tests ...` is run "
              "with `ACTION: run_mutation`. Files in references/ are read with "
              "`ACTION: read_reference <file>`.")),
    "skill-text": Condition(
        "skill-text", ("run_tests", "read_reference", "finish"), with_skill=True,
        note=("The mutation script CANNOT run in this sandbox: do the mutation review by hand, "
              "as the skill describes. Files in references/ are read with "
              "`ACTION: read_reference <file>`.")),
}


def parse_conditions(text: str) -> list[Condition]:
    names = [c.strip() for c in text.split(",") if c.strip()]
    unknown = [n for n in names if n not in CONDITIONS]
    if unknown:
        raise SystemExit(f"unknown condition(s) {unknown}; available: {list(CONDITIONS)}")
    return [CONDITIONS[n] for n in names]

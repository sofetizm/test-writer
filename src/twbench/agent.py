"""A minimal tool-using agent loop with a plain-text protocol.

Plain text instead of native function calling: the same harness works with any chat
model — API models and small local models alike.
"""
from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .backends import Backend
from .conditions import TASK, Condition, reference
from .mutation import format_report
from .mutation import run as run_mutation
from .tasks import Task, make_workspace, run_pytest

_CODE = re.compile(r"```(?:python|py)\s*\n(.*?)```", re.DOTALL)
_ACTION = re.compile(r"^\s*\**ACTION:\**\s*([a-z_]+)(?:\s+(\S+))?\s*$", re.MULTILINE | re.IGNORECASE)
MAX_TOOL_OUTPUT = 2500
OMITTED = "```python\n# (earlier version of the test file omitted)\n```"


def parse_reply(text: str) -> tuple[str | None, str | None, str | None]:
    """Return (test file content or None, action or None, action argument or None)."""
    blocks = _CODE.findall(text or "")
    code = blocks[-1].strip() + "\n" if blocks else None
    actions = _ACTION.findall(text or "")
    if not actions:
        return code, None, None
    name, arg = actions[-1]
    return code, name.lower(), (arg or None)


def compact(messages: list[dict]) -> list[dict]:
    """Keep only the latest version of the test file in the history (saves tokens)."""
    last_assistant = max((i for i, m in enumerate(messages) if m["role"] == "assistant"),
                         default=-1)
    out = []
    for i, m in enumerate(messages):
        if m["role"] == "assistant" and i != last_assistant:
            m = {**m, "content": _CODE.sub(OMITTED, m["content"])}
        out.append(m)
    return out


def _trim(text: str, limit: int = MAX_TOOL_OUTPUT) -> str:
    return text if len(text) <= limit else "...(truncated)...\n" + text[-limit:]


@dataclass
class Episode:
    task: str
    condition: str
    turns: int = 0
    actions: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    seconds: float = 0.0
    finished: bool = False
    wrote_tests: bool = False
    transcript: list[dict] = field(default_factory=list)

    def summary(self) -> dict:
        d = asdict(self)
        d.pop("transcript")
        return d


def run_episode(backend: Backend, task: Task, condition: Condition, workspace: Path,
                max_turns: int = 6) -> Episode:
    make_workspace(task, workspace)
    test_path = workspace / task.test_rel
    ep = Episode(task.name, condition.name)
    started = time.monotonic()
    messages = [
        {"role": "system", "content": condition.system_prompt()},
        {"role": "user", "content": TASK.format(module=task.module_path.name, name=task.name,
                                                 test_rel=task.test_rel, source=task.source)},
    ]
    nudged = False
    for _turn in range(max_turns):
        reply = backend.chat(compact(messages))
        ep.turns += 1
        ep.input_tokens += reply.input_tokens
        ep.output_tokens += reply.output_tokens
        ep.cost_usd += reply.cost_usd
        messages.append({"role": "assistant", "content": reply.text})

        code, action, arg = parse_reply(reply.text)
        if code:
            test_path.write_text(code, encoding="utf-8")
            ep.wrote_tests = True
        if action is None:
            if nudged:
                break
            nudged = True
            result = "Your reply must end with one ACTION line. Continue."
        elif action == "finish":
            ep.actions.append("finish")
            ep.finished = True
            break
        elif action not in condition.actions:
            result = (f"Action `{action}` is not available. Available: "
                      + ", ".join(condition.actions))
        else:
            ep.actions.append(action)
            result = _do(action, arg, task, workspace, test_path)
        messages.append({"role": "user", "content": result})

    ep.seconds = round(time.monotonic() - started, 1)
    ep.transcript = messages
    return ep


def _do(action: str, arg: str | None, task: Task, ws: Path, test_path: Path) -> str:
    if action == "read_reference":
        text = reference(arg or "")
        return text if text else ("Unknown reference. Available: checklist.md, patterns.md, "
                                  "anti-patterns.md")
    if not test_path.exists():
        return "There is no test file yet. Put the test file in a ```python block first."
    if action == "run_tests":
        code, out, counts = run_pytest(ws, task.test_rel)
        status = "ALL TESTS PASSED" if code == 0 else f"pytest exit code {code}"
        return f"{status} {counts}\n\n{_trim(out)}"
    if action == "run_mutation":
        rep = run_mutation(ws, Path(task.module_path.name), [task.test_rel])
        return _trim(format_report(rep))
    return f"Unknown action {action}"

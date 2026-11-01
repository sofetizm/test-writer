
import pytest

from twbench.agent import compact, parse_reply, run_episode
from twbench.backends import Scripted
from twbench.conditions import CONDITIONS, parse_conditions, reference
from twbench.run import evaluate_tests
from twbench.tasks import all_tasks, select

TEST_BODY = "from pagination import paginate\n\ndef test_a():\n    assert paginate(0, 1)['pages'] == 1\n"
GOOD = f"```python\n{TEST_BODY}```"


def test_parse_reply_code_and_action():
    code, action, arg = parse_reply(f"Plan...\n{GOOD}\nACTION: run_tests")
    assert code.startswith("from pagination") and action == "run_tests" and arg is None


def test_parse_reply_variants():
    assert parse_reply("**ACTION:** read_reference patterns.md")[1:] == ("read_reference", "patterns.md")
    assert parse_reply("text only") == (None, None, None)
    two = "```python\nA = 1\n```\n```py\nB = 2\n```\nACTION: finish"
    assert parse_reply(two)[0] == "B = 2\n"
    assert parse_reply("ACTION: run_tests\nACTION: finish")[1] == "finish"


def test_compact_keeps_only_latest_code():
    msgs = [{"role": "system", "content": "s"}, {"role": "assistant", "content": GOOD},
            {"role": "user", "content": "ok"}, {"role": "assistant", "content": GOOD}]
    out = compact(msgs)
    assert "omitted" in out[1]["content"] and "paginate" in out[3]["content"]
    assert msgs[1]["content"] == GOOD


def test_conditions():
    assert "test-writer" not in CONDITIONS["baseline"].system_prompt()
    assert "run_mutation" not in CONDITIONS["baseline"].system_prompt()
    skill = CONDITIONS["skill"].system_prompt()
    assert "Mutation testing" in skill or "mutation testing" in skill
    assert "ACTION: run_mutation" in skill
    text = CONDITIONS["skill-text"].system_prompt()
    assert "CANNOT run" in text and "ACTION: run_mutation" not in text
    with pytest.raises(SystemExit):
        parse_conditions("baseline,magic")


def test_reference_access_is_sandboxed():
    assert "Boundary" in reference("patterns.md")
    assert reference("../SKILL.md") is None
    assert reference("missing.md") is None


def test_tasks_have_reference_suites():
    tasks = all_tasks()
    assert len(tasks) == 10
    assert all(t.reference_tests.exists() for t in tasks)


def test_episode_flow(tmp_path):
    task = select("pagination")[0]
    backend = Scripted([
        "I will start.",
        GOOD + "\nACTION: run_mutation",
        "ACTION: run_tests",
        "ACTION: finish",
    ])
    ep = run_episode(backend, task, CONDITIONS["baseline"], tmp_path / "ws")
    assert ep.finished and ep.wrote_tests
    assert ep.actions == ["run_tests", "finish"]
    texts = [m["content"] for m in ep.transcript if m["role"] == "user"]
    assert any("must end with one ACTION" in t for t in texts)
    assert any("not available" in t for t in texts)
    assert any("ALL TESTS PASSED" in t for t in texts)
    m = evaluate_tests(task, tmp_path / "ws")
    assert m["valid"] and 0 < m["score"] < 100


def test_two_missing_actions_end_episode(tmp_path):
    ep = run_episode(Scripted(["hm", "hm"]), select("money")[0], CONDITIONS["baseline"],
                     tmp_path / "ws")
    assert ep.turns == 2 and not ep.finished and not ep.wrote_tests
    assert evaluate_tests(select("money")[0], tmp_path / "ws") == {
        "valid": False, "score": 0.0, "reason": "no test file"}


def test_max_turns(tmp_path):
    ep = run_episode(Scripted(["ACTION: run_tests"] * 10), select("money")[0],
                     CONDITIONS["baseline"], tmp_path / "ws", max_turns=3)
    assert ep.turns == 3 and not ep.finished


def test_skill_episode_with_mutation_feedback(tmp_path):
    task = select("pagination")[0]
    backend = Scripted([GOOD + "\nACTION: run_mutation", "ACTION: finish"])
    ep = run_episode(backend, task, CONDITIONS["skill"], tmp_path / "ws")
    feedback = ep.transcript[3]["content"]
    assert feedback.startswith("Mutation score:") and "Surviving mutants" in feedback


def test_tests_failing_on_correct_code_are_excluded(tmp_path):
    task = select("pagination")[0]
    wrong = "\n\ndef test_wrong():\n    assert paginate(0, 1)['pages'] == 7\n"
    bad = f"```python\n{TEST_BODY}{wrong}```"
    run_episode(Scripted([bad + "\nACTION: finish"]), task, CONDITIONS["baseline"], tmp_path / "ws")
    m = evaluate_tests(task, tmp_path / "ws")
    assert m["valid"] and m["excluded_tests"] == 1 and m["tests_failed"] == 1


def test_reference_suites_pass_on_original(tmp_path):
    from twbench.tasks import make_workspace, run_pytest
    for t in all_tasks():
        ws = make_workspace(t, tmp_path / t.name, tests=t.reference_tests.read_text())
        code, out, counts = run_pytest(ws, t.test_rel)
        assert code == 0, (t.name, out[-500:])
        assert counts["passed"] >= 10

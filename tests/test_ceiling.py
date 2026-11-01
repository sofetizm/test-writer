"""Slow: the reference suites still reach the recorded ceiling (catches regressions in
the mutation engine or accidental edits of the benchmark tasks)."""
import json

import pytest

from twbench.ceiling import CEILING_FILE, compute

pytestmark = pytest.mark.slow


def test_ceiling_is_up_to_date():
    recorded = json.loads(CEILING_FILE.read_text())
    fresh = compute()
    assert {k: (v["killed"], v["total"]) for k, v in fresh.items()} == \
           {k: (v["killed"], v["total"]) for k, v in recorded.items()}

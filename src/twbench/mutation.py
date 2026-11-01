"""The benchmark uses exactly the script that ships with the skill (single source of truth)."""
import importlib.util
import sys

from . import SKILL_DIR

_PATH = SKILL_DIR / "scripts" / "mutation_score.py"
_spec = importlib.util.spec_from_file_location("mutation_score", _PATH)
mutation_score = importlib.util.module_from_spec(_spec)
sys.modules["mutation_score"] = mutation_score
_spec.loader.exec_module(mutation_score)

run = mutation_score.run
format_report = mutation_score.format_report
collect_mutations = mutation_score.collect_mutations
apply_mutation = mutation_score.apply_mutation

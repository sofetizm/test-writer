# Changelog

## Skill v0.2
- Run plain pytest before mutation testing.
- On a failing test: read the actual value and trace the code instead of guessing;
  at most two attempts per failing case.
- `mutation_score.py`: lists every test that fails on the original code, explains
  collection errors, fixes the Hypothesis seed so scores are reproducible.

Benchmark harness: the first `ACTION:` in a reply wins and anything after it is ignored
(models sometimes appended a second action or invented the tool output).

## Skill v0.1
First version. Benchmark results with `gpt-oss-120b` are in `results/gpt-oss-120b/`.

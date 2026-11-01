"""Benchmark: does the test-writer skill make AI agents write tests that catch more bugs?"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / "skills" / "test-writer"
TASKS_DIR = ROOT / "bench" / "tasks"
REFERENCE_DIR = ROOT / "bench" / "reference"

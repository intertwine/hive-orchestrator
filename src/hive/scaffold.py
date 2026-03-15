"""Workspace and project scaffolding helpers."""

from __future__ import annotations

from pathlib import Path


def program_stub_markdown() -> str:
    """Return the default conservative PROGRAM.md stub."""
    return """---
program_version: 1
mode: workflow
default_executor: local
budgets:
  max_wall_clock_minutes: 30
  max_steps: 25
  max_tokens: 20000
  max_cost_usd: 2.0
paths:
  allow:
    - src/**
    - tests/**
    - docs/**
  deny:
    - secrets/**
    - infra/prod/**
commands:
  allow: []
  deny:
    - rm -rf /
    - terraform apply
evaluators: []
promotion:
  requires_all: []
  review_required_when_paths_match: []
  auto_close_task: false
escalation:
  when_paths_match: []
  when_commands_match: []
---

# Goal

Define the autonomous work contract for this project.

# Constraints

- Fill in safe evaluator commands before autonomous runs.
- Commands in `commands.allow` must match evaluator commands exactly.
"""


def generate_program_stub(project_dir: Path) -> Path:
    """Create a conservative PROGRAM.md stub when missing."""
    target = project_dir / "PROGRAM.md"
    target.write_text(program_stub_markdown(), encoding="utf-8")
    return target

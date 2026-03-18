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
  allow_unsafe_without_evaluators: false
  allow_accept_without_changes: false
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

- This file tells Hive what it may change, which checks must pass, and when a human should stop the loop.
- Runs will stop for review until you add at least one real evaluator and list it in
  `promotion.requires_all`.
- If this project is intentionally manual or low-governance, set
  `promotion.allow_unsafe_without_evaluators: true` explicitly so reviewers can see that choice.
- If you want report-only or no-change runs to promote, set
  `promotion.allow_accept_without_changes: true` explicitly so that choice is visible too.
- Keep `commands.allow` aligned with the exact commands you expect Hive to run.
"""


def generate_program_stub(project_dir: Path) -> Path:
    """Create a conservative PROGRAM.md stub when missing."""
    target = project_dir / "PROGRAM.md"
    target.write_text(program_stub_markdown(), encoding="utf-8")
    return target


def starter_task_specs(project_title: str) -> list[dict[str, object]]:
    """Return a small, opinionated task chain for a fresh workspace."""
    subject = project_title.strip() or "the project"
    return [
        {
            "title": f"Define the first thin slice for {subject}",
            "status": "ready",
            "priority": 1,
            "acceptance": [
                "Scope is small enough to review in one PR or session.",
                "Acceptance criteria are written down in the task or AGENCY.md.",
                "Relevant files or directories are identified.",
            ],
            "summary_md": (
                "Turn the project goal into the smallest useful slice that is safe to hand to "
                "a human or agent."
            ),
        },
        {
            "title": f"Implement the first thin slice for {subject}",
            "status": "proposed",
            "priority": 1,
            "acceptance": [
                "The slice is implemented or documented in a reviewable form.",
                "Run artifacts or handoff notes capture what changed.",
                "The result is ready for review or explicit follow-up.",
            ],
            "summary_md": "Build the first useful slice once scope and boundaries are clear.",
        },
        {
            "title": f"Review, document, and hand off the first thin slice for {subject}",
            "status": "proposed",
            "priority": 2,
            "acceptance": [
                "Human-facing projections are synced.",
                "Open questions and next tasks are documented.",
                "The task ends in review, done, or a clear handoff state.",
            ],
            "summary_md": (
                "Close the loop with projections, notes, and the next clean handoff for the "
                "workspace."
            ),
        },
    ]

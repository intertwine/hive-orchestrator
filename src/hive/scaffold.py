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
  # Starter default: accept no-op runs so the first hive-finish loop completes cleanly.
  # Tighten to false once your project produces real changes on every run.
  allow_accept_without_changes: true
  requires_all: []
  review_required_when_paths_match: []
  # Starter default: auto-close tasks on accept so downstream work unblocks immediately.
  # Set to false when you want an explicit human review step between accept and done.
  auto_close_task: true
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
- The starter defaults allow no-change runs and auto-close tasks so the first
  `onboard → next → work → finish` loop completes cleanly. Tighten these once you
  have real evaluators and want an explicit review gate.
- Keep `commands.allow` aligned with the exact commands you expect Hive to run.
"""


def generate_program_stub(project_dir: Path) -> Path:
    """Create a conservative PROGRAM.md stub when missing."""
    target = project_dir / "PROGRAM.md"
    target.write_text(program_stub_markdown(), encoding="utf-8")
    return target


def starter_task_specs(project_title: str, objective: str | None = None) -> list[dict[str, object]]:
    """Return a small, opinionated task chain for a fresh workspace."""
    subject = project_title.strip() or "the project"
    goal = (objective or "").strip()
    goal_sentence = f"Project goal: {goal}" if goal else ""
    return [
        {
            "title": f"Plan the first milestone for {subject}",
            "status": "ready",
            "priority": 1,
            "acceptance": [
                "The project goal is translated into one small, reviewable milestone.",
                "Acceptance criteria are written down in the task or AGENCY.md.",
                "Relevant files, directories, or open questions are identified.",
            ],
            "summary_md": (
                "Turn the plain-English project goal into the first useful milestone that is safe "
                "to hand to a human or agent."
                + (f"\n\n{goal_sentence}" if goal_sentence else "")
            ),
        },
        {
            "title": f"Build the first reviewable milestone for {subject}",
            "status": "proposed",
            "priority": 1,
            "acceptance": [
                "The milestone is implemented or documented in a reviewable form.",
                "Run artifacts or handoff notes capture what changed.",
                "The result is ready for review or explicit follow-up.",
            ],
            "summary_md": (
                "Build the first useful milestone once scope and boundaries are clear."
                + (f"\n\n{goal_sentence}" if goal_sentence else "")
            ),
        },
        {
            "title": f"Review, document, and hand off the first milestone for {subject}",
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
                + (f"\n\n{goal_sentence}" if goal_sentence else "")
            ),
        },
    ]

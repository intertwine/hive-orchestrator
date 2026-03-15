---
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
    - README.md
    - docs/**
    - projects/demo/**
  deny:
    - .hive/cache/**
    - .hive/worktrees/**
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
  requires_all: []
  review_required_when_paths_match: []
  auto_close_task: false
escalation:
  when_paths_match: []
  when_commands_match: []
---

# Goal

Teach the standard Hive loop on a safe, docs-only surface.

# Constraints

- Keep changes small enough to review in one session or PR.
- Prefer docs and narrative updates over product changes in this demo project.
- This walkthrough is intentionally manual: claiming tasks and closing the loop happens through the CLI,
  so the demo policy does not grant autonomous writes to `.hive/tasks/*.md`.
- Governed runs stay disabled until you add at least one required evaluator and list it in
  `promotion.requires_all`.

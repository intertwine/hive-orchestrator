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
- Add evaluator commands only if you are deliberately turning the demo into a governed run example.

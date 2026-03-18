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

- This demo is meant for small, reviewable changes that fit in one session or PR.
- Stay on the docs-only surface here: `README.md`, `docs/**`, and `projects/demo/**`.
- Claim tasks and close the loop through the CLI. The canonical task files stay in `.hive/tasks/*.md`,
  so this policy does not grant autonomous writes there.
- Runs will stop for review until you add at least one real evaluator and list it in
  `promotion.requires_all`.

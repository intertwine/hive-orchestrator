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
    - .github/workflows/**
    - Makefile
    - README.md
    - images/**
    - pyproject.toml
    - scripts/**
    - GLOBAL.md
    - frontend/console/**
    - src/**
    - tests/**
    - docs/**
    - projects/hive-v25/**
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
- Keep the browser console as the primary human experience; desktop work must reuse the same frontend and API contract rather than fork a second UI stack.
- Treat the public v2.4.0 release cut as the gating precondition before claiming substantive v2.5 implementation tasks.
- Use the Clay design language as visual direction, but adapt it to a dense operator console with truthful states and accessible contrast.
- Runs will stop for review until you add at least one real evaluator and list it in
  `promotion.requires_all`.
- If this project is intentionally manual or low-governance, set
  `promotion.allow_unsafe_without_evaluators: true` explicitly so reviewers can see that choice.
- If you want report-only or no-change runs to promote, set
  `promotion.allow_accept_without_changes: true` explicitly so that choice is visible too.
- Keep `commands.allow` aligned with the exact commands you expect Hive to run.

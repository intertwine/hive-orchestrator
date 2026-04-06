---
budgets:
  max_cost_usd: 2.0
  max_steps: 25
  max_tokens: 20000
  max_wall_clock_minutes: 30
commands:
  allow:
  - make check
  deny:
  - rm -rf /
  - terraform apply
default_executor: local
escalation:
  when_commands_match: []
  when_paths_match: []
evaluators:
- command: make check
  id: make-check
  required: true
mode: workflow
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
program_version: 1
promotion:
  allow_accept_without_changes: false
  allow_unsafe_without_evaluators: false
  auto_close_task: false
  requires_all:
  - make-check
  review_required_when_paths_match:
  - frontend/console/**
  - src/hive/console/**
  - src/hive/resources/console/**
---

# Goal

Define the autonomous work contract for this project.

# Constraints

- This file tells Hive what it may change, which checks must pass, and when a human should stop the loop.
- Keep the browser console as the primary human experience; desktop work must reuse the same frontend and API contract rather than fork a second UI stack.
- Treat the public v2.4.0 release cut as the gating precondition before claiming substantive v2.5 implementation tasks.
- Use the Clay design language as visual direction, but adapt it to a dense operator console with truthful states and accessible contrast.
- `make check` is the baseline required evaluator for governed v2.5 runs, and it must stay truthful.
- Changes to browser console UI, console APIs, or packaged console assets must still stop for human
  review until richer frontend-specific evaluator coverage lands.
- If this project is intentionally manual or low-governance, set
  `promotion.allow_unsafe_without_evaluators: true` explicitly so reviewers can see that choice.
- If you want report-only or no-change runs to promote, set
  `promotion.allow_accept_without_changes: true` explicitly so that choice is visible too.
- Keep `commands.allow` aligned with the exact commands you expect Hive to run.

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
    - pyproject.toml
    - GLOBAL.md
    - src/**
    - tests/**
    - docs/**
    - projects/hive-v24/**
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

Implement the v2.4 ecosystem-integration line in small mergeable slices:
Milestone 0 wiring first, Milestone 1 foundation second, then Pi, OpenClaw,
Hermes, and launch polish without regressing existing Codex/Claude flows.

# Constraints

- This file tells Hive what it may change, which checks must pass, and when a human should stop the loop.
- Do not re-open already-closed v2.3 debates while working this line.
- Do not collapse Pi, OpenClaw, and Hermes into one generic RPC adapter.
- Do not break existing Codex/Claude/live-driver surfaces while adding v2.4 capabilities.
- Do not begin OpenClaw or Hermes implementation before the Milestone 1 adapter/Hive Link slice is stable.
- Keep canonical task claims current because Claude may also be working from the same RFC.
- Runs will stop for review until you add at least one real evaluator and list it in
  `promotion.requires_all`.
- If this project is intentionally manual or low-governance, set
  `promotion.allow_unsafe_without_evaluators: true` explicitly so reviewers can see that choice.
- If you want report-only or no-change runs to promote, set
  `promotion.allow_accept_without_changes: true` explicitly so that choice is visible too.
- Keep `commands.allow` aligned with the exact commands you expect Hive to run.

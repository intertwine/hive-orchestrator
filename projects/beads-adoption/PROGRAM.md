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

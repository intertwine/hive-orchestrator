---
program_version: 1
mode: workflow
default_executor: local

budgets:
  max_wall_clock_minutes: 45
  max_steps: 60
  max_tokens: 90000
  max_cost_usd: 7.5

paths:
  allow:
    - src/**
    - tests/**
    - docs/**
    - examples/**
  deny:
    - .github/workflows/prod/**
    - infra/prod/**
    - secrets/**
    - migrations/**

commands:
  allow:
    - uv run pytest -q
    - uv run ruff check .
    - uv run mypy src
  deny:
    - terraform apply
    - kubectl apply
    - rm -rf /

evaluators:
  - id: lint
    command: uv run ruff check .
    required: true
  - id: unit
    command: uv run pytest -q
    required: true
  - id: types
    command: uv run mypy src
    required: false

promotion:
  requires_all:
    - lint
    - unit
  review_required_when_paths_match:
    - src/hive/security/**
    - infra/**
    - migrations/**
  auto_close_task: false

escalation:
  when_paths_match:
    - infra/**
    - migrations/**
  when_commands_match:
    - "terraform apply"
    - "kubectl apply"
---

# Goal

Implement the Hive 2.0 vertical slice without regressing existing Hive behavior.

# Constraints

- CLI-first is non-negotiable.
- Do not make SQLite canonical.
- Do not reintroduce giant MCP tool catalogs.
- Keep generated sections bounded and deterministic.

# Reviewer checklist

- JSON output is stable and snapshot-tested.
- Task files remain the source of truth after edits.
- `hive run eval` is required before promotion.
- Memory files never include secrets.

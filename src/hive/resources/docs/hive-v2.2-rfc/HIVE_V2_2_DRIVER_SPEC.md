# Hive 2.2 Driver Spec

Every driver in Hive 2.2 uses the same basic contract.

## Required methods

- `probe`
- `launch`
- `resume`
- `status`
- `interrupt`
- `steer`
- `collect_artifacts`
- `stream_events`

## Normalized run states

- `queued`
- `compiling_context`
- `launching`
- `running`
- `awaiting_input`
- `awaiting_review`
- `blocked`
- `completed_candidate`
- `accepted`
- `rejected`
- `escalated`
- `cancelled`
- `failed`

## Why this matters

The driver layer keeps run metadata, artifacts, and steering history stable even when work moves between local execution, Codex, Claude Code, or a manual handoff.

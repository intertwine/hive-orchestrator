# Compare Harnesses

Hive is the control plane above the worker harness, not a replacement for one.

## Codex

Choose Codex when you want a strong coding worker with a prepared worktree, a compiled run pack, and a fast path from task to patch.

Good fit:

- implementation-heavy slices
- patch review loops
- codebase work where the worktree and run artifacts matter

## Claude Code

Choose Claude Code when you want broader repo search, longer synthesis, or a handoff-friendly transcript pack.

Good fit:

- repo-wide refactors
- architectural synthesis
- work where searching and summarizing across many files matters more than raw speed

## Local

Choose the local driver when Hive itself should execute the bounded run locally.

Good fit:

- deterministic local flows
- test-heavy slices
- small automation loops where a separate harness would be overkill

## Manual

Choose the manual driver when a person or an unsupported harness needs to take over without losing the run record.

Good fit:

- clipboard handoffs
- external specialist review
- staged approval or sign-off work

## The rule of thumb

Keep the worker you like. Use Hive to decide what should happen next, capture context and policy, track the run, and keep the audit trail intact when work moves between harnesses.

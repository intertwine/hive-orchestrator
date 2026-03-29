# Compare Harnesses

Hive is the control plane above the worker harness, not a replacement for one.

## Pi

Choose Pi when you want the deepest native v2.4 companion path: a real `open` flow for governed runs plus `attach` for continuing a live Pi session.

Good fit:

- governed work that should launch from inside Pi
- advisory continuation of a live Pi session
- teams that want one native package with `next/search/open/attach/finish/note/status`

Truth:

- `pi-hive open ...` is governed and Hive-owned
- `pi-hive attach ...` is advisory and binds an existing Pi session
- both modes persist trajectory and steering artifacts

## OpenClaw

Choose OpenClaw when you want Hive to supervise a live Gateway conversation without forcing a relaunch.

Good fit:

- attach-first OpenClaw workflows
- advisory supervision of an existing `sessionKey`
- gateway-backed chat where steering and notes should round-trip back to OpenClaw

Truth:

- v2.4 OpenClaw is attach-only
- governance is always advisory
- the sandbox owner is OpenClaw or external, not Hive
- no native plugin is required for the base path

## Hermes

Choose Hermes when you want Hermes-native skills, advisory attach, and a privacy-preserving fallback when live attach is not available.

Good fit:

- attach-first Hermes CLI or gateway sessions
- Hermes-native skill/toolset workflows
- cases where trajectory import fallback matters

Truth:

- v2.4 Hermes is attach/import, not managed
- governance is always advisory
- private Hermes memory (`MEMORY.md`, `USER.md`) is never bulk-imported automatically

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

- Choose Pi when you want the deepest native companion integration.
- Choose OpenClaw or Hermes when you want native attach-first advisory supervision.
- Choose Codex or Claude Code when you want Hive-prepared coding worktrees for patch loops and synthesis.

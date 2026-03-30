# Agent Hive Autonomy v2.5 Plan

Date: 2026-03-30
Context: Follow-up to `docs/AUTONOMY_GAP_ANALYSIS.md` after the full v2.4 sprint

## Executive Verdict

The v2.4 sprint did not expose a failure of Hive's core task, run, or campaign
model. It exposed a missing event-and-notification layer at the boundary between
Hive, GitHub, and agent sessions.

In practice, the human operator had to relay:

- PR creation
- review requests
- review comments
- re-review requests
- merge completion
- base-branch movement
- “what should I do next?” assignment

That is why the shortest path to materially more autonomy in v2.5 is not a new
planner. It is a GitHub event bridge, durable agent inboxes, and a wakeable
background loop that can turn state changes into the next concrete action.

## What Already Worked In v2.4

- canonical task claims prevented direct collision
- the task graph and blockers were expressive enough for milestone sequencing
- the review process could be executed by agents once someone told them that work
  was waiting
- PRs stayed small and mergeable when each slice focused on one real blocker
- the repo could sustain multiple concurrent worktrees and cross-agent review
  without architectural confusion

## Root-Cause Taxonomy

### 1. Missing Event Transport

Hive had state, but not enough event transport. GitHub PR, review, CI, and merge
events were not translated into Hive-native signals.

### 2. Missing Durable Agent Inbox

Agents had no durable queue of actionable items such as:

- “review PR #168”
- “re-review latest head on PR #165”
- “your PR is green and mergeable”
- “main moved; rebase before continuing”

### 3. Missing PR Lifecycle Automation

The run lifecycle and the GitHub lifecycle still had a manual seam between them.
Agents could implement and validate a slice, but the repo still depended on chat
messages for PR creation, review routing, and merge completion.

### 4. Missing Freshness Guarantees

Humans repeatedly had to answer questions like:

- is this PR ready for re-review?
- did `main` move?
- which task is actually next?
- is the project ledger still truthful?

That is an autonomy failure even when the underlying implementation is correct.

## Proposed v2.5 Architecture

### Milestone 1: GitHub Event Bridge

Translate GitHub events into Hive events:

- `pr.created`
- `pr.review.requested`
- `pr.review.submitted`
- `pr.comment.created`
- `ci.completed`
- `pr.merged`

Start with GitHub Actions or polling if needed; graduate to a webhook path later.

### Milestone 2: Durable Agent Inbox

Add a file-backed per-agent inbox, for example:

- `.hive/agents/codex/inbox.ndjson`
- `.hive/agents/claude/inbox.ndjson`

Each item should include:

- task ID
- PR number and URL
- latest head SHA
- event type
- reviewer/author identity
- exact requested next action

### Milestone 3: Wake And Resume Path

Agents need a standard way to resume with inbox context rather than waiting for
human chat relay. Session-start hooks and scheduled wakeups are the likely first
implementation path.

### Milestone 4: PR Lifecycle Automation

Connect accepted runs to GitHub:

- create PRs from promoted runs
- assign the right reviewer
- request re-review after fixes
- auto-merge once CI and review policy are both green

### Milestone 5: Background Orchestrator

Run a lightweight loop that watches:

- ready tasks
- blocked tasks becoming unblocked
- inbox items awaiting action
- CI completion
- merges that should trigger rebases or next-task dispatch

This loop should dispatch actions, not just recommend them.

## Suggested Success Metrics

The v2.5 autonomy line is successful when the v2.4 sprint could be replayed with:

- zero “please review PR #N” messages from the operator
- zero “new comments are up, please re-review” relays
- zero “PR merged, move to the next slice” relays
- zero ambiguity about whether task/project truth surfaces match GitHub reality
- operator involvement reduced to policy, prioritization, and true exception handling

## Recommended Sequencing

1. GitHub event bridge
2. durable inbox
3. wake/resume path
4. PR lifecycle automation
5. background orchestrator

This order matters. A scheduler without durable events and inbox delivery will
only automate polling and still depend on humans to explain state changes.

## Scope Guardrails

v2.5 autonomy work should not start by rewriting the core task/run abstractions.
The v2.4 sprint showed that those already support the work. The leverage is in
the boundary layer and the operational glue.

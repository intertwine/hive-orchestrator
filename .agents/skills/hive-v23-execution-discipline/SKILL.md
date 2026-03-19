---
name: hive-v23-execution-discipline
description: Ship Hive v2.3 and other large Hive RFC work in mergeable slices with strong autonomy, bounded delegation, and blocking Claude review discipline. Use this skill when working on long-running Hive changes that span multiple PRs, subagents, review cycles, or release gates.
---

# Hive v2.3 Execution Discipline

Use this skill for Hive work that is too large for a single edit loop and too important for casual review handling.

## Outcomes

- keep `main` releasable
- move the RFC forward in the highest-value order
- use subagents for bounded side lanes, not for core judgment
- treat Claude review as part of the implementation loop, not as decoration
- leave a compact restart trail after every merge or pause

## Ground Truth First

Before substantial work:

```bash
git status --short
git worktree list
gh pr status
hive doctor --json
```

Then classify the current work into:

- release blockers
- mergeable slices
- follow-up debt

Prefer the smallest slice that removes a real blocker.

## Default Autonomy Loop

1. identify the next blocker on the critical path
2. choose one mergeable slice that attacks it
3. implement locally if it is blocking or tightly coupled
4. delegate only bounded side work
5. run local validation before asking for review
6. treat review findings as new work, not commentary
7. merge only when the slice is actually green
8. record the new head and the next blocker

Do not stall on tiny cleanup once the next real blocker is known.
Do not keep adding unrelated work to an already-mergeable PR.

## Delegation Rules

Delegate when the task is concrete, independent, and non-blocking for your immediate next step.

Good delegation targets:

- audit a subset of merged PRs
- investigate one suspected bug and return evidence
- implement a bounded patch with a disjoint file set
- build focused tests for an already-designed fix

Keep local ownership for:

- contract design
- integration across multiple lanes
- PR triage and merge decisions
- any task whose answer is needed before your next move

Every delegated task should include:

- exact goal
- file ownership or read-only scope
- required output format
- reminder that other agents may be editing nearby code

After delegation:

- do not wait by reflex
- work another non-overlapping lane
- review returned changes before trusting them
- reconcile Claude findings yourself before merge

## Claude Review Discipline

Before `@Claude review`:

- make the PR single-purpose
- run the relevant local tests, or `make check` when the slice is broad
- post a short summary of what changed and what was validated

When review lands, classify each finding:

- confirmed bug
- missing test or truthfulness gap
- false alarm disproven by current code
- valid follow-up but non-blocking

Rules:

- treat must-fix findings as blocking until fixed or disproven with evidence
- confirm against the current branch, not memory
- respond with file paths, test names, and the exact commit that addressed the issue
- do not merge because a PR is “probably fine”
- do not ignore Claude because CI is green

If the review workflow itself is broken, land the smallest bootstrap fix first, then rerun review on the real PR.

## PR Sizing And Merge Discipline

Prefer one subsystem or one risk cluster per PR.

Warning signs that a PR is too large:

- multiple unrelated review themes
- difficult-to-summarize purpose
- repeated “while I’m here” changes
- reviewer confusion about what is actually blocking

When that happens:

- merge the safe foundation slice
- reopen the next slice on top
- keep the train moving in small reviewed steps

Literal green means:

- local validation passed
- required GitHub checks passed
- no unresolved must-fix review findings remain

## RFC Prioritization Heuristics

For Hive v2.3, prefer this order:

1. runtime contracts and truthful capability reporting
2. live Codex and Claude adapters plus approval round-tripping
3. sandbox paths that are real enough to release truthfully
4. campaign and retrieval internals that support operator judgment
5. console and docs polish

When scope fights back, prefer one path that is truly real over several shallow integrations.

## Context Protection

After every merge, push, or major handoff, capture:

- current branch and head
- latest merged `main` head if relevant
- what is now complete
- what is still blocking release
- the next highest-value step

Keep this compact enough to survive a long session or compaction.

## Cleanup Hygiene

During long Hive sessions, periodically check for:

```bash
git status --short
git worktree list
pgrep -fl "codex_app_server_worker.py|claude_sdk_worker.py|agent_dispatcher|hive "
```

Look for:

- orphan worker processes
- stale temp worktrees
- untracked `.hive/events/*.jsonl` noise
- local changes on the wrong branch

Clean generated artifacts promptly so they do not masquerade as intentional work.

## Closeout Checklist

Before you stop or hand off:

- ensure the checkout state matches your verbal summary
- note any unpushed local commits
- call out unresolved blockers explicitly
- state whether Claude review is still pending, clear, or blocking
- say what the very next step should be

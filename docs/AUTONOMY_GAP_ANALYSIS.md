# Agent Hive Autonomy Gap Analysis

Date: 2026-03-29
Context: Post-v2.4 implementation sprint analysis
Source: Direct observation of the Claude + Codex multi-agent development session that delivered v2.4 milestones M0–M5 across PRs #163–#175

## Problem Statement

During the v2.4 development sprint, two agents (Claude Code and Codex) implemented
the complete adapter-family split, Hive Link protocol, Pi/OpenClaw/Hermes integrations,
console delegate visibility, and acceptance test coverage — shipping 13 PRs across
~48 hours. Despite this velocity, the human operator (Bryan) had to act as the
**dispatch loop, notification bus, review router, and merge gatekeeper** for every
single PR lifecycle event.

The exact handholding pattern was:
- "Codex has a PR up, please review"
- "New comments on your PR"
- "Codex made fixes, please re-review"
- "OK, merge it"
- "Codex has claimed M2, take the next slice"
- "Please review PR #168 while Codex reviews your #165"

This is the opposite of what Agent Hive is designed to achieve. This document
catalogs the specific gaps that prevented autonomy and proposes concrete fixes.

## Observed Human Interventions

### 1. PR Notification Relay (33% of operator messages)

The operator's most frequent role was telling one agent about another agent's output:

| Pattern | Count | Example |
|---|---|---|
| "Codex has PR #N ready for review" | 7 | "PR 166 is up, please review" |
| "New review comments on your PR" | 6 | "Comments are in for your 165" |
| "Fixes pushed, re-review" | 5 | "Codex made changes, please re-review" |
| "PR merged, proceed" | 4 | "OK 168 is merged" |

**Root cause:** Agents have no way to discover that a PR was created, a review was
posted, or a merge happened. GitHub is a black box — the only notification channel
is the human.

### 2. Work Assignment / Task Routing (20% of operator messages)

The operator explicitly directed which agent takes which milestone:

| Pattern | Example |
|---|---|
| "Codex has claimed M2, take next slice" | Work allocation |
| "You can take M3 and go" | Task assignment |
| "Begin planning and implementation of M4" | Scope delegation |
| "Codex will concentrate on OpenClaw parity" | Parallel work coordination |

**Root cause:** Hive has task claiming, but no mechanism for agents to observe each
other's claims and self-select the next available work. Campaign ticks are manual
CLI invocations, not background processes.

### 3. Review Coordination (25% of operator messages)

The operator orchestrated the review dance between agents:

| Pattern | Example |
|---|---|
| "Review PR #N while Codex reviews yours" | Parallel review assignment |
| "Use a subagent to protect context" | Review strategy guidance |
| "Please address the findings" | Fix directive |
| "Give it a once-over and we'll merge" | Final approval delegation |

**Root cause:** No review-request routing exists. When a PR is created, there's no
mechanism to notify the other agent that a review is needed, or to match reviewers
to PRs based on expertise or availability.

### 4. Merge Authorization (10% of operator messages)

The operator was the merge gatekeeper:

| Pattern | Example |
|---|---|
| "Green light to merge" | Explicit merge authorization |
| "Take over and merge" | Merge delegation |
| "Codex will merge 166" | Merge assignment |

**Root cause:** No CI-gated auto-merge. The promotion flow in Hive is local
(evaluator commands), not integrated with GitHub's merge protection.

### 5. Context Synchronization (12% of operator messages)

The operator told agents about state changes they couldn't see:

| Pattern | Example |
|---|---|
| "M0 is merged, move forward with M1" | Post-merge state update |
| "166 is merged, ensure M1 interoperates" | Rebase trigger |
| "Both 169 and 170 are merged" | State synchronization |

**Root cause:** Agents don't watch `origin/main`. They work in isolation until
the human tells them the world changed.

## What Agent Hive Already Has

These coordination primitives are mature and worked well during the sprint:

| Capability | How it was used |
|---|---|
| **Task claiming with TTL** | Prevented Claude and Codex from colliding on the same milestone |
| **Hive task state** | `.hive/tasks/*.md` was the canonical work tracker |
| **Campaign scoring** | `recommend_next_task()` correctly prioritized work |
| **Governed runs** | Evaluators and PROGRAM.md policies gated unsafe promotions |
| **Event audit trail** | JSONL logs captured the full execution history |
| **Steering** | Operators could pause/focus/boost via `hive steer` |
| **Driver abstraction** | Local, Codex, Claude, Pi, OpenClaw, Hermes all work through one interface |
| **Capability snapshots** | Truthful declared/probed/effective model prevented false claims |

The problem is not inside Hive — it's at the **boundary between Hive and GitHub**.

## Concrete Gaps

### Gap 1: No GitHub Event Bridge

**What's missing:** A listener that converts GitHub events into Hive events.

**Required mappings:**

| GitHub Event | Hive Action |
|---|---|
| PR created | Emit `pr.created` event; notify assigned reviewer agent |
| PR review submitted | Emit `pr.review.submitted`; notify PR author agent |
| PR review comment | Emit `pr.review.comment`; notify PR author agent |
| CI checks completed | Emit `ci.completed`; if green + approved → auto-merge |
| PR merged | Emit `pr.merged`; update task status; trigger rebase for blocked PRs |
| Issue created | Create `.hive/tasks/` entry from issue body |

**Implementation options:**
- **GitHub App webhook** — receives push events, converts to Hive events
- **GitHub Actions workflow** — `on: pull_request` / `on: pull_request_review` triggers Hive CLI
- **Polling service** — `hive github sync` command that polls `gh api` periodically

**Recommendation:** Start with GitHub Actions workflow triggers (zero infrastructure,
works in existing CI). Add webhook listener later for real-time.

### Gap 2: No Agent Notification / Wake Mechanism

**What's missing:** A way to tell Agent X "there's work for you."

**Current state:** Agents must poll `hive next` or `hive portfolio status`. There's
no push mechanism.

**Required:**
- Agent inbox: a per-agent queue of actionable items (review requests, merge
  notifications, task assignments)
- Wake trigger: a way to start an agent session in response to an event
  (e.g., `claude --resume <session> --message "PR #165 has review comments"`)

**Implementation options:**
- **File-based inbox:** `.hive/agents/<agent-name>/inbox.ndjson` — agents poll on session start
- **Claude Code hooks:** `SessionStart` hook reads inbox and injects context
- **GitHub Actions dispatch:** `workflow_dispatch` event triggers agent session with payload
- **MCP notification:** Hive MCP server pushes notifications to connected agents

**Recommendation:** File-based inbox + SessionStart hook is the simplest path.
Claude Code's hook system already supports this pattern.

### Gap 3: No PR Lifecycle Automation

**What's missing:** The bridge between "run accepted" and "PR merged on GitHub."

**Current state:** `finish_run_flow()` evaluates and promotes locally. The human
must then `git push`, `gh pr create`, wait for review, and merge.

**Required:**
- `hive promote` should optionally create a PR via `gh pr create`
- PR body should include task ID, run ID, evaluation results, and artifacts
- Review assignment should route to the configured reviewer (human or agent)
- Merge should happen automatically when CI passes + review approves

**Implementation:**
```
hive run promote <run-id> --create-pr --reviewer codex --auto-merge
```

This would:
1. Push the worktree branch
2. Create PR with structured body (task link, eval results, diff stats)
3. Assign reviewer
4. Emit `pr.created` event to agent inbox
5. When CI + review pass → `gh pr merge`

### Gap 4: No Cross-Agent Handoff Protocol

**What's missing:** When Agent A finishes a PR and Agent B needs to act on it,
there's no structured handoff.

**During v2.4:** Claude would finish a PR, Bryan would tell Codex to review it,
Codex would post findings, Bryan would tell Claude to fix them. Each relay lost
context and added latency.

**Required:**
- `hive handoff <from-agent> <to-agent> --context "PR #165 ready for review"`
- Handoff creates an inbox entry for the target agent
- Handoff includes: task ID, PR URL, relevant file paths, review scope

**Implementation:** Extend the existing steering system. A handoff is a steering
event of type `handoff` that targets a specific agent and includes structured
context.

### Gap 5: No Background Orchestration Loop

**What's missing:** A persistent process that ticks the campaign/portfolio loop
and dispatches work to agents.

**Current state:** `hive campaign tick` is a manual CLI command. Someone has to
invoke it.

**Required:**
- Background scheduler that runs `portfolio tick` every N minutes
- Watches for: ready tasks, blocked tasks becoming unblocked, review-pending runs
- Dispatches work to available agents via inbox + wake mechanism
- Monitors CI status and triggers merges when gates pass

**Implementation options:**
- **Cron job:** `*/5 * * * * hive campaign tick --auto-dispatch`
- **Persistent service:** `hive orchestrate serve` — long-running process
- **GitHub Actions scheduled workflow:** `schedule: - cron: '*/5 * * * *'`

**Recommendation:** Start with cron (`claude-code-scheduler` pattern already exists).
Graduate to persistent service when the event volume warrants it.

## Proposed v2.5 Scope

Based on this analysis, a v2.5 release focused on autonomous SDLC would deliver:

### Milestone 1: GitHub Event Bridge
- GitHub Actions workflow that emits Hive events on PR/review/merge
- `hive github sync` command for manual polling fallback
- Task-to-PR bidirectional linking

### Milestone 2: Agent Inbox + Wake
- File-based agent inbox (`.hive/agents/<name>/inbox.ndjson`)
- SessionStart hook integration for auto-context on wake
- `hive inbox` CLI for agents to consume their queue

### Milestone 3: PR Lifecycle Automation
- `hive promote --create-pr` with structured PR body
- Review assignment routing
- CI-gated auto-merge via `hive merge --when-green`

### Milestone 4: Cross-Agent Handoff
- `hive handoff` command with structured context
- Review-request routing (agent A → agent B)
- Handoff event in audit trail

### Milestone 5: Background Orchestrator
- `hive orchestrate` persistent loop
- Campaign tick automation
- Blocked-task unblock detection
- CI status monitoring

## Success Criteria

The v2.4 sprint would have been fully autonomous if:

1. **Zero "please review PR #N" messages from operator.** Agent A creates PR →
   Hive notifies Agent B → Agent B reviews → findings posted → Agent A fixes →
   re-review → merge. All automatic.

2. **Zero "PR merged, proceed" messages.** Merge event triggers rebase of blocked
   branches and task status updates. Agents pick up next work from their inbox.

3. **Zero "take the next slice" messages.** Campaign tick auto-dispatches ready
   tasks to available agents based on capability and lane allocation.

4. **Operator role reduced to:** strategic steering (pause/focus/boost), policy
   changes (PROGRAM.md), and exception handling (escalated runs).

## Effort Estimate

| Milestone | Effort | Dependencies |
|---|---|---|
| M1: GitHub Event Bridge | 3-5 days | GitHub Actions knowledge |
| M2: Agent Inbox + Wake | 2-3 days | M1 for event source |
| M3: PR Lifecycle | 3-5 days | M1 + M2 |
| M4: Cross-Agent Handoff | 2-3 days | M2 |
| M5: Background Orchestrator | 3-5 days | M1 + M2 |
| **Total** | **13-21 days** | |

## Appendix: Session Statistics

The v2.4 sprint produced:
- 13 PRs (#163–#175)
- ~8,500 lines of new code
- ~150 new tests (773 total at completion)
- 3 new packages (pi-hive, openclaw-hive-bridge, hermes-skill)
- 5 new src/ packages (integrations, link, trajectory, drivers/pi, cli/integrate)
- Multi-round reviews on every PR (average 2.3 review cycles per PR)

Human interventions required: ~45 messages across ~48 hours, of which ~85%
were dispatch/notification/routing that a GitHub event bridge + agent inbox
would have eliminated.

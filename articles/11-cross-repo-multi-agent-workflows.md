# Cross-Repo Multi-Agent Workflows

_One repository can hold the orchestration state even when the actual work targets another repository._

---

![Hero: Beyond Repository Boundaries](images/cross-repo-multi-agent-workflows/img-01_v1.png)
_The orchestration repo does not need to be the same repo as the code being studied or changed._

---

## Why Cross-Repo Work Matters

Real software organizations do not live in one repository.

You may need to:

- coordinate changes across multiple internal repos
- prepare improvements for an upstream open source dependency
- analyze a third-party SDK before building an integration
- keep planning and execution state in one repo while targeting another

Hive can support that pattern without forcing the orchestration state to move.

## The Core Idea

Keep the durable orchestration state in the Hive workspace, and point a project at an external target repository when needed.

That target can live in project metadata:

```yaml
target_repo:
  url: https://github.com/org/external-repo
  branch: main
```

The important part is not the field itself. It is the separation of concerns:

- Hive repo holds the task state, notes, policy, and handoffs
- target repo holds the code being inspected or changed

This is often a much better operational shape than trying to stuff both concerns into one place.

## What Hive Can Do Today

Hive's optional context assembly path can use `target_repo` metadata to enrich the work packet for an agent.

That means a dispatcher or context builder can:

- clone the external repo
- gather a file tree
- read a few key files
- package that context alongside the Hive project state

The result is a better briefing for the next session without making the external repo the source of orchestration truth.

## A Good Cross-Repo Pattern

This pattern works well:

### Phase 1: analyze

Create tasks for understanding the target repo:

- map the architecture
- identify likely improvement slices
- capture risks and constraints

### Phase 2: choose the slice

Use the Hive project to decide what change is worth making and what should wait.

### Phase 3: implement

Work in the target repo, but record state and decisions back in the Hive workspace.

### Phase 4: review and handoff

Keep the PR, patch, or proposed change tied back to the Hive task and run artifacts.

This gives you continuity even when the code and the orchestration state live in different repos.

## Why This Is Better Than A Giant Scratchpad

Without structure, cross-repo work often collapses into a giant note document full of:

- repo URLs
- half-finished analysis
- local assumptions
- missing follow-up state

Hive helps by keeping the usual operating surfaces intact:

- canonical tasks
- claims
- startup context
- memory
- runs
- projections

The repo boundary changes. The orchestration discipline does not.

## The Main Things To Be Careful About

### Access and trust

Just because a project points at another repo does not mean every agent should automatically get write access to it.

Be explicit about credentials, cloning strategy, and review boundaries.

### Context size

Cross-repo work can explode the amount of material you hand to a session. Prefer targeted file selection and summaries over dumping an entire codebase into context.

### Source of truth

Do not let the external repo become a shadow copy of the orchestration state. Keep decisions, blockers, and task progress in Hive.

## Bottom Line

Cross-repo work is where weak orchestration systems start to come apart.

Hive handles it well because the durable state already lives outside any single session and outside any single runtime.

That makes it much easier to keep the work coherent even when the code you are touching lives somewhere else.

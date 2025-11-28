# Dependency Graphs in Practice

*This is the fourth article in a series exploring Agent Hive and AI agent orchestration.*

---

![Hero: Why Dependencies Matter](images/04-hero-dependencies.png)
*One project needs no tracking. Five you can manage. Fifty? Implicit dependencies become a liability. Agent Hive makes relationships explicit and queryable.*

---

## Why Dependencies Matter

When you have one project, you don't need dependency tracking. You just work on it until it's done.

When you have five projects, you can probably keep the relationships in your head. Project B needs the database schema from Project A. Project D can wait until C is done. You manage.

When you have fifty projects across multiple agents and humans, implicit dependencies become a liability. Work starts on things that aren't ready. Critical blockers sit unnoticed while downstream teams wonder why they're stuck. The left hand doesn't know what the right hand needs.

Agent Hive's dependency system makes these relationships explicit, queryable, and enforceable.

## The Four Dependency Types

Agent Hive supports four types of relationships between projects, each serving a different purpose:

### 1. blocked_by: "I need this first"

The most common dependency. This project cannot proceed until the listed projects are completed.

```yaml
# api-integration/AGENCY.md
dependencies:
  blocked_by: [database-schema, auth-service]
```

This says: "Don't start api-integration until both database-schema AND auth-service are completed."

The Cortex engine checks this before marking a project as ready for work. An agent querying for ready work won't see api-integration until its blockers are cleared.

### 2. blocks: "Things waiting on me"

The inverse of blocked_by. Lists projects that depend on this one completing.

```yaml
# database-schema/AGENCY.md
dependencies:
  blocks: [api-integration, data-migration, analytics-pipeline]
```

This is informational from the current project's perspective, but critical for understanding impact. If database-schema is delayed, three other projects are affected.

Note: You can define relationships from either direction. `A.blocked_by: [B]` and `B.blocks: [A]` are equivalent. Agent Hive normalizes both into a unified graph.

### 3. parent: "I'm part of something bigger"

Hierarchical relationships for breaking large initiatives into smaller projects.

```yaml
# auth-login/AGENCY.md
dependencies:
  parent: auth-epic

# auth-registration/AGENCY.md
dependencies:
  parent: auth-epic

# auth-password-reset/AGENCY.md
dependencies:
  parent: auth-epic
```

The parent project (auth-epic) contains the overall objective; child projects contain the specific implementation work. This enables:
- Rolling up status across related work
- Understanding which tactical projects serve which strategic goals
- Navigating from high-level to low-level and back

### 4. related: "You might want to know about this"

Non-blocking contextual relationships. These don't affect scheduling but help agents understand context.

```yaml
# api-v2/AGENCY.md
dependencies:
  related: [api-v1, deprecation-plan, client-migration]
```

When working on api-v2, an agent might benefit from reading the related projects for context—but they're not required to wait for anything.

![The Four Dependency Types](images/04-dependency-types.png)
*Four dependency types for different relationships: blocked_by (must wait), blocks (others waiting), parent (hierarchy), related (context only).*

## Viewing the Dependency Graph

Agent Hive provides multiple ways to visualize dependencies:

### CLI: Human-Readable

```bash
uv run python -m src.cortex --deps
```

Output:

```
============================================================
DEPENDENCY GRAPH
============================================================
Timestamp: 2025-01-15T14:30:00
Total Projects: 8

BLOCKED PROJECTS:
----------------------------------------
*** api-integration
    Status: active
    Blocked by: database-schema, auth-service
    Reason: Blocked by uncompleted: database-schema, auth-service

*** frontend-integration
    Status: pending
    Blocked by: api-integration
    Reason: Blocked by uncompleted: api-integration

UNBLOCKED PROJECTS:
----------------------------------------
    database-schema [active]
      Blocks: api-integration, data-migration
    auth-service [active]
      Blocks: api-integration
    documentation [active]
    testing-framework [completed]

DEPENDENCY TREE:
----------------------------------------
[*] database-schema
  [!] api-integration
    [!] frontend-integration
[*] auth-service
  [!] api-integration
[*] documentation
[+] testing-framework

Legend: [+] completed  [*] active  [!] blocked  [-] pending
============================================================
```

### CLI: JSON for Programmatic Use

```bash
uv run python -m src.cortex --deps --json
```

Output:

```json
{
  "timestamp": "2025-01-15T14:30:00Z",
  "total_projects": 8,
  "has_cycles": false,
  "cycles": [],
  "projects": [
    {
      "project_id": "api-integration",
      "status": "active",
      "priority": "high",
      "owner": null,
      "blocked": false,
      "blocks": ["frontend-integration"],
      "blocked_by": ["database-schema", "auth-service"],
      "effectively_blocked": true,
      "blocking_reasons": ["Blocked by uncompleted: database-schema, auth-service"],
      "in_cycle": false
    }
  ]
}
```

### Dashboard: Visual

The Streamlit dashboard shows dependencies in the sidebar and project detail views, with visual indicators for blocked status and cycle warnings.

## Finding Ready Work

The primary use of dependency tracking is identifying what's actually actionable:

```bash
uv run python -m src.cortex --ready
```

Output:

```
============================================================
READY WORK
============================================================
Timestamp: 2025-01-15T14:30:00
Found 3 project(s) ready for work

!!  database-schema
    Priority: high
    Tags: infrastructure, database
    Path: projects/database-schema/AGENCY.md

!!  auth-service
    Priority: high
    Tags: security, backend
    Path: projects/auth-service/AGENCY.md

!   documentation
    Priority: medium
    Tags: docs
    Path: projects/documentation/AGENCY.md

============================================================
```

A project is "ready" when:
- `status` is `active`
- `blocked` is `false`
- `owner` is `null` (unclaimed)
- All `blocked_by` dependencies are `completed`

This query runs without any LLM calls—it's pure graph traversal.

![Ready Work Detection](images/04-ready-work.png)
*Finding ready work requires no LLM calls—just pure graph traversal. Projects with all blockers cleared light up as claimable.*

## Cycle Detection

Circular dependencies create deadlocks that can never be resolved:

```yaml
# project-a/AGENCY.md
dependencies:
  blocked_by: [project-b]

# project-b/AGENCY.md
dependencies:
  blocked_by: [project-c]

# project-c/AGENCY.md
dependencies:
  blocked_by: [project-a]  # Uh oh
```

None of these projects can ever start. Each is waiting for something that's waiting for something that's waiting for it.

Agent Hive detects these cycles automatically:

```bash
uv run python -m src.cortex --deps

# Output includes:
!!! CYCLES DETECTED !!!
    project-a -> project-b -> project-c -> project-a
```

The dashboard shows cycle warnings prominently. Resolving cycles requires human intervention to restructure the dependencies.

![Cycle Detection](images/04-cycle-detection.png)
*Circular dependencies are deadlocks that can never resolve. Each project waits for something that's waiting for it. Cortex detects these cycles automatically.*

## Real-World Examples

### Example 1: Feature Development Pipeline

A typical feature moving from research to production:

```
research-auth → design-auth → implement-auth → test-auth → deploy-auth
```

```yaml
# research-auth/AGENCY.md
project_id: research-auth
status: completed
dependencies:
  blocks: [design-auth]

# design-auth/AGENCY.md
project_id: design-auth
status: completed
dependencies:
  blocked_by: [research-auth]
  blocks: [implement-auth]

# implement-auth/AGENCY.md
project_id: implement-auth
status: active
dependencies:
  blocked_by: [design-auth]
  blocks: [test-auth]

# test-auth/AGENCY.md
project_id: test-auth
status: pending
dependencies:
  blocked_by: [implement-auth]
  blocks: [deploy-auth]

# deploy-auth/AGENCY.md
project_id: deploy-auth
status: pending
dependencies:
  blocked_by: [test-auth]
```

Query result: Only `implement-auth` shows as ready work.

![Feature Development Pipeline](images/04-feature-pipeline.png)
*A typical feature pipeline: research → design → implement → test → deploy. Each stage blocked by the previous, creating orderly progression.*

### Example 2: Platform Migration

Multiple workstreams that must coordinate:

```
                    ┌─────────────────┐
                    │   migration-    │
                    │     planning    │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │  database-   │  │   api-       │  │   frontend-  │
    │  migration   │  │   migration  │  │   migration  │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                 │
           └─────────────────┼─────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   integration-  │
                    │     testing     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    cutover      │
                    └─────────────────┘
```

```yaml
# database-migration/AGENCY.md
dependencies:
  blocked_by: [migration-planning]
  blocks: [integration-testing]

# api-migration/AGENCY.md
dependencies:
  blocked_by: [migration-planning]
  blocks: [integration-testing]

# frontend-migration/AGENCY.md
dependencies:
  blocked_by: [migration-planning]
  blocks: [integration-testing]

# integration-testing/AGENCY.md
dependencies:
  blocked_by: [database-migration, api-migration, frontend-migration]
  blocks: [cutover]
```

The three migration projects can run in parallel once planning completes. Integration testing waits for all three.

![Platform Migration Diagram](images/04-platform-migration.png)
*Platform migration: planning unlocks three parallel workstreams, integration testing waits for all three, then cutover can proceed. Complex coordination made visible.*

### Example 3: Epic with Sub-Projects

Breaking a large initiative into manageable pieces:

```yaml
# auth-epic/AGENCY.md
project_id: auth-epic
status: active
priority: high
---
# Authentication System Epic

## Objective
Implement complete authentication system with login, registration, and password management.

## Sub-Projects
- auth-login (in progress)
- auth-registration (pending)
- auth-password-reset (pending)

# auth-login/AGENCY.md
dependencies:
  parent: auth-epic
  blocks: [auth-registration]  # Sharing some components

# auth-registration/AGENCY.md
dependencies:
  parent: auth-epic
  blocked_by: [auth-login]  # Reuses login components

# auth-password-reset/AGENCY.md
dependencies:
  parent: auth-epic
  related: [auth-login, auth-registration]  # Context only
```

## Dependency Best Practices

### 1. Be Explicit

If project B needs something from project A, declare it. Don't rely on "everyone knows" or implied ordering.

### 2. Minimize Dependencies

Every dependency is a potential delay. Only declare true blockers—things that genuinely cannot proceed without the prerequisite.

### 3. Use Related for Context

Not every connection is a blocker. If two projects are conceptually related but can proceed independently, use `related` instead of `blocked_by`.

### 4. Review for Cycles Early

Before adding dependencies, think through whether you're creating a cycle. It's easier to prevent cycles than to resolve them.

### 5. Keep Granularity Consistent

Dependencies work best when projects are similarly sized. A tiny bug fix depending on a months-long epic creates awkward scheduling.

### 6. Update Status Promptly

Downstream projects remain blocked until the blocker is marked `completed`. Don't leave completed work in `active` status.

![Dependency Best Practices](images/04-best-practices.png)
*Dependency management rules: be explicit, minimize dependencies, use related for context, watch for cycles, keep consistent granularity, update status promptly.*

## Programmatic Access

For tools and automation, all dependency information is available via the Cortex API:

```python
from src.cortex import Cortex

cortex = Cortex()

# Get full dependency summary
summary = cortex.get_dependency_summary()

# Check if specific project is blocked
blocking_info = cortex.is_blocked("api-integration")
print(blocking_info)
# {
#   'is_blocked': True,
#   'reasons': ['Blocked by uncompleted: database-schema'],
#   'blocking_projects': ['database-schema'],
#   'in_cycle': False,
#   'cycle': []
# }

# Build raw dependency graph
graph = cortex.build_dependency_graph(cortex.discover_projects())
# graph['nodes']: project metadata
# graph['edges']: what each project blocks
# graph['reverse_edges']: what blocks each project

# Detect cycles
cycles = cortex.detect_cycles()
```

![The Full Dependency Graph View](images/04-full-graph.png)
*The full dependency graph: every project, every relationship, every status—visible and queryable. Complexity becomes clarity.*

## Conclusion

Dependency tracking transforms project coordination from implicit tribal knowledge to explicit, queryable structure. Agents can find ready work instantly. Humans can see why things are blocked. Cycles are detected before they cause deadlocks.

The investment is small—a few lines of YAML in each AGENCY.md file. The return is clarity about what can proceed and what's waiting.

---

*Next in the series: "Skills and Protocols" - teaching agents to work effectively within Agent Hive.*

*Agent Hive is open source at [github.com/intertwine/hive-orchestrator](https://github.com/intertwine/hive-orchestrator).*

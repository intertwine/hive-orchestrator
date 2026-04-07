---
workspace_version: 2
last_sync: null
---

# Hive Workspace

Hive is now a CLI-first, substrate-backed workspace.

## What Matters

- `.hive/` holds canonical machine state
- `projects/*/PROGRAM.md` holds execution and evaluator policy
- `GLOBAL.md`, `projects/*/AGENCY.md`, and `AGENTS.md` are human-facing projections

## Fast Path

```bash
hive doctor --json
hive project list --json
hive task ready --json
hive context startup --project <project-id> --json
hive sync projections --json
```

## Working Notes

- Use `hive project create` and `hive task create` for new work.
- Use `hive migrate v1-to-v2` only when importing an older checklist-based repo.
- Use `make session PROJECT=<project-id>` when you want a saved startup bundle for an agent.

<!-- hive:begin projects -->
## Projects

| Project | ID | Status | Priority | Ready | In Progress | Blocked |
|---|---|---:|---:|---:|---:|---:|
| Agent Coordination Layer (Phase 4) | agent-coordination | completed | 2 | 0 | 0 | 0 |
| Beads Pattern Adoption for Hive Orchestrator | beads-adoption | completed | 1 | 0 | 0 | 0 |
| Demo Project | demo | active | 2 | 1 | 0 | 0 |
| Cross-Repository Improvement: Social Compliance Generator | cross-repo-social-compliance | active | 1 | 2 | 0 | 0 |
| Hive MCP Server | hive-mcp | completed | 1 | 0 | 0 | 0 |
| Hive v2.4 Ecosystem Integrations | hive-v24 | active | 2 | 0 | 0 | 0 |
| Hive v2.5 Command Center | hive-v25 | active | 1 | 12 | 1 | 0 |
| OpenCode Plugin for Agent Hive | opencode-plugin | active | 1 | 31 | 0 | 0 |
<!-- hive:end projects -->

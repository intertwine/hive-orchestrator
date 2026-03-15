# Hive 2.0 spec bundle

This bundle turns the Hive 2.0 planning analysis into an implementation handoff package for Codex.

## Files

- `HIVE_V2_SPEC.md` — master technical spec
- `SCHEMA.sql` — derived SQLite cache schema
- `MIGRATION_PLAN.md` — migration plan from Hive 1.x
- `MILESTONE_ISSUE_TREE.md` — epics and issue breakdown
- `AGENT_INTERFACE.md` — CLI-first / Code Mode / optional MCP guidance
- `HANDOFF_TO_CODEX.md` — recommended implementation order
- `examples/` — sample repo artifacts and file shapes

## Recommended reading order

1. `HIVE_V2_SPEC.md`
2. `AGENT_INTERFACE.md`
3. `SCHEMA.sql`
4. `MIGRATION_PLAN.md`
5. `MILESTONE_ISSUE_TREE.md`
6. `HANDOFF_TO_CODEX.md`

## Key thesis

Hive 2.0 should be:

- **CLI-first**
- **structured-file canonical**
- **memory-enabled**
- **`PROGRAM.md`-driven**
- **run/evaluator gated**
- **optional thin Code Mode / MCP**
- **friendly to Codex, Claude Code, OpenCode, Pi, and Hermes**

## Source inspirations

- Hive v1: https://github.com/intertwine/hive-orchestrator
- Observational Memory: https://github.com/intertwine/observational-memory
- Beads: https://github.com/steveyegge/beads
- autoresearch: https://github.com/karpathy/autoresearch
- Cloudflare Code Mode: https://blog.cloudflare.com/code-mode/
- Cloudflare MCP server: https://github.com/cloudflare/mcp
- Pi coding agent essay: https://mariozechner.at/posts/2025-11-30-pi-coding-agent/
- Hermes docs: https://hermes-agent.nousresearch.com/docs/

## Notes

- Canonical repo state is text-based. SQLite is cache only.
- Direct CLI is the default integration path.
- MCP, if retained, should be a two-tool adapter (`search`, `execute`) rather than a large tool catalog.
- The examples intentionally show generated markers and structured task files instead of task checkboxes as the machine truth.

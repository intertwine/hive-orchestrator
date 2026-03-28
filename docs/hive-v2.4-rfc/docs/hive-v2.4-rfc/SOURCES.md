# Sources

This RFC bundle is based on the following current external references.

## Agent Hive / Mellona Agent Hive

1. `intertwine/hive-orchestrator` README and repo tree — current product framing, docs layout, release line, operator console story.
2. `pyproject.toml` — current packaging pattern that already force-includes `docs/hive-v2.2-rfc` and `docs/hive-v2.3-rfc`.
3. `docs/V2_3_STATUS.md` — current release ledger showing the Pi/Hermes/OpenClaw design sprint was deferred from v2.3.

## Pi

4. Pi SDK docs — `createAgentSession()`, `AgentSession`, event streaming, steer/followUp, resource loader.
5. Pi package docs / npm package metadata — current package and ecosystem positioning.

## OpenClaw

6. OpenClaw Gateway architecture docs — gateway as source of truth for sessions/routing.
7. OpenClaw Pi integration architecture — OpenClaw embeds Pi via the Pi SDK, not via subprocess RPC.
8. OpenClaw ACP docs — ACP bridge is gateway-backed and limited in scope.
9. OpenClaw plugin architecture docs — native plugins are in-process and not sandboxed.
10. OpenClaw session/history docs — gateway session history and live transcript APIs.
11. OpenClaw skills / plugins docs — native install/distribution paths.

## Hermes

12. Hermes docs home — product positioning, skills, memory, MCP, gateway, cron, trajectory export.
13. Hermes architecture docs — gateway/session/tool/runtime layering.
14. Hermes messaging gateway docs — long-lived gateway with sessions and cron.
15. Hermes skills docs — skills as procedural memory and extension surface.
16. Hermes configuration docs — location of persistent memory, skills, cron.
17. Hermes security docs — approval flow in gateway mode.
18. Hermes AGENTS tips docs — AGENTS.md as native project context surface.
19. Hermes creating skills docs — secure setup guidance and sandbox/env passthrough.
20. Hermes CLI reference docs — gateway/setup/status/user-facing command surface.

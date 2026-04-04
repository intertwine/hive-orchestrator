# Post-v2.4 Roadmap RFC Bundle

This bundle proposes the next release train after publishing v2.4.

Recommended sequence:

1. **Publish v2.4** as the ecosystem-integration release.
2. **v2.5 — Command Center**: make the console a first-class product with world-class UX and an optional desktop shell.
3. **v2.6 — Task Master Foundations**: close the autonomy gap with mission state, heartbeats, wake conditions, review brokering, and explainability.
4. **v2.7 — Mission Governor**: let Hive keep campaigns moving with bounded autonomous orchestration.
5. **v3.0 — Hive Lab**: offline backtesting and continual improvement for skills, routing, context, evaluators, and policy.

Files:

- `docs/POST_V2_4_RELEASE_ROADMAP.md`
- `docs/POST_V2_4_ACCEPTANCE_MATRIX.md`
- `docs/POST_V2_4_MILESTONE_ISSUE_TREE.md`
- `docs/HANDOFF_TO_CODEX.md`
- `docs/hive-v2.5-rfc/HIVE_V2_5_COMMAND_CENTER_RFC.md`
- `docs/hive-v2.5-rfc/HIVE_V2_5_DESKTOP_SHELL_DECISION.md`
- `docs/hive-v2.6-rfc/HIVE_V2_6_TASK_MASTER_FOUNDATIONS_RFC.md`
- `docs/hive-v2.7-rfc/HIVE_V2_7_MISSION_GOVERNOR_RFC.md`
- `docs/hive-v3.0-rfc/HIVE_V3_0_HIVE_LAB_RFC.md`
- `docs/SOURCES.md`

Guiding decisions:

- The current repo already reads as **v2.4 complete in source** while PyPI still shows **2.3.2**, so publish v2.4 before starting new theme work.
- Keep the browser console as the canonical UI, but architect it so the same frontend can be wrapped in a desktop shell.
- Choose **Tauri 2** for the desktop shell path. Do not choose Electron unless Tauri hits a blocking issue.
- Make **Task Master** the product-facing name for the mission-governance subsystem.
- Keep **continual learning** offline and reviewable; do not let live autonomy silently mutate itself.

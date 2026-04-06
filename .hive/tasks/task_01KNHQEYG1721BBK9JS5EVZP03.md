---
acceptance:
- Shared typography, spacing, color, motion, and elevation tokens exist for the console.
- Core UI primitives support the command-center look without hard-coded one-off styling
  per page.
- The design language preserves browser-first usability and accessible contrast despite
  the stylized treatment.
claimed_until: '2026-04-06T18:24:32.265678Z'
created_at: '2026-04-06T15:44:27.649019Z'
edges: {}
id: task_01KNHQEYG1721BBK9JS5EVZP03
kind: task
labels:
- ui
- design-system
owner: codex
parent_id: task_01KNHQCCFAB4KWR88RGJX2JJTF
priority: 1
project_id: hive-v25
relevant_files:
- frontend/console/src/styles.css
- frontend/console/src/components
- frontend/console/src/App.tsx
source: {}
status: done
title: Build the Clay-aligned command-center design system and token library
updated_at: '2026-04-06T16:29:52.282106Z'
---

## Summary
Introduced a Clay-inspired token library and retuned the shared console shell primitives around it.

## Notes
Added shared typography, color, spacing, motion, radius, and elevation tokens in frontend/console/src/styles.css; refreshed the v2.5 shell copy/highlights in ConsoleLayout.tsx; validated with npm --prefix frontend/console run build and npm --prefix frontend/console run test.

## History
- 2026-04-06T15:44:27.649019Z bootstrap created.
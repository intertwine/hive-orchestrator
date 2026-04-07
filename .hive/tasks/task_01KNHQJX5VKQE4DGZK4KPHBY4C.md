---
acceptance:
- CI covers meaningful browser-console validation beyond route smoke tests.
- Automated accessibility checks exist for the primary v2.5 surfaces.
- Maintainer docs and/or make targets point at the new validation path.
claimed_until: '2026-04-07T07:56:25.920051Z'
created_at: '2026-04-06T15:46:37.371175Z'
edges: {}
id: task_01KNHQJX5VKQE4DGZK4KPHBY4C
kind: task
labels:
- testing
owner: codex
parent_id: task_01KNHQCCFAB4KWR88RGJX2JJTF
priority: 1
project_id: hive-v25
relevant_files:
- frontend/console/package.json
- frontend/console/src/test
- .github/workflows/ci.yml
- Makefile
source: {}
status: done
title: Strengthen the console validation harness with component, E2E, and accessibility
  gates
updated_at: '2026-04-07T07:27:25.453968Z'
---

## Summary
Promote the console from smoke coverage to release-gate coverage in CI and local maintainer flows.

## Notes
- Imported or created by Hive 2.0.

## History
- 2026-04-06T15:46:37.371175Z bootstrap created.
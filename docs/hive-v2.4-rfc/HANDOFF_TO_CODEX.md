# Handoff to Codex for v2.4

Read in this order:

1. `docs/hive-v2.4-rfc/HIVE_V2_4_RFC.md`
2. `docs/hive-v2.4-rfc/HIVE_V2_4_ADAPTER_MODEL_AND_LINK_SPEC.md`
3. `docs/hive-v2.4-rfc/HIVE_V2_4_HARNESS_PACKAGES_AND_ONBOARDING.md`
4. `docs/hive-v2.4-rfc/HIVE_V2_4_IMPLEMENTATION_PLAN.md`
5. `docs/hive-v2.4-rfc/HIVE_V2_4_ACCEPTANCE_TESTS.md`
6. `docs/V2_4_STATUS.md`

## Important constraints

- Do not re-open the already-closed v2.3 debates.
- Do not implement one generic `RpcDriver` for Pi/OpenClaw/Hermes.
- Do not make OpenClaw native plugins the required base path.
- Do not bulk-import Hermes private memory stores.
- Do not let attach mode pretend it is governed.
- Do not break existing Codex/Claude surfaces while adding v2.4.

## Expected first PRs

### PR 1
- add this RFC bundle to the repo
- add `docs/V2_4_STATUS.md`
- wire packaging includes

### PR 2
- add adapter-family split
- add Hive Link protocol/types
- add dummy integration tests
- add minimal console truth surfaces

### PR 3
- Pi package skeleton + doctor + attach foundations

Only after PR 2 is stable should work begin on OpenClaw and Hermes.

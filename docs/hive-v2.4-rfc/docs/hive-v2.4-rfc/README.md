# Agent Hive v2.4 RFC Bundle

This bundle is the planning and design reference for **Agent Hive / Mellona Agent Hive v2.4**.

v2.3 closed the control-plane gaps around truthful runtime depth for Codex and Claude, hybrid retrieval, campaigns, and the operator console. The remaining major product opportunity is to make Hive a **first-class control-plane companion inside the Pi, OpenClaw, and Hermes ecosystems** rather than treating those products as a single generic “RPC harness” bucket.

## Files

- `HIVE_V2_4_RFC.md` — main RFC and product decisions
- `HIVE_V2_4_ADAPTER_MODEL_AND_LINK_SPEC.md` — adapter split, Hive Link protocol, normalized trajectory format, capability rules
- `HIVE_V2_4_HARNESS_PACKAGES_AND_ONBOARDING.md` — Pi/OpenClaw/Hermes package strategy, attach/managed flows, onboarding
- `HIVE_V2_4_IMPLEMENTATION_PLAN.md` — milestone order, code-area map, rollout plan
- `HIVE_V2_4_ACCEPTANCE_TESTS.md` — north-star scenarios and hard release gates
- `SOURCES.md` — external product and platform references used in this RFC
- `../V2_4_STATUS.md` — maintainer-facing execution ledger template for the release line

## Intended use

Start with `HIVE_V2_4_RFC.md`, then implement in this order:

1. adapter-model correction
2. Hive Link and normalized trajectory capture
3. companion packages and attach mode
4. Pi managed mode
5. OpenClaw and Hermes gateway/delegate attach flows
6. console truth surfaces and docs

## One-sentence summary

**v2.4 makes Agent Hive a first-class observe-and-steer companion inside Pi, OpenClaw, and Hermes by splitting worker-session vs delegate-gateway integrations, shipping native ecosystem packages, and standardizing attach-first session telemetry through Hive Link.**

# Agent Hive v2.3 Completion RFC Bundle

This bundle is the historical planning and design reference for **Agent Hive / Mellona Agent Hive v2.3**.

Current scoped release truth lives in [`docs/V2_3_STATUS.md`](../V2_3_STATUS.md). Use that ledger for what is
actually required, complete, deferred, or still blocking the release call.

## Files

- `HIVE_V2_3_RFC.md` — main RFC and product decisions
- `HIVE_V2_3_RUNTIME_AND_SANDBOX_SPEC.md` — driver, handoff, capability, event, and sandbox spec
- `HIVE_V2_3_RETRIEVAL_AND_CAMPAIGNS_SPEC.md` — hybrid retrieval and portfolio/campaign scheduler spec
- `HIVE_V2_3_IMPLEMENTATION_PLAN.md` — milestone order, code-area map, rollout plan
- `HIVE_V2_3_ACCEPTANCE_TESTS.md` — north-star scenarios and hard release gates
- `SOURCES.md` — external product and platform references used in this RFC

## Intended use

Start with `HIVE_V2_3_RFC.md`, then implement in this order:

1. runtime contracts and capability truthfulness
2. deep Codex and Claude drivers
3. sandbox backends
4. hybrid retrieval
5. portfolio campaigns and console polish
6. acceptance tests and release docs

## One-sentence summary

**v2.3 completes Hive 2.2 by making it a truthful, harness-agnostic observe-and-steer control plane with deep runtime adapters, real sandboxes, explainable retrieval, and policy-driven multi-project orchestration.**

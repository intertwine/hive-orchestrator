# PR: Add v2.4 RFC bundle for Pi / OpenClaw / Hermes ecosystem integrations

## Summary

This PR adds the v2.4 design bundle and status ledger for the next Agent Hive release line.

The core design change is to stop treating Pi, OpenClaw, and Hermes as one generic “RPC harness” family and instead split integrations into:

- `WorkerSessionAdapter` — bounded coding/work sessions (Pi)
- `DelegateGatewayAdapter` — long-lived gateway/delegate systems (OpenClaw, Hermes)

The bundle also freezes:

- four integration levels: pack, companion, attach, managed
- advisory vs governed truth surfaces
- Hive Link as the native session bridge
- native ecosystem package strategy
- acceptance tests and release gates

## Why now

v2.3 already closed the major control-plane gaps around truthful Codex/Claude depth, retrieval, campaigns, and console UX. The next major growth opportunity is to make Hive a first-class player inside Pi, OpenClaw, and Hermes rather than treating them as a deferred generic adapter bucket.

## Files added

- `docs/V2_4_STATUS.md`
- `docs/hive-v2.4-rfc/README.md`
- `docs/hive-v2.4-rfc/HIVE_V2_4_RFC.md`
- `docs/hive-v2.4-rfc/HIVE_V2_4_ADAPTER_MODEL_AND_LINK_SPEC.md`
- `docs/hive-v2.4-rfc/HIVE_V2_4_HARNESS_PACKAGES_AND_ONBOARDING.md`
- `docs/hive-v2.4-rfc/HIVE_V2_4_IMPLEMENTATION_PLAN.md`
- `docs/hive-v2.4-rfc/HIVE_V2_4_ACCEPTANCE_TESTS.md`
- `docs/hive-v2.4-rfc/SOURCES.md`

## Follow-up implementation order

1. repo/status wiring
2. adapter-model correction + Hive Link
3. Pi package + attach + managed
4. OpenClaw skill + bridge + attach
5. Hermes skill/toolset + attach
6. console/docs/release polish

## Non-goals in this PR

- no runtime implementation yet
- no OpenClaw managed mode
- no Hermes managed mode
- no new sandbox work
- no continual-learning implementation yet

## Review checklist

- [ ] adapter-family split is clear and justified
- [ ] package strategy feels native to each ecosystem
- [ ] advisory vs governed truth is explicit
- [ ] acceptance tests are strong enough to drive implementation
- [ ] status ledger matches the intended v2.4 scope

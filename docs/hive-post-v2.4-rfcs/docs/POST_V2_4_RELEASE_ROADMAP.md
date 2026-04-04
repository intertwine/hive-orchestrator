# Post-v2.4 Release Roadmap

## Executive decision

Publish v2.4 now, then run a four-release sequence:

- **v2.5 — Command Center**
- **v2.6 — Task Master Foundations**
- **v2.7 — Mission Governor**
- **v3.0 — Hive Lab**

This is the cleanest path because the current product line has already solved the substrate problem:

- the repo README already describes v2.4-native Pi, OpenClaw, and Hermes flows;
- the console is now a real observe-and-steer surface, not just a toy dashboard;
- the remaining gap is no longer “can Hive integrate with workers?” but “can operators love the UI?” and then “can Hive keep work moving without invisible human babysitting?”

## Why this sequence

### 1. The next short-term adoption bottleneck is the console
The console is now good enough to prove the architecture, but it is not yet polished enough to become the obvious daily home for non-power users. A console-first release will improve:

- first-run comprehension
- supervisor confidence
- review efficiency
- adoption by less terminal-oriented users
- the human experience before autonomy becomes deeper

### 2. Task Master should come after console polish, not before it
Once Hive starts making more autonomous orchestration decisions, the operator will need excellent visibility into:

- what Hive decided
- why it decided that
- what it did next
- what it needs from the human

A mediocre console plus a powerful governor is a trust failure waiting to happen.

### 3. Continual learning belongs after Task Master
The system should first emit rich mission-governance evidence, then learn from it offline. Otherwise the lab only learns from worker trajectories and misses the orchestration layer that actually determines long-horizon success.

## Release themes

## v2.5 — Command Center

**Theme:** make the console feel like a real product.

**North star:** a smart but busy user should be able to install Hive, open the console, understand the portfolio, triage what matters, and take meaningful actions without reading repo internals or memorizing CLI primitives.

**Primary deliverables:**

- refined information architecture
- design system and interaction model
- action center / command palette
- run detail and review ergonomics
- notifications and deep links
- onboarding and adoption polish
- optional Tauri desktop shell beta

## v2.6 — Task Master Foundations

**Theme:** close the babysitting gap.

**North star:** Hive should proactively request progress, schedule review, compile mission state, and escalate real decisions without the human manually shepherding each step.

**Primary deliverables:**

- mission-state compiler
- structured worker heartbeats
- event-driven wake loop
- review broker alpha
- autonomy policy / circuit breakers
- explainability surfaces in console and CLI

## v2.7 — Mission Governor

**Theme:** keep campaigns moving.

**North star:** for healthy governed campaigns, Hive can keep work moving for hours without manual prompting while remaining truthful, auditable, and bounded.

**Primary deliverables:**

- automatic next-run launch
- rerouting and side-quest spawning
- cross-harness review orchestration
- daily briefs and campaign commitment updates
- autopilot modes with strict guardrails

## v3.0 — Hive Lab

**Theme:** get better from history.

**North star:** completed runs and governance decisions become case files that can generate reviewable, backtested improvements to skills, routing, context compilation, evaluators, and policy.

**Primary deliverables:**

- case-file capture
- graders and benchmark sets
- proposal generation
- backtesting
- canaries and rollback
- optional experimental adapter-finetuning lane

## Desktop decision

The right sequence is:

1. make the browser console excellent;
2. keep the frontend and APIs shell-friendly;
3. ship a **Tauri 2 desktop shell beta** as part of v2.5;
4. decide on desktop GA after real user feedback.

Do **not** create a second product line. The desktop app should wrap the same console frontend and local Hive daemon.

## Why Tauri 2

Tauri 2 is the right fit for Agent Hive because it:

- is stable and targets desktop platforms with a system-webview architecture;
- has a capability and plugin-permission model that fits a local control-plane app;
- has official plugins for updater, tray, notification, dialog, and store;
- keeps the desktop shell thinner than Electron.

Electron remains a credible fallback and has very mature updater tooling, but it ships Chromium and Node, which increases footprint and security/maintenance burden. Wails v3 is interesting, but still alpha.

## Parallel tracks that should not define the release train

These may land inside the releases below, but they should not become the headline:

- E2B / Daytona parity hardening
- cross-encoder reranking tuning
- Qdrant enterprise backend
- OpenClaw managed mode
- Hermes managed mode
- LoRA / RFT experiments

## Governance rule for the whole roadmap

Each release after v2.4 must preserve three truths:

1. **Browser console remains first-class.**
2. **CLI remains canonical and scriptable.**
3. **Any new autonomy must be explainable, bounded, and reviewable.**

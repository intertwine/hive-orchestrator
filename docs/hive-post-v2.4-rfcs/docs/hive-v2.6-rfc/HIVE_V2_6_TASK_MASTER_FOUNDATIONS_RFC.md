# Hive v2.6 RFC — Task Master Foundations

## Thesis

v2.4 solved ecosystem integration.  
v2.5 will solve operator UX.  
v2.6 should solve the **babysitting gap**.

The recurring dogfooding failure is not that workers cannot do useful work. The failure is that the human still acts as the invisible foreman:

- asking for progress
- asking for review
- nudging the next step
- coordinating between agents
- noticing stale sessions
- keeping campaign state coherent

Task Master should become the mission-governance layer that closes that gap.

## Naming

- **Task Master** = product-facing name
- **Mission Governor** = architecture term for the outer-loop subsystem

## Goal

Make Hive proactive enough that it can keep campaigns healthy and coherent without requiring the operator to manually shepherd every review, status request, or next-step decision.

## Scope

## In scope

### 1. Mission-state compiler
For each campaign, compile a durable mission state from:

- tasks
- run outcomes
- campaign decisions
- delegate notes
- memory artifacts
- operator steering
- review outcomes

Required artifacts:

- `.hive/campaigns/<id>/mission-state.json`
- `.hive/campaigns/<id>/committed-plan.md`
- `.hive/campaigns/<id>/open-threads.md`
- `.hive/campaigns/<id>/state-evidence.json`

Every major state item must carry:

- confidence
- freshness
- provenance
- owner
- review deadline

### 2. Structured worker heartbeats
Add a common status contract for governed runs and attached delegates:

- current objective
- current subtask
- progress estimate
- blocker
- confidence
- next intended action
- needs review?
- needs decision?
- stale-context risk?

The contract should support both:
- push heartbeats
- pull-on-demand status requests

### 3. Event-driven wake loop
Add a real Task Master process:

- `hive taskmaster serve`
- `hive taskmaster tick`
- `hive taskmaster status`
- `hive taskmaster pause`
- `hive taskmaster resume`
- `hive taskmaster explain`

It should wake on:

- run completion
- run failure
- approval request
- blocked/inbox item
- stale heartbeat
- delegate note
- campaign cadence
- budget threshold

### 4. Review broker alpha
Broker review and progress requests automatically:

- create reviewer work when policy says a run needs review
- ask stale workers for structured status
- request cross-harness review when confidence is low
- create side-quest tasks when a blocker requires research
- merge review output back into mission state

### 5. Policy and circuit breakers
Per campaign or workspace policy:

- allowed action classes
- quiet hours
- escalation thresholds
- cooldown/hysteresis
- max concurrent broker actions
- max failed-loop count
- budget caps

### 6. Explainability surfaces
Operators must be able to answer:

- why Task Master woke up
- why it chose this action
- what evidence it used
- what it considered but rejected
- what policy constrained it

## Out of scope

- fully autonomous campaign execution
- silent self-modification
- offline learning lab
- heavy new sandbox capabilities

## Architecture

## Core loop
1. ingest events and heartbeats
2. refresh mission state if needed
3. evaluate wake reason
4. score candidate actions
5. choose bounded next action
6. emit action + explanation
7. wait for result or next wake

## Action classes for v2.6
Allowed:
- request status
- request review
- create follow-up task
- post steering note
- requeue task
- update brief / committed plan
- escalate to operator

Not yet allowed by default:
- autonomous run launch
- autonomous reroute
- autonomous finish/promote

Those belong to v2.7.

## Milestones

## M1 — Mission state and heartbeats
Deliver:

- campaign mission-state artifacts
- heartbeat schema
- adapters for local/Codex/Claude/Pi
- coarse advisory heartbeats for OpenClaw/Hermes
- mission-state inspector in console

## M2 — Wake loop and broker
Deliver:

- taskmaster service
- event subscriptions
- stale-run detection
- structured progress requests
- reviewer request generation
- broker action ledger

## M3 — Explainability and policy
Deliver:

- taskmaster explain surfaces
- policy editor
- circuit-breaker behavior
- quiet hours / notification policy
- operator controls in console and CLI

## Acceptance criteria

### Functional
- Task Master maintains mission-state artifacts for active campaigns.
- Governed runs and supported delegates emit structured status in a common shape.
- Task Master can wake on completion, failure, stale heartbeat, inbox item, delegate note, and cadence.
- Task Master can request review and request status without human prompting.
- All Task Master actions are written to a durable decision log.

### Trust
- Every Task Master action has a human-readable explanation.
- Operators can pause or resume Task Master per campaign.
- Circuit breakers stop repeated bad loops.
- Advisory sessions remain advisory; Task Master does not pretend to own them.

### Autonomy-gap closure
- During a healthy campaign, the operator no longer needs to manually ask for routine progress updates.
- When a run becomes stale, Hive notices and reacts.
- When a run completes and policy requires review, Hive requests or schedules that review on its own.

### UI
- The console shows mission state, recent Task Master actions, next planned action, and stale-state warnings.
- Operators can see both the committed plan and open threads for a campaign.

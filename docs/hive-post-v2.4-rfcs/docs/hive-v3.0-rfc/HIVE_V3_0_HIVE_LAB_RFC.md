# Hive v3.0 RFC — Hive Lab

## Thesis

By the time v3.0 starts, Hive should have:

- durable run artifacts
- normalized trajectories
- mission-state histories
- Task Master decisions
- review outcomes
- operator overrides
- campaign briefs
- policy explanations

That creates the raw material for a true offline improvement lab.

## Goal

Turn historical work into reviewable, backtested improvement proposals for:

- skills
- routing rules
- context compilation
- retrieval tuning
- evaluator coverage
- campaign policy
- Task Master heuristics

Model adaptation (LoRA / RFT / fine-tuning) is an optional later lane, not the first target.

## Core idea

**Collect → Grade → Mine → Propose → Backtest → Canary → Promote**

The lab must remain offline-first and reviewable.  
It must never silently self-edit production behavior.

## Scope

## In scope

### 1. Case-file capture
For each completed run and governance decision, store a case file including:

- repo snapshot / commit
- task family
- harness and sandbox
- context bundle hash
- retrieval trace
- skills used
- evaluator outputs
- approvals
- steering actions
- Task Master decisions
- final outcome
- cost / latency / duration

### 2. Graders and benchmark sets
Support:

- deterministic checks
- LLM judges
- human calibration samples
- held-out benchmark suites by task family

### 3. Proposal generation
Generate explicit proposals, not vague “lessons”:

- skill patch
- context compiler rule
- routing rule
- retrieval parameter change
- evaluator addition
- campaign-policy adjustment

### 4. Backtesting
Replay held-out cases with proposed changes and compare:

- outcome quality
- process quality
- cost
- latency
- review burden
- regression risk

### 5. Canary and promotion
Accepted proposals can be:

- canaried on a small slice of work
- monitored
- rolled back
- promoted to wider rollout

## Out of scope for initial v3.0
- fully automatic production self-modification
- broad model retraining as the default improvement path
- replacing human review for risky proposals

## Prioritization ladder

Optimize these layers in order:

1. skills
2. context compiler
3. routing / scheduling policy
4. evaluator and promotion rules
5. prompt/program templates
6. model adapters / LoRA / RFT last

## Milestones

## M1 — Data and grading
Deliver:

- case-file schema
- collector jobs
- grader framework
- benchmark set support
- lab UI or CLI for case inspection

## M2 — Proposal and backtesting
Deliver:

- proposal generator
- replay harness
- metric dashboards
- diffable proposal artifacts
- approval workflow

## M3 — Canary and rollout
Deliver:

- canary controls
- rollback
- proposal registry
- adoption reports
- production promotion workflow

## Acceptance criteria

### Functional
- Historical runs and Task Master decisions can be collected into case files.
- The lab can generate at least one concrete proposal type and backtest it.
- Backtests report both improvements and regressions.
- Accepted proposals can be canaried and rolled back.

### Trust
- Every proposal includes evidence.
- Every proposal is reviewable before rollout.
- Production behavior never changes silently from the lab.

### Strategic
- The lab can improve at least one non-model layer before model-adaptation work begins.
- The system can explain which class of failures it is trying to fix and how success is measured.

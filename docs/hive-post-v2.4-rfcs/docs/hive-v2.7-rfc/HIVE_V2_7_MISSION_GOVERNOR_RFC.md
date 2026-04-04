# Hive v2.7 RFC — Mission Governor

## Thesis

v2.6 should make Hive proactive.  
v2.7 should make Hive **operationally autonomous enough to keep healthy campaigns moving**.

This is where Task Master becomes a true mission governor.

## Goal

For governed campaigns with a strong `PROGRAM.md`, good evaluators, and acceptable harness/sandbox support, Hive can keep work progressing for hours without manual prompting while staying auditable and bounded.

## Core promise

The operator moves from “foreman” to “supervisor and final authority.”

Hive should be able to:

- choose the next governed run
- launch it
- request review
- reroute or split side quests
- update campaign commitment state
- escalate only when policy, confidence, or authority requires it

## Scope

## In scope

### 1. Autonomous next-step execution
Allow Task Master to:

- launch next governed run
- select harness/driver by policy
- select sandbox profile by policy
- requeue or defer work
- create side quests and merge them back

### 2. Reroute and rescue
When a run is unhealthy or blocked, Task Master can:

- reroute to another harness
- request a reviewer run
- create blocker-unlock work
- ask for targeted research
- pause the failing lane

### 3. Campaign commitment updates
Task Master maintains:

- committed plan
- open threads
- last major decision
- next intended sequence
- current blockers
- budget/health summary

### 4. Review swarm
For selected campaigns, policy can require:

- second-harness review
- separate-model review
- human approval
- code-owner review
- deterministic evaluator re-run

### 5. Autopilot modes
Per campaign:

- `observe`
- `assist`
- `governed-autopilot`
- `quiet-autopilot`

Each mode explicitly controls what Hive may do without asking first.

### 6. Daily and cadence briefs
Task Master should generate:

- daily brief
- overnight brief
- end-of-campaign brief
- “what changed since yesterday” summary
- unresolved-risk summary

## Out of scope

- offline learning and proposal generation
- automatic skill mutation
- hidden self-modification

## Safety rules

- Any irreversible or high-risk action still follows policy gates.
- Campaigns can only enter autopilot with a doctor/eligibility check.
- All actions remain inspectable in the console and decision logs.
- Quiet modes suppress noise, not auditability.

## Milestones

## M1 — Governed-autopilot for healthy campaigns
Deliver:

- launch-next action
- harness/sandbox selection integration
- autopilot mode model
- doctor checks for autopilot eligibility
- campaign action ledger

## M2 — Rescue and review swarm
Deliver:

- reroute action
- review swarm
- side-quest creation
- merge-back summaries
- blocker-unlock workflows

## M3 — Briefs and operational polish
Deliver:

- daily/overnight briefs
- quiet-autopilot
- better escalation paths
- autopilot controls in console
- incident/recovery flows

## Acceptance criteria

### Functional
- A governed campaign can keep launching appropriate next runs without manual prompting.
- Hive can request or launch review automatically according to campaign policy.
- Hive can reroute blocked or failing work according to policy.
- Side-quest results can merge back into the main campaign context.

### Safety
- Autopilot is opt-in and policy-gated.
- Doctor checks prevent autopilot on weakly governed projects.
- Every autonomous action has an explanation and an audit entry.
- Circuit breakers stop runaway or repetitive loops.

### Operator experience
- The operator can see current autopilot mode, recent actions, pending escalations, and why Hive believes the campaign is healthy or unhealthy.
- The operator can pause, downgrade, or override autopilot from the console.
- Daily/overnight briefs let a supervisor catch up quickly after time away.

### Outcome
- In a healthy demo campaign, Hive can keep work moving for an extended unattended period with bounded escalations and no need for the human to manually remind workers to review, report, or continue.

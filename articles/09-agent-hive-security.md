# Security in Agent Hive

_Security in Hive starts with narrowing the surface area, not with pretending autonomous systems are harmless._

---

![Hero: Security Layers](images/agent-hive-security/img-01_v1.png)
_Hive separates state, policy, execution, and review so that one mistake does not quietly become system-wide chaos._

---

## The Security Posture In One Sentence

Hive assumes agents are useful, fallible, and sometimes dangerous.

That assumption shapes the system:

- canonical task state is explicit and auditable
- human-facing docs are separate from machine state
- autonomous runs are governed by `PROGRAM.md`
- execution is bounded
- artifacts are reviewable
- optional integrations stay optional

Hive is not built around "just trust the agent."

## The Main Security Boundaries

### 1. Structured substrate vs. narrative docs

Hive v2 moved machine state into `.hive/`.

That is a security feature as much as an architectural one.

It means:

- task claims are not inferred from prose
- ready work is not scraped from checkbox lists
- run artifacts live in predictable places
- cache can be rebuilt from canonical files

`AGENCY.md` still matters, but it matters as a human document. That reduces the chance that a stray sentence or malformed checklist becomes accidental machine input.

### 2. `PROGRAM.md` as an autonomy contract

Every serious autonomous workflow needs a written policy boundary.

In Hive, that boundary is `PROGRAM.md`.

It controls:

- allowed paths
- denied paths
- permitted evaluator commands
- escalation conditions
- review requirements
- budgets

That does two things:

- it limits what a run is supposed to do
- it gives reviewers a concrete contract to evaluate the run against

Without that contract, "the agent seemed reasonable" becomes the policy. That is not strong enough.

### 3. Reviewable run artifacts

Hive stores run data under `.hive/runs/`.

That includes things like:

- metadata
- plans
- patch data
- summaries
- reviews
- command logs
- evaluator output

This is an underrated part of the security model. Security is much better when a reviewer can see what happened without reverse-engineering it from scattered logs.

## The Threats Hive Is Trying To Reduce

### Prompt-shaped confusion

Narrative project documents are useful, but they can also contain stale instructions, partial thoughts, or hostile content copied from elsewhere.

Hive reduces that risk by:

- keeping canonical task state structured
- assembling startup context deliberately
- separating policy from prose

The lesson is simple: treat human docs as useful input, not as automatically trusted instructions.

### Unbounded execution

Autonomous systems get dangerous fast when they can run anything, anywhere.

Hive counters that with:

- allow/deny command rules
- allow/deny path rules
- bounded `execute`
- local worktree isolation for runs
- review and escalation gates

The point is not to create a perfect sandbox. The point is to make dangerous behavior explicit and harder to do by accident.

### Silent state corruption

V1-style systems often rot when the only state is half-structured Markdown that different tools interpret differently.

Hive v2 is stricter:

- canonical task files have schema
- links are validated
- claims expire
- cache is derived, not authoritative
- projections can be regenerated

That makes recovery and inspection much cleaner.

### Overpowered integrations

GitHub apps, MCP servers, coordinators, and chatops integrations can be useful. They also expand the attack surface.

Hive's stance is that the core CLI should work without them.

That gives you a defensible baseline:

- local CLI use
- Git review
- explicit policy
- optional integrations added only when they earn their keep

## Safe Defaults Matter More Than Clever Warnings

The safest default Hive choices are also the least glamorous ones:

- the core CLI does not require a model API key
- `PROGRAM.md` starts conservative
- runs need evaluators to be accepted
- human docs are projections, not the machine database
- optional services are off until configured

Those defaults are what keep a new workspace from starting life in an over-trusting state.

## What To Review Before You Let Agents Run Wild

### `PROGRAM.md`

Read it like a security policy, not like boilerplate.

Ask:

- do the allowed paths make sense
- are evaluator commands minimal
- are denied paths actually sensitive enough
- should review be mandatory for some areas

### Secrets handling

Keep secrets out of project docs and out of canonical task files.

Use normal secret-management tools, environment injection, and CI secrets. Hive is not a secret store.

### Execution profile

If you are using `hive execute` or autonomous evaluators, be honest about the trust model on that machine.

Bounded local execution is still execution.

### Optional web surfaces

If you turn on a coordinator, dashboard, or GitHub automation, treat those as real services:

- restrict credentials
- scope tokens narrowly
- keep permissions minimal
- log enough to understand misuse

## A Practical Deployment Checklist

For a solo developer:

- use the CLI first
- keep `PROGRAM.md` narrow
- prefer local review before auto-accepting runs
- avoid adding integrations you do not need

For a small team:

- standardize `PROGRAM.md` conventions
- require review on sensitive paths
- keep branch protection on
- use issue/PR automation only with scoped tokens

For a larger organization:

- define workspace templates
- make run acceptance auditable
- decide where secrets, evaluators, and human approvals live
- treat dispatcher and harness integrations as production systems

## What Hive Does Not Promise

Hive does not make autonomous code execution magically safe.
Hive does not solve malicious dependencies.
Hive does not replace endpoint security, repository controls, or human judgment.

What it does do is give you a cleaner, tighter operating model than "let the agent loose and hope the transcript is enough."

That is a real security improvement.

## Bottom Line

The best security property in Hive is not a clever filter or a fancy sandbox.

It is the system shape itself:

- explicit state
- explicit policy
- explicit claims
- explicit artifacts
- explicit review

That shape makes bad decisions easier to catch and easier to recover from.

For an agent orchestration platform, that is the difference between something exciting and something you can actually run.

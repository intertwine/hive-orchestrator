# Agent Hive v2.4 RFC — Native Ecosystem Integrations for Pi, OpenClaw, and Hermes

Status: Proposed  
Date: 2026-03-27  
Audience: product, engineering, docs, release, design  
Applies to: `intertwine/hive-orchestrator` / package `mellona-hive` / product `Agent Hive`

Current release truth for v2.3 lives in `docs/V2_3_STATUS.md`. This RFC defines the **next line**: v2.4.

## 1. Executive summary

Agent Hive 2.3 closed most of the gaps left in the original v2 vision:

- truthful, live Codex and Claude integrations
- a real observe-and-steer console
- hybrid retrieval
- campaign reasoning
- real sandbox profiles
- packaged docs and status-ledger discipline

The big thing left is **ecosystem reach**.

Pi, OpenClaw, and Hermes are not just “more harnesses.” They are ecosystems with their own users, extension models, session semantics, and growth loops. If Hive wants to become the control plane above many agent systems, it cannot treat those products as a single generic RPC adapter problem.

That old framing is wrong.

### The core design correction

Hive v2.4 will stop thinking in terms of one “RPC harness” family and instead support **two adapter families**:

1. **WorkerSession adapters** — bounded coding/work sessions with a clear open → stream → steer → finish lifecycle
2. **DelegateGateway adapters** — long-lived agent/gateway systems that own sessions, channels, schedules, and persistent delegates

This single change fixes the biggest category error in the current design.

### The concrete v2.4 product line

Hive v2.4 will be:

- **Pack-first**: installable inside the native Pi/OpenClaw/Hermes environment
- **Companion-first**: useful without asking users to abandon their current harness
- **Attach-first**: able to observe a native session that Hive did not launch
- **Managed where it truly fits**: Pi gets full managed mode; OpenClaw/Hermes start with companion + attach as the primary product value
- **Truthful by default**: advisory vs governed mode, session owner, sandbox owner, and capability provenance must be obvious everywhere

The message becomes:

> **Keep your agent. Add Hive.**  
> For Pi, OpenClaw, and Hermes, Hive must show up where those users already work.

## 2. Problem statement

The remaining gap after v2.3 is not substrate quality. The substrate is good enough. The gap is **ecosystem-native integration**.

The deferred Pi/OpenClaw/Hermes work matters because:

- these ecosystems have large and fast-growing user communities
- they each already have skills, plugin, or package channels that users trust
- they each think about sessions and control differently
- they are exactly the sort of harnesses people want to keep using while adding a higher-level orchestration layer

### 2.1 Why the old “RPC harness” framing fails

Pi, OpenClaw, and Hermes look similar only from far away.

- **Pi** is fundamentally a session-centric coding harness with an SDK and a headless RPC path.
- **OpenClaw** is a gateway platform. It embeds Pi through the Pi SDK instead of treating Pi as a subprocess, and the Gateway is the source of truth for sessions and routing.
- **Hermes** is a long-lived agent platform with its own gateway, cron, memory, skills, toolsets, and messaging surfaces.

Trying to flatten all three into one generic `RpcDriver` would force Hive into the wrong abstractions:
- launch-centric instead of session-centric
- subprocess-centric instead of gateway-centric
- code-worker-centric instead of delegate-centric

## 3. Decisions resolved in this RFC

These are hard decisions. They are no longer open questions.

### 3.1 Split adapter families

Hive will support two top-level adapter kinds.

#### A. WorkerSession adapters

Use this when the native harness exposes a bounded work session that can be:
- opened
- streamed
- steered
- completed
- attached to a task/run

**First v2.4 target**
- Pi

**Existing analogous model**
- Codex
- Claude Code

#### B. DelegateGateway adapters

Use this when the native harness owns:
- long-lived session routing
- multi-surface conversations
- scheduled work
- gateway/session stores
- delegates or background agents

**First v2.4 targets**
- OpenClaw
- Hermes

### 3.2 Freeze four integration levels

Every integration advertises one or more of these levels.

#### Level 0 — Pack
Hive is present in the native ecosystem as an installable package, skill, or bundle.

#### Level 1 — Companion
The user stays inside Pi/OpenClaw/Hermes and can call Hive actions there:
- next work
- search
- attach/open
- finish/escalate
- steering note / status

#### Level 2 — Attach
Hive can bind to an already-running native session and surface it in the Hive console without relaunching it.

#### Level 3 — Managed
Hive launches the session itself with worktree/runpack/policy/sandbox ownership.

### 3.3 Freeze governance modes

Every attached or managed integration must expose one of:

- **advisory** — Hive observes and can steer, but it does not own the launch context or outer sandbox
- **governed** — Hive owns the runpack, policy, worktree, and outer sandbox

This distinction is non-negotiable.

Attach mode is usually `advisory`.
Managed mode is usually `governed`.

### 3.4 Use Hive Link as the native session bridge

Hive will **not** use MCP or ACP as its core long-lived session protocol.

Those standards are useful, but they are not enough for Hive’s needs:
- lifecycle ownership
- capability truth snapshots
- approvals
- run artifacts
- steering
- normalized trajectories
- governance/sandbox provenance

Instead, Hive v2.4 will add a dedicated bridge layer:

- **stable JSON CLI** for one-shot control
- **Hive Link** for streaming/attach session control

### 3.5 Treat MCP and ACP as secondary, not primary

- **MCP** remains useful as a thin companion-tool surface inside other agents.
- **ACP** remains useful as an editor attach/interoperability path.
- Neither becomes the canonical Hive runtime protocol.

### 3.6 Harness-specific design choices

#### Pi
- primary: **library-first**
- secondary/fallback: **RPC**
- v2.4 target: **Companion + Attach + Managed**

#### OpenClaw
- primary: **Gateway-first**
- secondary: **ClawHub skill**
- not primary: native plugin runtime
- v2.4 target: **Companion + Attach**
- managed mode: **deferred**

#### Hermes
- primary: **skill/toolset-first**
- secondary: **gateway attach**
- tertiary: **MCP recipe**
- v2.4 target: **Companion + Attach**
- managed mode: **deferred except optional local-beta spike if nearly free**

## 4. Why these choices are right

### 4.1 Pi should be library-first

Pi’s SDK centers on `createAgentSession()` and `AgentSession`, with explicit event subscription, prompt/steer/follow-up methods, and a resource loader that can supply extensions, skills, prompt templates, and context files. That is exactly the shape Hive wants for a deep worker-session integration.

RPC remains valuable, but it should be the fallback attach/headless path, not the deepest architecture.

### 4.2 OpenClaw should be gateway-first

OpenClaw’s own docs describe a long-lived Gateway that owns messaging surfaces, sessions, routing, and nodes. Its ACP bridge is explicitly a gateway-backed bridge with limited ACP scope, and the docs for native plugins are unusually direct that they run in-process and are not sandboxed.

That means:
- the **Gateway** is the real integration point
- **native plugins are not the base path**
- ACP is not enough to be the primary control plane

### 4.3 Hermes should be skill/toolset-first

Hermes is not just a coding harness. It is a persistent agent platform with:
- gateway
- sessions
- cron
- memory
- skills
- toolsets
- MCP support
- AGENTS-aware context
- trajectory export

The easiest adoption path for Hermes users is not “launch Hermes from Hive.” It is:
- install Hive support as a native Hermes capability
- keep using Hermes the way they already do
- attach that work into Hive when supervision, portfolio reasoning, or campaign control matters

## 5. Goals

1. Make Hive feel native inside Pi, OpenClaw, and Hermes.
2. Let users start with **Companion** mode and upgrade to **Attach** or **Managed** later.
3. Ensure **Attach** mode requires no transcript copying and no relaunch.
4. Keep Hive’s model-facing surface thin: JSON CLI + Hive Link.
5. Standardize one normalized `trajectory.jsonl` format across all adapters.
6. Preserve strict truthfulness around governance and sandbox ownership.
7. Produce artifacts that directly feed the later continual-learning/backtesting line.

## 6. Non-goals

1. Do not create one generic `RpcDriver` and call it done.
2. Do not make OpenClaw or Hermes “managed” before companion + attach are product-quality.
3. Do not require MCP or ACP for the core integration path.
4. Do not import private personal memory from Hermes or OpenClaw wholesale into Hive.
5. Do not require users to hand-edit config files as the primary onboarding path.
6. Do not promise governed execution when Hive does not own the outer sandbox.
7. Do not add a large new tool catalog to the model-facing interface.

## 7. Support matrix for v2.4

| Harness | Adapter family | v2.4 product level | Governance target | Primary technical path |
|---|---|---|---|---|
| Pi | WorkerSession | Pack + Companion + Attach + Managed | governed in Managed; advisory in Attach | Pi SDK via companion runner; RPC fallback |
| OpenClaw | DelegateGateway | Pack + Companion + Attach | advisory | Gateway bridge + ClawHub skill |
| Hermes | DelegateGateway | Pack + Companion + Attach | advisory | skill/toolset + gateway/CLI attach + optional MCP recipe |

## 8. Product surfaces that must ship

### 8.1 Native ecosystem packages

#### Pi
`@mellona/pi-hive`

#### OpenClaw
- `agent-hive` ClawHub skill
- `openclaw-hive-bridge` external bridge

#### Hermes
- first-class Hermes integration inside `mellona-hive`
- exportable Hermes skill/toolset bundle
- optional MCP recipe
- optional future `mellona-hermes` meta-package only if discovery pressure warrants it

### 8.2 Hive CLI and core

New or frozen surfaces:

- `hive integrate list`
- `hive integrate <pi|openclaw|hermes>`
- `hive integrate doctor <pi|openclaw|hermes> --json`
- `hive link serve`
- `hive attach <harness> <native-session-ref> ...`
- `hive detach <session-or-run-id>`

One-shot JSON CLI remains canonical for:
- `next`
- `search`
- `work`
- `finish`
- `status`
- `note`

### 8.3 Console

The console must show:
- native harness identity
- integration level
- governance mode
- session owner
- sandbox owner
- attach vs managed origin
- live normalized trajectory
- steering history
- native session handle
- raw/native artifact links where available

## 9. Release red lines

v2.4 must **not** ship if any of these are still true:

1. Pi/OpenClaw/Hermes are still described as one generic RPC family.
2. Users must leave their native harness to get first value from Hive.
3. Attach mode requires transcript copy/paste or manual artifact shuffling.
4. Advisory vs governed status is not obvious in the console and artifacts.
5. The integration package names, install commands, and onboarding flows are still vague.
6. OpenClaw requires a native plugin for the base experience.
7. A harness-private memory store is silently imported into Hive.
8. `trajectory.jsonl` is not standardized across all v2.4 adapters.
9. `hive integrate doctor` cannot explain what each integration can actually do on the current machine.

## 10. North-star success scenario

A Pi user, an OpenClaw user, and a Hermes user should each be able to do the following in under five minutes:

1. install the native Hive integration in the ecosystem they already use
2. connect it to an existing Hive workspace
3. ask for next work from inside that harness
4. attach a live session to Hive without relaunching it
5. see that session in the Hive console with truthful governance/sandbox labeling
6. steer it from Hive or from the native harness
7. finish or escalate it without losing native ergonomics

If that works, v2.4 is doing the right thing.

## 11. What success unlocks next

v2.4 is not just a packaging exercise. It creates the clean substrate for the later continual-learning line by standardizing:

- native harness identity
- integration level
- governance mode
- normalized trajectories
- attached-session artifacts
- steering deltas
- context manifests
- skill provenance
- final dispositions

That is the data quality upgrade the future backtesting and self-improvement system needs.

## 12. Summary of the winning design

- **Pi is a WorkerSession integration**
- **OpenClaw and Hermes are DelegateGateway integrations**
- **Companion-first beats launch-first for adoption**
- **Attach mode is mandatory**
- **Managed mode belongs with Pi first**
- **Hive Link is the session bridge**
- **MCP and ACP stay secondary**
- **Governance truth must be obvious everywhere**

That is the design that maximizes user utility, ecosystem reach, onboarding ease, and long-term product integrity.

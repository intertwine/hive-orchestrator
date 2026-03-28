# Agent Hive v2.4 Harness Packages and Onboarding

Status: Proposed  
Date: 2026-03-27

## 1. Purpose

This document turns the high-level v2.4 design into concrete package, install, and onboarding choices for Pi, OpenClaw, and Hermes.

The key principle is simple:

> **Meet users where they already are.**

That means native package channels first, attach mode second, deep managed mode only where it adds obvious value.

## 2. Shared product rules

These rules apply across all three ecosystems.

### 2.1 First value must be native

A user’s first successful interaction should happen **inside the harness they already use**, not in the Hive CLI.

### 2.2 One install story per ecosystem

The default story must be one obvious install path:
- npm for Pi
- ClawHub + npm bridge for OpenClaw
- pip + Hermes skill/toolset bundle for Hermes

### 2.3 Same action vocabulary, native wrappers

Every ecosystem should expose the same core intents:
- next work
- search Hive
- open/attach
- finish/escalate
- note/status

But the wrapper UX can be native:
- slash commands
- skills
- tool actions
- extension menus
- chat commands

### 2.4 Attach mode is not optional

Users must be able to attach **an already-running session** to Hive.

## 3. Pi plan

### 3.1 Package

Create:

```text
packages/pi-hive/
```

Publish as:

```text
@mellona/pi-hive
```

### 3.2 Why this is the right shape

Pi’s SDK already gives Hive the right primitives:
- `createAgentSession()`
- direct event subscription
- queued `steer()` / `followUp()`
- resource-loader support for skills/context/templates
- a fallback RPC path for headless attach or interop

This means Pi is the best candidate for a **true managed integration**, not just attach.

### 3.3 Deliverables

#### A. Native companion package
`@mellona/pi-hive` must provide:
- native commands or prompts for `hive_next`, `hive_search`, `hive_open`, `hive_attach`, `hive_finish`, `hive_note`, `hive_status`
- automatic workspace detection
- Hive Link connection helper
- resource-loader injection for Hive-projected context

#### B. Managed runner
Provide a small Node entrypoint that Hive’s Python core can launch:

```text
packages/pi-hive/bin/pi-hive-runner
```

This runner should:
- connect to Hive Link over stdio or websocket
- create an `AgentSession` through the Pi SDK
- mount Hive-selected context/resources
- stream normalized events
- accept steering from Hive
- write artifacts and close cleanly

#### C. Attach helper
Allow an already-running Pi session to bind to Hive without relaunch.

### 3.4 Modes in v2.4

| Mode | Required in v2.4 |
|---|---|
| Pack | yes |
| Companion | yes |
| Attach | yes |
| Managed | yes |

### 3.5 Pi onboarding flow

#### Recommended path
1. `npm install -g @mellona/pi-hive`
2. in Hive workspace: `hive integrate pi`
3. from Pi: run the native Hive action for “connect workspace”
4. ask Pi for next work or attach current session
5. watch the run appear in Hive console

#### Doctor expectations
`hive integrate doctor pi --json` must verify:
- Node/npm present
- Pi present or installable
- `@mellona/pi-hive` version
- attach support
- managed-runner support
- link handshake success

## 4. OpenClaw plan

### 4.1 Packages

Create:

```text
packages/openclaw-hive-bridge/
```

Publish as an npm package, plus a ClawHub skill:

- npm package: `openclaw-hive-bridge`
- ClawHub skill: `agent-hive`

### 4.2 Why this is the right shape

OpenClaw’s Gateway is the source of truth for sessions. The docs also make two important things very clear:
- the ACP bridge is a gateway-backed ACP bridge, not a full ACP-native runtime
- native plugins run in-process and are not sandboxed

So the right base design is:
- **Gateway bridge first**
- **ClawHub skill for discovery and native actions**
- **native plugin not required**

### 4.3 Deliverables

#### A. ClawHub skill
The `agent-hive` skill should expose:
- next work
- search Hive
- attach current session
- post steering note
- finish/escalate

It should also provide a guided “link this Gateway to Hive” action.

#### B. External bridge
`openclaw-hive-bridge` should:
- authenticate to the OpenClaw Gateway
- list sessions and delegates
- map `sessionKey` to Hive run/delegate session
- subscribe to session history / live transcript APIs
- normalize events into Hive Link
- publish steering or notes back to the gateway

#### C. Optional later onboarding plugin
A native plugin may later help with setup UX, but it must remain optional and thin.

### 4.4 Modes in v2.4

| Mode | Required in v2.4 |
|---|---|
| Pack | yes |
| Companion | yes |
| Attach | yes |
| Managed | no |

### 4.5 OpenClaw onboarding flow

#### Recommended path
1. install `agent-hive` skill from ClawHub
2. install or run `openclaw-hive-bridge`
3. `hive integrate openclaw`
4. connect the bridge to the local or remote Gateway
5. attach an existing `sessionKey` to Hive

#### Doctor expectations
`hive integrate doctor openclaw --json` must verify:
- bridge installed or reachable
- gateway endpoint reachable
- session list accessible
- attach supported
- steering path available
- whether the connection is local or remote

## 5. Hermes plan

### 5.1 Packaging

For v2.4.0, keep canonical implementation in the main Python package:

```text
src/hive/integrations/hermes/
```

and ship exportable Hermes-native assets under:

```text
packages/hermes-skill/
```

Do **not** require a separate `mellona-hermes` runtime package for v2.4.0.
A thin alias/meta-package can come later if discovery pressure justifies it.

### 5.2 Why this is the right shape

Hermes is already Python-based and already supports:
- skills
- toolsets
- AGENTS-based context
- MCP
- gateway/messaging
- cron
- trajectory export

The simplest path to adoption is:
- let Hermes keep being Hermes
- add Hive as a native skill/toolset and attach layer
- avoid a second mandatory Python packaging story on day one

### 5.3 Deliverables

#### A. Hermes skill/toolset bundle
Expose:
- next work
- search Hive
- attach current session or job
- finish/escalate
- note/status

Implementation should use the stable Hive JSON CLI and/or Hive Link, not private internal coupling.

#### B. Gateway/CLI attach
Allow:
- gateway sessions
- background jobs / cron jobs
- local CLI sessions
to attach into Hive as advisory sessions.

#### C. MCP recipe
Ship a documented optional MCP path for users who prefer that installation style, but do not make it the primary product surface.

#### D. Trajectory import fallback
If a Hermes session cannot stay live-attached, import Hermes trajectory export into Hive as a normalized `trajectory.jsonl` after the fact.

### 5.4 Modes in v2.4

| Mode | Required in v2.4 |
|---|---|
| Pack | yes |
| Companion | yes |
| Attach | yes |
| Managed | no |

### 5.5 Memory policy

Hermes has its own durable memory system and skill self-improvement loop.
Hive must not bulk-import that private memory by default.

Allowed imports:
- project-relevant summary snippets
- explicit operator-approved skills/procedures
- normalized trajectories and artifacts
- explicit notes that the user or skill marked as exportable

### 5.6 Hermes onboarding flow

#### Recommended path
1. install/update `mellona-hive` with Hermes integration support
2. `hive integrate hermes`
3. load the Agent Hive skill/toolset in Hermes
4. attach a current gateway session, CLI session, or cron job to Hive
5. supervise from the Hive console while continuing to work from Hermes

#### Doctor expectations
`hive integrate doctor hermes --json` must verify:
- Hermes installed
- skill/toolset files present
- AGENTS/context compatibility
- attach path available
- optional MCP recipe readiness
- optional trajectory-import fallback readiness

## 6. Cross-harness UX requirements

### 6.1 Minimal companion UX

Within each harness, the user must be able to do all of this without reading the Hive docs first:

- connect workspace
- ask for next work
- search Hive
- attach current session
- see whether the session is advisory or governed
- finish or escalate

### 6.2 Copy and naming

Use the same product phrasing everywhere:

- “Connect to Agent Hive”
- “Attach this session to Hive”
- “Advisory session” / “Governed run”
- “Search Hive”
- “Get next task”

### 6.3 No manual transcript copying

This is an explicit red line.

## 7. Repo layout and ownership

### 7.1 Python core
Suggested new areas:

```text
src/hive/integrations/
src/hive/link/
src/hive/trajectory/
```

### 7.2 Native packages

```text
packages/pi-hive/
packages/openclaw-hive-bridge/
packages/hermes-skill/
```

### 7.3 Docs
Add:
- native install guides
- compare-harness updates
- operator flows for attach mode
- FAQ entries about advisory vs governed

## 8. Publish and release expectations

### 8.1 v2.4 release assets

Must include:
- install docs
- companion package docs
- attach screenshots/gifs for console
- truthfulness table by harness
- one native “hello world” demo per harness

### 8.2 Metrics worth watching after release

- time to first successful attach
- attach success rate
- proportion of sessions started in companion mode vs managed mode
- steering usage rate
- finish/escalate rate per harness
- install friction by harness

## 9. What not to do

1. Do not start with a thick OpenClaw plugin.
2. Do not force Hermes users into a second packaging story on day one.
3. Do not make Pi managed mode depend on fragile terminal scraping.
4. Do not bypass Hive Link with one-off ad hoc socket formats.
5. Do not hide attach limitations; show them honestly.

## 10. Summary

The package strategy is:

- **Pi**: `@mellona/pi-hive` with full companion + attach + managed support
- **OpenClaw**: `agent-hive` ClawHub skill plus `openclaw-hive-bridge`
- **Hermes**: first-class built-in integration + Hermes skill/toolset + optional MCP recipe

That combination gives Hive first-class ecosystem presence without overcommitting to the wrong runtime model.

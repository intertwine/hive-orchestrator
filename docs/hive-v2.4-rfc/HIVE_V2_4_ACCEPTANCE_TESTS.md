# Agent Hive v2.4 Acceptance Tests

Status: Proposed  
Date: 2026-03-27

## 1. Purpose

These are the hard release gates for v2.4.

If a scenario below fails, the release is not done.

## 2. Cross-cutting release gates

### Gate 1 — Adapter model correction
**Pass when**
- Pi is implemented as `WorkerSessionAdapter`
- OpenClaw and Hermes are implemented as `DelegateGatewayAdapter`
- no product docs still describe all three as a single generic RPC family

### Gate 2 — Native first value
**Pass when**
- each harness has a native install story
- first successful “next work” can happen inside the native harness
- no harness requires users to start in raw Hive CLI for first value

### Gate 3 — Attach without relaunch
**Pass when**
- Pi, OpenClaw, and Hermes can all bind a live session to Hive without transcript copy/paste
- the attached session appears in the console within 3 seconds on a local network/host

### Gate 4 — Governance truth
**Pass when**
- console, JSON, and artifacts all show advisory vs governed
- sandbox owner is visible
- session owner / native handle is visible

### Gate 5 — Normalized trajectories
**Pass when**
- every attached/managed session emits `trajectory.jsonl`
- required event kinds exist
- raw/native refs are preserved when available

### Gate 6 — Companion action parity
**Pass when**
- each harness exposes actions for next/search/open-or-attach/finish/note/status
- naming is native, but intent coverage is complete

## 3. Pi scenarios

### Scenario PI-1 — install and connect
1. fresh machine with Node and Pi available
2. install `@mellona/pi-hive`
3. run `hive integrate pi`
4. connect package to workspace

**Pass when**
- doctor returns attach + managed support
- Pi can ask Hive for next work from inside Pi
- no manual config editing is required for the happy path

### Scenario PI-2 — attach current Pi session
1. start a Pi session outside Hive
2. attach it to a ready task
3. continue working

**Pass when**
- console shows the attached session
- governance mode is advisory
- steering note from Hive shows up in Pi
- `trajectory.jsonl` persists

### Scenario PI-3 — managed Pi run
1. select a ready task
2. launch managed Pi mode from Hive
3. observe work and finish

**Pass when**
- governance mode is governed
- worktree and runpack are owned by Hive
- steering works
- artifacts/diff/final disposition are persisted

## 4. OpenClaw scenarios

### Scenario OC-1 — install and connect
1. install `agent-hive` skill
2. install/run `openclaw-hive-bridge`
3. run `hive integrate openclaw`
4. point Hive at the Gateway

**Pass when**
- doctor can reach the gateway
- session listing works
- the skill can call Hive-native actions

### Scenario OC-2 — attach live Gateway session
1. open an OpenClaw conversation
2. attach the current `sessionKey` to Hive
3. continue chatting normally

**Pass when**
- the session appears in Hive as a delegate/advisory session
- live transcript updates stream into the console
- steering/note round-trips back to OpenClaw
- no native plugin is required

### Scenario OC-3 — truthfulness
**Pass when**
- console explicitly labels the session advisory
- the actual sandbox owner is shown as OpenClaw or external, not Hive
- capability doctor does not claim managed support

## 5. Hermes scenarios

### Scenario HE-1 — install and connect
1. install/update Hive with Hermes integration support
2. run `hive integrate hermes`
3. enable/load the Hive skill/toolset in Hermes

**Pass when**
- doctor finds Hermes
- skill/toolset actions work
- AGENTS-based context remains intact

### Scenario HE-2 — attach live Hermes session
1. start a Hermes CLI or gateway session
2. attach it to Hive
3. continue the native Hermes workflow

**Pass when**
- the session appears in Hive as advisory
- normalized trajectory is persisted
- steering note reaches Hermes
- finish/escalate path is available without leaving Hermes-native ergonomics

### Scenario HE-3 — trajectory import fallback
1. run a Hermes session without live attach
2. export its trajectory
3. import into Hive

**Pass when**
- the imported trajectory maps to Hive event kinds
- raw provenance is preserved
- the console can inspect it as a completed advisory session

### Scenario HE-4 — memory privacy
**Pass when**
- Hermes `MEMORY.md` / `USER.md` are not bulk-imported automatically
- only explicitly allowed project-relevant summaries or trajectories are imported

## 6. Console scenarios

### Scenario UI-1 — run/delegate detail truth
Open a Pi managed run, an OpenClaw attached session, and a Hermes attached session.

**Pass when**
each detail view shows:
- harness
- integration level
- governance mode
- native session handle
- capability snapshot
- steering history
- trajectory

### Scenario UI-2 — inbox / exceptions
**Pass when**
- attached advisory sessions can still raise escalations/notes into the inbox
- managed Pi runs appear alongside existing Codex/Claude runs without special-case UI confusion

## 7. Doctor scenarios

### Scenario DOC-1 — integrate doctor
Run:
- `hive integrate doctor pi --json`
- `hive integrate doctor openclaw --json`
- `hive integrate doctor hermes --json`

**Pass when**
all return:
- detected versions
- supported levels
- effective capabilities
- guidance on what is missing

## 8. Docs and install scenarios

### Scenario DOCS-1 — source and installed docs
**Pass when**
- the installed package can search and return the v2.4 RFC bundle
- Start Here and Compare Harnesses include Pi/OpenClaw/Hermes paths
- operator docs explain advisory vs governed

### Scenario DOCS-2 — 5-minute onboarding
Have a new user follow each harness guide.

**Pass when**
- average happy-path setup is under 5 minutes
- no hidden manual config steps are required
- failure modes are diagnosable with `hive integrate doctor`

## 9. Release red-line checklist

v2.4 must not be tagged if any checkbox is false:

- [ ] adapter split is real in code and docs
- [ ] Hive Link is real in code and tests
- [ ] Pi companion + attach + managed are real
- [ ] OpenClaw companion + attach are real
- [ ] Hermes companion + attach are real
- [ ] advisory vs governed truth is visible everywhere
- [ ] `trajectory.jsonl` exists and is normalized
- [ ] onboarding docs and doctors are aligned

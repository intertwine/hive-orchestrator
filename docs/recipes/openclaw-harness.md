# OpenClaw Harness Guide

Use OpenClaw when you want to keep chatting in a live Gateway session and let Hive supervise it as an advisory delegate.

## Five-minute path

Install Hive and the bridge, then add the `agent-hive` skill from ClawHub:

```bash
uv tool install 'mellona-hive[console]'
npm install -g openclaw-hive-bridge
```

Verify the bridge and gateway path:

```bash
hive integrate doctor openclaw --json
hive integrate openclaw
```

Then attach the live session:

```bash
hive integrate attach openclaw <session-key>
```

In practice, most users will trigger that through the `agent-hive` skill action rather than typing it directly.

## Truth

- OpenClaw is attach-only in v2.4
- governance is always advisory
- the sandbox owner is OpenClaw or external, not Hive
- the supported path is gateway bridge plus skill, not a required in-process plugin

## If something fails

Run:

```bash
hive integrate doctor openclaw --json
```

That will tell you whether the bridge is installed, the gateway is reachable, session listing works, and steering is available.

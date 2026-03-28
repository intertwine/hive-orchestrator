# openclaw-hive-bridge

Bridge between an OpenClaw Gateway and Agent Hive for session attach, event streaming, and steering.

## Install

```bash
npm install -g openclaw-hive-bridge
```

## Usage

### Local stdio mode (recommended for `hive integrate openclaw`)

```bash
openclaw-hive-bridge --gateway http://localhost:3000 --stdio
```

### HTTP mode (for remote bridge access)

```bash
openclaw-hive-bridge --gateway http://localhost:3000 --http 8800
```

## What it does

1. Connects to the OpenClaw Gateway API
2. Lists active sessions and delegates
3. Maps Gateway `sessionKey` to Hive delegate session IDs
4. Subscribes to session history and live transcript streams
5. Normalizes events into the Hive Link NDJSON protocol
6. Forwards steering and notes from Hive back to the Gateway

## Hive integration

After installing the bridge, connect it to Hive:

```bash
hive integrate openclaw
```

Then attach a live Gateway session:

```bash
hive integrate attach openclaw <session-key>
```

## Environment variables

| Variable | Description |
|---|---|
| `OPENCLAW_GATEWAY_URL` | Default Gateway URL when `--gateway` is omitted |

## Status

This is a v2.4 scaffold. The bridge protocol is stable; Gateway API integration is in progress.

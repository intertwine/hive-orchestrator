# Running YOLO Loops Unattended (Local or Cloud)

This guide shows how to run Agent Hive YOLO loops without GitHub Actions. It targets three scenarios:

1. **Local workstation** (background process with logs + heartbeat)
2. **Cloud sandbox** (long-lived VM or container)
3. **Systemd service** (production-ish supervision)

## 1) Local machine (background process)

Use the helper scripts in `scripts/` for a simple supervised run. These scripts write:

- **PID file**: used for stop/restart
- **Log file**: append-only log output
- **Heartbeat JSON**: updated after every loop cycle

```bash
export HIVE_BASE_PATH=/path/to/hive-orchestrator
export YOLO_STYLE=loom
export SLEEP_SECONDS=30
export MAX_DISPATCHES=1
export AGENT_NAME=claude-sonnet-4
export AGENT_MENTION=@claude
export EXTRA_LABELS="model:claude-sonnet-4,integration:mcp"

scripts/run_yolo_loop.sh
```

To stop:

```bash
export HIVE_BASE_PATH=/path/to/hive-orchestrator
scripts/stop_yolo_loop.sh
```

## 2) Cloud sandbox (VM/container)

Any long-lived VM or container can run the loop. The two things you need are:

- An OpenRouter API key (for Cortex)
- GitHub CLI auth if you want issue creation

Example (container entrypoint):

```bash
uv run python -m src.agent_dispatcher \
  --path /app \
  --yolo-loop \
  --yolo-style loom \
  --loop-sleep 30 \
  --loop-heartbeat /app/yolo-loop-heartbeat.json
```

You can pair that with your platform’s health checks by watching the heartbeat file.

## 3) Systemd service (Linux)

Below is a minimal unit file. Adjust paths for your environment.

```ini
# /etc/systemd/system/agent-hive-yolo.service
[Unit]
Description=Agent Hive YOLO Loop
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/hive-orchestrator
Environment=OPENROUTER_API_KEY=...your key...
ExecStart=/usr/bin/env bash -lc \
  "uv run python -m src.agent_dispatcher \
    --path /opt/hive-orchestrator \
    --yolo-loop \
    --yolo-style loom \
    --loop-sleep 30 \
    --loop-heartbeat /opt/hive-orchestrator/yolo-loop-heartbeat.json"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable agent-hive-yolo
sudo systemctl start agent-hive-yolo
```

## Operational notes

- **Heartbeat JSON** is updated after each loop cycle. Use it for watchdogs.
- **Logs** are your primary audit trail. Pipe them to your log stack if needed.
- **Backoff** is handled by the `loom` style; use `ralph-wiggum` only when you want aggressive polling.

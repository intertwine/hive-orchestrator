#!/usr/bin/env bash
set -euo pipefail

HIVE_BASE_PATH=${HIVE_BASE_PATH:-"$(pwd)"}
LOG_PATH=${LOG_PATH:-"$HIVE_BASE_PATH/yolo-loop.log"}
PID_PATH=${PID_PATH:-"$HIVE_BASE_PATH/yolo-loop.pid"}
HEARTBEAT_PATH=${HEARTBEAT_PATH:-"$HIVE_BASE_PATH/yolo-loop-heartbeat.json"}
YOLO_STYLE=${YOLO_STYLE:-"loom"}
SLEEP_SECONDS=${SLEEP_SECONDS:-"30"}
MAX_DISPATCHES=${MAX_DISPATCHES:-"1"}
AGENT_NAME=${AGENT_NAME:-"claude-code"}
AGENT_MENTION=${AGENT_MENTION:-"@claude"}
EXTRA_LABELS=${EXTRA_LABELS:-""}

if [[ -f "$PID_PATH" ]]; then
  echo "PID file exists at $PID_PATH. Stop the existing loop before starting a new one."
  exit 1
fi

cmd=(
  uv run python -m src.agent_dispatcher
  --path "$HIVE_BASE_PATH"
  --yolo-loop
  --yolo-style "$YOLO_STYLE"
  --loop-sleep "$SLEEP_SECONDS"
  --loop-heartbeat "$HEARTBEAT_PATH"
  --max "$MAX_DISPATCHES"
  --agent-name "$AGENT_NAME"
)

if [[ -n "$AGENT_MENTION" ]]; then
  cmd+=(--agent-mention "$AGENT_MENTION")
else
  cmd+=(--agent-mention none)
fi

IFS=',' read -r -a labels <<< "$EXTRA_LABELS"
for label in "${labels[@]}"; do
  trimmed=$(echo "$label" | xargs)
  if [[ -n "$trimmed" ]]; then
    cmd+=(--extra-label "$trimmed")
  fi
done

echo "Starting YOLO loop..."
nohup "${cmd[@]}" >> "$LOG_PATH" 2>&1 &
loop_pid=$!

echo "$loop_pid" > "$PID_PATH"
echo "Started. PID: $loop_pid"
echo "Logs: $LOG_PATH"
echo "Heartbeat: $HEARTBEAT_PATH"

#!/usr/bin/env bash
set -euo pipefail

HIVE_BASE_PATH=${HIVE_BASE_PATH:-"$(pwd)"}
PID_PATH=${PID_PATH:-"$HIVE_BASE_PATH/yolo-loop.pid"}

if [[ ! -f "$PID_PATH" ]]; then
  echo "No PID file found at $PID_PATH"
  exit 0
fi

loop_pid=$(cat "$PID_PATH")
if [[ -z "$loop_pid" ]]; then
  echo "PID file is empty."
  exit 1
fi

if kill "$loop_pid" >/dev/null 2>&1; then
  echo "Stopped YOLO loop process $loop_pid"
else
  echo "Failed to stop process $loop_pid (may not be running)"
fi

rm -f "$PID_PATH"

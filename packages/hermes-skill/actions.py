#!/usr/bin/env python3
"""Hermes agent-hive skill — action implementations.

Each action wraps a stable ``hive`` CLI command. The skill manifest
(manifest.json) declares the intents; this module executes them.

Usage from Hermes runtime::

    from actions import execute_action
    result = execute_action("hive_next", {"project_id": "demo"})

Or as a CLI::

    python actions.py hive_next '{"project_id": "demo"}'
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any


def _run_hive(args: list[str]) -> dict[str, Any]:
    """Run a hive CLI command and return parsed JSON or raw output."""
    try:
        result = subprocess.run(
            ["hive", *args],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, OSError) as exc:
        return {"ok": False, "error": str(exc)}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }


def _sync_hermes_session(session_id: str) -> dict[str, Any]:
    """Sync an attached Hermes session transcript into Hive."""
    return _run_hive(["--json", "integrate", "sync", "hermes", session_id])


def _poll_hermes_actions(session_id: str, since_seq: int = -1) -> dict[str, Any]:
    """Poll pending Hive actions for an attached Hermes session."""
    return _run_hive(
        [
            "--json",
            "integrate",
            "poll-actions",
            "hermes",
            session_id,
            "--since-seq",
            str(since_seq),
        ]
    )


def hive_next(params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Ask Hive for the next recommended task."""
    args = ["--json", "next"]
    if params and params.get("project_id"):
        args.extend(["--project-id", params["project_id"]])
    return _run_hive(args)


def hive_search(params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Search Hive workspace."""
    if not params or not params.get("query"):
        return {"ok": False, "error": "query is required"}
    return _run_hive(["--json", "search", params["query"]])


def hive_attach(params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Attach the current Hermes session to Hive."""
    if not params or not params.get("session_id"):
        return {"ok": False, "error": "session_id is required"}
    args = ["--json", "integrate", "attach", "hermes", params["session_id"]]
    if params.get("project_id"):
        args.extend(["--project-id", params["project_id"]])
    if params.get("task_id"):
        args.extend(["--task-id", params["task_id"]])
    attached = _run_hive(args)
    if not attached.get("ok"):
        return attached
    return {
        **attached,
        "sync": _sync_hermes_session(params["session_id"]),
        "pending_actions": _poll_hermes_actions(params["session_id"]),
    }


def hive_finish(params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Finish or escalate the current task."""
    if not params or not params.get("run_id"):
        return {"ok": False, "error": "run_id is required"}
    return _run_hive(["--json", "finish", params["run_id"]])


def hive_note(params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Post a steering note."""
    if not params or not params.get("run_id") or not params.get("note"):
        return {"ok": False, "error": "run_id and note are required"}
    return _run_hive(
        ["--json", "steer", "note", params["run_id"], "--message", params["note"]]
    )


def hive_status(params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Show Hive workspace or run status."""
    if params and params.get("run_id"):
        return _run_hive(["--json", "console", "run", params["run_id"]])
    payload = _run_hive(["--json", "console", "home"])
    if params and params.get("session_id"):
        since_seq = int(params.get("since_seq", -1))
        payload["attached_session"] = {
            "sync": _sync_hermes_session(params["session_id"]),
            "pending_actions": _poll_hermes_actions(
                params["session_id"], since_seq=since_seq
            ),
        }
    return payload


ACTIONS: dict[str, Any] = {
    "hive_next": hive_next,
    "hive_search": hive_search,
    "hive_attach": hive_attach,
    "hive_finish": hive_finish,
    "hive_note": hive_note,
    "hive_status": hive_status,
}


def execute_action(intent: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a skill action by intent name."""
    handler = ACTIONS.get(intent)
    if handler is None:
        return {"ok": False, "error": f"Unknown intent: {intent}"}
    return handler(params)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {"ok": False, "error": "Usage: actions.py <intent> [json-params]"}
            )
        )
        sys.exit(2)
    intent_arg = sys.argv[1]
    params_arg: dict[str, Any] = {}
    if len(sys.argv) > 2:
        try:
            params_arg = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "Invalid JSON params"}))
            sys.exit(2)
    print(json.dumps(execute_action(intent_arg, params_arg)))

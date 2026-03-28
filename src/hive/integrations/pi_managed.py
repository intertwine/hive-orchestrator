"""Managed-runner helpers for the Pi worker integration."""

from __future__ import annotations

from pathlib import Path

from src.hive.drivers.types import RunLaunchRequest


def build_pi_runner_command(
    request: RunLaunchRequest,
    *,
    node_path: str,
    runner_path: str | Path,
    state_path: str | Path,
    steering_path: str | Path,
    trajectory_path: str | Path,
    last_message_path: str | Path,
    native_session_ref: str,
) -> list[str]:
    """Return the managed Pi runner command for a prepared Hive run."""
    return [
        node_path,
        str(Path(runner_path)),
        "--run-id",
        request.run_id,
        "--task-id",
        request.task_id,
        "--project-id",
        request.project_id,
        "--worktree",
        request.workspace.worktree_path,
        "--artifacts",
        request.artifacts_path,
        "--context",
        request.compiled_context_path,
        "--state",
        str(Path(state_path)),
        "--steering",
        str(Path(steering_path)),
        "--trajectory",
        str(Path(trajectory_path)),
        "--last-message",
        str(Path(last_message_path)),
        "--native-session-ref",
        native_session_ref,
    ]


__all__ = ["build_pi_runner_command"]

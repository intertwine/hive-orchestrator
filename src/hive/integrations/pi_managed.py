"""Managed-runner helpers for the Pi worker integration."""

from __future__ import annotations

from pathlib import Path

from src.hive.drivers.types import RunLaunchRequest


def build_pi_runner_command(
    request: RunLaunchRequest,
    *,
    node_path: str,
    runner_path: str | Path,
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
    ]


__all__ = ["build_pi_runner_command"]

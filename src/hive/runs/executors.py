"""Executor interfaces for Hive runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from src.hive.clock import utc_now_iso


@dataclass
class CommandResult:
    """Structured executor result."""

    command: str
    started_at: str
    finished_at: str
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False


class LocalExecutor:
    """Run commands locally inside the run worktree."""

    name = "local"

    def run_command(self, command: str, *, cwd: Path, timeout_seconds: int) -> CommandResult:
        started_at = utc_now_iso()
        try:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
            return CommandResult(
                command=command,
                started_at=started_at,
                finished_at=utc_now_iso(),
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = (
                exc.stdout.decode("utf-8", errors="replace")
                if isinstance(exc.stdout, bytes)
                else exc.stdout or ""
            )
            stderr = (
                exc.stderr.decode("utf-8", errors="replace")
                if isinstance(exc.stderr, bytes)
                else exc.stderr or ""
            )
            return CommandResult(
                command=command,
                started_at=started_at,
                finished_at=utc_now_iso(),
                returncode=None,
                stdout=stdout,
                stderr=stderr,
                timed_out=True,
            )


class GitHubActionsExecutor:
    """Placeholder executor surface for future remote execution."""

    name = "github-actions"

    def run_command(self, command: str, *, cwd: Path, timeout_seconds: int) -> CommandResult:
        del command, cwd, timeout_seconds
        raise NotImplementedError("The github-actions executor is a stub in this MVP")


def get_executor(name: str):
    """Return a named executor implementation."""
    normalized = name.strip().lower()
    if normalized == "local":
        return LocalExecutor()
    if normalized == "github-actions":
        return GitHubActionsExecutor()
    raise ValueError(f"Unsupported executor: {name}")


__all__ = ["CommandResult", "GitHubActionsExecutor", "LocalExecutor", "get_executor"]

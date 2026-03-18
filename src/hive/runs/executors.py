"""Executor interfaces for Hive runs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Protocol

from src.hive.clock import utc_now_iso
from src.hive.runtime.runpack import SandboxPolicy
from src.hive.sandbox import sandboxed_command


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


class Executor(Protocol):
    """Common executor surface for local and remote run backends."""

    def run_command(self, command: str, *, cwd: Path, timeout_seconds: int) -> CommandResult:
        """Execute a shell command within a run workspace."""


class LocalExecutor:
    """Run commands locally inside the run worktree."""

    name = "local"

    def __init__(self, sandbox_policy: SandboxPolicy | None = None):
        self.sandbox_policy = sandbox_policy

    def run_command(self, command: str, *, cwd: Path, timeout_seconds: int) -> CommandResult:
        started_at = utc_now_iso()
        try:
            argv, use_shell = self._command_payload(command, cwd=cwd)
            completed = subprocess.run(
                argv,
                shell=use_shell,
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
        except (NotImplementedError, OSError, ValueError) as exc:
            return CommandResult(
                command=command,
                started_at=started_at,
                finished_at=utc_now_iso(),
                returncode=1,
                stdout="",
                stderr=str(exc),
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

    def _command_payload(self, command: str, *, cwd: Path) -> tuple[list[str] | str, bool]:
        if self.sandbox_policy is None:
            return command, True
        return sandboxed_command(self.sandbox_policy, command=command, cwd=cwd)


class GitHubActionsExecutor:
    """Placeholder executor surface for future remote execution."""

    name = "github-actions"

    def run_command(self, command: str, *, cwd: Path, timeout_seconds: int) -> CommandResult:
        del command, cwd, timeout_seconds
        raise NotImplementedError("The github-actions executor is a stub in this MVP")


def _load_sandbox_policy(
    policy: SandboxPolicy | dict | str | Path | None,
) -> SandboxPolicy | None:
    if policy is None:
        return None
    if isinstance(policy, SandboxPolicy):
        return policy
    if isinstance(policy, (str, Path)):
        payload = json.loads(Path(policy).read_text(encoding="utf-8"))
        return SandboxPolicy(**payload)
    if isinstance(policy, dict):
        return SandboxPolicy(**policy)
    return None


def get_executor(
    name: str,
    *,
    sandbox_policy: SandboxPolicy | dict | str | Path | None = None,
) -> Executor:
    """Return a named executor implementation."""
    normalized = name.strip().lower()
    if normalized == "local":
        return LocalExecutor(_load_sandbox_policy(sandbox_policy))
    if normalized == "github-actions":
        return GitHubActionsExecutor()
    raise ValueError(f"Unsupported executor: {name}")


__all__ = ["CommandResult", "Executor", "GitHubActionsExecutor", "LocalExecutor", "get_executor"]

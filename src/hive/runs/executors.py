"""Executor interfaces for Hive runs."""

from __future__ import annotations

from dataclasses import dataclass
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
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
    sandbox: dict[str, object] | None = None


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
        if self.sandbox_policy is not None and self.sandbox_policy.backend == "e2b":
            return _run_e2b_command(
                self.sandbox_policy,
                command=command,
                cwd=cwd,
                timeout_seconds=timeout_seconds,
                started_at=started_at,
            )
        try:
            argv, use_shell = self._command_payload(command, cwd=cwd)
            sandbox = self._sandbox_metadata(command, argv=argv, use_shell=use_shell, cwd=cwd)
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
                sandbox=sandbox,
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
                sandbox=self._sandbox_metadata(command, cwd=cwd),
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
                sandbox=self._sandbox_metadata(command, argv=argv, use_shell=use_shell, cwd=cwd),
            )

    def _command_payload(self, command: str, *, cwd: Path) -> tuple[list[str] | str, bool]:
        if self.sandbox_policy is None:
            return command, True
        return sandboxed_command(self.sandbox_policy, command=command, cwd=cwd)

    def _sandbox_metadata(
        self,
        command: str,
        *,
        argv: list[str] | str | None = None,
        use_shell: bool | None = None,
        cwd: Path | None = None,
    ) -> dict[str, object] | None:
        if self.sandbox_policy is None:
            return None
        command_payload: list[str] | str | None = None
        if isinstance(argv, list):
            command_payload = list(argv)
        elif isinstance(argv, str):
            command_payload = argv
        return {
            "backend": self.sandbox_policy.backend,
            "profile": self.sandbox_policy.profile,
            "provenance": self.sandbox_policy.provenance,
            "network_mode": self.sandbox_policy.network.get("mode"),
            "network_allowlist": list(self.sandbox_policy.network.get("allowlist") or []),
            "command": command,
            "command_payload": command_payload,
            "shell": use_shell,
            "cwd": str(cwd) if cwd else None,
        }


_E2B_REMOTE_WORKTREE = "/workspace"
_E2B_REMOTE_ARTIFACTS = "/artifacts"
_E2B_REMOTE_ARCHIVE = "/tmp/hive-mounts.tar.gz"
_E2B_DENY_ALL = "0.0.0.0/0"


def _e2b_mount_roots(policy: SandboxPolicy, cwd: Path) -> tuple[Path, Path]:
    mounts = list(policy.mounts.get("read_write") or [])
    host_worktree = Path(str(mounts[0] if mounts else cwd)).resolve()
    host_artifacts = Path(str(mounts[1] if len(mounts) > 1 else cwd)).resolve()
    return host_worktree, host_artifacts


def _archive_mounts(host_worktree: Path, host_artifacts: Path) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        archive.add(host_worktree, arcname="workspace")
        if host_artifacts != host_worktree:
            archive.add(host_artifacts, arcname="artifacts")
    return buffer.getvalue()


def _load_e2b_sdk():
    """Import the optional E2B SDK only when the hosted executor is selected."""
    try:
        from e2b import Sandbox  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised through monkeypatching
        raise ImportError(
            "E2B SDK is not installed. Install `mellona-hive[sandbox-e2b]` "
            "or `pip install e2b` to use the hosted-managed executor."
        ) from exc
    return Sandbox


def _e2b_env(policy: SandboxPolicy) -> dict[str, str]:
    env: dict[str, str] = {}
    if bool(policy.env.get("inherit")):
        return dict(os.environ)
    allowed_names = list(policy.env.get("allowlist") or []) + list(
        policy.env.get("passthrough") or []
    )
    for env_name in allowed_names:
        value = os.environ.get(str(env_name))
        if value is not None:
            env[str(env_name)] = value
    return env


def _stringify_output(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _coerce_remote_returncode(result: object) -> int:
    for key in ("exit_code", "returncode"):
        value = getattr(result, key, None)
        if value is None and isinstance(result, dict):
            value = result.get(key)
        if value is not None:
            return int(value)
    return 0


def _run_e2b_command(
    policy: SandboxPolicy,
    *,
    command: str,
    cwd: Path,
    timeout_seconds: int,
    started_at: str,
) -> CommandResult:
    """Run one evaluator-style command inside an ephemeral E2B sandbox."""
    started = started_at
    host_worktree, host_artifacts = _e2b_mount_roots(policy, cwd)
    allowlist = [
        str(item) for item in list(policy.network.get("allowlist") or []) if str(item).strip()
    ]
    if allowlist:
        return CommandResult(
            command=command,
            started_at=started,
            finished_at=utc_now_iso(),
            returncode=1,
            stdout="",
            stderr=(
                "E2B hosted-managed execution currently supports deny-all or inherited network "
                "policies only; allowlists are not wired yet."
            ),
            timed_out=False,
            sandbox={
                "backend": policy.backend,
                "profile": policy.profile,
                "provenance": policy.provenance,
                "network_mode": policy.network.get("mode"),
                "network_allowlist": allowlist,
                "command": command,
                "command_payload": {"transport": "e2b-sdk"},
                "shell": False,
                "cwd": str(cwd),
                "workspace_sync": "upload_only",
            },
        )
    try:
        relative_cwd = cwd.resolve().relative_to(host_worktree)
    except ValueError:
        relative_cwd = Path(".")
    remote_cwd = str((Path(_E2B_REMOTE_WORKTREE) / relative_cwd).as_posix())
    sandbox_metadata: dict[str, object] = {
        "backend": policy.backend,
        "profile": policy.profile,
        "provenance": policy.provenance,
        "network_mode": policy.network.get("mode"),
        "network_allowlist": allowlist,
        "command": command,
        "command_payload": {
            "transport": "e2b-sdk",
            "remote_cwd": remote_cwd,
        },
        "shell": False,
        "cwd": str(cwd),
        "workspace_sync": "upload_only",
        "remote_worktree": _E2B_REMOTE_WORKTREE,
        "remote_artifacts": _E2B_REMOTE_ARTIFACTS,
    }
    sandbox = None
    try:
        if any(
            policy.resources.get(key) is not None for key in ("cpu", "memory_mb", "disk_mb")
        ):
            raise NotImplementedError(
                "E2B hosted-managed execution does not yet project explicit CPU, "
                "memory, or disk limits."
            )
        if list(policy.mounts.get("read_only") or []):
            raise NotImplementedError(
                "E2B hosted-managed execution does not yet project extra read-only mounts."
            )
        sandbox_class = _load_e2b_sdk()
        create_kwargs = {
            "timeout": max(int(timeout_seconds) + 60, 300),
            "metadata": {
                "hive_backend": policy.backend,
                "hive_profile": policy.profile,
                "hive_cwd": str(cwd),
            },
            "allow_internet_access": policy.network.get("mode") != "deny",
        }
        sandbox = sandbox_class.create(**create_kwargs)
        sandbox_metadata["remote_sandbox_id"] = getattr(sandbox, "sandbox_id", None)
        archive_bytes = _archive_mounts(host_worktree, host_artifacts)
        sandbox.files.make_dir(_E2B_REMOTE_WORKTREE)
        sandbox.files.make_dir(_E2B_REMOTE_ARTIFACTS)
        sandbox.files.write(_E2B_REMOTE_ARCHIVE, archive_bytes)
        sandbox.commands.run(
            (
                f"mkdir -p {_E2B_REMOTE_WORKTREE} {_E2B_REMOTE_ARTIFACTS} && "
                f"tar -xzf {_E2B_REMOTE_ARCHIVE} -C / && rm -f {_E2B_REMOTE_ARCHIVE}"
            ),
            cwd="/",
            timeout=max(timeout_seconds, 60),
        )
        result = sandbox.commands.run(
            command,
            cwd=remote_cwd,
            envs=_e2b_env(policy) or None,
            timeout=timeout_seconds,
        )
        return CommandResult(
            command=command,
            started_at=started,
            finished_at=utc_now_iso(),
            returncode=_coerce_remote_returncode(result),
            stdout=_stringify_output(getattr(result, "stdout", "")),
            stderr=_stringify_output(getattr(result, "stderr", "")),
            timed_out=False,
            sandbox=sandbox_metadata,
        )
    except Exception as exc:  # pylint: disable=broad-except
        if exc.__class__.__name__ == "TimeoutException":
            return CommandResult(
                command=command,
                started_at=started,
                finished_at=utc_now_iso(),
                returncode=None,
                stdout=_stringify_output(getattr(exc, "stdout", "")),
                stderr=_stringify_output(getattr(exc, "stderr", str(exc))),
                timed_out=True,
                sandbox=sandbox_metadata,
            )
        if exc.__class__.__name__ == "CommandExitException" or getattr(
            exc, "exit_code", None
        ) is not None:
            return CommandResult(
                command=command,
                started_at=started,
                finished_at=utc_now_iso(),
                returncode=int(getattr(exc, "exit_code", 1) or 1),
                stdout=_stringify_output(getattr(exc, "stdout", "")),
                stderr=_stringify_output(getattr(exc, "stderr", str(exc))),
                timed_out=False,
                sandbox=sandbox_metadata,
            )
        return CommandResult(
            command=command,
            started_at=started,
            finished_at=utc_now_iso(),
            returncode=1,
            stdout="",
            stderr=str(exc),
            timed_out=False,
            sandbox=sandbox_metadata,
        )
    finally:
        if sandbox is not None:
            try:
                sandbox.kill()
            except Exception:  # pragma: no cover - defensive cleanup
                pass


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

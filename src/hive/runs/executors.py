"""Executor interfaces for Hive runs."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import io
import json
import os
from pathlib import Path
import shlex
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
        try:
            if self.sandbox_policy is not None and self.sandbox_policy.backend == "e2b":
                return _run_e2b_command(
                    self.sandbox_policy,
                    command=command,
                    cwd=cwd,
                    timeout_seconds=timeout_seconds,
                    started_at=started_at,
                )
            if self.sandbox_policy is not None and self.sandbox_policy.backend == "daytona":
                return _run_daytona_command(
                    self.sandbox_policy,
                    command=command,
                    cwd=cwd,
                    timeout_seconds=timeout_seconds,
                    started_at=started_at,
                )
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


_REMOTE_WORKTREE = "/workspace"
_REMOTE_ARTIFACTS = "/artifacts"
_REMOTE_ARCHIVE = "/tmp/hive-mounts.tar.gz"
_DAYTONA_SESSION_ID = "hive-exec"


def _policy_mount_roots(policy: SandboxPolicy, cwd: Path) -> tuple[Path, Path]:
    mounts = list(policy.mounts.get("read_write") or [])
    if len(mounts) < 2:
        raise ValueError(
            "Remote sandbox execution requires read_write mounts for both the worktree "
            "and artifacts directories."
        )
    host_worktree = Path(str(mounts[0])).resolve()
    host_artifacts = Path(str(mounts[1])).resolve()
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


def _load_daytona_sdk():
    """Import the optional Daytona SDK only when the self-hosted executor is selected."""
    try:
        from daytona import (  # type: ignore[import-not-found]
            CreateSandboxFromImageParams,
            CreateSandboxFromSnapshotParams,
            Daytona,
            DaytonaConfig,
            Resources,
            SessionExecuteRequest,
        )
    except ImportError as exc:  # pragma: no cover - exercised through monkeypatching
        raise ImportError(
            "Daytona SDK is not installed. Install `mellona-hive[sandbox-daytona]` "
            "or `pip install daytona` to use the team-self-hosted executor."
        ) from exc
    return (
        Daytona,
        DaytonaConfig,
        CreateSandboxFromImageParams,
        CreateSandboxFromSnapshotParams,
        Resources,
        SessionExecuteRequest,
    )


def _filtered_env(policy: SandboxPolicy) -> dict[str, str]:
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
            try:
                return int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Remote executor returned a non-integer {key}: {value!r}"
                ) from exc
    raise ValueError(
        "Remote executor result did not expose an exit_code/returncode; refusing to assume success."
    )


def _e2b_allow_internet_access(policy: SandboxPolicy) -> bool:
    mode = str(policy.network.get("mode") or "").strip().lower()
    if mode == "deny":
        return False
    if mode == "inherit":
        return True
    raise ValueError(
        "E2B hosted-managed execution only supports network modes 'deny' and 'inherit'; "
        f"got {mode or '<unset>'!r}."
    )


def _is_e2b_timeout_exception(exc: Exception) -> bool:
    if not exc.__class__.__module__.startswith("e2b"):
        return False
    return exc.__class__.__name__ == "TimeoutException" or isinstance(exc, TimeoutError)


def _is_e2b_command_exit_exception(exc: Exception) -> bool:
    if not exc.__class__.__module__.startswith("e2b"):
        return False
    exit_code = getattr(exc, "exit_code", None)
    if exit_code is not None:
        return True
    return exc.__class__.__name__ == "CommandExitException"


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
    allowlist = [
        str(item) for item in list(policy.network.get("allowlist") or []) if str(item).strip()
    ]
    sandbox_metadata: dict[str, object] = {
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
        "remote_worktree": _REMOTE_WORKTREE,
        "remote_artifacts": _REMOTE_ARTIFACTS,
    }
    try:
        host_worktree, host_artifacts = _policy_mount_roots(policy, cwd)
    except ValueError:
        return CommandResult(
            command=command,
            started_at=started,
            finished_at=utc_now_iso(),
            returncode=1,
            stdout="",
            stderr=(
                "Remote sandbox execution requires read_write mounts for both the worktree and "
                "artifacts directories."
            ),
            timed_out=False,
            sandbox=sandbox_metadata,
        )
    if allowlist:
        return CommandResult(
            command=command,
            started_at=started,
            finished_at=utc_now_iso(),
            returncode=1,
            stdout="",
            stderr=(
                "E2B hosted-managed execution currently supports deny-all or inherited "
                "network policies only; allowlists are not wired yet."
            ),
            timed_out=False,
            sandbox=sandbox_metadata,
        )
    try:
        relative_cwd = cwd.resolve().relative_to(host_worktree)
    except ValueError as exc:
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
    remote_cwd = str((Path(_REMOTE_WORKTREE) / relative_cwd).as_posix())
    sandbox_metadata["command_payload"] = {"transport": "e2b-sdk", "remote_cwd": remote_cwd}
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
            "allow_internet_access": _e2b_allow_internet_access(policy),
        }
        sandbox = sandbox_class.create(**create_kwargs)
        sandbox_metadata["remote_sandbox_id"] = getattr(sandbox, "sandbox_id", None)
        archive_bytes = _archive_mounts(host_worktree, host_artifacts)
        sandbox.files.make_dir(_REMOTE_WORKTREE)
        sandbox.files.make_dir(_REMOTE_ARTIFACTS)
        sandbox.files.write(_REMOTE_ARCHIVE, archive_bytes)
        sandbox.commands.run(
            (
                f"mkdir -p {_REMOTE_WORKTREE} {_REMOTE_ARTIFACTS} && "
                f"tar -xzf {_REMOTE_ARCHIVE} -C / && rm -f {_REMOTE_ARCHIVE}"
            ),
            cwd="/",
            timeout=max(timeout_seconds, 60),
        )
        result = sandbox.commands.run(
            command,
            cwd=remote_cwd,
            envs=_filtered_env(policy) or None,
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
        if _is_e2b_timeout_exception(exc):
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
        if _is_e2b_command_exit_exception(exc):
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


def _daytona_config_kwargs() -> dict[str, str]:
    config: dict[str, str] = {}
    for env_name, field_name in (
        ("DAYTONA_API_KEY", "api_key"),
        ("DAYTONA_API_URL", "api_url"),
        ("DAYTONA_TARGET", "target"),
        ("DAYTONA_JWT_TOKEN", "jwt_token"),
        ("DAYTONA_ORGANIZATION_ID", "organization_id"),
    ):
        value = os.environ.get(env_name)
        if value:
            config[field_name] = value
    return config


def _daytona_resources(policy: SandboxPolicy, resources_class):
    if all(policy.resources.get(key) is None for key in ("cpu", "memory_mb", "disk_mb")):
        return None
    return resources_class(
        cpu=policy.resources.get("cpu"),
        memory=policy.resources.get("memory_mb"),
        disk=policy.resources.get("disk_mb"),
    )


def _validated_daytona_allowlist(policy: SandboxPolicy) -> list[str]:
    allowlist = [
        str(item).strip() for item in list(policy.network.get("allowlist") or []) if str(item).strip()
    ]
    if not allowlist:
        return []
    if len(allowlist) > 10:
        raise NotImplementedError(
            "Daytona team-self-hosted execution supports up to 10 CIDR network allowlist entries."
        )
    invalid: list[str] = []
    for entry in allowlist:
        if "/" not in entry:
            invalid.append(entry)
            continue
        try:
            ipaddress.ip_network(entry, strict=False)
        except ValueError:
            invalid.append(entry)
    if invalid:
        raise NotImplementedError(
            "Daytona team-self-hosted execution only supports network allowlists as CIDR "
            f"blocks; unsupported entries: {', '.join(invalid)}"
        )
    return allowlist


def _remote_shell_command(command: str, *, remote_cwd: str) -> str:
    payload = f"cd {shlex.quote(remote_cwd)} && {command}"
    return f"sh -lc {shlex.quote(payload)}"


def _run_daytona_command(
    policy: SandboxPolicy,
    *,
    command: str,
    cwd: Path,
    timeout_seconds: int,
    started_at: str,
) -> CommandResult:
    """Run one evaluator-style command inside an ephemeral Daytona sandbox."""
    started = started_at
    host_worktree, host_artifacts = _policy_mount_roots(policy, cwd)
    if list(policy.mounts.get("read_only") or []):
        raise NotImplementedError(
            "Daytona team-self-hosted execution does not yet project extra read-only mounts."
        )
    allowlist = _validated_daytona_allowlist(policy)
    try:
        relative_cwd = cwd.resolve().relative_to(host_worktree)
    except ValueError:
        relative_cwd = Path(".")
    remote_cwd = str((Path(_REMOTE_WORKTREE) / relative_cwd).as_posix())
    sandbox_metadata: dict[str, object] = {
        "backend": policy.backend,
        "profile": policy.profile,
        "provenance": policy.provenance,
        "network_mode": policy.network.get("mode"),
        "network_allowlist": allowlist,
        "command": command,
        "command_payload": {
            "transport": "daytona-sdk",
            "remote_cwd": remote_cwd,
        },
        "shell": False,
        "cwd": str(cwd),
        "workspace_sync": "upload_only",
        "remote_worktree": _REMOTE_WORKTREE,
        "remote_artifacts": _REMOTE_ARTIFACTS,
    }
    sandbox = None
    session_created = False
    try:
        (
            daytona_class,
            config_class,
            create_image_params_class,
            create_snapshot_params_class,
            resources_class,
            session_request_class,
        ) = _load_daytona_sdk()
        config_kwargs = _daytona_config_kwargs()
        if not config_kwargs.get("api_url"):
            raise ValueError("DAYTONA_API_URL is required for team-self-hosted execution.")
        if not (
            config_kwargs.get("api_key")
            or (
                config_kwargs.get("jwt_token")
                and config_kwargs.get("organization_id")
            )
        ):
            raise ValueError(
                "Daytona execution requires DAYTONA_API_KEY or "
                "DAYTONA_JWT_TOKEN with DAYTONA_ORGANIZATION_ID."
            )
        create_kwargs: dict[str, object] = {
            "env_vars": _filtered_env(policy) or None,
            "labels": {
                "hive_backend": policy.backend,
                "hive_profile": policy.profile,
                "hive_cwd": str(cwd),
            },
            "ephemeral": True,
            "network_block_all": policy.network.get("mode") == "deny" and not allowlist,
            "network_allow_list": ",".join(allowlist) if allowlist else None,
            "resources": _daytona_resources(policy, resources_class),
        }
        snapshot = os.environ.get("HIVE_DAYTONA_SNAPSHOT")
        if snapshot:
            create_params = create_snapshot_params_class(snapshot=snapshot, **create_kwargs)
            sandbox_metadata["snapshot"] = snapshot
        else:
            image = os.environ.get("HIVE_DAYTONA_IMAGE") or os.environ.get(
                "HIVE_SANDBOX_IMAGE", "python:3.11-slim"
            )
            create_params = create_image_params_class(image=image, **create_kwargs)
            sandbox_metadata["image"] = image
        daytona = daytona_class(config_class(**config_kwargs))
        sandbox = daytona.create(create_params, timeout=max(timeout_seconds + 60, 300))
        sandbox_metadata["remote_sandbox_id"] = getattr(
            sandbox,
            "id",
            getattr(sandbox, "sandbox_id", None),
        )
        archive_bytes = _archive_mounts(host_worktree, host_artifacts)
        sandbox.fs.create_folder(_REMOTE_WORKTREE, "755")
        sandbox.fs.create_folder(_REMOTE_ARTIFACTS, "755")
        # Daytona supports bytes -> remote_path uploads for in-memory artifacts.
        sandbox.fs.upload_file(archive_bytes, _REMOTE_ARCHIVE)
        sync_result = sandbox.process.exec(
            _remote_shell_command(
                (
                    f"mkdir -p {_REMOTE_WORKTREE} {_REMOTE_ARTIFACTS} && "
                    f"tar -xzf {_REMOTE_ARCHIVE} -C / && rm -f {_REMOTE_ARCHIVE}"
                ),
                remote_cwd="/",
            ),
            timeout=max(timeout_seconds, 60),
        )
        if _coerce_remote_returncode(sync_result) != 0:
            raise RuntimeError(_stringify_output(getattr(sync_result, "result", "mount sync failed")))
        sandbox.process.create_session(_DAYTONA_SESSION_ID)
        session_created = True
        result = sandbox.process.execute_session_command(
            _DAYTONA_SESSION_ID,
            session_request_class(command=_remote_shell_command(command, remote_cwd=remote_cwd)),
            timeout=timeout_seconds,
        )
        return CommandResult(
            command=command,
            started_at=started,
            finished_at=utc_now_iso(),
            returncode=_coerce_remote_returncode(result),
            stdout=_stringify_output(
                getattr(result, "stdout", getattr(result, "output", getattr(result, "result", "")))
            ),
            stderr=_stringify_output(getattr(result, "stderr", "")),
            timed_out=False,
            sandbox=sandbox_metadata,
        )
    except Exception as exc:  # pylint: disable=broad-except
        if "Timeout" in exc.__class__.__name__:
            return CommandResult(
                command=command,
                started_at=started,
                finished_at=utc_now_iso(),
                returncode=None,
                stdout=_stringify_output(
                    getattr(exc, "stdout", getattr(exc, "output", getattr(exc, "result", "")))
                ),
                stderr=_stringify_output(getattr(exc, "stderr", str(exc))),
                timed_out=True,
                sandbox=sandbox_metadata,
            )
        if getattr(exc, "exit_code", None) is not None:
            return CommandResult(
                command=command,
                started_at=started,
                finished_at=utc_now_iso(),
                returncode=int(getattr(exc, "exit_code", 1) or 1),
                stdout=_stringify_output(
                    getattr(exc, "stdout", getattr(exc, "output", getattr(exc, "result", "")))
                ),
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
            if session_created:
                try:
                    sandbox.process.delete_session(_DAYTONA_SESSION_ID)
                except Exception:  # pragma: no cover - defensive cleanup
                    pass
            try:
                sandbox.delete(timeout=max(timeout_seconds, 60))
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

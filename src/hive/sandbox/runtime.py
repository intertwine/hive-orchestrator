"""Runtime sandbox selection and local command wrapping."""

from __future__ import annotations

import atexit
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from typing import TYPE_CHECKING

from src.hive.flags import feature_flags
from src.hive.sandbox.registry import get_backend, iter_backend_probes

if TYPE_CHECKING:
    from src.hive.runtime.runpack import SandboxPolicy

_PROFILE_BACKENDS = {
    "local-safe": ("podman", "docker-rootless"),
    "local-fast": ("asrt",),
    "hosted-managed": ("e2b",),
    "team-self-hosted": ("daytona",),
    "experimental": ("cloudflare",),
}
_WIRED_BACKENDS = {"podman", "docker-rootless", "asrt", "e2b", "daytona"}
_ASRT_SETTINGS_DIR_PREFIX = "asrt-settings-"
_ASRT_SETTINGS_FILE_NAME = "settings.json"
_ASRT_SETTINGS_MAX_AGE_SECONDS = 24 * 60 * 60
_ASRT_SETTINGS_CLEANUP_DIRS: set[Path] = set()
_RESOLVED_BACKEND_BINARIES: dict[str, str] = {}


def _backend_readiness_reason(backend_name: str, probe) -> str:
    details: list[str] = []
    blockers = [str(item) for item in list(probe.blockers or []) if str(item).strip()]
    warnings = [str(item) for item in list(probe.warnings or []) if str(item).strip()]
    if blockers:
        details.append("; ".join(blockers))
    if warnings:
        details.append("; ".join(warnings))
    if backend_name not in _WIRED_BACKENDS:
        details.append("executor wiring has not landed yet")
    return f"{backend_name}: " + "; ".join(details) if details else backend_name


def _sandbox_profile_unavailable(
    profile: str,
    backend_names: tuple[str, ...],
    *,
    details: list[str] | None = None,
) -> ValueError:
    supported = ", ".join(backend_names)
    suffix = ""
    if details:
        suffix = " " + " ".join(details)
    return ValueError(
        f"Sandbox profile {profile!r} requires one of [{supported}], but none were detected."
        + suffix
    )


def _read_write_mounts(policy: SandboxPolicy, cwd: Path) -> tuple[Path, Path]:
    mounts = list(policy.mounts.get("read_write") or [])
    host_worktree = Path(str(mounts[0] if mounts else cwd)).resolve()
    host_artifacts = Path(str(mounts[1] if len(mounts) > 1 else cwd)).resolve()
    return host_worktree, host_artifacts


def _discover_backend_binary(backend_name: str, *, probe=None) -> str:
    """Resolve a backend binary once from probe evidence or backend lookup.

    Probe-backed policies normally populate the cache at selection time. The
    `_find_binary()` fallback remains for compatibility paths that bypass
    `resolve_sandbox_policy()` entirely, such as manually constructed policies or
    deserialized policies whose backend probe omitted `evidence["binary"]`.
    """
    backend = get_backend(backend_name)
    probe = probe or backend.probe()
    binary = str((probe.evidence or {}).get("binary") or "").strip()
    if binary:
        return binary
    finder = getattr(backend, "_find_binary", None)
    if callable(finder):
        resolved = finder()
        if resolved:
            return str(resolved)
    raise ValueError(
        f"Sandbox backend {backend_name!r} was selected, but Hive could not resolve its binary path."
    )


def _resolved_backend_binary(backend_name: str) -> str:
    cached = _RESOLVED_BACKEND_BINARIES.get(backend_name)
    if cached:
        return cached
    resolved = _discover_backend_binary(backend_name)
    _RESOLVED_BACKEND_BINARIES[backend_name] = resolved
    return resolved


def _register_asrt_settings_cleanup(directory: Path) -> None:
    _ASRT_SETTINGS_CLEANUP_DIRS.add(directory)


@atexit.register
def _cleanup_asrt_settings_dirs() -> None:
    for directory in list(_ASRT_SETTINGS_CLEANUP_DIRS):
        shutil.rmtree(directory, ignore_errors=True)
        _ASRT_SETTINGS_CLEANUP_DIRS.discard(directory)


def _prune_stale_asrt_settings_dirs(parent: Path) -> None:
    cutoff = time.time() - _ASRT_SETTINGS_MAX_AGE_SECONDS
    for candidate in parent.glob(f"{_ASRT_SETTINGS_DIR_PREFIX}*"):
        if not candidate.is_dir():
            continue
        try:
            if candidate.stat().st_mtime < cutoff:
                shutil.rmtree(candidate, ignore_errors=True)
        except OSError:
            continue


def _write_asrt_settings_file(policy: SandboxPolicy, cwd: Path) -> Path:
    # The local executor consumes the returned path after this helper returns, so
    # runtime-level cleanup cannot safely delete the directory immediately. We
    # keep per-process cleanup plus stale-dir pruning for orphaned leftovers.
    _, host_artifacts = _read_write_mounts(policy, cwd)
    host_artifacts.mkdir(parents=True, exist_ok=True)
    settings_root = host_artifacts.parent
    settings_root.mkdir(parents=True, exist_ok=True)
    _prune_stale_asrt_settings_dirs(settings_root)
    settings_dir = Path(
        tempfile.mkdtemp(
            prefix=_ASRT_SETTINGS_DIR_PREFIX,
            dir=settings_root,
        )
    )
    _register_asrt_settings_cleanup(settings_dir)
    settings_path = settings_dir / _ASRT_SETTINGS_FILE_NAME
    settings_path.write_text(
        json.dumps(_asrt_settings_payload(policy, cwd), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return settings_path


def _asrt_settings_payload(policy: SandboxPolicy, cwd: Path) -> dict[str, object]:
    host_worktree, host_artifacts = _read_write_mounts(policy, cwd)
    return {
        "network": {
            "allowedDomains": list(policy.network.get("allowlist") or []),
            "deniedDomains": [],
            "allowLocalBinding": False,
        },
        "filesystem": {
            "denyRead": [str(Path.home())],
            "allowRead": [str(host_worktree), str(host_artifacts)],
            "allowWrite": [str(host_worktree), str(host_artifacts), "/tmp"],
            "denyWrite": [],
        },
        "enableWeakerNestedSandbox": False,
        "enableWeakerNetworkIsolation": False,
    }


def container_path_for_host(policy: SandboxPolicy, host_path: str | Path) -> str:
    """Translate a host path into the configured container path when possible."""
    host = Path(host_path).resolve()
    if policy.backend == "legacy-host":
        return str(host)
    host_worktree, host_artifacts = _read_write_mounts(policy, host.parent)
    mappings = (
        (host_worktree, Path(str(policy.mounts.get("container_worktree") or "/workspace"))),
        (host_artifacts, Path(str(policy.mounts.get("container_artifacts") or "/artifacts"))),
    )
    for host_root, container_root in mappings:
        try:
            relative = host.relative_to(host_root)
        except ValueError:
            continue
        return str((container_root / relative).as_posix())
    return str(host)


def resolve_sandbox_policy(
    *,
    worktree_path: str,
    artifacts_path: str,
    profile: str = "default",
) -> SandboxPolicy:
    """Resolve the effective sandbox policy for a run profile."""
    from src.hive.runtime.runpack import (  # pylint: disable=import-outside-toplevel
        SandboxPolicy,
        default_sandbox_policy,
    )

    normalized = profile.strip().lower() or "default"
    if not feature_flags().get("hive.sandbox_v2", True):
        return default_sandbox_policy(
            worktree_path=worktree_path,
            artifacts_path=artifacts_path,
            profile=normalized,
        )
    backend_names = _PROFILE_BACKENDS.get(normalized)
    if not backend_names:
        return default_sandbox_policy(
            worktree_path=worktree_path,
            artifacts_path=artifacts_path,
            profile=normalized,
        )
    probes = {probe.backend: probe for probe in iter_backend_probes(backend_names)}
    readiness_failures: list[str] = []
    for backend_name in backend_names:
        probe = probes.get(backend_name)
        if probe is None or not probe.available:
            continue
        if probe.configured is False or backend_name not in _WIRED_BACKENDS:
            readiness_failures.append(_backend_readiness_reason(backend_name, probe))
            continue
        try:
            _RESOLVED_BACKEND_BINARIES[backend_name] = _discover_backend_binary(
                backend_name,
                probe=probe,
            )
        except ValueError as exc:
            readiness_failures.append(str(exc))
            continue
        return SandboxPolicy(
            backend=backend_name,
            isolation_class=probe.isolation_class,
            network={"mode": "deny", "allowlist": []},
            mounts={
                "read_only": [],
                "read_write": [worktree_path, artifacts_path],
                "container_worktree": "/workspace",
                "container_artifacts": "/artifacts",
            },
            resources={
                "cpu": None,
                "memory_mb": None,
                "disk_mb": None,
                "wall_clock_sec": None,
            },
            env={"inherit": False, "allowlist": ["LANG", "LC_ALL"], "passthrough": []},
            snapshot=False,
            resume=False,
            profile=normalized,
            provenance=f"sandbox_v2_backend:{backend_name}",
        )
    raise _sandbox_profile_unavailable(normalized, backend_names, details=readiness_failures)


def sandboxed_command(
    policy: SandboxPolicy,
    *,
    command: str,
    cwd: Path,
) -> tuple[list[str] | str, bool]:
    """Return an executor-ready command payload for the selected sandbox."""
    if policy.backend == "legacy-host":
        return command, True

    if policy.backend == "asrt":
        settings_path = _write_asrt_settings_file(policy, cwd)
        return [
            _resolved_backend_binary(policy.backend),
            "--settings",
            str(settings_path),
            "sh",
            "-lc",
            command,
        ], False

    if policy.backend not in {"podman", "docker-rootless"}:
        raise NotImplementedError(
            f"Sandbox backend {policy.backend!r} is not wired into the local executor yet."
        )

    binary = "podman" if policy.backend == "podman" else "docker"
    image = os.environ.get("HIVE_SANDBOX_IMAGE", "python:3.11-slim")
    host_worktree, host_artifacts = _read_write_mounts(policy, cwd)
    container_worktree = str(policy.mounts.get("container_worktree") or "/workspace")
    container_artifacts = str(policy.mounts.get("container_artifacts") or "/artifacts")
    try:
        relative_cwd = cwd.resolve().relative_to(host_worktree)
    except ValueError:
        relative_cwd = Path(".")
    container_cwd = str((Path(container_worktree) / relative_cwd).as_posix())
    base = [
        binary,
        "run",
        "--rm",
        "--interactive",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "--network",
        "none",
        "--volume",
        f"{host_worktree}:{container_worktree}:rw",
        "--volume",
        f"{host_artifacts}:{container_artifacts}:rw",
        "--workdir",
        container_cwd,
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
    ]
    for readonly in list(policy.mounts.get("read_only") or []):
        readonly_path = Path(str(readonly)).resolve()
        target_name = readonly_path.name or "ro"
        base.extend(["--volume", f"{readonly_path}:/readonly/{target_name}:ro"])
    for env_name in list(policy.env.get("allowlist") or []):
        value = os.environ.get(str(env_name))
        if value is not None:
            base.extend(["--env", f"{env_name}={value}"])
    for env_name in list(policy.env.get("passthrough") or []):
        value = os.environ.get(str(env_name))
        if value is not None:
            base.extend(["--env", f"{env_name}={value}"])
    cpu_limit = policy.resources.get("cpu")
    memory_mb = policy.resources.get("memory_mb")
    if cpu_limit:
        base.extend(["--cpus", str(cpu_limit)])
    if memory_mb:
        base.extend(["--memory", f"{memory_mb}m"])
    if policy.backend == "podman":
        base.extend(["--userns=keep-id", "--security-opt", "label=disable"])
    base.extend([image, "sh", "-lc", command])
    return base, False


__all__ = ["container_path_for_host", "resolve_sandbox_policy", "sandboxed_command"]

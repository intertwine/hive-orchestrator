"""Runtime sandbox selection and local command wrapping."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from src.hive.flags import feature_flags
from src.hive.sandbox.registry import iter_backend_probes

if TYPE_CHECKING:
    from src.hive.runtime.runpack import SandboxPolicy

_PROFILE_BACKENDS = {
    "local-safe": ("podman", "docker-rootless"),
    "local-fast": ("asrt",),
    "hosted-managed": ("e2b",),
    "team-self-hosted": ("daytona",),
    "experimental": ("cloudflare",),
}


def _sandbox_profile_unavailable(profile: str, backend_names: tuple[str, ...]) -> ValueError:
    supported = ", ".join(backend_names)
    return ValueError(
        f"Sandbox profile {profile!r} requires one of [{supported}], but none were detected."
    )


def _read_write_mounts(policy: SandboxPolicy, cwd: Path) -> tuple[Path, Path]:
    mounts = list(policy.mounts.get("read_write") or [])
    host_worktree = Path(str(mounts[0] if mounts else cwd)).resolve()
    host_artifacts = Path(str(mounts[1] if len(mounts) > 1 else cwd)).resolve()
    return host_worktree, host_artifacts


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
    for backend_name in backend_names:
        probe = probes.get(backend_name)
        if probe is None or not probe.available:
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
    raise _sandbox_profile_unavailable(normalized, backend_names)


def sandboxed_command(
    policy: SandboxPolicy,
    *,
    command: str,
    cwd: Path,
) -> tuple[list[str] | str, bool]:
    """Return an executor-ready command payload for the selected sandbox."""
    if policy.backend == "legacy-host":
        return command, True

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
        "--network",
        "none",
        "--volume",
        f"{host_worktree}:{container_worktree}:rw",
        "--volume",
        f"{host_artifacts}:{container_artifacts}:rw",
        "--workdir",
        container_cwd,
    ]
    if policy.backend == "podman":
        base.extend(["--userns=keep-id", "--security-opt", "label=disable"])
    base.extend([image, "sh", "-lc", command])
    return base, False


__all__ = ["container_path_for_host", "resolve_sandbox_policy", "sandboxed_command"]

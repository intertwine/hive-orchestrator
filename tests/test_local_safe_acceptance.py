"""Real local-safe acceptance proof for CI runners with rootless Podman."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.hive.runs.executors import LocalExecutor
from src.hive.sandbox.registry import get_backend
from src.hive.sandbox.runtime import resolve_sandbox_policy


pytestmark = pytest.mark.skipif(
    os.getenv("HIVE_RUN_LOCAL_SAFE_ACCEPTANCE") != "1",
    reason="Set HIVE_RUN_LOCAL_SAFE_ACCEPTANCE=1 to run the real Podman acceptance proof.",
)


def _assert_podman_rootless_probe() -> None:
    probe = get_backend("podman").probe()

    assert probe.available is True
    assert probe.configured is True
    assert probe.supported_profiles == ["local-safe"]
    assert (probe.evidence or {}).get("binary")
    assert (probe.evidence or {}).get("rootless") is True


def _local_safe_executor(tmp_path: Path) -> tuple[Path, Path, LocalExecutor]:
    worktree = tmp_path / "workspace"
    artifacts = tmp_path / "artifacts"
    worktree.mkdir()
    artifacts.mkdir()

    policy = resolve_sandbox_policy(
        worktree_path=str(worktree),
        artifacts_path=str(artifacts),
        profile="local-safe",
    )

    assert policy.backend == "podman"
    assert policy.profile == "local-safe"
    assert policy.network["mode"] == "deny"
    return worktree, artifacts, LocalExecutor(policy)


def test_local_safe_podman_executes_real_command(tmp_path):
    """A real Podman-backed local-safe run should execute inside the mounted worktree."""
    _assert_podman_rootless_probe()
    worktree, artifacts, executor = _local_safe_executor(tmp_path)
    (worktree / "input.txt").write_text("sandbox proof\n", encoding="utf-8")

    result = executor.run_command(
        (
            "python -c \"from pathlib import Path; "
            "print(Path.cwd()); "
            "print(Path('input.txt').read_text().strip()); "
            "Path('output.txt').write_text('ok\\n', encoding='utf-8')\""
        ),
        cwd=worktree,
        timeout_seconds=120,
    )

    assert result.returncode == 0, result.stderr
    assert result.timed_out is False
    assert result.sandbox is not None
    assert result.sandbox["backend"] == "podman"
    assert result.sandbox["profile"] == "local-safe"
    assert result.sandbox["network_mode"] == "deny"
    assert "/workspace" in result.stdout
    assert "sandbox proof" in result.stdout
    assert (worktree / "output.txt").read_text(encoding="utf-8") == "ok\n"
    assert artifacts.is_dir()


def test_local_safe_podman_denies_outbound_network(tmp_path):
    """The real local-safe Podman path should keep outbound networking disabled by default."""
    _assert_podman_rootless_probe()
    worktree, _artifacts, executor = _local_safe_executor(tmp_path)

    result = executor.run_command(
        'python -c "import socket; socket.create_connection((\'1.1.1.1\', 80), 2)"',
        cwd=worktree,
        timeout_seconds=30,
    )

    assert result.returncode not in (None, 0)
    assert result.timed_out is False
    assert result.sandbox is not None
    assert result.sandbox["backend"] == "podman"
    assert result.sandbox["network_mode"] == "deny"

"""Opt-in real remote sandbox acceptance proofs for credentialed environments."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.hive.runs.executors import LocalExecutor
from src.hive.runtime.runpack import SandboxPolicy


def _remote_policy(*, backend: str, profile: str, worktree: Path, artifacts: Path) -> SandboxPolicy:
    return SandboxPolicy(
        backend=backend,
        isolation_class="remote-sandbox",
        network={"mode": "deny", "allowlist": []},
        mounts={
            "read_only": [],
            "read_write": [str(worktree), str(artifacts)],
            "container_worktree": "/workspace",
            "container_artifacts": "/artifacts",
        },
        resources={"cpu": None, "memory_mb": None, "disk_mb": None, "wall_clock_sec": None},
        env={"inherit": False, "allowlist": ["LANG", "LC_ALL"], "passthrough": []},
        snapshot=False,
        resume=False,
        profile=profile,
        provenance=f"sandbox_v2_backend:{backend}",
    )


def _has_daytona_auth() -> bool:
    return bool(os.environ.get("DAYTONA_API_KEY")) or (
        bool(os.environ.get("DAYTONA_JWT_TOKEN"))
        and bool(os.environ.get("DAYTONA_ORGANIZATION_ID"))
    )


@pytest.mark.skipif(
    os.environ.get("HIVE_RUN_E2B_ACCEPTANCE") != "1",
    reason="Set HIVE_RUN_E2B_ACCEPTANCE=1 to run the real E2B acceptance proof.",
)
def test_e2b_remote_acceptance(tmp_path):
    pytest.importorskip("e2b")
    if not (os.environ.get("E2B_API_KEY") or os.environ.get("E2B_ACCESS_TOKEN")):
        pytest.skip("Set E2B_API_KEY or E2B_ACCESS_TOKEN to run the E2B acceptance proof.")

    worktree = tmp_path / "worktree"
    artifacts = tmp_path / "artifacts"
    worktree.mkdir()
    artifacts.mkdir()
    (worktree / "README.md").write_text("remote acceptance\n", encoding="utf-8")

    # LocalExecutor is the unified entry point for both local and remote sandboxes.
    executor = LocalExecutor(
        _remote_policy(
            backend="e2b",
            profile="hosted-managed",
            worktree=worktree,
            artifacts=artifacts,
        )
    )
    result = executor.run_command("sh -lc 'cat README.md && pwd'", cwd=worktree, timeout_seconds=60)

    assert result.returncode == 0
    assert "remote acceptance" in result.stdout
    assert result.stdout.strip().endswith("/workspace")
    assert result.sandbox is not None
    assert result.sandbox["backend"] == "e2b"
    assert result.sandbox["workspace_sync"] == "upload_only"
    assert result.sandbox["command_payload"]["transport"] == "e2b-sdk"
    assert result.sandbox["network_mode"] == "deny"
    assert result.sandbox["remote_sandbox_id"]


@pytest.mark.skipif(
    os.environ.get("HIVE_RUN_DAYTONA_ACCEPTANCE") != "1",
    reason="Set HIVE_RUN_DAYTONA_ACCEPTANCE=1 to run the real Daytona acceptance proof.",
)
def test_daytona_remote_acceptance(tmp_path):
    pytest.importorskip("daytona")
    if not os.environ.get("DAYTONA_API_URL"):
        pytest.skip("Set DAYTONA_API_URL to run the Daytona acceptance proof.")
    if not _has_daytona_auth():
        pytest.skip(
            "Set DAYTONA_API_KEY or DAYTONA_JWT_TOKEN with DAYTONA_ORGANIZATION_ID "
            "to run the Daytona acceptance proof."
        )

    worktree = tmp_path / "worktree"
    artifacts = tmp_path / "artifacts"
    worktree.mkdir()
    artifacts.mkdir()
    (worktree / "README.md").write_text("remote acceptance\n", encoding="utf-8")

    # LocalExecutor is the unified entry point for both local and remote sandboxes.
    executor = LocalExecutor(
        _remote_policy(
            backend="daytona",
            profile="team-self-hosted",
            worktree=worktree,
            artifacts=artifacts,
        )
    )
    result = executor.run_command("sh -lc 'cat README.md && pwd'", cwd=worktree, timeout_seconds=60)

    assert result.returncode == 0
    assert "remote acceptance" in result.stdout
    assert result.stdout.strip().endswith("/workspace")
    assert result.sandbox is not None
    assert result.sandbox["backend"] == "daytona"
    assert result.sandbox["workspace_sync"] == "upload_only"
    assert result.sandbox["command_payload"]["transport"] == "daytona-sdk"
    assert result.sandbox["network_mode"] == "deny"
    assert result.sandbox["remote_sandbox_id"]
    assert result.sandbox.get("snapshot") or result.sandbox.get("image")

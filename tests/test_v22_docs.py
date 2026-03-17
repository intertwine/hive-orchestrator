"""Docs coverage for the v2.2 control-plane story."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_control_plane_docs_and_harness_guides_exist():
    """The v2.2 launch docs should cover compare, IA, flows, harnesses, and migration."""
    compare = (REPO_ROOT / "docs" / "COMPARE_HARNESSES.md").read_text(encoding="utf-8")
    ia = (REPO_ROOT / "docs" / "UI_INFORMATION_ARCHITECTURE.md").read_text(encoding="utf-8")
    flows = (REPO_ROOT / "docs" / "OPERATOR_FLOWS.md").read_text(encoding="utf-8")
    migration = (REPO_ROOT / "docs" / "MIGRATING_TO_V2_2.md").read_text(encoding="utf-8")
    codex = (REPO_ROOT / "docs" / "recipes" / "codex-harness.md").read_text(encoding="utf-8")
    claude = (REPO_ROOT / "docs" / "recipes" / "claude-code-harness.md").read_text(
        encoding="utf-8"
    )
    campaigns = (REPO_ROOT / "docs" / "recipes" / "campaigns-and-briefs.md").read_text(
        encoding="utf-8"
    )
    drivers = (REPO_ROOT / "docs" / "recipes" / "driver-development.md").read_text(
        encoding="utf-8"
    )

    assert "control plane" in compare.lower()
    assert "Runs" in ia
    assert "Campaigns" in ia
    assert "manager loop" in flows.lower()
    assert "the real product surface is the React console" in migration
    assert "Codex" in codex
    assert "Claude Code" in claude
    assert "hive campaign create" in campaigns
    assert "normalized run model" in drivers.lower()

"""Docs coverage for control-plane reference surfaces."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_control_plane_docs_and_harness_guides_exist():
    """Reference docs should cover compare, IA, flows, harnesses, migration, and examples."""
    compare = (REPO_ROOT / "docs" / "COMPARE_HARNESSES.md").read_text(encoding="utf-8")
    ia = (REPO_ROOT / "docs" / "UI_INFORMATION_ARCHITECTURE.md").read_text(encoding="utf-8")
    flows = (REPO_ROOT / "docs" / "OPERATOR_FLOWS.md").read_text(encoding="utf-8")
    migration = (REPO_ROOT / "docs" / "MIGRATING_TO_V2_2.md").read_text(encoding="utf-8")
    examples = (REPO_ROOT / "examples" / "README.md").read_text(encoding="utf-8")
    parser = (REPO_ROOT / "src" / "hive" / "cli" / "parser.py").read_text(encoding="utf-8")
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
    assert "Hive v2.3 console" in ia
    assert "Runs" in ia
    assert "Campaigns" in ia
    assert "capability snapshot" in ia
    assert "retrieval trace" in ia
    assert "manager loop" in flows.lower()
    assert "the real product surface is the React console" in migration
    assert "hive onboard demo" in examples
    assert "current v2 substrate" in examples
    assert 'description="Hive v2.3 control-plane CLI"' in parser
    assert "Codex" in codex
    assert "Claude Code" in claude
    assert "hive campaign create" in campaigns
    assert "normalized run model" in drivers.lower()

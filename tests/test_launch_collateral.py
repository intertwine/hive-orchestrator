"""Checks for the v2.2 demo collateral and walkthrough assets."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.hive import demo_fixture


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_demo_walkthrough_exists_and_points_to_real_commands():
    """The launch demo doc should tell a maintainer exactly how to build and capture the fixture."""
    demo = (REPO_ROOT / "docs" / "DEMO_WALKTHROUGH.md").read_text(encoding="utf-8")

    assert "scripts/build_v22_demo_workspace.py" in demo
    assert "frontend/console/scripts/captureDemoAssets.mjs" in demo
    assert "north_star_manifest.json" in demo
    assert "hive --path /tmp/hive-v22-demo console serve" in demo
    assert "observe-and-steer-demo.webm" in demo
    assert "console-home.png" in demo
    assert "console-run-detail.png" in demo


def test_readme_and_compare_docs_keep_the_control_plane_launch_story():
    """Launch-facing docs should keep the command-center framing explicit."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    compare = (REPO_ROOT / "docs" / "COMPARE_HARNESSES.md").read_text(encoding="utf-8")

    assert "control plane" in readme.lower()
    assert "command center" in readme.lower()
    assert "docs/DEMO_WALKTHROUGH.md" in readme
    assert "control plane above the worker harness" in compare.lower()


def test_launch_assets_are_checked_in():
    """The launch walkthrough should ship with real screenshots and a demo clip."""
    for relative_path in (
        "images/launch/console-home.png",
        "images/launch/console-inbox.png",
        "images/launch/console-runs.png",
        "images/launch/console-run-detail.png",
        "images/launch/observe-and-steer-demo.webm",
    ):
        asset = REPO_ROOT / relative_path
        assert asset.exists()
        assert asset.stat().st_size > 0


def test_demo_builder_fails_cleanly_when_campaign_tick_launches_no_run(tmp_path, monkeypatch):
    """Demo generation should explain fixture drift instead of crashing on empty campaign output."""

    def empty_tick(*_args, **_kwargs):
        return {"launched_runs": []}

    monkeypatch.setattr(demo_fixture, "tick_campaign", empty_tick)

    with pytest.raises(RuntimeError, match="Campaign tick produced no runs"):
        demo_fixture.build_north_star_demo(tmp_path / "demo")

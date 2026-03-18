"""Tests for v2.2 campaigns, briefs, and guided onboarding."""

# pylint: disable=missing-function-docstring,unused-argument
# pylint: disable=import-error,no-name-in-module,too-few-public-methods,line-too-long

from __future__ import annotations

import json
from pathlib import Path
import subprocess

from tests.conftest import init_git_repo
from hive.cli.main import main as hive_main
from src.hive.store.projects import discover_projects
from src.hive.store.task_files import list_tasks


def _invoke_cli_json(capsys, argv: list[str]) -> dict:
    exit_code = hive_main(argv)
    captured = capsys.readouterr()
    assert exit_code == 0
    return json.loads(captured.out)


class TestCampaignsAndOnboarding:
    """Campaigns, briefs, and guided flows should feel product-level."""

    def test_onboard_blank_workspace_applies_generic_starter_evaluator(
        self, temp_hive_dir, capsys
    ):
        init_git_repo(temp_hive_dir)

        onboard = _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "onboard", "demo", "--title", "Demo"],
        )

        assert onboard["project"]["status"] == "active"
        assert onboard["project"]["priority"] == 2
        assert onboard["program"]["blocked_autonomous_promotion"] is False
        assert onboard["program"]["applied_template"]["id"] == "local-smoke"
        assert "hive work --project-id demo --owner <your-name>" in onboard["next_steps"]
        assert any("projects/demo/PROGRAM.md" in step for step in onboard["next_steps"])
        assert any(
            "hive program add-evaluator demo <real-evaluator-id>" in step
            for step in onboard["next_steps"]
        )
        assert any(
            "starter stub" in step and "does not validate real project behavior" in step
            for step in onboard["next_steps"]
        )

    def test_onboard_and_adopt_seed_safe_projects(self, temp_hive_dir, capsys):
        (Path(temp_hive_dir) / "pyproject.toml").write_text(
            "[project]\nname = 'demo'\nversion = '0.1.0'\n",
            encoding="utf-8",
        )
        (Path(temp_hive_dir) / "tests").mkdir()

        onboard = _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "onboard", "demo", "--title", "Demo"],
        )

        assert onboard["project"]["id"] == "demo"
        assert onboard["program"]["blocked_autonomous_promotion"] is False
        assert len(onboard["tasks"]) == 3

        adopted_dir = Path(temp_hive_dir) / "adopted"
        adopted_dir.mkdir()
        (adopted_dir / "pyproject.toml").write_text(
            "[project]\nname = 'adopted'\nversion = '0.1.0'\n",
            encoding="utf-8",
        )
        (adopted_dir / "tests").mkdir()

        adopt = _invoke_cli_json(
            capsys,
            ["--path", str(adopted_dir), "--json", "adopt", "app", "--title", "App"],
        )

        assert adopt["project"]["slug"] == "app"
        assert adopt["program"]["blocked_autonomous_promotion"] is False
        assert list_tasks(adopted_dir)

    def test_campaign_tick_launches_run_and_daily_brief_is_created(self, temp_hive_dir, capsys):
        init_git_repo(temp_hive_dir)
        (Path(temp_hive_dir) / "pyproject.toml").write_text(
            "[project]\nname = 'demo'\nversion = '0.1.0'\n",
            encoding="utf-8",
        )
        (Path(temp_hive_dir) / "tests").mkdir()

        onboard = _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "onboard", "demo", "--title", "Demo"],
        )
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )

        campaign = _invoke_cli_json(
            capsys,
            [
                "--path",
                temp_hive_dir,
                "--json",
                "campaign",
                "create",
                "--title",
                "Daily docs push",
                "--goal",
                "Keep the docs moving every day.",
                "--project-id",
                onboard["project"]["id"],
                "--driver",
                "local",
            ],
        )
        tick = _invoke_cli_json(
            capsys,
            [
                "--path",
                temp_hive_dir,
                "--json",
                "campaign",
                "tick",
                campaign["campaign"]["id"],
                "--owner",
                "manager",
            ],
        )
        brief = _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "brief", "daily"],
        )

        assert tick["launched_runs"]
        assert tick["active_runs"]
        assert tick["active_runs"][0]["campaign_id"] == campaign["campaign"]["id"]
        assert brief["path"].endswith(".md")
        assert Path(brief["path"]).exists()
        assert "campaigns" in brief
        assert discover_projects(temp_hive_dir)

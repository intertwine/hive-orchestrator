"""Tests for the Hive 2.1 portfolio control plane."""

# pylint: disable=missing-function-docstring,missing-class-docstring,unused-argument
# pylint: disable=redefined-outer-name,import-error,no-name-in-module,too-few-public-methods
# pylint: disable=line-too-long,wrong-import-order,unsubscriptable-object,duplicate-code

from __future__ import annotations

import json
from pathlib import Path
import subprocess

from tests.conftest import init_git_repo, write_safe_program
import pytest

from hive.cli.main import main as hive_main
from src.hive.control import (
    finish_run_flow,
    portfolio_status,
    recommend_next_task,
    steer_project,
    tick_portfolio,
    work_on_task,
)
from src.hive.store.projects import create_project
from src.hive.store.task_files import claim_task, create_task, get_task


def _invoke_cli_json(capsys, argv: list[str]) -> dict:
    exit_code = hive_main(argv)
    captured = capsys.readouterr()
    assert exit_code == 0
    return json.loads(captured.out)


class TestHiveControlPlane:
    """Tests for agent-manager style portfolio commands."""

    def test_cli_work_human_output_defaults_to_summary_view(self, temp_hive_dir, capsys):
        """Human-facing work output should stay compact unless the operator asks for context."""
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")

        exit_code = hive_main(
            [
                "--path",
                temp_hive_dir,
                "work",
                "--project-id",
                "demo",
                "--owner",
                "manager",
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "Started governed work on" in captured.out
        assert "Run:" in captured.out
        assert "# AGENTS" not in captured.out

    def test_cli_work_human_output_can_print_context_on_demand(self, temp_hive_dir, capsys):
        """`--print-context` should preserve the old full-bundle behavior when requested."""
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")

        exit_code = hive_main(
            [
                "--path",
                temp_hive_dir,
                "work",
                "--project-id",
                "demo",
                "--owner",
                "manager",
                "--print-context",
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "# AGENTS" in captured.out

    def test_cli_finish_human_output_includes_reject_reason(self, tmp_path, capsys):
        """Human-facing finish output should explain why a run was rejected."""
        workspace = tmp_path / "finish-human"
        workspace.mkdir(parents=True, exist_ok=True)
        init_git_repo(workspace)

        onboard = _invoke_cli_json(
            capsys,
            ["--path", str(workspace), "--json", "onboard", "demo", "--title", "Demo"],
        )
        run = _invoke_cli_json(
            capsys,
            [
                "--path",
                str(workspace),
                "--json",
                "work",
                "--project-id",
                "demo",
                "--owner",
                "manager",
            ],
        )["run"]

        exit_code = hive_main(["--path", str(workspace), "finish", run["id"], "--owner", "manager"])
        captured = capsys.readouterr()

        assert onboard["program"]["applied_template"]["id"] == "local-smoke"
        assert exit_code == 0
        assert "Promotion decision: reject" in captured.out
        assert "Run did not produce workspace changes" in captured.out

    def test_recommend_next_skips_paused_projects(self, temp_hive_dir, capsys):
        """Paused projects should drop out of manager recommendations."""
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        second = create_project(temp_hive_dir, "docs", title="Docs")
        create_task(temp_hive_dir, second.id, "Ship docs", status="ready", priority=1)

        steer_project(temp_hive_dir, "demo", paused=True, actor="operator")

        recommendation = recommend_next_task(temp_hive_dir)

        assert recommendation is not None
        assert recommendation["task"]["project_id"] == second.id

    def test_recommend_next_respects_focus_task_override(self, temp_hive_dir, capsys):
        """A focused task should win even when another task has equal or better default ranking."""
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        extra = create_task(
            temp_hive_dir,
            "demo",
            "Focused task",
            status="ready",
            priority=3,
        )

        steer_project(temp_hive_dir, "demo", focus_task_id=extra.id, actor="operator")

        recommendation = recommend_next_task(temp_hive_dir, project_id="demo")

        assert recommendation is not None
        assert recommendation["task"]["id"] == extra.id

    def test_work_on_task_claims_starts_run_and_writes_context(self, temp_hive_dir, capsys):
        """The happy-path work helper should checkpoint, claim, start, and assemble context."""
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        output_path = Path(temp_hive_dir) / "SESSION_CONTEXT.md"

        payload = work_on_task(
            temp_hive_dir,
            project_id="demo",
            owner="manager",
            output_path=output_path,
        )

        task = get_task(temp_hive_dir, payload["task"]["id"])
        assert payload["checkpoint"]["committed"] is True
        assert payload["run"]["status"] == "running"
        assert task.status == "in_progress"
        assert output_path.exists()

    def test_finish_run_flow_escalates_when_force_review_is_set(self, temp_hive_dir, capsys):
        """Human steering should be able to force review even when evaluators pass."""
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        payload = work_on_task(temp_hive_dir, project_id="demo", owner="manager")
        steer_project(temp_hive_dir, "demo", force_review=True, actor="operator")

        finished = finish_run_flow(temp_hive_dir, payload["run"]["id"], actor="manager")

        assert finished["action"] == "escalate"
        assert finished["run"]["status"] == "escalated"

    def test_work_on_task_refuses_active_foreign_claim(self, temp_hive_dir, capsys):
        """Managers should not silently steal a live claim from another owner."""
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        recommendation = recommend_next_task(temp_hive_dir, project_id="demo")
        assert recommendation is not None
        task_id = recommendation["task"]["id"]
        claim_task(temp_hive_dir, task_id, "alice", ttl_minutes=60)

        with pytest.raises(ValueError, match="actively claimed by alice"):
            work_on_task(temp_hive_dir, task_id=task_id, owner="bob")

    def test_work_on_task_validates_task_before_checkpoint(self, temp_hive_dir, capsys):
        """Mistyped task IDs should fail before creating a checkpoint commit."""
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        marker = Path(temp_hive_dir) / "README.md"
        marker.write_text("pending local change\n", encoding="utf-8")

        with pytest.raises(FileNotFoundError, match="Task not found"):
            work_on_task(temp_hive_dir, task_id="task_missing", owner="manager")

        status = subprocess.run(
            ["git", "status", "--short"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        head = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=temp_hive_dir,
            check=False,
            capture_output=True,
            text=True,
        )
        assert "README.md" in status.stdout
        assert head.returncode != 0

    def test_cli_work_and_finish_happy_path(self, temp_hive_dir, capsys):
        """CLI `work` and `finish` should cover the common manager loop end to end."""
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        context_path = Path(temp_hive_dir) / "SESSION_CONTEXT.md"

        work_payload = _invoke_cli_json(
            capsys,
            [
                "--path",
                temp_hive_dir,
                "--json",
                "work",
                "--project-id",
                "demo",
                "--owner",
                "manager",
                "--output",
                "SESSION_CONTEXT.md",
            ],
        )
        run = work_payload["run"]
        promoted_path = Path(run["worktree_path"]) / "src" / "manager_promoted.py"
        promoted_path.parent.mkdir(parents=True, exist_ok=True)
        promoted_path.write_text("print('manager promoted')\n", encoding="utf-8")
        subprocess.run(["git", "add", "src/manager_promoted.py"], cwd=run["worktree_path"], check=True)
        subprocess.run(
            ["git", "commit", "-m", "Manager change"],
            cwd=run["worktree_path"],
            check=True,
            capture_output=True,
            text=True,
        )

        finish_payload = _invoke_cli_json(
            capsys,
            [
                "--path",
                temp_hive_dir,
                "--json",
                "finish",
                run["id"],
                "--owner",
                "manager",
            ],
        )

        assert work_payload["run"]["status"] == "running"
        assert work_payload["output_path"] == str(context_path.resolve())
        assert context_path.exists()
        assert finish_payload["action"] == "promote"
        assert finish_payload["run"]["status"] == "accepted"
        assert (Path(temp_hive_dir) / "src" / "manager_promoted.py").exists()

    def test_tick_portfolio_start_and_review(self, temp_hive_dir, capsys):
        """Portfolio ticks should cover the start and review manager loop modes."""
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")

        start_payload = tick_portfolio(
            temp_hive_dir,
            mode="start",
            owner="manager",
            project_id="demo",
            output_path="SESSION_CONTEXT.md",
        )
        run = start_payload["work"]["run"]
        promoted_path = Path(run["worktree_path"]) / "docs" / "tick-review.md"
        promoted_path.parent.mkdir(parents=True, exist_ok=True)
        promoted_path.write_text("tick review artifact\n", encoding="utf-8")
        subprocess.run(["git", "add", "docs/tick-review.md"], cwd=run["worktree_path"], check=True)
        subprocess.run(
            ["git", "commit", "-m", "Tick review artifact"],
            cwd=run["worktree_path"],
            check=True,
            capture_output=True,
            text=True,
        )

        review_payload = tick_portfolio(
            temp_hive_dir,
            mode="review",
            owner="manager",
            run_id=run["id"],
        )

        assert start_payload["mode"] == "start"
        assert start_payload["work"]["run"]["status"] == "running"
        assert review_payload["mode"] == "review"
        assert review_payload["finish"]["action"] == "promote"
        assert review_payload["finish"]["run"]["status"] == "accepted"
        assert (Path(temp_hive_dir) / "docs" / "tick-review.md").exists()

    def test_cli_portfolio_status_steer_and_tick(self, temp_hive_dir, capsys):
        """Portfolio commands should expose status, steering, and bounded ticks."""
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")

        recommendation = recommend_next_task(temp_hive_dir, project_id="demo")
        assert recommendation is not None
        task_id = recommendation["task"]["id"]
        steer_payload = _invoke_cli_json(
            capsys,
            [
                "--path",
                temp_hive_dir,
                "--json",
                "portfolio",
                "steer",
                "demo",
                "--focus-task",
                task_id,
                "--boost",
                "2",
                "--note",
                "Keep the demo moving.",
            ],
        )
        status_payload = _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "portfolio", "status"],
        )
        tick_payload = _invoke_cli_json(
            capsys,
            [
                "--path",
                temp_hive_dir,
                "--json",
                "portfolio",
                "tick",
                "--mode",
                "recommend",
                "--project-id",
                "demo",
            ],
        )

        assert steer_payload["steering"]["focus_task_id"] == task_id
        assert steer_payload["steering"]["boost"] == 2
        assert status_payload["recommendation"]["task"]["id"] == task_id
        assert tick_payload["recommendation"]["task"]["id"] == task_id
        recommendation = portfolio_status(temp_hive_dir)["recommended_next"]
        assert recommendation is not None
        assert recommendation["task"]["id"] == task_id

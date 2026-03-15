"""Tests for the Hive 2.1 portfolio control plane."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

from hive.cli.main import main as hive_main
from src.hive.control import (
    finish_run_flow,
    portfolio_status,
    recommend_next_task,
    steer_project,
    work_on_task,
)
from src.hive.store.projects import create_project, discover_projects
from src.hive.store.task_files import create_task, get_task


def _invoke_cli_json(capsys, argv: list[str]) -> dict:
    exit_code = hive_main(argv)
    captured = capsys.readouterr()
    assert exit_code == 0
    return json.loads(captured.out)


def _safe_program(command: str = "python -c \"print('ok')\"") -> str:
    return f"""---
program_version: 1
mode: workflow
default_executor: local
budgets:
  max_wall_clock_minutes: 30
  max_steps: 25
  max_tokens: 20000
  max_cost_usd: 2.0
paths:
  allow:
    - src/**
    - tests/**
    - docs/**
  deny: []
commands:
  allow:
    - {json.dumps(command)}
  deny: []
evaluators:
  - id: unit
    command: {json.dumps(command)}
    required: true
promotion:
  allow_unsafe_without_evaluators: false
  requires_all:
    - unit
  review_required_when_paths_match: []
  auto_close_task: false
escalation:
  when_paths_match: []
  when_commands_match: []
---

# Goal

Run a governed task safely.
"""


def _init_git_repo(path: str | Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Hive Tests"], cwd=path, check=True)


def _write_safe_program(root: str | Path, project_id: str, command: str = "python -c \"print('ok')\""):
    project = next(project for project in discover_projects(root) if project.id == project_id)
    project.program_path.write_text(_safe_program(command), encoding="utf-8")
    return project


class TestHiveControlPlane:
    """Tests for agent-manager style portfolio commands."""

    def test_recommend_next_skips_paused_projects(self, temp_hive_dir, capsys):
        """Paused projects should drop out of manager recommendations."""
        _init_git_repo(temp_hive_dir)
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
        _init_git_repo(temp_hive_dir)
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
        _init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        _write_safe_program(temp_hive_dir, "demo")
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
        _init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        _write_safe_program(temp_hive_dir, "demo")
        payload = work_on_task(temp_hive_dir, project_id="demo", owner="manager")
        steer_project(temp_hive_dir, "demo", force_review=True, actor="operator")

        finished = finish_run_flow(temp_hive_dir, payload["run"]["id"], actor="manager")

        assert finished["action"] == "escalate"
        assert finished["run"]["status"] == "escalated"

    def test_cli_work_and_finish_happy_path(self, temp_hive_dir, capsys):
        """CLI `work` and `finish` should cover the common manager loop end to end."""
        _init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        _write_safe_program(temp_hive_dir, "demo")
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

    def test_cli_portfolio_status_steer_and_tick(self, temp_hive_dir, capsys):
        """Portfolio commands should expose status, steering, and bounded ticks."""
        _init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        _write_safe_program(temp_hive_dir, "demo")

        task_id = recommend_next_task(temp_hive_dir, project_id="demo")["task"]["id"]
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
        assert portfolio_status(temp_hive_dir)["recommended_next"]["task"]["id"] == task_id

"""Driver and run-contract tests for Hive 2.2 foundations."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

from hive.cli.main import main as hive_main
from src.hive.runs.engine import load_run, start_run
from src.hive.scheduler.query import ready_tasks
from src.hive.store.projects import discover_projects
from src.hive.store.task_files import create_task


def _invoke_cli_json(capsys, argv: list[str]) -> dict:
    exit_code = hive_main(argv)
    captured = capsys.readouterr()
    assert exit_code == 0
    return json.loads(captured.out)


def _init_git_repo(path: str | Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Hive Tests"], cwd=path, check=True)


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
  allow_accept_without_changes: true
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


def _write_safe_program(root: str | Path, project_id: str) -> None:
    project = next(project for project in discover_projects(root) if project.id == project_id)
    project.program_path.write_text(_safe_program(), encoding="utf-8")


class TestHiveDrivers:
    """Conformance tests for the v2.2 driver layer."""

    def test_cli_drivers_list_shows_all_supported_drivers(self, temp_hive_dir, capsys):
        payload = _invoke_cli_json(capsys, ["--path", temp_hive_dir, "--json", "drivers", "list"])

        assert [driver["driver"] for driver in payload["drivers"]] == [
            "local",
            "manual",
            "codex",
            "claude-code",
        ]

    def test_run_start_for_external_harness_drivers_writes_normalized_artifacts(
        self, temp_hive_dir, capsys
    ):
        _init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        _write_safe_program(temp_hive_dir, "demo")
        create_task(temp_hive_dir, "demo", "Codex slice", status="ready", priority=1)
        create_task(temp_hive_dir, "demo", "Claude slice", status="ready", priority=1)
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )

        for driver_name in ("codex", "claude-code"):
            task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
            run = start_run(temp_hive_dir, task_id, driver_name=driver_name)
            metadata = load_run(temp_hive_dir, run.id)
            run_root = Path(temp_hive_dir) / ".hive" / "runs" / run.id

            assert metadata["driver"] == driver_name
            assert metadata["status"] == "awaiting_input"
            assert (run_root / "launch.json").exists()
            assert (run_root / "context" / "manifest.json").exists()
            assert (run_root / "context" / "compiled" / "run-brief.md").exists()
            assert (run_root / "transcript" / "normalized.jsonl").exists()
            assert (run_root / "workspace" / "patch.diff").exists()
            assert (run_root / "workspace" / "changed_files.json").exists()
            assert (run_root / "driver" / "driver-metadata.json").exists()
            assert (run_root / "driver" / "handles.json").exists()
            assert (run_root / "review" / "summary.md").exists()
            assert (run_root / "review" / "review.md").exists()
            assert (run_root / "plan" / "plan.md").exists()
            assert (run_root / "plan" / "plan.json").exists()
            assert (run_root / "logs" / "stdout.txt").exists()
            assert (run_root / "logs" / "stderr.txt").exists()
            assert (run_root / "events.jsonl").exists()

    def test_local_run_start_records_v22_event_sequence_and_status(self, temp_hive_dir, capsys):
        _init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        _write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="local")
        payload = _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "run", "status", run.id],
        )
        events_path = Path(temp_hive_dir) / ".hive" / "runs" / run.id / "events.jsonl"
        event_types = [
            json.loads(line)["type"]
            for line in events_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        assert payload["status"]["state"] == "running"
        assert payload["status"]["driver"] == "local"
        assert event_types[:5] == [
            "run.queued",
            "run.context_compiled",
            "context.compiled",
            "run.launch_started",
            "run.launched",
        ]
        assert "run.status.changed" in event_types

    def test_cli_steer_reroute_preserves_lineage_and_updates_driver(self, temp_hive_dir, capsys):
        _init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        _write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="local")

        payload = _invoke_cli_json(
            capsys,
            [
                "--path",
                temp_hive_dir,
                "--json",
                "steer",
                "reroute",
                run.id,
                "--driver",
                "codex",
                "--reason",
                "Use Codex for a broader repo pass",
            ],
        )
        metadata = load_run(temp_hive_dir, run.id)
        handles_path = Path(temp_hive_dir) / ".hive" / "runs" / run.id / "driver" / "handles.json"
        handles = json.loads(handles_path.read_text(encoding="utf-8"))
        timeline = (
            Path(temp_hive_dir) / ".hive" / "runs" / run.id / "events.jsonl"
        ).read_text(encoding="utf-8")

        assert payload["run"]["driver"] == "codex"
        assert metadata["driver"] == "codex"
        assert metadata["status"] == "awaiting_input"
        assert handles["active"]["driver"] == "codex"
        assert len(handles["history"]) >= 2
        assert "steering.reroute_requested" in timeline
        assert "steering.rerouted" in timeline

    def test_cli_steer_pause_resume_and_cancel_update_run_timeline(self, temp_hive_dir, capsys):
        _init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        _write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="local")

        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "steer", "pause", run.id, "--reason", "Wait"],
        )
        paused = load_run(temp_hive_dir, run.id)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "steer", "resume", run.id, "--reason", "Go"],
        )
        resumed = load_run(temp_hive_dir, run.id)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "steer", "cancel", run.id, "--reason", "Stop"],
        )
        cancelled = load_run(temp_hive_dir, run.id)
        task = ready_tasks(temp_hive_dir, project_id="demo")[0]
        timeline = (
            Path(temp_hive_dir) / ".hive" / "runs" / run.id / "events.jsonl"
        ).read_text(encoding="utf-8")

        assert paused["health"] == "paused"
        assert resumed["health"] == "healthy"
        assert cancelled["status"] == "cancelled"
        assert task["id"] == run.task_id
        assert "steering.pause" in timeline
        assert "steering.resume" in timeline
        assert "steering.cancel" in timeline
        assert "run.cancelled" in timeline

"""Tests for the Hive v2 substrate and CLI."""

from __future__ import annotations

import json
from pathlib import Path

from src.hive.cli.main import main as hive_main
from src.hive.memory import observe_project, reflect_project, startup_context
from src.hive.migrate import migrate_v1_to_v2
from src.hive.models.task import TaskRecord
from src.hive.projections.agency_md import RUN_BEGIN, RUN_END, TASK_BEGIN, TASK_END
from src.hive.projections.global_md import BEGIN as GLOBAL_BEGIN
from src.hive.projections.global_md import END as GLOBAL_END
from src.hive.runs import accept_run, eval_run, start_run
from src.hive.scheduler.query import ready_tasks
from src.hive.store.cache import rebuild_cache
from src.hive.store.layout import ensure_layout, tasks_dir
from src.hive.store.projects import discover_projects
from src.hive.store.task_files import get_task, save_task


def _program_markdown(command: str, auto_close: bool = False) -> str:
    return f"""---
program_version: 1
mode: workflow
default_executor: local
budgets:
  max_wall_clock_minutes: 30
  max_steps: 25
  max_tokens: 20000
  max_cost_usd: 0.0
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
  requires_all:
    - unit
  auto_close_task: {str(auto_close).lower()}
escalation:
  when_paths_match: []
  when_commands_match: []
---

# Goal

Run a safe evaluator.
"""


class TestHiveV2TaskFiles:
    """Tests for canonical task file behavior."""

    def test_task_round_trip_preserves_unknown_frontmatter(self, temp_hive_dir):
        """Unknown frontmatter keys should survive load/save."""
        ensure_layout(temp_hive_dir)
        task = TaskRecord(
            id="task_test_roundtrip",
            project_id="test-project",
            title="Round-trip task",
            status="ready",
            metadata={"custom_field": {"nested": True}},
            summary_md="Summary",
            notes_md="Notes",
        )
        save_task(temp_hive_dir, task)

        reloaded = get_task(temp_hive_dir, task.id)
        assert reloaded.metadata["custom_field"] == {"nested": True}
        assert reloaded.summary_md == "Summary"
        assert reloaded.notes_md == "Notes"


class TestHiveV2Migration:
    """Tests for v1 -> v2 migration."""

    def test_migrate_imports_tasks_program_and_markers(self, temp_hive_dir, temp_project):
        """Migration should create canonical tasks, a PROGRAM stub, and projection markers."""
        report = migrate_v1_to_v2(temp_hive_dir)
        result = report.to_dict()
        assert result["ok"] is True
        assert result["projects_imported"] >= 1
        assert result["tasks_imported"] >= 3

        tasks = list(tasks_dir(temp_hive_dir).glob("task_*.md"))
        assert tasks

        program_path = Path(temp_project).parent / "PROGRAM.md"
        assert program_path.exists()

        global_content = Path(temp_hive_dir, "GLOBAL.md").read_text(encoding="utf-8")
        assert GLOBAL_BEGIN in global_content
        assert GLOBAL_END in global_content

        agency_content = Path(temp_project).read_text(encoding="utf-8")
        assert TASK_BEGIN in agency_content
        assert TASK_END in agency_content
        assert RUN_BEGIN in agency_content
        assert RUN_END in agency_content
        assert "## Tasks" in agency_content

    def test_migration_dry_run_does_not_create_task_files(self, temp_hive_dir):
        """Dry-run migration should report without mutating task storage."""
        report = migrate_v1_to_v2(temp_hive_dir, dry_run=True)
        assert report.to_dict()["ok"] is True
        assert list(tasks_dir(temp_hive_dir).glob("task_*.md")) == []


class TestHiveV2Runs:
    """Tests for run engine happy paths."""

    def test_run_start_eval_and_accept_respects_auto_close(self, temp_hive_dir, temp_project):
        """Accepted runs should leave tasks in review when auto_close_task is false."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(_program_markdown(command, auto_close=False), encoding="utf-8")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)
        result = eval_run(temp_hive_dir, run.id)
        assert result["run"]["status"] == "evaluating"

        accepted = accept_run(temp_hive_dir, run.id)
        task = get_task(temp_hive_dir, task_id)
        assert accepted["status"] == "accepted"
        assert task.status == "review"


class TestHiveV2Memory:
    """Tests for memory observe/reflect/context behavior."""

    def test_memory_observe_reflect_and_context(self, temp_hive_dir, temp_project):
        """Observations should feed reflections and startup context."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        transcript = Path(temp_hive_dir) / "sample-transcript.md"
        transcript.write_text("We discussed Hive v2 task migration.", encoding="utf-8")

        observe_project(temp_hive_dir, transcript_path=str(transcript))
        outputs = reflect_project(temp_hive_dir)
        assert outputs["profile"].exists()
        assert outputs["active"].exists()

        context = startup_context(temp_hive_dir, project_id=project.id, profile="light", query="migration")
        assert context["project_id"] == project.id
        assert any(section["name"] == "profile" for section in context["sections"])


class TestHiveV2Cli:
    """Tests for the CLI JSON surface."""

    def test_cli_task_ready_json_after_migration(self, temp_hive_dir, capsys):
        """The CLI should return stable JSON for ready tasks."""
        migrate_v1_to_v2(temp_hive_dir)
        rebuild_cache(temp_hive_dir)

        exit_code = hive_main(["--path", temp_hive_dir, "--json", "task", "ready"])
        captured = capsys.readouterr()

        assert exit_code == 0
        payload = json.loads(captured.out)
        assert payload["version"]
        assert "tasks" in payload

    def test_cli_cache_rebuild_command(self, temp_hive_dir, capsys):
        """Cache rebuild should create the derived SQLite database."""
        migrate_v1_to_v2(temp_hive_dir)

        exit_code = hive_main(["--path", temp_hive_dir, "--json", "cache", "rebuild"])
        captured = capsys.readouterr()

        assert exit_code == 0
        payload = json.loads(captured.out)
        assert Path(payload["path"]).exists()

    def test_cli_run_show_returns_metadata(self, temp_hive_dir, temp_project, capsys):
        """Run show should surface persisted metadata after start."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(_program_markdown(command), encoding="utf-8")
        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)

        exit_code = hive_main(["--path", temp_hive_dir, "--json", "run", "show", run.id])
        captured = capsys.readouterr()

        assert exit_code == 0
        payload = json.loads(captured.out)
        assert payload["run"]["id"] == run.id

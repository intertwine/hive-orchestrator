"""Tests for the Hive v2 substrate and CLI."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from src.hive.cli.main import main as hive_main
from src.hive.memory import observe_project, reflect_project, startup_context
from src.hive.migrate import migrate_v1_to_v2
from src.hive.models.task import TaskRecord
from src.hive.projections.agency_md import RUN_BEGIN, RUN_END, TASK_BEGIN, TASK_END
from src.hive.projections.global_md import BEGIN as GLOBAL_BEGIN
from src.hive.projections.global_md import END as GLOBAL_END
from src.hive.runs import accept_run, eval_run, start_run
from src.hive.runs.engine import escalate_run, reject_run
from src.hive.search import search_workspace
from src.hive.scheduler.query import project_summary, ready_tasks
from src.hive.store.cache import _memory_scope_parts, rebuild_cache
from src.hive.store.layout import ensure_layout, tasks_dir
from src.hive.store.projects import discover_projects
from src.hive.store.task_files import get_task, link_tasks, save_task


def _program_markdown(
    command: str,
    auto_close: bool = False,
    allow_commands: list[str] | None = None,
) -> str:
    allowed = allow_commands if allow_commands is not None else [command]
    allow_block = (
        "\n" + "\n".join(f"    - {json.dumps(item)}" for item in allowed)
        if allowed
        else " []"
    )
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
  allow:{allow_block}
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

    def test_link_tasks_rejects_missing_destination(self, temp_hive_dir):
        """Linking should fail fast when the destination task does not exist."""
        ensure_layout(temp_hive_dir)
        source = TaskRecord(
            id="task_link_source",
            project_id="test-project",
            title="Link source",
            status="ready",
        )
        save_task(temp_hive_dir, source)

        try:
            link_tasks(temp_hive_dir, source.id, "blocks", "task_missing")
        except FileNotFoundError:
            pass
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected missing destination task to raise FileNotFoundError")

    def test_task_round_trip_preserves_noncanonical_sections(self, temp_hive_dir):
        """Custom task sections should survive load/save cycles."""
        ensure_layout(temp_hive_dir)
        task = TaskRecord(
            id="task_test_sections",
            project_id="test-project",
            title="Section task",
            status="ready",
            summary_md="Summary",
            notes_md="Notes",
            history_md="History",
        )
        save_task(temp_hive_dir, task)
        task_file = Path(temp_hive_dir) / ".hive" / "tasks" / f"{task.id}.md"
        task_file.write_text(
            task_file.read_text(encoding="utf-8") + "\n\n## References\n- docs/example.md\n",
            encoding="utf-8",
        )

        reloaded = get_task(temp_hive_dir, task.id)
        save_task(temp_hive_dir, reloaded)

        rendered = task_file.read_text(encoding="utf-8")
        assert "## References" in rendered
        assert "- docs/example.md" in rendered


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

    def test_eval_run_rejects_commands_outside_allow_list(self, temp_hive_dir, temp_project):
        """Evaluators should only run commands explicitly allow-listed in PROGRAM.md."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(
            _program_markdown(command, allow_commands=[]),
            encoding="utf-8",
        )

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)
        try:
            eval_run(temp_hive_dir, run.id)
        except ValueError as exc:
            assert "allow-listed" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected evaluator allow-list validation to fail")

    def test_start_run_rejects_terminal_task_statuses(self, temp_hive_dir, temp_project):
        """Runs should not reopen blocked or completed tasks."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        task = get_task(temp_hive_dir, task_id)
        task.status = "done"
        save_task(temp_hive_dir, task)

        try:
            start_run(temp_hive_dir, task_id)
        except ValueError as exc:
            assert "Cannot start run" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected terminal task status to block run creation")

    def test_eval_run_rejects_non_running_statuses(self, temp_hive_dir, temp_project):
        """Evaluators should only run from the running state."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(_program_markdown(command), encoding="utf-8")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)
        eval_run(temp_hive_dir, run.id)

        try:
            eval_run(temp_hive_dir, run.id)
        except ValueError as exc:
            assert "Cannot evaluate run" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected non-running run evaluation to fail")

    def test_accept_run_requires_evaluating_status(self, temp_hive_dir, temp_project):
        """Runs should not be accepted before evaluator execution."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(_program_markdown(command), encoding="utf-8")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)

        try:
            accept_run(temp_hive_dir, run.id)
        except ValueError as exc:
            assert "Cannot accept run" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected accept without evaluation to fail")

    def test_reject_run_rejects_terminal_statuses(self, temp_hive_dir, temp_project):
        """Rejected runs should not overwrite already-finalized outcomes."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(_program_markdown(command), encoding="utf-8")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)
        eval_run(temp_hive_dir, run.id)
        accept_run(temp_hive_dir, run.id)

        try:
            reject_run(temp_hive_dir, run.id)
        except ValueError as exc:
            assert "Cannot reject run" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected rejecting an accepted run to fail")

    def test_reject_run_requeues_claimed_task(self, temp_hive_dir, temp_project):
        """Rejected runs should return claimed tasks to the ready queue."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(_program_markdown(command), encoding="utf-8")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        task = get_task(temp_hive_dir, task_id)
        task.status = "claimed"
        task.owner = "codex"
        task.claimed_until = "2099-01-01T00:00:00Z"
        save_task(temp_hive_dir, task)

        run = start_run(temp_hive_dir, task_id)
        rejected = reject_run(temp_hive_dir, run.id, reason="retry")
        reloaded = get_task(temp_hive_dir, task_id)
        ready_ids = [item["id"] for item in ready_tasks(temp_hive_dir, project_id=project.id)]

        assert rejected["status"] == "rejected"
        assert reloaded.status == "ready"
        assert reloaded.owner is None
        assert reloaded.claimed_until is None
        assert task_id in ready_ids

    def test_escalate_run_rejects_terminal_statuses(self, temp_hive_dir, temp_project):
        """Escalation should not reopen finalized runs or tasks."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(_program_markdown(command), encoding="utf-8")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)
        eval_run(temp_hive_dir, run.id)
        accept_run(temp_hive_dir, run.id)

        try:
            escalate_run(temp_hive_dir, run.id)
        except ValueError as exc:
            assert "Cannot escalate run" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected escalating an accepted run to fail")

    def test_expired_claimed_task_returns_to_ready_queue(self, temp_hive_dir, temp_project):
        """Expired claimed tasks should be surfaced by ready detection again."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        task = get_task(temp_hive_dir, task_id)
        task.status = "claimed"
        task.owner = "codex"
        task.claimed_until = "2000-01-01T00:00:00Z"
        save_task(temp_hive_dir, task)

        ready = ready_tasks(temp_hive_dir, project_id=project.id)
        ready_entry = next(item for item in ready if item["id"] == task_id)
        assert ready_entry["status"] == "ready"


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

    def test_cache_rebuild_keeps_memory_docs_unique_per_scope_key(self, temp_hive_dir, temp_project):
        """Memory docs should not collide when multiple scoped docs share the same kind."""
        migrate_v1_to_v2(temp_hive_dir)
        memory_root = Path(temp_hive_dir) / ".hive" / "memory" / "project"
        for scope_key in ("demo", "ops"):
            directory = memory_root / scope_key
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "observations.md").write_text(
                f"# Observations\n\n{scope_key}\n",
                encoding="utf-8",
            )

        db_path = rebuild_cache(temp_hive_dir)
        connection = sqlite3.connect(db_path)
        try:
            rows = list(
                connection.execute(
                    "SELECT id, scope, scope_key, kind FROM memory_docs ORDER BY scope_key"
                )
            )
        finally:
            connection.close()

        assert ("project:demo:observations", "project", "demo", "observations") in rows
        assert ("project:ops:observations", "project", "ops", "observations") in rows

    def test_cache_rebuild_skips_unknown_memory_kinds(self, temp_hive_dir, temp_project):
        """Custom memory markdown files should not abort cache rebuild."""
        migrate_v1_to_v2(temp_hive_dir)
        memory_root = Path(temp_hive_dir) / ".hive" / "memory" / "project" / "demo"
        memory_root.mkdir(parents=True, exist_ok=True)
        (memory_root / "notes.md").write_text("# Notes\n\ncustom\n", encoding="utf-8")
        (memory_root / "observations.md").write_text("# Observations\n\nok\n", encoding="utf-8")

        db_path = rebuild_cache(temp_hive_dir)
        connection = sqlite3.connect(db_path)
        try:
            kinds = list(connection.execute("SELECT scope_key, kind FROM memory_docs ORDER BY kind"))
        finally:
            connection.close()

        assert ("demo", "observations") in kinds
        assert ("demo", "notes") not in kinds

    def test_memory_scope_parts_rejects_invalid_shapes(self):
        """Memory scope parsing should reject unsupported paths and scopes."""
        try:
            _memory_scope_parts(Path("observations.md"))
        except ValueError as exc:
            assert "Unsupported memory doc path" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected shallow memory path to fail")

        try:
            _memory_scope_parts(Path("custom/demo/observations.md"))
        except ValueError as exc:
            assert "Unsupported memory scope" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected unsupported memory scope to fail")

    def test_cache_rebuild_skips_orphaned_runs(self, temp_hive_dir, temp_project):
        """Run metadata pointing at missing tasks should not abort cache rebuild."""
        migrate_v1_to_v2(temp_hive_dir)
        runs_dir = Path(temp_hive_dir) / ".hive" / "runs" / "run_orphaned"
        runs_dir.mkdir(parents=True, exist_ok=True)
        (runs_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "id": "run_orphaned",
                    "project_id": discover_projects(temp_hive_dir)[0].id,
                    "task_id": "task_missing",
                    "status": "running",
                    "started_at": "2026-03-15T00:00:00Z",
                }
            ),
            encoding="utf-8",
        )

        db_path = rebuild_cache(temp_hive_dir)
        connection = sqlite3.connect(db_path)
        try:
            run_ids = [row[0] for row in connection.execute("SELECT id FROM runs")]
        finally:
            connection.close()

        assert "run_orphaned" not in run_ids


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

    def test_cache_ready_and_active_claim_views_handle_iso_expiry(self, temp_hive_dir, temp_project):
        """SQLite views should parse ISO timestamps when deciding claim expiry."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        ready_ids_before = [item["id"] for item in ready_tasks(temp_hive_dir, project_id=project.id)]

        expired_task = get_task(temp_hive_dir, ready_ids_before[0])
        expired_task.status = "claimed"
        expired_task.owner = "codex"
        expired_task.claimed_until = "2000-01-01T00:00:00Z"
        save_task(temp_hive_dir, expired_task)

        active_task = get_task(temp_hive_dir, ready_ids_before[1])
        active_task.status = "claimed"
        active_task.owner = "codex"
        active_task.claimed_until = "2099-01-01T00:00:00Z"
        save_task(temp_hive_dir, active_task)

        db_path = rebuild_cache(temp_hive_dir)
        connection = sqlite3.connect(db_path)
        try:
            ready_ids = [row[0] for row in connection.execute("SELECT id FROM ready_tasks")]
            active_claim_ids = [row[0] for row in connection.execute("SELECT task_id FROM active_claims")]
        finally:
            connection.close()

        assert expired_task.id in ready_ids
        assert expired_task.id not in active_claim_ids
        assert active_task.id not in ready_ids
        assert active_task.id in active_claim_ids

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

    def test_cli_search_returns_json_hits(self, temp_hive_dir, temp_project, capsys):
        """Workspace search should emit stable JSON results."""
        migrate_v1_to_v2(temp_hive_dir)
        task_id = ready_tasks(temp_hive_dir)[0]["id"]
        task = get_task(temp_hive_dir, task_id)
        task.summary_md = "Search token: crimson-parakeet"
        save_task(temp_hive_dir, task)
        observe_project(temp_hive_dir, note="crimson-parakeet memory")
        reflect_project(temp_hive_dir)
        rebuild_cache(temp_hive_dir)

        exit_code = hive_main(["--path", temp_hive_dir, "--json", "search", "crimson-parakeet"])
        captured = capsys.readouterr()

        assert exit_code == 0
        payload = json.loads(captured.out)
        assert payload["version"]
        assert any(result["kind"] == "task" for result in payload["results"])
        assert any(result["kind"] == "memory" for result in payload["results"])


class TestHiveV2Scheduler:
    """Tests for scheduler summaries."""

    def test_project_summary_counts_expired_claims_as_ready(self, temp_hive_dir, temp_project):
        """Expired claimed tasks should align between ready queue and project summary."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        baseline = next(item for item in project_summary(temp_hive_dir) if item["id"] == project.id)
        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        task = get_task(temp_hive_dir, task_id)
        task.status = "claimed"
        task.owner = "codex"
        task.claimed_until = "2000-01-01T00:00:00Z"
        save_task(temp_hive_dir, task)

        summary = next(item for item in project_summary(temp_hive_dir) if item["id"] == project.id)
        assert summary["ready"] == baseline["ready"]


class TestHiveV2Search:
    """Tests for the workspace search surface."""

    def test_search_workspace_returns_workspace_hits(self, temp_hive_dir, temp_project):
        """Search should surface task and memory content from the cache-backed workspace corpus."""
        migrate_v1_to_v2(temp_hive_dir)
        task_id = ready_tasks(temp_hive_dir)[0]["id"]
        task = get_task(temp_hive_dir, task_id)
        task.summary_md = "Unique task token: amber-kestrel"
        save_task(temp_hive_dir, task)
        observe_project(temp_hive_dir, note="amber-kestrel memory")
        reflect_project(temp_hive_dir)
        rebuild_cache(temp_hive_dir)

        results = search_workspace(temp_hive_dir, "amber-kestrel", scopes=["workspace"], limit=10)
        kinds = {item["kind"] for item in results}
        assert "task" in kinds
        assert "memory" in kinds

    def test_search_workspace_returns_api_example_and_project_hits(self, temp_hive_dir, temp_project):
        """Search should cover API docs, example files, and project summaries."""
        migrate_v1_to_v2(temp_hive_dir)

        results = search_workspace(temp_hive_dir, "ready", scopes=["api", "examples", "project"], limit=20)
        kinds = {item["kind"] for item in results}
        assert "command" in kinds
        assert "example" in kinds
        assert "project" in kinds


class TestHiveV2Execute:
    """Tests for the bounded execute surface."""

    def test_cli_execute_python_can_compose_multiple_hive_calls(self, temp_hive_dir, temp_project, capsys):
        """Execute should expose a typed Hive client inside bounded Python."""
        migrate_v1_to_v2(temp_hive_dir)
        exit_code = hive_main(
            [
                "--path",
                temp_hive_dir,
                "--json",
                "execute",
                "--language",
                "python",
                "--code",
                (
                    "result = {"
                    "'projects': len(hive.project.list()), "
                    "'next': hive.scheduler.next(), "
                    "'ready': len(hive.task.ready({'limit': 5}))"
                    "}"
                ),
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        payload = json.loads(captured.out)
        assert payload["ok"] is True
        assert payload["value"]["projects"] >= 1
        assert payload["value"]["next"]["id"]
        assert payload["value"]["ready"] >= 1

    def test_cli_execute_python_timeout_is_reported(self, temp_hive_dir, temp_project, capsys):
        """Execute should fail cleanly when the subprocess exceeds its timeout."""
        migrate_v1_to_v2(temp_hive_dir)
        exit_code = hive_main(
            [
                "--path",
                temp_hive_dir,
                "--json",
                "execute",
                "--language",
                "python",
                "--timeout-seconds",
                "1",
                "--code",
                "import time\ntime.sleep(2)\nresult = {'ok': True}",
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        payload = json.loads(captured.out)
        assert payload["ok"] is False
        assert payload["timed_out"] is True

    def test_cli_execute_rejects_unsupported_language(self, temp_hive_dir, temp_project, capsys):
        """Execute should fail clearly for languages outside the MVP surface."""
        migrate_v1_to_v2(temp_hive_dir)
        exit_code = hive_main(
            [
                "--path",
                temp_hive_dir,
                "--json",
                "execute",
                "--language",
                "ts",
                "--code",
                "export default async () => ({ ok: true })",
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        payload = json.loads(captured.out)
        assert payload["ok"] is False
        assert "Python only" in payload["error"]

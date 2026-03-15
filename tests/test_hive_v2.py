"""Tests for the Hive v2 substrate and CLI."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import sqlite3

import pytest

from src.hive.cli.main import main as hive_main
from src.hive.codemode.execute import MAX_EXECUTE_BYTES
from src.hive.memory import observe_project, reflect_project, search_memory, startup_context
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
from src.hive.store.layout import ensure_layout, global_memory_dir, tasks_dir
from src.hive.store.projects import discover_projects
from src.hive.store.task_files import get_task, link_tasks, list_tasks, save_task

hive_cli_main = importlib.import_module("src.hive.cli.main")


def _program_markdown(
    command: str,
    auto_close: bool = False,
    allow_commands: list[str] | None = None,
    allow_paths: list[str] | None = None,
    deny_paths: list[str] | None = None,
    review_paths: list[str] | None = None,
    escalation_paths: list[str] | None = None,
    escalation_commands: list[str] | None = None,
    executor: str = "local",
) -> str:
    allowed = allow_commands if allow_commands is not None else [command]
    allowed_paths = allow_paths if allow_paths is not None else ["src/**", "tests/**", "docs/**"]
    denied_paths = deny_paths if deny_paths is not None else []
    review_required = review_paths if review_paths is not None else []
    escalate_when_paths = escalation_paths if escalation_paths is not None else []
    escalate_when_commands = escalation_commands if escalation_commands is not None else []
    allow_block = (
        "\n" + "\n".join(f"    - {json.dumps(item)}" for item in allowed) if allowed else " []"
    )
    allow_paths_block = "\n" + "\n".join(f"    - {json.dumps(item)}" for item in allowed_paths)
    deny_paths_block = (
        "\n" + "\n".join(f"    - {json.dumps(item)}" for item in denied_paths)
        if denied_paths
        else " []"
    )
    review_paths_block = (
        "\n" + "\n".join(f"    - {json.dumps(item)}" for item in review_required)
        if review_required
        else " []"
    )
    escalation_paths_block = (
        "\n" + "\n".join(f"    - {json.dumps(item)}" for item in escalate_when_paths)
        if escalate_when_paths
        else " []"
    )
    escalation_commands_block = (
        "\n" + "\n".join(f"    - {json.dumps(item)}" for item in escalate_when_commands)
        if escalate_when_commands
        else " []"
    )
    return f"""---
program_version: 1
mode: workflow
default_executor: {executor}
budgets:
  max_wall_clock_minutes: 30
  max_steps: 25
  max_tokens: 20000
  max_cost_usd: 0.0
paths:
  allow:{allow_paths_block}
  deny:{deny_paths_block}
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
  review_required_when_paths_match:{review_paths_block}
  auto_close_task: {str(auto_close).lower()}
escalation:
  when_paths_match:{escalation_paths_block}
  when_commands_match:{escalation_commands_block}
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
        assert "## Imported Legacy Tasks" in agency_content

    def test_migration_dry_run_does_not_create_task_files(self, temp_hive_dir):
        """Dry-run migration should report without mutating task storage."""
        report = migrate_v1_to_v2(temp_hive_dir, dry_run=True)
        assert report.to_dict()["ok"] is True
        assert not list(tasks_dir(temp_hive_dir).glob("task_*.md"))

    def test_migration_rewrite_replaces_legacy_checklist_section(self, temp_hive_dir, temp_project):
        """Rewrite mode should replace legacy checklists after import."""
        report = migrate_v1_to_v2(temp_hive_dir, rewrite=True)
        agency_content = Path(temp_project).read_text(encoding="utf-8")

        assert report.to_dict()["tasks_imported"] >= 3
        assert "## Imported Legacy Tasks" in agency_content
        assert "- [ ] Task 1" not in agency_content
        assert "generated task rollup" in agency_content.lower()

    def test_migration_infers_dependency_duplicate_and_supersedes_edges(self, temp_hive_dir):
        """Explicit relation notes should become canonical task edges."""
        agency_path = Path(temp_hive_dir) / "projects" / "relations" / "AGENCY.md"
        agency_path.parent.mkdir(parents=True, exist_ok=True)
        agency_path.write_text(
            """---
project_id: relations
status: active
priority: high
---
# Relations Project

## Tasks
- [ ] Build foundation
- [ ] Ship docs
  depends on Build foundation
- [ ] Legacy docs
  duplicate of Ship docs
- [ ] Replacement docs
  supersedes Legacy docs
""",
            encoding="utf-8",
        )

        report = migrate_v1_to_v2(temp_hive_dir)
        tasks = {
            task.title: task for task in list_tasks(temp_hive_dir) if task.project_id == "relations"
        }

        assert report.edges_inferred == 3
        assert tasks["Build foundation"].edges["blocks"] == [tasks["Ship docs"].id]
        assert tasks["Ship docs"].edges["duplicates"] == [tasks["Legacy docs"].id]
        assert tasks["Replacement docs"].edges["supersedes"] == [tasks["Legacy docs"].id]
        assert tasks["Ship docs"].status == "blocked"

    def test_migration_infers_dependency_synonyms(self, temp_hive_dir):
        """Relation synonym phrases should map to dependency edges."""
        agency_path = Path(temp_hive_dir) / "projects" / "dependency-synonyms" / "AGENCY.md"
        agency_path.parent.mkdir(parents=True, exist_ok=True)
        agency_path.write_text(
            """---
project_id: dependency-synonyms
status: active
priority: high
---
# Dependency Synonyms

## Tasks
- [ ] Shared foundation
- [ ] Review docs
  blocked by Shared foundation
- [ ] Publish docs
  requires Review docs
""",
            encoding="utf-8",
        )

        report = migrate_v1_to_v2(temp_hive_dir)
        tasks = {
            task.title: task
            for task in list_tasks(temp_hive_dir)
            if task.project_id == "dependency-synonyms"
        }

        assert report.edges_inferred == 2
        assert tasks["Shared foundation"].edges["blocks"] == [tasks["Review docs"].id]
        assert tasks["Review docs"].edges["blocks"] == [tasks["Publish docs"].id]
        assert tasks["Review docs"].status == "blocked"
        assert tasks["Publish docs"].status == "blocked"

    def test_migration_warns_on_ambiguous_relation_targets(self, temp_hive_dir):
        """Ambiguous relation targets should warn and fall back to proposed tasks."""
        agency_path = Path(temp_hive_dir) / "projects" / "ambiguous" / "AGENCY.md"
        agency_path.parent.mkdir(parents=True, exist_ok=True)
        agency_path.write_text(
            """---
project_id: ambiguous
status: active
priority: medium
---
# Ambiguous Project

## Tasks
- [ ] Shared dependency
- [ ] Shared dependency
- [ ] Waiting task
  depends on Shared dependency
""",
            encoding="utf-8",
        )

        report = migrate_v1_to_v2(temp_hive_dir)
        result = report.to_dict()
        tasks = [task for task in list_tasks(temp_hive_dir) if task.project_id == "ambiguous"]
        waiting_task = next(task for task in tasks if task.title == "Waiting task")

        assert any(
            "Ambiguous relation target 'Shared dependency'" in warning["message"]
            for warning in result["warnings"]
        )
        assert waiting_task.status == "proposed"

    def test_migration_warns_on_missing_relation_targets(self, temp_hive_dir):
        """Missing relation targets should warn and fall back to proposed tasks."""
        agency_path = Path(temp_hive_dir) / "projects" / "missing-relation" / "AGENCY.md"
        agency_path.parent.mkdir(parents=True, exist_ok=True)
        agency_path.write_text(
            """---
project_id: missing-relation
status: active
priority: medium
---
# Missing Relation Project

## Tasks
- [ ] Waiting task
  depends on Missing dependency
""",
            encoding="utf-8",
        )

        report = migrate_v1_to_v2(temp_hive_dir)
        result = report.to_dict()
        task = next(
            task for task in list_tasks(temp_hive_dir) if task.project_id == "missing-relation"
        )

        assert any(
            "Could not confidently infer relation target 'Missing dependency'" in warning["message"]
            for warning in result["warnings"]
        )
        assert task.status == "proposed"

    def test_migration_warns_on_unindented_relation_notes(self, temp_hive_dir):
        """Top-level relation hints should warn when they are not indented under a task."""
        agency_path = Path(temp_hive_dir) / "projects" / "inline-relations" / "AGENCY.md"
        agency_path.parent.mkdir(parents=True, exist_ok=True)
        agency_path.write_text(
            """---
project_id: inline-relations
status: active
priority: medium
---
# Inline Relations Project

## Tasks
- [ ] Build foundation
- [ ] Ship docs
depends on Build foundation
""",
            encoding="utf-8",
        )

        report = migrate_v1_to_v2(temp_hive_dir)
        result = report.to_dict()
        tasks = {
            task.title: task
            for task in list_tasks(temp_hive_dir)
            if task.project_id == "inline-relations"
        }

        assert any(
            "Relation hint 'depends on Build foundation' was not indented" in warning["message"]
            for warning in result["warnings"]
        )
        assert tasks["Ship docs"].status == "ready"

    def test_migration_handles_list_dependencies_frontmatter(self, temp_hive_dir):
        """Legacy list-form dependencies should not abort migration."""
        agency_path = Path(temp_hive_dir) / "projects" / "list-dependencies" / "AGENCY.md"
        agency_path.parent.mkdir(parents=True, exist_ok=True)
        agency_path.write_text(
            """---
project_id: list-dependencies
status: active
priority: medium
dependencies:
  - setup
  - review
---
# List Dependencies Project

## Tasks
- [ ] Ship docs
""",
            encoding="utf-8",
        )

        report = migrate_v1_to_v2(temp_hive_dir)
        tasks = [
            task for task in list_tasks(temp_hive_dir) if task.project_id == "list-dependencies"
        ]

        assert report.to_dict()["ok"] is True
        assert len(tasks) == 1
        assert tasks[0].status == "ready"

    def test_migration_keeps_blocked_status_when_one_dependency_resolves(self, temp_hive_dir):
        """A resolved dependency should keep the task blocked even if another target is missing."""
        agency_path = Path(temp_hive_dir) / "projects" / "mixed-dependencies" / "AGENCY.md"
        agency_path.parent.mkdir(parents=True, exist_ok=True)
        agency_path.write_text(
            """---
project_id: mixed-dependencies
status: active
priority: high
---
# Mixed Dependencies Project

## Tasks
- [ ] Build foundation
- [ ] Ship docs
  depends on Build foundation
  depends on Missing dependency
""",
            encoding="utf-8",
        )

        report = migrate_v1_to_v2(temp_hive_dir)
        result = report.to_dict()
        tasks = {
            task.title: task
            for task in list_tasks(temp_hive_dir)
            if task.project_id == "mixed-dependencies"
        }

        assert tasks["Build foundation"].edges["blocks"] == [tasks["Ship docs"].id]
        assert tasks["Ship docs"].status == "blocked"
        assert any(
            "Could not confidently infer relation target 'Missing dependency'" in warning["message"]
            for warning in result["warnings"]
        )

    def test_cli_migrate_supports_rewrite_mode(self, temp_hive_dir, temp_project, capsys):
        """The CLI should execute rewrite migrations without the old placeholder warning."""
        del temp_project
        exit_code = hive_main(
            ["--path", temp_hive_dir, "--json", "migrate", "v1-to-v2", "--rewrite"]
        )
        captured = capsys.readouterr()
        payload = json.loads(captured.out)

        assert exit_code == 0
        assert payload["ok"] is True
        assert payload["rewritten_files"]
        assert "not implemented" not in captured.err


class TestHiveV2Runs:
    """Tests for run engine happy paths."""

    def test_run_start_creates_git_worktree_and_branch(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Run startup should create a linked git worktree with a dedicated branch."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(_program_markdown(command), encoding="utf-8")
        commit_workspace(temp_hive_dir, "prepare run workspace")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)
        worktree = Path(run.worktree_path)
        plan = json.loads(
            (Path(temp_hive_dir) / ".hive" / "runs" / run.id / "plan.json").read_text(
                encoding="utf-8"
            )
        )
        assert worktree.exists()
        assert (worktree / ".git").exists()
        assert plan["branch_name"] == run.branch_name
        assert plan["base_commit"]

    def test_run_start_eval_and_accept_respects_auto_close(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Accepted runs should leave tasks in review when auto_close_task is false."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(
            _program_markdown(command, auto_close=False), encoding="utf-8"
        )
        commit_workspace(temp_hive_dir, "prepare run workspace")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)
        result = eval_run(temp_hive_dir, run.id)
        assert result["run"]["status"] == "evaluating"

        accepted = accept_run(temp_hive_dir, run.id)
        task = get_task(temp_hive_dir, task_id)
        assert accepted["status"] == "accepted"
        assert task.status == "review"

    def test_eval_run_rejects_commands_outside_allow_list(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Evaluators should only run commands explicitly allow-listed in PROGRAM.md."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(
            _program_markdown(command, allow_commands=[]),
            encoding="utf-8",
        )
        commit_workspace(temp_hive_dir, "prepare run workspace")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)
        try:
            eval_run(temp_hive_dir, run.id)
        except ValueError as exc:
            assert "allow-listed" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected evaluator allow-list validation to fail")

    def test_start_run_rejects_terminal_task_statuses(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Runs should not reopen blocked or completed tasks."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        task = get_task(temp_hive_dir, task_id)
        task.status = "done"
        save_task(temp_hive_dir, task)
        commit_workspace(temp_hive_dir, "prepare terminal task")

        try:
            start_run(temp_hive_dir, task_id)
        except ValueError as exc:
            assert "Cannot start run" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected terminal task status to block run creation")

    def test_eval_run_rejects_non_running_statuses(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Evaluators should only run from the running state."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(_program_markdown(command), encoding="utf-8")
        commit_workspace(temp_hive_dir, "prepare run workspace")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)
        eval_run(temp_hive_dir, run.id)

        try:
            eval_run(temp_hive_dir, run.id)
        except ValueError as exc:
            assert "Cannot evaluate run" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected non-running run evaluation to fail")

    def test_accept_run_requires_evaluating_status(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Runs should not be accepted before evaluator execution."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(_program_markdown(command), encoding="utf-8")
        commit_workspace(temp_hive_dir, "prepare run workspace")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)

        try:
            accept_run(temp_hive_dir, run.id)
        except ValueError as exc:
            assert "Cannot accept run" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected accept without evaluation to fail")

    def test_reject_run_rejects_terminal_statuses(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Rejected runs should not overwrite already-finalized outcomes."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(_program_markdown(command), encoding="utf-8")
        commit_workspace(temp_hive_dir, "prepare run workspace")

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

    def test_reject_run_requeues_claimed_task(self, temp_hive_dir, temp_project, commit_workspace):
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
        commit_workspace(temp_hive_dir, "prepare claimed run workspace")

        run = start_run(temp_hive_dir, task_id)
        rejected = reject_run(temp_hive_dir, run.id, reason="retry")
        reloaded = get_task(temp_hive_dir, task_id)
        ready_ids = [item["id"] for item in ready_tasks(temp_hive_dir, project_id=project.id)]

        assert rejected["status"] == "rejected"
        assert reloaded.status == "ready"
        assert reloaded.owner is None
        assert reloaded.claimed_until is None
        assert task_id in ready_ids

    def test_escalate_run_rejects_terminal_statuses(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Escalation should not reopen finalized runs or tasks."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(_program_markdown(command), encoding="utf-8")
        commit_workspace(temp_hive_dir, "prepare run workspace")

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

    def test_eval_run_captures_patch_and_command_log(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Evaluating a run should persist patch and command-log artifacts."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(_program_markdown(command), encoding="utf-8")
        commit_workspace(temp_hive_dir, "prepare run workspace")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)
        (Path(run.worktree_path) / "src" / "generated.py").parent.mkdir(parents=True, exist_ok=True)
        (Path(run.worktree_path) / "src" / "generated.py").write_text(
            "print('hello from run')\n",
            encoding="utf-8",
        )

        result = eval_run(temp_hive_dir, run.id)
        metadata = result["run"]["metadata_json"]
        patch = Path(result["run"]["patch_path"]).read_text(encoding="utf-8")
        command_log = Path(result["run"]["command_log_path"]).read_text(encoding="utf-8")

        assert "src/generated.py" in metadata["touched_paths"]
        assert "generated.py" in patch
        assert '"step_type": "eval"' in command_log
        assert metadata["command_count"] == 1

    def test_accept_run_blocks_paths_requiring_review(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Promotion should stop when touched paths trigger manual review rules."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(
            _program_markdown(command, review_paths=["src/**"]),
            encoding="utf-8",
        )
        commit_workspace(temp_hive_dir, "prepare run workspace")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)
        (Path(run.worktree_path) / "src" / "needs_review.py").parent.mkdir(
            parents=True, exist_ok=True
        )
        (Path(run.worktree_path) / "src" / "needs_review.py").write_text(
            "print('review')\n",
            encoding="utf-8",
        )

        result = eval_run(temp_hive_dir, run.id)
        try:
            accept_run(temp_hive_dir, run.id)
        except ValueError as exc:
            assert "requires review" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected review-gated promotion to fail")

        assert result["promotion_decision"]["decision"] == "escalate"

    def test_accept_run_allows_nested_paths_matching_program_globs(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Recursive path policies should match nested files on Python 3.11."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(
            _program_markdown(command, allow_paths=["src/**"]),
            encoding="utf-8",
        )
        commit_workspace(temp_hive_dir, "prepare nested path run workspace")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)
        nested_path = Path(run.worktree_path) / "src" / "hive" / "nested.py"
        nested_path.parent.mkdir(parents=True, exist_ok=True)
        nested_path.write_text("print('nested')\n", encoding="utf-8")

        result = eval_run(temp_hive_dir, run.id)
        accepted = accept_run(temp_hive_dir, run.id)

        assert "src/hive/nested.py" in result["run"]["metadata_json"]["touched_paths"]
        assert accepted["status"] == "accepted"

    def test_eval_run_uses_executor_stub_for_github_actions(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """The GitHub Actions executor should exist as a stubbed interface point."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(
            _program_markdown(command, executor="github-actions"),
            encoding="utf-8",
        )
        commit_workspace(temp_hive_dir, "prepare run workspace")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)

        try:
            eval_run(temp_hive_dir, run.id)
        except NotImplementedError as exc:
            assert "stub" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("Expected github-actions executor stub to raise")

    def test_cache_rebuild_populates_run_steps_from_command_log(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Command-log entries should populate the derived run_steps cache table."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(_program_markdown(command), encoding="utf-8")
        commit_workspace(temp_hive_dir, "prepare run workspace")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)
        eval_run(temp_hive_dir, run.id)

        db_path = rebuild_cache(temp_hive_dir)
        connection = sqlite3.connect(db_path)
        try:
            rows = list(
                connection.execute("SELECT run_id, step_type, status FROM run_steps ORDER BY seq")
            )
        finally:
            connection.close()

        assert (run.id, "eval", "succeeded") in rows


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

        context = startup_context(
            temp_hive_dir, project_id=project.id, profile="light", query="migration"
        )
        assert context["project_id"] == project.id
        assert any(section["name"] == "project-profile" for section in context["sections"])

    def test_memory_global_scope_merges_into_startup_context(
        self, temp_hive_dir, temp_project, monkeypatch
    ):
        """Startup context should merge optional user-global memory when present."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        monkeypatch.setenv("XDG_DATA_HOME", str(Path(temp_hive_dir) / ".xdg"))

        observe_project(temp_hive_dir, note="project continuity note")
        reflect_project(temp_hive_dir)
        observe_project(temp_hive_dir, note="global-firefly continuity note", scope="global")
        reflect_project(temp_hive_dir, scope="global")

        context = startup_context(
            temp_hive_dir,
            project_id=project.id,
            profile="default",
            query="global-firefly",
        )

        assert (global_memory_dir() / "profile.md").exists()
        assert any(section["name"] == "global-profile" for section in context["sections"])
        assert any(hit["scope"] == "global" for hit in context["search_hits"])

    def test_memory_global_search_reads_nested_markdown_files(
        self, temp_hive_dir, temp_project, monkeypatch
    ):
        """Global memory search should recurse into nested directories."""
        migrate_v1_to_v2(temp_hive_dir)
        monkeypatch.setenv("XDG_DATA_HOME", str(Path(temp_hive_dir) / ".xdg"))
        nested_dir = global_memory_dir() / "work"
        nested_dir.mkdir(parents=True, exist_ok=True)
        (nested_dir / "notes.md").write_text("nested-aurora memory note", encoding="utf-8")

        results = search_memory(temp_hive_dir, "nested-aurora", scope="global", limit=8)

        assert any(hit["scope"] == "global" for hit in results)
        assert any(str(hit["title"]).endswith("work/notes.md") for hit in results)

    def test_memory_search_and_context_include_recent_accepted_runs(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Memory search and startup context should include accepted run summaries."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(
            _program_markdown(command, auto_close=False),
            encoding="utf-8",
        )
        commit_workspace(temp_hive_dir, "prepare memory run workspace")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)
        eval_run(temp_hive_dir, run.id)
        accept_run(temp_hive_dir, run.id)
        summary_path = Path(run.summary_path)
        summary_path.write_text("# Summary\n\naccepted-orchid continuity\n", encoding="utf-8")
        rebuild_cache(temp_hive_dir)

        results = startup_context(
            temp_hive_dir,
            project_id=project.id,
            profile="default",
            task_id=task_id,
            query="accepted-orchid",
        )
        memory_hits = search_memory(
            temp_hive_dir,
            "accepted-orchid",
            scope="all",
            project_id=project.id,
            task_id=task_id,
            limit=8,
        )

        assert any(hit["kind"] == "run_summary" for hit in results["search_hits"])
        assert any(run_summary["id"] == run.id for run_summary in results["recent_runs"])
        assert any(hit["kind"] == "run_summary" for hit in memory_hits)

    def test_memory_search_and_context_resolve_relative_run_summary_paths(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Accepted run summaries should load when metadata stores relative artifact paths."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(
            _program_markdown(command, auto_close=False),
            encoding="utf-8",
        )
        commit_workspace(temp_hive_dir, "prepare relative summary run workspace")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)
        eval_run(temp_hive_dir, run.id)
        accept_run(temp_hive_dir, run.id)
        summary_path = Path(run.summary_path)
        summary_path.write_text("# Summary\n\nrelative-orchid continuity\n", encoding="utf-8")
        metadata_path = Path(temp_hive_dir) / ".hive" / "runs" / run.id / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["summary_path"] = str(Path(".hive") / "runs" / run.id / "summary.md")
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        rebuild_cache(temp_hive_dir)

        results = startup_context(
            temp_hive_dir,
            project_id=project.id,
            profile="default",
            query="relative-orchid",
        )
        memory_hits = search_memory(
            temp_hive_dir,
            "relative-orchid",
            scope="all",
            project_id=project.id,
            limit=8,
        )

        assert any(run_summary["id"] == run.id for run_summary in results["recent_runs"])
        assert any(hit["kind"] == "run_summary" for hit in memory_hits)

    def test_recent_runs_sort_by_acceptance_time(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Startup context should order recent runs by acceptance time, not run ID."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(
            _program_markdown(command, auto_close=False),
            encoding="utf-8",
        )
        commit_workspace(temp_hive_dir, "prepare acceptance order workspace")

        ready_ids = [item["id"] for item in ready_tasks(temp_hive_dir, project_id=project.id)]
        first_run = start_run(temp_hive_dir, ready_ids[0])
        eval_run(temp_hive_dir, first_run.id)
        accept_run(temp_hive_dir, first_run.id)

        commit_workspace(temp_hive_dir, "snapshot first accepted run")
        project = discover_projects(temp_hive_dir)[0]
        project.program_path.write_text(
            _program_markdown(command, auto_close=False),
            encoding="utf-8",
        )
        commit_workspace(temp_hive_dir, "restore program after snapshot")

        second_ready_ids = [
            item["id"]
            for item in ready_tasks(temp_hive_dir, project_id=project.id)
            if item["id"] != ready_ids[0]
        ]
        second_run = start_run(temp_hive_dir, second_ready_ids[0])
        eval_run(temp_hive_dir, second_run.id)
        accept_run(temp_hive_dir, second_run.id)

        first_metadata_path = (
            Path(temp_hive_dir) / ".hive" / "runs" / first_run.id / "metadata.json"
        )
        first_metadata = json.loads(first_metadata_path.read_text(encoding="utf-8"))
        first_metadata["finished_at"] = "2099-01-01T00:00:00Z"
        first_metadata_path.write_text(
            json.dumps(first_metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        results = startup_context(
            temp_hive_dir,
            project_id=project.id,
            profile="default",
            query="ok",
        )

        assert results["recent_runs"][0]["id"] == first_run.id

    def test_workspace_search_indexes_relative_run_summary_paths(
        self, temp_hive_dir, temp_project, commit_workspace
    ):
        """Workspace search should index run summaries even when metadata uses relative paths."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(
            _program_markdown(command, auto_close=False),
            encoding="utf-8",
        )
        commit_workspace(temp_hive_dir, "prepare workspace search run workspace")

        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        run = start_run(temp_hive_dir, task_id)
        eval_run(temp_hive_dir, run.id)
        accept_run(temp_hive_dir, run.id)
        summary_path = Path(run.summary_path)
        summary_path.write_text("# Summary\n\ncache-relative-swan note\n", encoding="utf-8")
        metadata_path = Path(temp_hive_dir) / ".hive" / "runs" / run.id / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["summary_path"] = str(Path(".hive") / "runs" / run.id / "summary.md")
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        rebuild_cache(temp_hive_dir)

        results = search_workspace(
            temp_hive_dir, "cache-relative-swan", scopes=["workspace"], limit=10
        )

        assert any(hit["kind"] == "run_summary" for hit in results)

    def test_cache_rebuild_keeps_memory_docs_unique_per_scope_key(
        self, temp_hive_dir, temp_project
    ):
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
            kinds = list(
                connection.execute("SELECT scope_key, kind FROM memory_docs ORDER BY kind")
            )
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

    def test_cli_version_flag_prints_package_version(self, capsys):
        """The global version flag should expose the installed CLI version."""
        with pytest.raises(SystemExit) as excinfo:
            hive_main(["--version"])
        captured = capsys.readouterr()

        assert excinfo.value.code == 0
        assert captured.out.strip().startswith("hive ")

    def test_cli_init_bootstraps_workspace_files(self, tmp_path, capsys):
        """Init should create a usable workspace, projections, and cache."""
        workspace = tmp_path / "fresh-hive"

        exit_code = hive_main(["--path", str(workspace), "--json", "init"])
        captured = capsys.readouterr()

        assert exit_code == 0
        payload = json.loads(captured.out)
        assert payload["created_files"]
        assert ".hive/README.md" in payload["created_files"]
        assert "AGENTS.md" in payload["created_files"]
        assert "GLOBAL.md" in payload["created_files"]
        assert ".gitignore" in payload["created_files"]
        assert (workspace / ".hive" / "cache" / "index.sqlite").exists()
        assert GLOBAL_BEGIN in (workspace / "GLOBAL.md").read_text(encoding="utf-8")
        assert "<!-- hive:begin compatibility -->" in (workspace / "AGENTS.md").read_text(
            encoding="utf-8"
        )
        assert any("hive quickstart demo" in step for step in payload["next_steps"])

    def test_cli_doctor_guides_empty_workspace_and_first_project(self, tmp_path, capsys):
        """Doctor should recommend bootstrap and first-project steps as the workspace evolves."""
        workspace = tmp_path / "doctor-hive"
        workspace.mkdir(parents=True, exist_ok=True)

        exit_code = hive_main(["--path", str(workspace), "--json", "doctor"])
        captured = capsys.readouterr()
        payload = json.loads(captured.out)

        assert exit_code == 0
        assert any("hive quickstart demo" in step for step in payload["next_steps"])
        assert any("hive init --json" in step for step in payload["next_steps"])

        hive_main(["--path", str(workspace), "--json", "init"])
        capsys.readouterr()
        hive_main(
            [
                "--path",
                str(workspace),
                "--json",
                "project",
                "create",
                "launch/demo",
                "--title",
                "Launch Demo",
            ]
        )
        capsys.readouterr()

        exit_code = hive_main(["--path", str(workspace), "--json", "doctor"])
        captured = capsys.readouterr()
        payload = json.loads(captured.out)

        assert exit_code == 0
        assert any(
            "hive task create --project-id launch-demo" in step for step in payload["next_steps"]
        )

    def test_cli_quickstart_bootstraps_first_project_and_task_chain(self, tmp_path, capsys):
        """Quickstart should leave a new user with a project and a meaningful ready queue."""
        workspace = tmp_path / "quickstart-hive"

        exit_code = hive_main(
            [
                "--path",
                str(workspace),
                "--json",
                "quickstart",
                "launch/demo",
                "--title",
                "Launch Demo",
                "--objective",
                "Ship the launch-ready Hive demo workspace.",
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        payload = json.loads(captured.out)
        assert payload["project"]["id"] == "launch-demo"
        assert Path(payload["project"]["path"]).exists()
        assert Path(payload["project"]["program_path"]).exists()
        assert len(payload["tasks"]) == 3
        assert payload["tasks"][0]["status"] == "ready"
        assert payload["tasks"][1]["status"] == "proposed"
        assert payload["tasks"][2]["status"] == "proposed"
        ready = ready_tasks(workspace, project_id="launch-demo")
        assert [item["title"] for item in ready] == [
            "Define the first thin slice for Launch Demo"
        ]
        agency_content = Path(payload["project"]["path"]).read_text(encoding="utf-8")
        assert "Ship the launch-ready Hive demo workspace." in agency_content
        assert any("hive task claim" in step for step in payload["next_steps"])

    def test_cli_quickstart_rejects_existing_project(self, tmp_path, capsys):
        """Quickstart should fail cleanly if the starter slug already exists."""
        workspace = tmp_path / "quickstart-duplicate"

        first_exit = hive_main(["--path", str(workspace), "--json", "quickstart"])
        capsys.readouterr()
        assert first_exit == 0

        second_exit = hive_main(["--path", str(workspace), "--json", "quickstart"])
        captured = capsys.readouterr()
        payload = json.loads(captured.out)

        assert second_exit == 1
        assert payload["ok"] is False
        assert "already exists" in payload["error"]

    def test_cli_quickstart_fails_cleanly_without_starter_tasks(
        self, tmp_path, capsys, monkeypatch
    ):
        """Quickstart should surface scaffold failures as structured JSON errors."""
        workspace = tmp_path / "quickstart-empty"

        monkeypatch.setattr(hive_cli_main, "starter_task_specs", lambda _title: [])

        exit_code = hive_main(["--path", str(workspace), "--json", "quickstart"])
        captured = capsys.readouterr()
        payload = json.loads(captured.out)

        assert exit_code == 1
        assert payload["ok"] is False
        assert payload["error"] == "Quickstart could not create starter tasks"

    def test_cli_project_create_scaffolds_agency_and_program(self, tmp_path, capsys):
        """Project creation should normalize slugs and scaffold narrative and policy files."""
        workspace = tmp_path / "scaffold-hive"
        hive_main(["--path", str(workspace), "--json", "init"])
        capsys.readouterr()

        exit_code = hive_main(
            [
                "--path",
                str(workspace),
                "--json",
                "project",
                "create",
                "Launch Ready / Website",
                "--title",
                "Launch Ready Website",
                "--objective",
                "Ship the public launch surface for Hive 2.0.",
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        payload = json.loads(captured.out)
        agency_path = Path(payload["project"]["path"])
        program_path = Path(payload["project"]["program_path"])

        assert payload["project"]["id"] == "launch-ready/website".replace("/", "-")
        assert agency_path.exists()
        assert program_path.exists()
        agency_content = agency_path.read_text(encoding="utf-8")
        assert "Ship the public launch surface for Hive 2.0." in agency_content
        assert TASK_BEGIN in agency_content
        assert RUN_BEGIN in agency_content
        assert "program_version: 1" in program_path.read_text(encoding="utf-8")
        assert any(
            "hive task create --project-id launch-ready-website" in step
            for step in payload["next_steps"]
        )

    def test_cli_project_create_whitespace_project_id_falls_back_to_slug(self, tmp_path, capsys):
        """Whitespace-only project IDs should fall back to the normalized slug-derived ID."""
        workspace = tmp_path / "whitespace-project-id"
        hive_main(["--path", str(workspace), "--json", "init"])
        capsys.readouterr()

        exit_code = hive_main(
            [
                "--path",
                str(workspace),
                "--json",
                "project",
                "create",
                "Launch Ready / API",
                "--project-id",
                "   ",
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        payload = json.loads(captured.out)
        assert payload["project"]["id"] == "launch-ready-api"

    def test_cli_project_create_rejects_duplicate_project_ids(self, tmp_path, capsys):
        """Project creation should reject a project ID that is already in use."""
        workspace = tmp_path / "duplicate-project-id"
        hive_main(["--path", str(workspace), "--json", "init"])
        capsys.readouterr()

        first_exit = hive_main(
            [
                "--path",
                str(workspace),
                "--json",
                "project",
                "create",
                "foo-bar",
            ]
        )
        capsys.readouterr()
        assert first_exit == 0

        second_exit = hive_main(
            [
                "--path",
                str(workspace),
                "--json",
                "project",
                "create",
                "foo/bar",
            ]
        )
        captured = capsys.readouterr()

        assert second_exit == 1
        payload = json.loads(captured.out)
        assert payload["ok"] is False
        assert "already exists" in payload["error"]
        assert not (workspace / "projects" / "foo" / "bar" / "AGENCY.md").exists()

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

    def test_cache_ready_and_active_claim_views_handle_iso_expiry(
        self, temp_hive_dir, temp_project
    ):
        """SQLite views should parse ISO timestamps when deciding claim expiry."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        ready_ids_before = [
            item["id"] for item in ready_tasks(temp_hive_dir, project_id=project.id)
        ]

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
            active_claim_ids = [
                row[0] for row in connection.execute("SELECT task_id FROM active_claims")
            ]
        finally:
            connection.close()

        assert expired_task.id in ready_ids
        assert expired_task.id not in active_claim_ids
        assert active_task.id not in ready_ids
        assert active_task.id in active_claim_ids

    def test_cli_run_show_returns_metadata(
        self, temp_hive_dir, temp_project, commit_workspace, capsys
    ):
        """Run show should surface persisted metadata after start."""
        migrate_v1_to_v2(temp_hive_dir)
        project = discover_projects(temp_hive_dir)[0]
        command = "python -c \"print('ok')\""
        project.program_path.write_text(_program_markdown(command), encoding="utf-8")
        commit_workspace(temp_hive_dir, "prepare run workspace")
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

    def test_cli_memory_search_supports_scope_and_task_filters(
        self, temp_hive_dir, temp_project, monkeypatch, capsys
    ):
        """Memory search should accept scope and task-aware query shaping."""
        migrate_v1_to_v2(temp_hive_dir)
        monkeypatch.setenv("XDG_DATA_HOME", str(Path(temp_hive_dir) / ".xdg"))
        project = discover_projects(temp_hive_dir)[0]
        task_id = ready_tasks(temp_hive_dir, project_id=project.id)[0]["id"]
        observe_project(temp_hive_dir, note="global-lantern context", scope="global")
        reflect_project(temp_hive_dir, scope="global")

        exit_code = hive_main(
            [
                "--path",
                temp_hive_dir,
                "--json",
                "memory",
                "search",
                "global-lantern",
                "--scope",
                "global",
                "--project",
                project.id,
                "--task",
                task_id,
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        payload = json.loads(captured.out)
        assert payload["results"]
        assert all(result["scope"] == "global" for result in payload["results"])


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

    def test_search_workspace_rebuilds_missing_cache_on_demand(self, temp_hive_dir, temp_project):
        """Search should rebuild the cache when no derived index exists yet."""
        migrate_v1_to_v2(temp_hive_dir)
        task_id = ready_tasks(temp_hive_dir)[0]["id"]
        task = get_task(temp_hive_dir, task_id)
        task.summary_md = "Unique cold-cache token: ivory-oriole"
        save_task(temp_hive_dir, task)

        cache_path = Path(temp_hive_dir) / ".hive" / "cache" / "index.sqlite"
        if cache_path.exists():
            cache_path.unlink()

        results = search_workspace(temp_hive_dir, "ivory-oriole", scopes=["workspace"], limit=10)
        assert cache_path.exists()
        assert any(item["kind"] == "task" for item in results)

    def test_search_workspace_returns_api_example_and_project_hits(
        self, temp_hive_dir, temp_project
    ):
        """Search should cover API docs, example files, and project summaries."""
        migrate_v1_to_v2(temp_hive_dir)

        results = search_workspace(
            temp_hive_dir, "ready", scopes=["api", "examples", "project"], limit=20
        )
        kinds = {item["kind"] for item in results}
        assert "command" in kinds
        assert "example" in kinds
        assert "project" in kinds

    def test_search_workspace_api_scope_excludes_schema_docs(self, temp_hive_dir, temp_project):
        """Schema docs should only appear when the explicit schema scope is requested."""
        migrate_v1_to_v2(temp_hive_dir)

        api_results = search_workspace(temp_hive_dir, "CREATE TABLE", scopes=["api"], limit=20)
        schema_results = search_workspace(
            temp_hive_dir, "CREATE TABLE", scopes=["schema"], limit=20
        )

        assert all(item["kind"] != "schema" for item in api_results)
        assert any(item["kind"] == "schema" for item in schema_results)


class TestHiveV2Execute:
    """Tests for the bounded execute surface."""

    def test_cli_execute_python_can_compose_multiple_hive_calls(
        self, temp_hive_dir, temp_project, capsys
    ):
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
                "2",
                "--code",
                (
                    "import time\n"
                    "print('hello before timeout', flush=True)\n"
                    "time.sleep(4)\n"
                    "result = {'ok': True}"
                ),
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        payload = json.loads(captured.out)
        assert payload["ok"] is False
        assert payload["timed_out"] is True
        assert payload["stdout"] == "hello before timeout\n"

    def test_cli_execute_python_runtime_exception_is_reported(
        self, temp_hive_dir, temp_project, capsys
    ):
        """Execute should surface runtime exceptions from the sandbox runner."""
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
                "raise RuntimeError('boom')",
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        payload = json.loads(captured.out)
        assert payload["ok"] is False
        assert payload["error"] == "boom"

    def test_cli_execute_rejects_oversized_input_files(self, temp_hive_dir, temp_project, capsys):
        """Execute should reject input files that exceed the CLI size guard."""
        migrate_v1_to_v2(temp_hive_dir)
        code_path = Path(temp_hive_dir) / "oversized-execute.py"
        code_path.write_text("x" * (MAX_EXECUTE_BYTES + 1), encoding="utf-8")

        exit_code = hive_main(
            [
                "--path",
                temp_hive_dir,
                "--json",
                "execute",
                "--language",
                "python",
                "--file",
                str(code_path),
            ]
        )
        captured = capsys.readouterr()

        assert exit_code == 0
        payload = json.loads(captured.out)
        assert payload["ok"] is False
        assert "exceeds" in payload["error"]

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

"""Driver and run-contract tests for Hive 2.2 foundations."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

from tests.conftest import init_git_repo, write_safe_program
from hive.cli.main import main as hive_main
from src.hive.runs.engine import (
    _build_reroute_launch_request,
    _refresh_workspace_state,
    load_run,
    start_run,
)
from src.hive.scheduler.query import ready_tasks
from src.hive.store.task_files import create_task


def _invoke_cli_json(capsys, argv: list[str]) -> dict:
    exit_code = hive_main(argv)
    captured = capsys.readouterr()
    assert exit_code == 0
    return json.loads(captured.out)


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
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
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
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
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
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
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

    def test_same_run_can_move_from_local_to_codex_to_claude_code(self, temp_hive_dir, capsys):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
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
                "Use Codex for stronger repo-wide reasoning",
            ],
        )
        _invoke_cli_json(
            capsys,
            [
                "--path",
                temp_hive_dir,
                "--json",
                "steer",
                "reroute",
                run.id,
                "--driver",
                "claude-code",
                "--reason",
                "Use Claude Code for broader synthesis",
            ],
        )

        metadata = load_run(temp_hive_dir, run.id)
        run_root = Path(temp_hive_dir) / ".hive" / "runs" / run.id
        handles = json.loads((run_root / "driver" / "handles.json").read_text(encoding="utf-8"))
        driver_history = [entry["driver"] for entry in handles["history"]]
        event_types = [
            json.loads(line)["type"]
            for line in (run_root / "events.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        assert metadata["driver"] == "claude-code"
        assert metadata["status"] == "awaiting_input"
        assert handles["active"]["driver"] == "claude-code"
        assert driver_history[0] == "local"
        assert "codex" in driver_history
        assert driver_history[-1] == "claude-code"
        assert (run_root / "transcript" / "normalized.jsonl").exists()
        assert event_types.count("steering.reroute_requested") == 2
        assert event_types.count("steering.rerouted") == 2

    def test_cli_steer_pause_resume_and_cancel_update_run_timeline(self, temp_hive_dir, capsys):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
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

    def test_launch_request_records_actual_base_branch(self, temp_hive_dir, capsys):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(["git", "branch", "-m", "release/demo"], cwd=temp_hive_dir, check=True)

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="codex")
        launch = json.loads(
            (Path(temp_hive_dir) / ".hive" / "runs" / run.id / "launch.json").read_text(
                encoding="utf-8"
            )
        )

        assert launch["workspace"]["base_branch"] == "release/demo"

    def test_reroute_launch_request_preserves_recorded_base_branch(self, temp_hive_dir, capsys):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(["git", "branch", "-m", "release/demo"], cwd=temp_hive_dir, check=True)

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="local")
        metadata = load_run(temp_hive_dir, run.id)
        request = _build_reroute_launch_request(
            Path(temp_hive_dir),
            metadata,
            driver_name="codex",
        )

        assert request.workspace.base_branch == "release/demo"

    def test_reroute_launch_request_handles_null_metadata_json(self, temp_hive_dir, capsys):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(["git", "branch", "-m", "release/demo"], cwd=temp_hive_dir, check=True)

        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="local")
        metadata = load_run(temp_hive_dir, run.id)
        metadata["metadata_json"] = None

        request = _build_reroute_launch_request(
            Path(temp_hive_dir),
            metadata,
            driver_name="codex",
        )

        assert request.workspace.base_branch == "release/demo"
        assert request.metadata["task_title"] == run.task_id

    def test_workspace_refresh_keeps_legacy_patch_inside_run_directory(
        self, temp_hive_dir, capsys
    ):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
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
        metadata = load_run(temp_hive_dir, run.id)
        run_root = Path(temp_hive_dir) / ".hive" / "runs" / run.id
        legacy_patch = run_root / "patch.diff"
        shared_patch = run_root.parent / "patch.diff"
        worktree_docs = Path(metadata["worktree_path"]) / "docs"
        worktree_docs.mkdir(parents=True, exist_ok=True)
        (worktree_docs / "legacy-note.md").write_text(
            "# Legacy patch note\n",
            encoding="utf-8",
        )
        metadata["patch_path"] = str(legacy_patch)

        _refresh_workspace_state(Path(temp_hive_dir), metadata)

        assert legacy_patch.exists()
        assert "legacy-note.md" in legacy_patch.read_text(encoding="utf-8")
        assert not shared_patch.exists()

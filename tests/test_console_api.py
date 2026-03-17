"""Tests for the Hive observe-console API."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

from fastapi.testclient import TestClient

from hive.cli.main import main as hive_main
from src.hive.console.api import app
from src.hive.runs.engine import eval_run, start_run
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


class TestObserveConsoleApi:
    """Smoke tests for the observe-console backend."""

    def test_health_home_runs_and_run_detail_endpoints(self, temp_hive_dir, capsys):
        _init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        _write_safe_program(temp_hive_dir, "demo")
        create_task(temp_hive_dir, "demo", "Review-ready slice", status="ready", priority=1)
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        run = start_run(temp_hive_dir, task_id, driver_name="codex")
        review_task_id = ready_tasks(temp_hive_dir, project_id="demo")[0]["id"]
        local_run = start_run(temp_hive_dir, review_task_id, driver_name="local")
        eval_run(temp_hive_dir, local_run.id)

        client = TestClient(app)
        health = client.get("/health", params={"path": temp_hive_dir})
        home = client.get("/home", params={"path": temp_hive_dir})
        inbox = client.get("/inbox", params={"path": temp_hive_dir})
        runs = client.get("/runs", params={"path": temp_hive_dir, "driver": "codex"})
        detail = client.get(f"/runs/{run.id}", params={"path": temp_hive_dir})

        assert health.status_code == 200
        assert health.json()["projects"] == 1
        assert home.status_code == 200
        assert home.json()["home"]["active_runs"]
        assert home.json()["home"]["inbox"]
        assert inbox.status_code == 200
        assert any(item["kind"] == "run-review" for item in inbox.json()["items"])
        assert any(item["kind"] == "run-input" for item in inbox.json()["items"])
        assert runs.status_code == 200
        assert len(runs.json()["runs"]) == 1
        assert runs.json()["runs"][0]["driver"] == "codex"
        assert detail.status_code == 200
        assert detail.json()["detail"]["run"]["id"] == run.id
        assert detail.json()["detail"]["context_manifest"]["run_id"] == run.id
        assert detail.json()["detail"]["timeline"]
        assert detail.json()["detail"]["artifacts"]["context_manifest"]
        assert "promotion_decision" in detail.json()["detail"]
        assert "driver_metadata" in detail.json()["detail"]
        assert "artifact_preview" in detail.json()["detail"]
        assert "inspector" in detail.json()["detail"]
        assert "context_entries" in detail.json()["detail"]

    def test_run_steer_endpoint_records_typed_steering_history(self, temp_hive_dir, capsys):
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

        client = TestClient(app)
        response = client.post(
            f"/runs/{run.id}/steer",
            params={"path": temp_hive_dir},
            json={"action": "note", "note": "Please keep this slice narrow.", "actor": "operator"},
        )
        detail = client.get(f"/runs/{run.id}", params={"path": temp_hive_dir})

        assert response.status_code == 200
        assert response.json()["run"]["id"] == run.id
        assert detail.status_code == 200
        assert detail.json()["detail"]["steering_history"]
        assert detail.json()["detail"]["steering_history"][-1]["type"] == "steering.note_added"

    def test_projects_campaigns_search_and_console_routes_are_available(self, temp_hive_dir, capsys):
        _init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "onboard", "demo", "--title", "Demo"],
        )
        _invoke_cli_json(
            capsys,
            [
                "--path",
                temp_hive_dir,
                "--json",
                "campaign",
                "create",
                "--title",
                "Launch week",
                "--goal",
                "Ship the first slice",
                "--project-id",
                "demo",
            ],
        )

        client = TestClient(app)
        projects = client.get("/projects", params={"path": temp_hive_dir})
        doctor = client.get("/projects/demo/doctor", params={"path": temp_hive_dir})
        context = client.get("/projects/demo/context", params={"path": temp_hive_dir})
        campaigns = client.get("/campaigns", params={"path": temp_hive_dir})
        campaign_id = campaigns.json()["campaigns"][0]["id"]
        campaign = client.get(f"/campaigns/{campaign_id}", params={"path": temp_hive_dir})
        search = client.get(
            "/search",
            params={"path": temp_hive_dir, "query": "Demo project", "scope": ["api", "project"]},
        )
        console = client.get("/console/")

        assert projects.status_code == 200
        assert projects.json()["projects"][0]["id"] == "demo"
        assert doctor.status_code == 200
        assert "blocked_autonomous_promotion" in doctor.json()["doctor"]
        assert context.status_code == 200
        assert context.json()["project"]["id"] == "demo"
        assert campaigns.status_code == 200
        assert campaigns.json()["campaigns"]
        assert campaign.status_code == 200
        assert campaign.json()["campaign"]["id"] == campaign_id
        assert search.status_code == 200
        assert search.json()["results"]
        assert console.status_code == 200
        assert "index-" in console.text

    def test_console_routes_serve_the_react_bundle_when_assets_exist(self, temp_hive_dir):
        client = TestClient(app)

        root = client.get("/")
        console = client.get("/console/")

        assert root.status_code == 200
        assert console.status_code == 200
        assert "text/html" in console.headers["content-type"]

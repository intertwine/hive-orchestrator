"""Tests for the Hive observe-console API."""

# pylint: disable=missing-function-docstring,unused-argument
# pylint: disable=import-error,no-name-in-module,too-few-public-methods,line-too-long,duplicate-code
# pylint: disable=wrong-import-order

from __future__ import annotations

import json
from pathlib import Path
import subprocess

from tests.conftest import init_git_repo, write_safe_program
from fastapi.testclient import TestClient

from hive.cli.main import main as hive_main
from src.hive.console.api import app
from src.hive.runs.engine import accept_run, eval_run, start_run
from src.hive.scheduler.query import ready_tasks
from src.hive.store.task_files import create_task


def _invoke_cli_json(capsys, argv: list[str]) -> dict:
    exit_code = hive_main(argv)
    captured = capsys.readouterr()
    assert exit_code == 0
    return json.loads(captured.out)


class TestObserveConsoleApi:
    """Smoke tests for the observe-console backend."""

    def test_health_home_runs_and_run_detail_endpoints(self, temp_hive_dir, capsys):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
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
        status = client.get("/status", params={"path": temp_hive_dir})

        assert health.status_code == 200
        assert health.json()["workspace"] == str(Path(temp_hive_dir).resolve())
        assert health.json()["version"] == "2.2.3"
        assert status.status_code == 200
        assert status.json()["projects"] == 1
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
        assert "handoff_manifest" in detail.json()["detail"]["inspector"]
        assert "reroute_bundle" in detail.json()["detail"]["inspector"]

    def test_run_steer_endpoint_records_typed_steering_history(self, temp_hive_dir, capsys):
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

    def test_run_steer_endpoint_allows_note_on_accepted_run(self, temp_hive_dir, capsys):
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
        eval_run(temp_hive_dir, run.id)
        accept_run(temp_hive_dir, run.id)

        client = TestClient(app)
        response = client.post(
            f"/runs/{run.id}/steer",
            params={"path": temp_hive_dir},
            json={"action": "note", "note": "Capture final operator context.", "actor": "operator"},
        )
        detail = client.get(f"/runs/{run.id}", params={"path": temp_hive_dir})

        assert response.status_code == 200
        assert response.json()["run"]["status"] == "accepted"
        assert response.json()["run"]["metadata_json"]["steering_history"][-1]["note"] == (
            "Capture final operator context."
        )
        assert detail.status_code == 200
        assert detail.json()["detail"]["steering_history"][-1]["type"] == "steering.note_added"

    def test_projects_campaigns_search_and_console_routes_are_available(
        self, temp_hive_dir, capsys
    ):
        init_git_repo(temp_hive_dir)
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
        assert campaigns.json()["campaigns"][0]["type"] == "delivery"
        assert campaign.status_code == 200
        assert campaign.json()["campaign"]["id"] == campaign_id
        assert "decision_preview" in campaign.json()
        assert "lane_quotas" in campaign.json()["campaign"]
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

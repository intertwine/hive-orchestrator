"""Release-grade acceptance proofs for Hive 2.2."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import time

from fastapi.testclient import TestClient

from hive.cli.main import main as hive_main
from src.hive.console.api import app
from src.hive.context_bundle import build_context_bundle
from src.hive.control.campaigns import generate_brief
from src.hive.control.portfolio import work_on_task
from src.hive.drivers.types import SteeringRequest
from src.hive.runs.engine import accept_run, eval_run, start_run, steer_run
from src.hive.scheduler.query import ready_tasks
from src.hive.search import search_workspace
from src.hive.store.events import emit_event
from src.hive.store.task_files import create_task
from tests.conftest import init_git_repo, write_safe_program


def _invoke_cli_json(capsys, argv: list[str]) -> dict:
    exit_code = hive_main(argv)
    captured = capsys.readouterr()
    assert exit_code == 0, captured.err
    return json.loads(captured.out)


def _commit_all(root: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def _seed_project(root: Path, capsys, project_id: str, title: str, *, extra_tasks: int = 4) -> None:
    _invoke_cli_json(
        capsys,
        ["--path", str(root), "--json", "onboard", project_id, "--title", title],
    )
    write_safe_program(root, project_id)
    for index in range(1, extra_tasks + 1):
        create_task(
            root,
            project_id,
            f"{title} acceptance task {index}",
            status="ready",
            priority=2,
            acceptance=[f"{title} acceptance task {index} can be governed safely."],
            summary_md=f"Acceptance proof task {index} for {project_id}.",
        )


def _next_task_id(root: Path, project_id: str) -> str:
    return str(ready_tasks(root, project_id=project_id, limit=None)[0]["id"])


def _start_local_accepted_run(root: Path, project_id: str) -> str:
    run = start_run(root, _next_task_id(root, project_id), driver_name="local")
    eval_run(root, run.id)
    accept_run(root, run.id)
    return run.id


def _start_local_review_run(root: Path, project_id: str) -> str:
    run = start_run(root, _next_task_id(root, project_id), driver_name="local")
    eval_run(root, run.id)
    return run.id


def _start_waiting_run(root: Path, project_id: str, driver: str) -> str:
    return start_run(root, _next_task_id(root, project_id), driver_name=driver).id


def _bootstrap_north_star_workspace(temp_hive_dir: str, capsys) -> dict[str, object]:
    """Create a three-project, ten-run workspace for the v2.2 north-star proof."""
    root = Path(temp_hive_dir)
    init_git_repo(root)

    projects = {
        "alpha": "Alpha Control Plane",
        "beta": "Beta Research Ops",
        "gamma": "Gamma Launch Loop",
    }
    for project_id, title in projects.items():
        _seed_project(root, capsys, project_id, title)

    campaign = _invoke_cli_json(
        capsys,
        [
            "--path",
            temp_hive_dir,
            "--json",
            "campaign",
            "create",
            "--title",
            "North Star Daily Brief",
            "--goal",
            "Keep three projects moving under one operator.",
            "--project-id",
            "alpha",
            "--project-id",
            "beta",
            "--project-id",
            "gamma",
            "--driver",
            "local",
        ],
    )

    _commit_all(root, "Bootstrap v2.2 north-star workspace")

    accepted_runs = [
        _start_local_accepted_run(root, "alpha"),
        _start_local_accepted_run(root, "beta"),
    ]
    review_runs = [
        _start_local_review_run(root, "alpha"),
        _start_local_review_run(root, "beta"),
    ]
    codex_waiting = _start_waiting_run(root, "alpha", "codex")
    manual_waiting = _start_waiting_run(root, "alpha", "manual")
    claude_waiting = _start_waiting_run(root, "beta", "claude-code")
    gamma_running = start_run(root, _next_task_id(root, "gamma"), driver_name="local").id

    rerouted = start_run(root, _next_task_id(root, "gamma"), driver_name="local").id
    steer_run(
        root,
        rerouted,
        SteeringRequest(
            action="reroute",
            reason="Need a stronger repo-wide harness pass.",
            note="Switch this run to Codex for broader reasoning.",
            target={"driver": "codex"},
        ),
        actor="console-operator",
    )

    campaign_tick = _invoke_cli_json(
        capsys,
        [
            "--path",
            temp_hive_dir,
            "--json",
            "campaign",
            "tick",
            campaign["campaign"]["id"],
            "--owner",
            "campaign-manager",
        ],
    )
    campaign_run_id = str(campaign_tick["launched_runs"][0]["id"])
    brief = _invoke_cli_json(
        capsys,
        ["--path", temp_hive_dir, "--json", "brief", "daily"],
    )

    return {
        "root": root,
        "campaign_id": str(campaign["campaign"]["id"]),
        "campaign_run_id": campaign_run_id,
        "brief_path": str(brief["path"]),
        "accepted_runs": accepted_runs,
        "review_runs": review_runs,
        "waiting_runs": [codex_waiting, manual_waiting, claude_waiting, rerouted],
        "running_runs": [gamma_running, campaign_run_id],
        "all_runs": accepted_runs
        + review_runs
        + [codex_waiting, manual_waiting, claude_waiting, gamma_running, rerouted, campaign_run_id],
    }


class TestV22Acceptance:
    """Release-grade acceptance and guardrail coverage for Hive 2.2."""

    def test_north_star_console_scenario(self, temp_hive_dir, capsys):
        scenario = _bootstrap_north_star_workspace(temp_hive_dir, capsys)
        client = TestClient(app)

        home = client.get("/home", params={"path": temp_hive_dir})
        inbox = client.get("/inbox", params={"path": temp_hive_dir})
        runs = client.get("/runs", params={"path": temp_hive_dir})
        codex_runs = client.get("/runs", params={"path": temp_hive_dir, "driver": "codex"})
        claude_runs = client.get("/runs", params={"path": temp_hive_dir, "driver": "claude-code"})
        manual_runs = client.get("/runs", params={"path": temp_hive_dir, "driver": "manual"})
        gamma_runs = client.get("/runs", params={"path": temp_hive_dir, "project_id": "gamma"})
        rerouted_detail = client.get(
            f"/runs/{scenario['waiting_runs'][-1]}",
            params={"path": temp_hive_dir},
        )
        campaign = client.get(
            f"/campaigns/{scenario['campaign_id']}",
            params={"path": temp_hive_dir},
        )
        brief_search = client.get(
            "/search",
            params={
                "path": temp_hive_dir,
                "query": "North Star Daily Brief",
                "scope": ["workspace"],
                "limit": 20,
            },
        )

        assert home.status_code == 200
        assert inbox.status_code == 200
        assert runs.status_code == 200
        assert rerouted_detail.status_code == 200
        assert campaign.status_code == 200
        assert brief_search.status_code == 200

        all_runs = runs.json()["runs"]
        assert len(all_runs) == 10
        assert {run["project_id"] for run in all_runs} == {"alpha", "beta", "gamma"}
        assert len(codex_runs.json()["runs"]) == 2
        assert len(claude_runs.json()["runs"]) == 1
        assert len(manual_runs.json()["runs"]) == 1
        assert len(gamma_runs.json()["runs"]) == 3

        inbox_items = inbox.json()["items"]
        assert sum(item["kind"] == "run-review" for item in inbox_items) >= 2
        assert sum(item["kind"] == "run-input" for item in inbox_items) >= 4

        home_payload = home.json()["home"]
        assert len(home_payload["active_runs"]) >= 4
        assert len(home_payload["inbox"]) >= 6
        assert len(home_payload["campaigns"]) == 1
        assert home_payload["recommended_next"] is not None

        rerouted = rerouted_detail.json()["detail"]
        assert rerouted["run"]["driver"] == "codex"
        assert any(
            event["type"] == "steering.rerouted" for event in rerouted["timeline"]
        )
        assert any(
            item["type"] == "steering.rerouted" for item in rerouted["steering_history"]
        )

        campaign_payload = campaign.json()
        assert campaign_payload["campaign"]["id"] == scenario["campaign_id"]
        assert any(
            run["id"] == scenario["campaign_run_id"] for run in campaign_payload["active_runs"]
        )

        search_results = brief_search.json()["results"]
        assert any(".hive/briefs/" in str(item.get("path", "")) for item in search_results)
        assert any(item.get("why") for item in search_results)

        for run_id in scenario["accepted_runs"]:
            detail = client.get(f"/runs/{run_id}", params={"path": temp_hive_dir}).json()["detail"]
            assert detail["run"]["status"] == "accepted"
            assert detail["evaluations"]
            assert detail["promotion_decision"]["decision"] == "accept"
            assert detail["context_manifest"]["run_id"] == run_id
            assert detail["artifacts"]["context_manifest"]

    def test_console_updates_without_manual_sync(self, temp_hive_dir, capsys):
        root = Path(temp_hive_dir)
        init_git_repo(root)
        _seed_project(root, capsys, "demo", "Demo Control Plane", extra_tasks=1)
        _commit_all(root, "Bootstrap sync-proof workspace")

        review_task = _next_task_id(root, "demo")
        run = start_run(root, review_task, driver_name="local")
        client = TestClient(app)

        before = client.get("/inbox", params={"path": temp_hive_dir}).json()["items"]
        eval_run(root, run.id)
        after = client.get("/inbox", params={"path": temp_hive_dir}).json()["items"]
        home = client.get("/home", params={"path": temp_hive_dir}).json()["home"]

        assert not any(item["kind"] == "run-review" for item in before)
        assert any(item["kind"] == "run-review" and item["run_id"] == run.id for item in after)
        assert any(item["kind"] == "run-review" and item["run_id"] == run.id for item in home["inbox"])

    def test_search_collapses_duplicate_task_hits_and_keeps_match_reasons(
        self, temp_hive_dir, capsys
    ):
        root = Path(temp_hive_dir)
        init_git_repo(root)
        _seed_project(root, capsys, "demo", "Demo Search", extra_tasks=0)
        task = create_task(
            root,
            "demo",
            "Polish the inbox board",
            status="ready",
            priority=1,
            acceptance=["Polish the inbox board keeps the operator view readable."],
            summary_md="Polish the inbox board with better filters and explanation copy.",
            notes_md="This inbox board task is repeated in the narrative on purpose.",
        )

        results = search_workspace(root, "Polish the inbox board", scopes=["workspace"], limit=10)
        task_hits = [
            item
            for item in results
            if item["kind"] == "task" and item.get("metadata", {}).get("entity_id") == task.id
        ]

        assert len(task_hits) == 1
        assert task_hits[0]["why"]
        assert len({(item["kind"], item.get("path"), item["title"]) for item in results}) == len(
            results
        )

    def test_guardrail_timings_stay_within_release_thresholds(self, temp_hive_dir, capsys):
        root = Path(temp_hive_dir)
        init_git_repo(root)

        start = time.perf_counter()
        _seed_project(root, capsys, "demo", "Demo Performance", extra_tasks=1)
        _commit_all(root, "Bootstrap performance workspace")
        work = work_on_task(root, project_id="demo", owner="perf-operator")
        onboard_to_run_seconds = time.perf_counter() - start

        run_id = str(work["run"]["id"])
        for index in range(1100):
            emit_event(
                root,
                actor="perf",
                entity_type="workspace",
                entity_id="workspace",
                event_type="portfolio.synthetic",
                source="tests.performance",
                payload={"seq": index},
            )

        client = TestClient(app)

        started = time.perf_counter()
        home = client.get("/home", params={"path": temp_hive_dir})
        home_seconds = time.perf_counter() - started

        started = time.perf_counter()
        detail = client.get(f"/runs/{run_id}", params={"path": temp_hive_dir})
        detail_seconds = time.perf_counter() - started

        started = time.perf_counter()
        context = build_context_bundle(root, project_ref="demo", task_id=str(work["task"]["id"]))
        context_seconds = time.perf_counter() - started

        search_workspace(root, "performance", scopes=["workspace"], limit=5)
        started = time.perf_counter()
        search_results = search_workspace(root, "performance", scopes=["workspace"], limit=5)
        search_seconds = time.perf_counter() - started

        started = time.perf_counter()
        brief = generate_brief(root, cadence="daily")
        brief_seconds = time.perf_counter() - started

        assert home.status_code == 200
        assert detail.status_code == 200
        assert context["rendered"]
        assert search_results
        assert Path(brief["path"]).exists()
        assert onboard_to_run_seconds < 600.0
        assert home_seconds < 2.0
        assert detail_seconds < 2.0
        assert context_seconds < 3.0
        assert search_seconds < 1.0
        assert brief_seconds < 30.0

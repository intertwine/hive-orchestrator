"""Reusable launch/demo fixture builder for the Hive v2.4 launch story."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
from typing import Any

from src.hive.control.campaigns import create_campaign_flow, generate_brief, tick_campaign
from src.hive.drivers.types import SteeringRequest
from src.hive.onboarding import onboard_workspace
from src.hive.runs.engine import accept_run, eval_run, start_run, steer_run
from src.hive.scheduler.query import ready_tasks
from src.hive.store.projects import get_project
from src.hive.store.task_files import create_task

DEMO_PROJECTS = {
    "alpha": "Pi Managed Control Plane",
    "beta": "OpenClaw Attach Control Plane",
    "gamma": "Hermes Advisory Control Plane",
}


def _run(cmd: list[str], *, cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


def _init_git_repo(root: Path) -> None:
    _run(["git", "init", "-q"], cwd=root)
    _run(["git", "config", "user.email", "demo@example.com"], cwd=root)
    _run(["git", "config", "user.name", "Hive Demo"], cwd=root)


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], cwd=root)
    _run(["git", "commit", "-m", message], cwd=root)


def _seed_project(root: Path, project_id: str, title: str, *, extra_tasks: int = 4) -> None:
    onboard_workspace(root, slug=project_id, title=title)
    project = get_project(root, project_id)
    project.program_path.write_text(
        """---
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
    - "python -c \\"print('ok')\\""
  deny: []
evaluators:
  - id: demo
    command: "python -c \\"print('ok')\\""
    required: true
promotion:
  allow_unsafe_without_evaluators: false
  allow_accept_without_changes: true
  requires_all:
    - demo
  review_required_when_paths_match: []
  auto_close_task: false
escalation:
  when_paths_match: []
  when_commands_match: []
---

# Goal

Run a governed demo task safely.
""",
        encoding="utf-8",
    )
    for index in range(1, extra_tasks + 1):
        create_task(
            root,
            project_id,
            f"{title} demo task {index}",
            status="ready",
            priority=2,
            acceptance=[f"{title} demo task {index} can be governed safely."],
            summary_md=f"Demo fixture task {index} for {project_id}.",
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


def build_north_star_demo(path: str | Path) -> dict[str, Any]:
    """Build the multi-project v2.4 launch fixture and return a manifest."""
    root = Path(path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    _init_git_repo(root)

    for project_id, title in DEMO_PROJECTS.items():
        # Alpha consumes an extra ready task for the Pi-managed showcase lane.
        _seed_project(root, project_id, title, extra_tasks=5 if project_id == "alpha" else 4)

    campaign = create_campaign_flow(
        root,
        title="Native Harness Daily Brief",
        goal="Keep Pi, OpenClaw, and Hermes moving under one operator.",
        project_ids=["alpha", "beta", "gamma"],
        driver="local",
        cadence="daily",
        brief_cadence="daily",
        max_active_runs=1,
    )

    _commit_all(root, "Bootstrap Hive v2.4 demo workspace")

    accepted_runs = [
        _start_local_accepted_run(root, "alpha"),
        _start_local_accepted_run(root, "beta"),
    ]
    review_runs = [
        _start_local_review_run(root, "alpha"),
        _start_local_review_run(root, "beta"),
    ]
    waiting_runs = [
        _start_waiting_run(root, "alpha", "codex"),
        _start_waiting_run(root, "alpha", "manual"),
        _start_waiting_run(root, "beta", "claude-code"),
    ]
    pi_running = start_run(root, _next_task_id(root, "alpha"), driver_name="pi").id
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
    waiting_runs.append(rerouted)

    tick = tick_campaign(root, str(campaign["campaign"]["id"]), owner="campaign-manager")
    launched_runs = tick.get("launched_runs", [])
    if not launched_runs:
        raise RuntimeError(
            "Campaign tick produced no runs. Check the demo fixture ready-task pool."
        )
    campaign_run_id = str(launched_runs[0]["id"])
    brief = generate_brief(root, cadence="daily")

    manifest = {
        "workspace": str(root),
        "campaign_id": str(campaign["campaign"]["id"]),
        "campaign_run_id": campaign_run_id,
        "brief_path": str(brief["path"]),
        "accepted_runs": accepted_runs,
        "review_runs": review_runs,
        "waiting_runs": waiting_runs,
        "running_runs": [pi_running, gamma_running, campaign_run_id],
        "showcase_run_id": rerouted,
        "projects": DEMO_PROJECTS,
        "all_runs": accepted_runs
        + review_runs
        + waiting_runs[:-1]
        + [pi_running, gamma_running, rerouted, campaign_run_id],
    }
    return manifest


def write_demo_manifest(path: str | Path, manifest: dict[str, Any]) -> Path:
    """Persist the demo manifest under .hive/demo for screenshot and walkthrough tooling."""
    root = Path(path).resolve()
    output_dir = root / ".hive" / "demo"
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "north_star_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path

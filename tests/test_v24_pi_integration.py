"""Tests for the Pi v2.4 integration foundation slice."""

from __future__ import annotations

import json
from pathlib import Path

from hive.cli.main import main as hive_main

from src.hive.drivers.types import RunBudget, RunLaunchRequest, RunWorkspace, SteeringRequest
from src.hive.integrations.models import GovernanceMode, IntegrationLevel
from src.hive.integrations.pi import PiEnvironment, PiWorkerAdapter
from src.hive.integrations.registry import get_integration, register_integration
from src.hive.trajectory.writer import load_trajectory


def _make_pi_package(root: Path) -> Path:
    package_dir = root / "pi-hive"
    bin_dir = package_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "package.json").write_text(
        json.dumps(
            {
                "name": "@mellona/pi-hive",
                "version": "0.1.0-test",
                "bin": {
                    "pi-hive": "./bin/pi-hive.js",
                    "pi-hive-runner": "./bin/pi-hive-runner.js",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (bin_dir / "pi-hive.js").write_text("#!/usr/bin/env node\n", encoding="utf-8")
    (bin_dir / "pi-hive-runner.js").write_text("#!/usr/bin/env node\n", encoding="utf-8")
    return package_dir


def _pi_env(workspace_root: Path, package_dir: Path | None) -> PiEnvironment:
    return PiEnvironment(
        workspace_root=workspace_root,
        node_path="/usr/bin/node",
        npm_path="/usr/bin/npm",
        node_version="v22.0.0",
        npm_version="10.0.0",
        package_dir=package_dir,
        package_version="0.1.0-test" if package_dir else None,
        cli_path=(package_dir / "bin" / "pi-hive.js") if package_dir else None,
        runner_path=(package_dir / "bin" / "pi-hive-runner.js") if package_dir else None,
    )


def _invoke_cli_json(capsys, argv: list[str]) -> dict:
    exit_code = hive_main(argv)
    captured = capsys.readouterr()
    assert exit_code == 0
    return json.loads(captured.out)


def test_pi_package_skeleton_exists():
    repo_root = Path(__file__).resolve().parents[1]
    package_dir = repo_root / "packages" / "pi-hive"
    manifest = json.loads((package_dir / "package.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "@mellona/pi-hive"
    assert (package_dir / "README.md").exists()
    assert (package_dir / "bin" / "pi-hive.js").exists()
    assert (package_dir / "bin" / "pi-hive-runner.js").exists()
    assert manifest["bin"]["pi-hive-runner"] == "./bin/pi-hive-runner.js"


def test_pi_probe_reports_supported_levels_and_setup_fields(tmp_path):
    package_dir = _make_pi_package(tmp_path)
    env = _pi_env(tmp_path, package_dir)
    adapter = PiWorkerAdapter(workspace_root=tmp_path, detector=lambda _root: env)

    info = adapter.probe().to_dict()

    assert info["adapter"] == "pi"
    assert info["supported_levels"] == ["pack", "companion", "attach", "managed"]
    assert info["supported_governance_modes"] == ["advisory", "governed"]
    assert info["install_path"] == str(package_dir)
    assert info["configuration_problems"] == []
    assert info["capability_snapshot"]["effective"]["managed_supported"] is True


def test_pi_probe_reports_missing_package_as_configuration_problem(tmp_path):
    env = _pi_env(tmp_path, None)
    adapter = PiWorkerAdapter(workspace_root=tmp_path, detector=lambda _root: env)

    info = adapter.probe().to_dict()

    assert info["available"] is False
    assert info["supported_levels"] == ["pack"]
    assert "companion package is not installed" in info["configuration_problems"][0]
    assert "npm install -g @mellona/pi-hive" in info["next_steps"][0]


def test_pi_managed_session_builds_runner_command_and_persists_trajectory(tmp_path):
    package_dir = _make_pi_package(tmp_path)
    env = _pi_env(tmp_path, package_dir)
    adapter = PiWorkerAdapter(workspace_root=tmp_path, detector=lambda _root: env)
    request = RunLaunchRequest(
        run_id="run_pi_001",
        task_id="task_pi_001",
        project_id="proj_pi",
        campaign_id=None,
        driver="pi",
        model=None,
        budget=RunBudget(max_tokens=500, max_cost_usd=0.1, max_wall_minutes=5),
        workspace=RunWorkspace(
            repo_root=str(tmp_path),
            worktree_path=str(tmp_path / "worktree"),
            base_branch="main",
        ),
        compiled_context_path=str(tmp_path / "context"),
        artifacts_path=str(tmp_path / "artifacts"),
        program_policy={},
    )

    session = adapter.open_session(request)
    events = list(adapter.stream_events(session))
    adapter.send_steer(
        session,
        SteeringRequest(action="note", note="Stay on the Pi-managed path."),
    )
    trajectory = load_trajectory(tmp_path, run_id="run_pi_001")

    assert session.integration_level == IntegrationLevel.MANAGED
    assert session.governance_mode == GovernanceMode.GOVERNED
    assert session.metadata["runner_command"][1].endswith("pi-hive-runner.js")
    assert [event["kind"] for event in events] == [
        "session_start",
        "assistant_delta",
        "artifact_written",
    ]
    assert [event.kind for event in trajectory] == [
        "session_start",
        "assistant_delta",
        "artifact_written",
        "steering_received",
    ]
    assert adapter.collect_artifacts(session)["trajectory_path"].endswith("trajectory.jsonl")


def test_pi_attach_session_persists_attach_trajectory(tmp_path):
    package_dir = _make_pi_package(tmp_path)
    env = _pi_env(tmp_path, package_dir)
    adapter = PiWorkerAdapter(workspace_root=tmp_path, detector=lambda _root: env)

    session = adapter.attach_session(
        "pi-live-42",
        GovernanceMode.ADVISORY,
        run_id="run_attach_001",
    )
    events = list(adapter.stream_events(session))
    trajectory = load_trajectory(tmp_path, run_id="run_attach_001")

    assert session.integration_level == IntegrationLevel.ATTACH
    assert session.governance_mode == GovernanceMode.ADVISORY
    assert events[0]["payload"]["mode"] == "attach"
    assert [event.kind for event in trajectory] == ["session_start", "assistant_delta"]


def test_registry_bootstraps_pi_integration():
    adapter = get_integration("pi")
    assert isinstance(adapter, PiWorkerAdapter)


def test_cli_integrate_doctor_pi_reports_setup_truth(tmp_path, capsys):
    package_dir = _make_pi_package(tmp_path)
    env = _pi_env(tmp_path, package_dir)
    original = get_integration("pi")
    register_integration("pi", PiWorkerAdapter(detector=lambda _root: env))
    try:
        payload = _invoke_cli_json(
            capsys,
            ["--path", str(tmp_path), "--json", "integrate", "doctor", "pi"],
        )
    finally:
        register_integration("pi", original)

    integration = payload["integrations"][0]
    assert integration["adapter"] == "pi"
    assert integration["supported_levels"][-1] == "managed"
    assert integration["install_path"] == str(package_dir)


def test_cli_integrate_pi_setup_assistant_uses_probe_payload(tmp_path, capsys):
    package_dir = _make_pi_package(tmp_path)
    env = _pi_env(tmp_path, package_dir)
    original = get_integration("pi")
    register_integration("pi", PiWorkerAdapter(detector=lambda _root: env))
    try:
        payload = _invoke_cli_json(
            capsys,
            ["--path", str(tmp_path), "--json", "integrate", "pi"],
        )
    finally:
        register_integration("pi", original)

    assert payload["integration"]["adapter"] == "pi"
    assert payload["integration"]["supported_governance_modes"] == [
        "advisory",
        "governed",
    ]
    assert payload["next_steps"]

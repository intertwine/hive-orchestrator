"""End-to-end Pi runtime tests for the M2 completion slice."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import pytest

from src.hive.cli.main import main as hive_main
from src.hive.drivers import SteeringRequest, get_driver
from src.hive.runs.engine import load_run, refresh_run_driver_state, run_artifacts, start_run, steer_run
from src.hive.store.task_files import create_task
from tests.conftest import init_git_repo, write_safe_program


def _invoke_cli_json(capsys, argv: list[str]) -> dict:
    exit_code = hive_main(argv)
    captured = capsys.readouterr()
    assert exit_code == 0, captured.err
    return json.loads(captured.out)


def _bootstrap_workspace(temp_hive_dir: str, capsys) -> None:
    root = Path(temp_hive_dir)
    init_git_repo(root)
    _invoke_cli_json(
        capsys, ["--path", temp_hive_dir, "--json", "onboard", "demo", "--title", "Demo"]
    )
    write_safe_program(root, "demo")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Bootstrap workspace"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def _wait_for(predicate, *, timeout: float = 5.0, interval: float = 0.1) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(interval)
    raise AssertionError("Timed out waiting for predicate.")


def _native_session_transcript(root: Path, native_session_ref: str) -> Path:
    return (
        root
        / ".hive"
        / "pi-native"
        / "sessions"
        / native_session_ref
        / "transcript.jsonl"
    )


def test_pi_driver_doctor_surfaces_real_worker_session_support():
    driver = get_driver("pi")
    info = driver.probe().to_dict()

    assert info["driver"] == "pi"
    assert info["capability_snapshot"]["adapter_family"] == "worker_session"
    assert info["capability_snapshot"]["declared"]["attach_supported"] is True


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required for Pi runtime tests.")
def test_pi_managed_run_launches_real_runner_and_round_trips_steering(temp_hive_dir, capsys):
    _bootstrap_workspace(temp_hive_dir, capsys)
    task = create_task(temp_hive_dir, "demo", "Pi managed slice", status="ready", priority=1)

    run = start_run(temp_hive_dir, task.id, driver_name="pi")

    assert run.driver == "pi"
    assert run.status == "running"
    artifacts = run_artifacts(temp_hive_dir, run.id)["artifacts"]
    assert artifacts["trajectory"].endswith("trajectory.jsonl")
    assert artifacts["steering"].endswith("steering.ndjson")

    steer_run(
        temp_hive_dir,
        run.id,
        SteeringRequest(action="note", note="Stay on the managed Pi path."),
    )

    _wait_for(
        lambda: refresh_run_driver_state(temp_hive_dir, run.id)["status"] == "completed_candidate"
    )
    metadata = load_run(temp_hive_dir, run.id)
    driver_status = metadata["metadata_json"]["driver_status"]
    trajectory_path = Path(metadata["trajectory_path"])
    trajectory_kinds = [
        json.loads(line)["kind"]
        for line in trajectory_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert driver_status["session"]["governance_mode"] == "governed"
    assert driver_status["session"]["integration_level"] == "managed"
    assert "steering_received" in trajectory_kinds
    assert trajectory_kinds[-1] == "session_end"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required for Pi runtime tests.")
def test_pi_attach_creates_advisory_run_and_delivers_notes_to_native_session(
    temp_hive_dir, capsys
):
    _bootstrap_workspace(temp_hive_dir, capsys)
    task = create_task(temp_hive_dir, "demo", "Pi attach slice", status="ready", priority=1)
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "packages" / "pi-hive" / "bin" / "pi-hive.js"
    native_session_ref = "pi-live-attach"
    process = subprocess.Popen(
        [
            shutil.which("node") or "node",
            str(script_path),
            "session-start",
            native_session_ref,
            "--workspace",
            temp_hive_dir,
            "--auto-exit-ms",
            "5000",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for(lambda: _native_session_transcript(Path(temp_hive_dir), native_session_ref).exists())
        payload = _invoke_cli_json(
            capsys,
            [
                "--path",
                temp_hive_dir,
                "--json",
                "integrate",
                "attach",
                "pi",
                native_session_ref,
                "--task-id",
                task.id,
            ],
        )
        run_id = payload["run"]["id"]

        steer_run(
            temp_hive_dir,
            run_id,
            SteeringRequest(action="note", note="Hello from Hive attach mode."),
        )

        transcript_path = _native_session_transcript(Path(temp_hive_dir), native_session_ref)
        _wait_for(
            lambda: "Hello from Hive attach mode."
            in transcript_path.read_text(encoding="utf-8")
        )
        metadata = refresh_run_driver_state(temp_hive_dir, run_id)
        driver_status = metadata["metadata_json"]["driver_status"]
        trajectory_text = Path(metadata["trajectory_path"]).read_text(encoding="utf-8")

        assert driver_status["session"]["governance_mode"] == "advisory"
        assert driver_status["session"]["integration_level"] == "attach"
        assert "steering_received" in trajectory_text
        assert "Hello from Hive attach mode." in transcript_path.read_text(encoding="utf-8")
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required for Pi runtime tests.")
def test_pi_companion_wrappers_open_and_attach_use_live_hive_commands(temp_hive_dir, capsys):
    _bootstrap_workspace(temp_hive_dir, capsys)
    managed_task = create_task(temp_hive_dir, "demo", "Pi wrapper open", status="ready", priority=1)
    attach_task = create_task(temp_hive_dir, "demo", "Pi wrapper attach", status="ready", priority=1)
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "packages" / "pi-hive" / "bin" / "pi-hive.js"
    hive_bin = repo_root / ".venv" / "bin" / "hive"
    env = {**os.environ, "HIVE_BIN": str(hive_bin)}

    managed = subprocess.run(
        [shutil.which("node") or "node", str(script_path), "open", managed_task.id, "--json"],
        cwd=temp_hive_dir,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    managed_payload = json.loads(managed.stdout)
    assert managed_payload["run"]["driver"] == "pi"

    native_session_ref = "pi-wrapper-attach"
    process = subprocess.Popen(
        [
            shutil.which("node") or "node",
            str(script_path),
            "session-start",
            native_session_ref,
            "--workspace",
            temp_hive_dir,
            "--auto-exit-ms",
            "5000",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for(lambda: _native_session_transcript(Path(temp_hive_dir), native_session_ref).exists())
        attached = subprocess.run(
            [
                shutil.which("node") or "node",
                str(script_path),
                "attach",
                native_session_ref,
                "--task-id",
                attach_task.id,
                "--json",
            ],
            cwd=temp_hive_dir,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        attached_payload = json.loads(attached.stdout)
        assert attached_payload["run"]["driver"] == "pi"
        assert attached_payload["session"]["governance_mode"] == "advisory"
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()

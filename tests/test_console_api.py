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
from src.hive.integrations.models import (
    AdapterFamily,
    GovernanceMode,
    IntegrationLevel,
    SessionHandle,
)
from src.hive.integrations.openclaw import persist_delegate_session
from src.hive.runs.engine import accept_run, eval_run, start_run
from src.hive.runtime.approvals import request_approval
from src.hive.runtime.capabilities import CapabilitySnapshot, capability_surface
from src.hive.scheduler.query import ready_tasks
from src.hive.store.events import emit_event
from src.hive.store.task_files import create_task
from src.hive.trajectory.schema import trajectory_event
from src.hive.trajectory.writer import append_trajectory_event


def _invoke_cli_json(capsys, argv: list[str]) -> dict:
    exit_code = hive_main(argv)
    captured = capsys.readouterr()
    assert exit_code == 0
    return json.loads(captured.out)


def _delegate_capability_snapshot(harness: str) -> CapabilitySnapshot:
    return CapabilitySnapshot(
        driver=harness,
        driver_version="1.0.0",
        declared=capability_surface(
            launch_mode="external_session",
            session_persistence="persistent",
            event_stream="structured_deltas",
            steering="note",
            native_sandbox="external",
            outer_sandbox_required=False,
            artifacts=["trajectory", "session-history"],
        ),
        effective=capability_surface(
            launch_mode="external_session",
            session_persistence="persistent",
            event_stream="structured_deltas",
            steering="note",
            native_sandbox="external",
            outer_sandbox_required=False,
            artifacts=["trajectory", "session-history"],
        ),
        probed={"attach_supported": True},
        evidence={"sandbox": f"Sandbox is owned by {harness}, not Hive."},
        governance_mode="advisory",
        integration_level="attach",
        adapter_family="delegate_gateway",
    )


def _parse_sse_events(text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        event_name = ""
        payload: dict = {}
        for line in block.splitlines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ").strip()
            elif line.startswith("data: "):
                payload = json.loads(line.removeprefix("data: "))
        events.append((event_name, payload))
    return events


def _write_delegate_session(
    workspace_root: Path,
    *,
    harness: str,
    delegate_session_id: str,
    native_session_ref: str,
    project_id: str,
    task_id: str,
    final_state: dict | None = None,
    steering_records: list[dict] | None = None,
    trajectory_events: list | None = None,
) -> None:
    session = SessionHandle(
        session_id=f"dsess-{delegate_session_id}",
        adapter_name=harness,
        adapter_family=AdapterFamily.DELEGATE_GATEWAY,
        native_session_ref=native_session_ref,
        governance_mode=GovernanceMode.ADVISORY,
        integration_level=IntegrationLevel.ATTACH,
        delegate_session_id=delegate_session_id,
        project_id=project_id,
        task_id=task_id,
        status="attached",
        metadata={"sandbox_owner": harness},
    )
    persist_delegate_session(
        workspace_root,
        session,
        capability_snapshot=_delegate_capability_snapshot(harness),
    )
    events = trajectory_events or [
        trajectory_event(
            seq=0,
            kind="assistant_message",
            harness=harness,
            adapter_family="delegate_gateway",
            native_session_ref=native_session_ref,
            delegate_session_id=delegate_session_id,
            project_id=project_id,
            task_id=task_id,
            payload={"text": f"{harness} transcript delta"},
            raw_ref=f"{harness}:{native_session_ref}:0",
        )
    ]
    for event in events:
        append_trajectory_event(workspace_root, event)
    steering_path = (
        workspace_root / ".hive" / "delegates" / delegate_session_id / "steering.ndjson"
    )
    records = steering_records or [
        {
            "ts": "2026-03-29T15:45:00Z",
            "action": "note",
            "note": f"Note from {harness}",
        }
    ]
    steering_path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    if final_state is not None:
        final_path = workspace_root / ".hive" / "delegates" / delegate_session_id / "final.json"
        final_path.write_text(
            json.dumps(final_state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


class TestObserveConsoleApi:
    """Smoke tests for the observe-console backend."""

    def test_health_home_runs_and_run_detail_endpoints(self, temp_hive_dir, capsys):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        review_ready_task = create_task(
            temp_hive_dir, "demo", "Review-ready slice", status="ready", priority=1
        )
        follow_up_task = create_task(
            temp_hive_dir, "demo", "Follow-up review slice", status="ready", priority=1
        )
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        run = start_run(temp_hive_dir, review_ready_task.id, driver_name="codex")
        local_run = start_run(temp_hive_dir, follow_up_task.id, driver_name="local")
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
        from src.hive import __version__
        assert health.json()["version"] == __version__
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

    def test_attention_notifications_and_activity_endpoints(self, temp_hive_dir, capsys):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )
        write_safe_program(temp_hive_dir, "demo")
        review_task = create_task(
            temp_hive_dir, "demo", "Review-ready slice", status="ready", priority=1
        )
        accepted_task = create_task(
            temp_hive_dir, "demo", "Accepted slice", status="ready", priority=2
        )
        subprocess.run(["git", "add", "-A"], cwd=temp_hive_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Bootstrap workspace"],
            cwd=temp_hive_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        review_run = start_run(temp_hive_dir, review_task.id, driver_name="codex")
        eval_run(temp_hive_dir, review_run.id)
        accepted_run = start_run(temp_hive_dir, accepted_task.id, driver_name="local")
        eval_run(temp_hive_dir, accepted_run.id)
        accept_run(temp_hive_dir, accepted_run.id)
        emit_event(
            temp_hive_dir,
            actor="hive",
            entity_type="run",
            entity_id=accepted_run.id,
            event_type="run.note_added",
            source="tests.console",
            run_id=accepted_run.id,
            project_id="demo",
            payload={
                "message": "Canonical /home route published.",
                "summary": "Stable browser deep link shipped.",
                "run_id": accepted_run.id,
                "project_id": "demo",
            },
        )

        client = TestClient(app)
        status = client.get("/status", params={"path": temp_hive_dir})
        inbox = client.get("/inbox", params={"path": temp_hive_dir})
        notifications = client.get("/notifications", params={"path": temp_hive_dir})
        activity = client.get("/activity", params={"path": temp_hive_dir})

        assert status.status_code == 200
        assert "attention_summary" in status.json()
        assert status.json()["notifications"] >= 2
        assert status.json()["activity"] >= 2

        assert inbox.status_code == 200
        assert inbox.json()["summary"]["total"] == len(inbox.json()["items"])
        review_item = next(
            item for item in inbox.json()["items"] if item["kind"] == "run-review"
        )
        assert review_item["severity"] == "critical"
        assert review_item["decision_type"] == "review"
        assert review_item["why_visible"]
        assert review_item["ignore_impact"]
        assert review_item["deep_link"] == f"/runs/{review_run.id}"

        assert notifications.status_code == 200
        assert notifications.json()["summary"]["by_notification_tier"]["actionable"] >= 1
        assert notifications.json()["summary"]["by_notification_tier"]["informational"] >= 1
        assert any(
            item["title"] == "Canonical /home route published."
            and item["notification_tier"] == "informational"
            for item in notifications.json()["items"]
        )
        assert any(
            item["title"].startswith("Accepted ")
            and item["notification_tier"] == "informational"
            for item in notifications.json()["items"]
        )

        assert activity.status_code == 200
        assert activity.json()["summary"]["total"] >= 2
        assert activity.json()["items"][0]["title"] == "Canonical /home route published."
        assert any(
            item["title"].startswith("Accepted ")
            and item["deep_link"] == f"/runs/{accepted_run.id}"
            for item in activity.json()["items"]
        )

    def test_events_stream_emits_snapshot_and_heartbeat_frames(
        self, temp_hive_dir, capsys
    ):
        init_git_repo(temp_hive_dir)
        _invoke_cli_json(
            capsys,
            ["--path", temp_hive_dir, "--json", "quickstart", "demo", "--title", "Demo"],
        )

        client = TestClient(app)
        response = client.get("/events/stream", params={"path": temp_hive_dir, "once": True})

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        events = _parse_sse_events(response.text)

        assert [event for event, _ in events] == ["snapshot", "heartbeat", "end"]
        snapshot_payload = events[0][1]
        heartbeat_payload = events[1][1]
        assert snapshot_payload["workspace"] == str(Path(temp_hive_dir).resolve())
        assert "synced_at" in snapshot_payload
        assert heartbeat_payload["workspace"] == str(Path(temp_hive_dir).resolve())
        expected_last_event_id = (
            snapshot_payload["events"][-1]["event_id"] if snapshot_payload["events"] else None
        )
        assert heartbeat_payload["last_event_id"] == expected_last_event_id
        assert "synced_at" in heartbeat_payload

    def test_v24_run_and_delegate_detail_truth_surfaces(self, temp_hive_dir, capsys):
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
        pi_run = start_run(temp_hive_dir, task_id, driver_name="pi")
        _write_delegate_session(
            Path(temp_hive_dir),
            harness="openclaw",
            delegate_session_id="del_openclaw_live",
            native_session_ref="oc-session-001",
            project_id="demo",
            task_id=task_id,
        )
        _write_delegate_session(
            Path(temp_hive_dir),
            harness="hermes",
            delegate_session_id="del_hermes_live",
            native_session_ref="hermes-session-001",
            project_id="demo",
            task_id=task_id,
        )

        client = TestClient(app)
        runs = client.get("/runs", params={"path": temp_hive_dir})
        home = client.get("/home", params={"path": temp_hive_dir})
        pi_detail = client.get(f"/runs/{pi_run.id}", params={"path": temp_hive_dir})
        openclaw_detail = client.get("/runs/del_openclaw_live", params={"path": temp_hive_dir})
        hermes_detail = client.get("/runs/del_hermes_live", params={"path": temp_hive_dir})

        assert runs.status_code == 200
        run_ids = {item["id"] for item in runs.json()["runs"]}
        assert pi_run.id in run_ids
        assert "del_openclaw_live" in run_ids
        assert "del_hermes_live" in run_ids

        assert home.status_code == 200
        active_run_ids = {item["id"] for item in home.json()["home"]["active_runs"]}
        assert pi_run.id in active_run_ids
        assert "del_openclaw_live" in active_run_ids
        assert "del_hermes_live" in active_run_ids

        assert pi_detail.status_code == 200
        assert pi_detail.json()["detail"]["detail_kind"] == "run"
        assert pi_detail.json()["detail"]["harness"] == "pi"
        assert pi_detail.json()["detail"]["integration_level"] == "managed"
        assert pi_detail.json()["detail"]["governance_mode"] == "governed"
        assert pi_detail.json()["detail"]["native_session_handle"].startswith("pi-managed:")
        assert pi_detail.json()["detail"]["capability_snapshot"]["adapter_family"] == "worker_session"
        assert pi_detail.json()["detail"]["steering_history"] == []
        assert pi_detail.json()["detail"]["trajectory"]

        assert openclaw_detail.status_code == 200
        assert openclaw_detail.json()["detail"]["detail_kind"] == "delegate_session"
        assert openclaw_detail.json()["detail"]["harness"] == "openclaw"
        assert openclaw_detail.json()["detail"]["integration_level"] == "attach"
        assert openclaw_detail.json()["detail"]["governance_mode"] == "advisory"
        assert openclaw_detail.json()["detail"]["native_session_handle"] == "oc-session-001"
        assert (
            openclaw_detail.json()["detail"]["capability_snapshot"]["adapter_family"]
            == "delegate_gateway"
        )
        assert openclaw_detail.json()["detail"]["steering_history"][0]["type"] == "steering.note_added"
        assert openclaw_detail.json()["detail"]["trajectory"][0]["native_session_ref"] == "oc-session-001"

        assert hermes_detail.status_code == 200
        assert hermes_detail.json()["detail"]["detail_kind"] == "delegate_session"
        assert hermes_detail.json()["detail"]["harness"] == "hermes"
        assert hermes_detail.json()["detail"]["integration_level"] == "attach"
        assert hermes_detail.json()["detail"]["governance_mode"] == "advisory"
        assert hermes_detail.json()["detail"]["native_session_handle"] == "hermes-session-001"
        assert (
            hermes_detail.json()["detail"]["capability_snapshot"]["adapter_family"]
            == "delegate_gateway"
        )
        assert hermes_detail.json()["detail"]["steering_history"][0]["type"] == "steering.note_added"
        assert hermes_detail.json()["detail"]["trajectory"][0]["native_session_ref"] == "hermes-session-001"

    def test_v24_delegate_sessions_surface_inbox_exceptions_and_notes(
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
        pi_run = start_run(temp_hive_dir, task_id, driver_name="pi")
        _write_delegate_session(
            Path(temp_hive_dir),
            harness="openclaw",
            delegate_session_id="del_openclaw_attention",
            native_session_ref="oc-session-777",
            project_id="demo",
            task_id=task_id,
            final_state={
                "status": "blocked",
                "reason": "Native session requested operator review before proceeding.",
            },
            steering_records=[
                {
                    "ts": "2026-03-29T15:46:00Z",
                    "action": "note",
                    "note": "Need operator review before continuing.",
                    "source": "delegate",
                    "inbox_visible": True,
                },
                {
                    "ts": "2026-03-29T15:47:00Z",
                    "action": "note",
                    "note": "Gateway conversation is waiting on a human decision.",
                    "source": "delegate",
                    "inbox_visible": True,
                }
            ],
            trajectory_events=[
                trajectory_event(
                    seq=0,
                    kind="assistant_message",
                    harness="openclaw",
                    adapter_family="delegate_gateway",
                    native_session_ref="oc-session-777",
                    delegate_session_id="del_openclaw_attention",
                    project_id="demo",
                    task_id=task_id,
                    payload={"text": "OpenClaw transcript delta"},
                    raw_ref="openclaw:oc-session-777:0",
                ),
                trajectory_event(
                    seq=1,
                    kind="approval_request",
                    harness="openclaw",
                    adapter_family="delegate_gateway",
                    native_session_ref="oc-session-777",
                    delegate_session_id="del_openclaw_attention",
                    project_id="demo",
                    task_id=task_id,
                    payload={"summary": "Approve escalation acknowledgement"},
                    raw_ref="openclaw:oc-session-777:1",
                ),
                trajectory_event(
                    seq=2,
                    kind="error",
                    harness="openclaw",
                    adapter_family="delegate_gateway",
                    native_session_ref="oc-session-777",
                    delegate_session_id="del_openclaw_attention",
                    project_id="demo",
                    task_id=task_id,
                    payload={"message": "Native harness raised an exception."},
                    raw_ref="openclaw:oc-session-777:2",
                ),
            ],
        )

        client = TestClient(app)
        inbox = client.get("/inbox", params={"path": temp_hive_dir})
        home = client.get("/home", params={"path": temp_hive_dir})

        assert inbox.status_code == 200
        items = inbox.json()["items"]
        assert any(
            item["kind"] == "delegate-blocked"
            and item["run_id"] == "del_openclaw_attention"
            and item["reason"] == "Native session requested operator review before proceeding."
            for item in items
        )
        assert any(
            item["kind"] == "delegate-note"
            and item["run_id"] == "del_openclaw_attention"
            and item["reason"] == "Need operator review before continuing."
            for item in items
        )
        assert any(
            item["kind"] == "delegate-note"
            and item["run_id"] == "del_openclaw_attention"
            and item["reason"] == "Gateway conversation is waiting on a human decision."
            for item in items
        )
        assert any(
            item["kind"] == "delegate-approval"
            and item["run_id"] == "del_openclaw_attention"
            and item["reason"] == "Approve escalation acknowledgement"
            for item in items
        )
        assert any(
            item["kind"] == "delegate-error"
            and item["run_id"] == "del_openclaw_attention"
            and item["reason"] == "Native harness raised an exception."
            for item in items
        )

        assert home.status_code == 200
        home_payload = home.json()["home"]
        assert any(run["id"] == pi_run.id for run in home_payload["active_runs"])
        assert any(
            item["kind"] == "delegate-blocked"
            and item["run_id"] == "del_openclaw_attention"
            for item in home_payload["inbox"]
        )

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

    def test_execute_console_action_endpoint_records_typed_steering_history(
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

        client = TestClient(app)
        response = client.post(
            "/actions/execute",
            params={"path": temp_hive_dir},
            json={
                "action_id": "run.note",
                "run_id": run.id,
                "note": "Please keep this slice narrow.",
                "actor": "operator",
            },
        )
        detail = client.get(f"/runs/{run.id}", params={"path": temp_hive_dir})

        assert response.status_code == 200
        assert response.json()["action_id"] == "run.note"
        assert response.json()["run"]["id"] == run.id
        assert detail.status_code == 200
        assert detail.json()["detail"]["steering_history"]
        assert detail.json()["detail"]["steering_history"][-1]["type"] == "steering.note_added"

    def test_execute_console_action_endpoint_resolves_pending_approval_with_reason(
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
        approval = request_approval(
            temp_hive_dir,
            run.id,
            kind="command",
            title="Approve git status",
            summary="Local driver wants to inspect the repo status.",
            requested_by="driver:local",
            payload={"command": "git status"},
        )

        client = TestClient(app)
        response = client.post(
            "/actions/execute",
            params={"path": temp_hive_dir},
            json={
                "action_id": "approval.reject",
                "run_id": run.id,
                "approval_id": approval["approval_id"],
                "actor": "operator",
                "reason": "Rejected because the command is outside this slice.",
            },
        )
        approvals = client.get(f"/runs/{run.id}/approvals", params={"path": temp_hive_dir})

        assert response.status_code == 200
        assert response.json()["action_id"] == "approval.reject"
        assert response.json()["request"]["reason"] == (
            "Rejected because the command is outside this slice."
        )
        assert response.json()["approval"]["approval_id"] == approval["approval_id"]
        assert response.json()["approval"]["status"] == "rejected"
        assert approvals.status_code == 200
        assert approvals.json()["approvals"][0]["status"] == "rejected"

    def test_runs_endpoint_accepts_canonical_and_legacy_claude_filters(self, temp_hive_dir, capsys):
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
        start_run(temp_hive_dir, task_id, driver_name="claude-code")

        client = TestClient(app)
        canonical = client.get("/runs", params={"path": temp_hive_dir, "driver": "claude"})
        legacy = client.get("/runs", params={"path": temp_hive_dir, "driver": "claude-code"})

        assert canonical.status_code == 200
        assert legacy.status_code == 200
        assert len(canonical.json()["runs"]) == 1
        assert len(legacy.json()["runs"]) == 1
        assert canonical.json()["runs"][0]["id"] == legacy.json()["runs"][0]["id"]
        assert canonical.json()["runs"][0]["driver"] == "claude"

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

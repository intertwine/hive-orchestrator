"""OpenClaw DelegateGatewayAdapter — gateway-first integration for v2.4.

OpenClaw's Gateway owns sessions. Hive attaches as an advisory observer/steerer
via an external bridge (``openclaw-hive-bridge``). Managed mode is deferred.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from src.hive.clock import utc_now_iso
from src.hive.drivers.types import SteeringRequest
from src.hive.ids import new_id
from src.hive.integrations.base import DelegateGatewayAdapter
from src.hive.integrations.models import (
    AdapterFamily,
    GovernanceMode,
    IntegrationInfo,
    IntegrationLevel,
    SessionHandle,
)
from src.hive.runtime.capabilities import CapabilitySnapshot, capability_surface


# ---------------------------------------------------------------------------
# Bridge client abstraction
# ---------------------------------------------------------------------------


@dataclass
class BridgeProbe:
    """Result of probing the openclaw-hive-bridge."""

    reachable: bool = False
    version: str = ""
    gateway_url: str = ""
    gateway_reachable: bool = False
    sessions_accessible: bool = False
    attach_supported: bool = False
    steering_supported: bool = False
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class OpenClawBridgeClient:
    """Client for communicating with the openclaw-hive-bridge process.

    The default implementation launches the bridge as a stdio subprocess
    and speaks NDJSON. Each request is a JSON line; each response is a JSON
    line back. Tests can subclass or replace this with an in-memory stub.
    """

    BINARY_NAMES = ("openclaw-hive-bridge",)

    def __init__(self, gateway_url: str | None = None) -> None:
        self._gateway_url = gateway_url or os.environ.get("OPENCLAW_GATEWAY_URL", "")

    def detect_binary(self) -> str | None:
        for name in self.BINARY_NAMES:
            path = shutil.which(name)
            if path:
                return str(Path(path).resolve())
        return None

    def _bridge_command(self) -> list[str] | None:
        binary = self.detect_binary()
        if not binary:
            return None
        cmd = [binary]
        if self._gateway_url:
            cmd.extend(["--gateway", self._gateway_url])
        cmd.append("--stdio")
        return cmd

    def _send_receive(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send one NDJSON request to the bridge and return the response."""
        cmd = self._bridge_command()
        if not cmd:
            return {"ok": False, "error": "Bridge binary not found."}
        try:
            result = subprocess.run(
                cmd,
                input=json.dumps(request) + "\n",
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
            return {"ok": False, "error": str(exc)}
        for line in result.stdout.strip().splitlines():
            if line.strip():
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        return {
            "ok": False,
            "error": result.stderr.strip() or "No response from bridge.",
        }

    def probe(self) -> BridgeProbe:
        binary = self.detect_binary()
        if not binary:
            return BridgeProbe(
                reachable=False,
                blockers=["openclaw-hive-bridge not found on PATH."],
                notes=[
                    "Install: npm install -g openclaw-hive-bridge",
                    "Or run the bridge from packages/openclaw-hive-bridge/.",
                ],
            )
        # Probe the bridge for gateway status.
        response = self._send_receive({"type": "probe"})
        gateway_reachable = bool(response.get("gateway_reachable"))
        return BridgeProbe(
            reachable=True,
            version=str(response.get("version", "0.1.0")),
            gateway_url=str(response.get("gateway_url", self._gateway_url)),
            gateway_reachable=gateway_reachable,
            sessions_accessible=bool(response.get("sessions_accessible")),
            attach_supported=bool(response.get("attach_supported", True)),
            steering_supported=bool(response.get("steering_supported", True)),
            notes=[f"Bridge detected at {binary}."]
            + (
                [f"Gateway at {self._gateway_url} is reachable."]
                if gateway_reachable
                else []
            ),
            blockers=[]
            if gateway_reachable
            else [
                f"Gateway at {self._gateway_url or '(not configured)'} is not reachable."
            ],
        )

    def list_sessions(self) -> list[dict[str, Any]]:
        response = self._send_receive({"type": "list_sessions"})
        return list(response.get("items", []))

    def attach(
        self, session_key: str, *, project_id: str | None = None
    ) -> dict[str, Any]:
        return self._send_receive(
            {
                "type": "attach",
                "native_session_ref": session_key,
                "project_id": project_id,
            }
        )

    def stream_events(self, session_key: str) -> Iterator[dict[str, Any]]:
        """Stream events from the bridge. Uses a single request/response for now."""
        response = self._send_receive(
            {
                "type": "stream_events",
                "native_session_ref": session_key,
            }
        )
        yield from response.get("events", [])

    def send_steer(
        self, session_key: str, action: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return self._send_receive(
            {
                "type": "steer",
                "session_key": session_key,
                "action": action,
                "payload": payload,
            }
        )

    def publish_note(self, session_key: str, note: str) -> dict[str, Any]:
        return self._send_receive(
            {
                "type": "note",
                "session_key": session_key,
                "note": note,
            }
        )

    def detach(self, session_key: str) -> dict[str, Any]:
        return self._send_receive(
            {
                "type": "detach",
                "native_session_ref": session_key,
            }
        )


# ---------------------------------------------------------------------------
# Delegate session persistence
# ---------------------------------------------------------------------------


def _delegates_dir(base_path: str | Path) -> Path:
    return Path(base_path).resolve() / ".hive" / "delegates"


def persist_delegate_session(
    base_path: str | Path,
    session: SessionHandle,
    capability_snapshot: CapabilitySnapshot | None = None,
) -> Path:
    """Write delegate session artifacts to disk."""
    session_dir = _delegates_dir(base_path) / (
        session.delegate_session_id or session.session_id
    )
    session_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "delegate_session_id": session.delegate_session_id or session.session_id,
        "adapter_name": session.adapter_name,
        "adapter_family": str(session.adapter_family),
        "native_session_ref": session.native_session_ref,
        "governance_mode": str(session.governance_mode),
        "integration_level": str(session.integration_level),
        "project_id": session.project_id,
        "task_id": session.task_id,
        "status": session.status,
        "attached_at": session.attached_at,
    }
    (session_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    if capability_snapshot:
        (session_dir / "capability-snapshot.json").write_text(
            json.dumps(capability_snapshot.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    # Ensure trajectory and steering files exist.
    for name in ("trajectory.jsonl", "steering.ndjson"):
        path = session_dir / name
        if not path.exists():
            path.touch()

    return session_dir


def finalize_delegate_session(
    base_path: str | Path,
    delegate_session_id: str,
    final: dict[str, Any],
) -> None:
    """Write final.json for a completed delegate session."""
    session_dir = _delegates_dir(base_path) / delegate_session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "final.json").write_text(
        json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def load_delegate_session(
    base_path: str | Path, delegate_session_id: str
) -> dict[str, Any] | None:
    """Load a persisted delegate session manifest."""
    manifest_path = _delegates_dir(base_path) / delegate_session_id / "manifest.json"
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def list_delegate_sessions(base_path: str | Path) -> list[dict[str, Any]]:
    """List all persisted delegate sessions."""
    delegates_root = _delegates_dir(base_path)
    if not delegates_root.exists():
        return []
    sessions = []
    for session_dir in sorted(delegates_root.iterdir()):
        manifest_path = session_dir / "manifest.json"
        if manifest_path.exists():
            sessions.append(json.loads(manifest_path.read_text(encoding="utf-8")))
    return sessions


def append_delegate_steering(
    base_path: str | Path,
    delegate_session_id: str,
    record: dict[str, Any],
) -> None:
    """Append a steering record to the delegate session's NDJSON log."""
    session_dir = _delegates_dir(base_path) / delegate_session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    steering_path = session_dir / "steering.ndjson"
    with open(steering_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# OpenClaw adapter
# ---------------------------------------------------------------------------


class OpenClawGatewayAdapter(DelegateGatewayAdapter):
    """Gateway-first adapter for OpenClaw.

    Communicates with the external ``openclaw-hive-bridge`` process to
    list, attach, steer, and detach Gateway sessions. All attached sessions
    are advisory — Hive never owns the OpenClaw sandbox.
    """

    name = "openclaw"
    adapter_family = AdapterFamily.DELEGATE_GATEWAY

    def __init__(
        self,
        bridge: OpenClawBridgeClient | None = None,
        base_path: str | Path | None = None,
    ) -> None:
        self._bridge = bridge or OpenClawBridgeClient()
        self._base_path = base_path
        self._sessions: dict[str, SessionHandle] = {}

    def _capability_snapshot(self, bridge_probe: BridgeProbe) -> CapabilitySnapshot:
        return CapabilitySnapshot(
            driver=self.name,
            driver_version=bridge_probe.version or "0.0.0",
            declared=capability_surface(
                launch_mode="gateway_bridge",
                session_persistence="persistent",
                event_stream="structured_deltas",
                approvals=[],
                skills="file_projection",
                worktrees="host_managed",
                subagents="none",
                native_sandbox="external",
                outer_sandbox_required=False,
                artifacts=["transcript", "session-history"],
                reroute_export="none",
            ),
            effective=capability_surface(
                launch_mode="gateway_bridge"
                if bridge_probe.gateway_reachable
                else "none",
                session_persistence="persistent"
                if bridge_probe.gateway_reachable
                else "none",
                event_stream="structured_deltas"
                if bridge_probe.gateway_reachable
                else "none",
                approvals=[],
                skills="file_projection",
                worktrees="host_managed",
                subagents="none",
                native_sandbox="external",
                outer_sandbox_required=False,
                artifacts=["transcript", "session-history"]
                if bridge_probe.gateway_reachable
                else [],
                reroute_export="none",
            ),
            probed={
                "bridge_reachable": bridge_probe.reachable,
                "gateway_url": bridge_probe.gateway_url,
                "gateway_reachable": bridge_probe.gateway_reachable,
                "sessions_accessible": bridge_probe.sessions_accessible,
                "attach_supported": bridge_probe.attach_supported,
                "steering_supported": bridge_probe.steering_supported,
            },
            confidence={
                "launch_mode": "verified"
                if bridge_probe.gateway_reachable
                else ("bridge_only" if bridge_probe.reachable else "unavailable"),
                "event_stream": "verified"
                if bridge_probe.gateway_reachable
                else ("bridge_only" if bridge_probe.reachable else "unavailable"),
            },
            evidence={
                "launch_mode": "OpenClaw Gateway bridge provides session access."
                if bridge_probe.gateway_reachable
                else (
                    "Bridge detected but gateway not reachable."
                    if bridge_probe.reachable
                    else "Bridge not detected — install openclaw-hive-bridge."
                ),
                "sandbox": "Sandbox is owned by OpenClaw, not Hive.",
            },
            governance_mode="advisory",
            integration_level="attach",
            adapter_family="delegate_gateway",
        )

    def probe(self) -> IntegrationInfo:
        bridge_probe = self._bridge.probe()
        return IntegrationInfo(
            adapter=self.name,
            adapter_family=self.adapter_family,
            governance_mode=GovernanceMode.ADVISORY,
            integration_level=IntegrationLevel.ATTACH,
            version=bridge_probe.version or "0.0.0",
            available=bridge_probe.reachable and bridge_probe.gateway_reachable,
            capability_snapshot=self._capability_snapshot(bridge_probe),
            notes=[
                *bridge_probe.notes,
                *[f"blocker: {b}" for b in bridge_probe.blockers],
                "Managed mode is deferred from v2.4.",
            ],
        )

    def list_sessions(self) -> list[dict[str, Any]]:
        return self._bridge.list_sessions()

    def attach_delegate_session(
        self,
        native_session_ref: str,
        governance: GovernanceMode,
        project_id: str | None = None,
        task_id: str | None = None,
    ) -> SessionHandle:
        # Fail fast if the bridge is not reachable or the gateway is unavailable.
        bridge_probe = self._bridge.probe()
        if not bridge_probe.reachable:
            raise ConnectionError(
                "Cannot attach: openclaw-hive-bridge is not reachable. "
                + (
                    bridge_probe.blockers[0]
                    if bridge_probe.blockers
                    else "Install the bridge first."
                )
            )
        if not bridge_probe.gateway_reachable:
            raise ConnectionError(
                "Cannot attach: OpenClaw gateway is not reachable. "
                + (
                    bridge_probe.blockers[0]
                    if bridge_probe.blockers
                    else "Configure OPENCLAW_GATEWAY_URL and restart the bridge."
                )
            )

        # OpenClaw sessions are always advisory — Hive never owns the sandbox.
        effective_governance = GovernanceMode.ADVISORY

        attach_result = self._bridge.attach(native_session_ref, project_id=project_id)
        if not attach_result.get("ok", False):
            error_msg = attach_result.get("error", "Bridge attach failed.")
            raise ConnectionError(f"Cannot attach {native_session_ref}: {error_msg}")

        delegate_id = new_id("del")
        session = SessionHandle(
            session_id=new_id("dsess"),
            adapter_name=self.name,
            adapter_family=self.adapter_family,
            native_session_ref=native_session_ref,
            governance_mode=effective_governance,
            integration_level=IntegrationLevel.ATTACH,
            delegate_session_id=delegate_id,
            project_id=project_id,
            task_id=task_id,
            status="attached",
        )
        self._sessions[native_session_ref] = session

        if self._base_path:
            persist_delegate_session(
                self._base_path,
                session,
                capability_snapshot=self._capability_snapshot(self._bridge.probe()),
            )

        return session

    def stream_events(self, session: SessionHandle) -> Iterator[dict[str, Any]]:
        from src.hive.trajectory.schema import trajectory_event
        from src.hive.trajectory.writer import append_trajectory_event

        seq = 0
        for raw_event in self._bridge.stream_events(session.native_session_ref):
            event = {
                "seq": seq,
                "kind": raw_event.get("kind", "assistant_delta"),
                "ts": raw_event.get("ts", utc_now_iso()),
                "harness": "openclaw",
                "adapter_family": "delegate_gateway",
                "native_session_ref": session.native_session_ref,
                "delegate_session_id": session.delegate_session_id,
                "project_id": session.project_id,
                "task_id": session.task_id,
                "payload": raw_event.get("payload", {}),
            }
            # Persist to trajectory file.
            if self._base_path and session.delegate_session_id:
                append_trajectory_event(
                    self._base_path,
                    trajectory_event(
                        seq=seq,
                        kind=event["kind"],
                        harness="openclaw",
                        adapter_family="delegate_gateway",
                        native_session_ref=session.native_session_ref,
                        delegate_session_id=session.delegate_session_id,
                        project_id=session.project_id,
                        task_id=session.task_id,
                        payload=event.get("payload", {}),
                    ),
                )
            yield event
            seq += 1

    def send_steer(
        self, session: SessionHandle, request: SteeringRequest
    ) -> dict[str, Any]:
        result = self._bridge.send_steer(
            session.native_session_ref,
            request.action,
            {"reason": request.reason, "note": request.note},
        )
        if self._base_path and session.delegate_session_id:
            append_delegate_steering(
                self._base_path,
                session.delegate_session_id,
                {
                    "ts": utc_now_iso(),
                    "action": request.action,
                    "reason": request.reason,
                    "note": request.note,
                    "result": result,
                },
            )
        return {"ok": True, "adapter": self.name, **result}

    def publish_note(self, session: SessionHandle, note: str) -> dict[str, Any]:
        result = self._bridge.publish_note(session.native_session_ref, note)
        if self._base_path and session.delegate_session_id:
            append_delegate_steering(
                self._base_path,
                session.delegate_session_id,
                {"ts": utc_now_iso(), "action": "note", "note": note, "result": result},
            )
        return {"ok": True, "adapter": self.name, **result}

    def collect_artifacts(self, session: SessionHandle) -> dict[str, Any]:
        artifacts = []
        if self._base_path and session.delegate_session_id:
            session_dir = _delegates_dir(self._base_path) / session.delegate_session_id
            for name in ("trajectory.jsonl", "steering.ndjson", "manifest.json"):
                path = session_dir / name
                if path.exists() and path.stat().st_size > 0:
                    artifacts.append({"name": name, "path": str(path)})
        return {
            "adapter": self.name,
            "session_id": session.session_id,
            "artifacts": artifacts,
        }

    def detach_delegate_session(self, session: SessionHandle) -> dict[str, Any]:
        self._bridge.detach(session.native_session_ref)
        session.status = "detached"
        self._sessions.pop(session.native_session_ref, None)

        if self._base_path and session.delegate_session_id:
            finalize_delegate_session(
                self._base_path,
                session.delegate_session_id,
                {
                    "status": "detached",
                    "detached_at": utc_now_iso(),
                    "reason": "operator-initiated",
                },
            )

        return {"ok": True, "session_id": session.session_id}


__all__ = [
    "BridgeProbe",
    "OpenClawBridgeClient",
    "OpenClawGatewayAdapter",
    "append_delegate_steering",
    "finalize_delegate_session",
    "list_delegate_sessions",
    "load_delegate_session",
    "persist_delegate_session",
]

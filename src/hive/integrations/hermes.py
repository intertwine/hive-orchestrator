"""Hermes DelegateGatewayAdapter — skill/toolset-first integration for v2.4.

Hermes is a persistent agent platform with its own gateway, cron, memory,
skills, and toolsets. Hive attaches as an advisory observer/steerer. The
primary integration surface is a native skill/toolset, not a subprocess bridge.

Key constraints from the RFC:
- Governance is always advisory — Hive never owns the Hermes sandbox.
- Managed mode is deferred from v2.4.
- No bulk import of private Hermes memory (MEMORY.md, USER.md).
- Trajectory import fallback for sessions that weren't live-attached.
"""

from __future__ import annotations

import json
import os
import shutil
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
from src.hive.integrations.openclaw import (
    append_delegate_steering,
    finalize_delegate_session,
    persist_delegate_session,
)
from src.hive.runtime.capabilities import CapabilitySnapshot, capability_surface


# ---------------------------------------------------------------------------
# Hermes environment detection
# ---------------------------------------------------------------------------

_ENV_HERMES_HOME = "HERMES_HOME"
_ENV_HERMES_GATEWAY_URL = "HERMES_GATEWAY_URL"

# Files that must NOT be bulk-imported from Hermes.
PRIVATE_MEMORY_FILES = frozenset({"MEMORY.md", "USER.md", ".memory", ".user"})


@dataclass
class HermesProbe:
    """Result of probing the local Hermes installation."""

    hermes_found: bool = False
    hermes_home: str = ""
    hermes_version: str = ""
    gateway_url: str = ""
    gateway_reachable: bool = False
    skill_installed: bool = False
    agents_context_intact: bool = False
    trajectory_export_available: bool = False
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _check_gateway_health(gateway_url: str) -> bool:
    """Attempt an HTTP health check against the Hermes gateway."""
    import urllib.request
    import urllib.error

    # Try common health endpoints.
    for path in ("/health", "/api/health", "/"):
        try:
            url = gateway_url.rstrip("/") + path
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status < 500:
                    return True
        except (urllib.error.URLError, OSError, ValueError):
            continue
    return False


def detect_hermes(workspace_root: Path | None = None) -> HermesProbe:
    """Inspect the local environment for Hermes availability."""
    hermes_binary = shutil.which("hermes")
    hermes_home = os.environ.get(_ENV_HERMES_HOME, "")
    gateway_url = os.environ.get(_ENV_HERMES_GATEWAY_URL, "")

    if not hermes_binary and not hermes_home:
        return HermesProbe(
            hermes_found=False,
            blockers=["Hermes not found on PATH and HERMES_HOME not set."],
            notes=[
                "Install Hermes or set HERMES_HOME to the Hermes installation directory.",
                "Then re-run: hive integrate hermes",
            ],
        )

    # Resolve hermes_home: prefer env var, fall back to binary parent.
    resolved_home = hermes_home
    if not resolved_home and hermes_binary:
        resolved_home = str(Path(hermes_binary).resolve().parent.parent)

    # Check for AGENTS.md context compatibility.
    root = Path(workspace_root or Path.cwd()).resolve()
    agents_path = root / "AGENTS.md"
    agents_intact = agents_path.exists()

    # Check if the skill bundle is loadable from the workspace.
    skill_dir = root / "packages" / "hermes-skill"
    skill_installed = (skill_dir / "manifest.json").exists()

    # Gateway reachability: actually probe when a URL is configured.
    gateway_configured = bool(gateway_url)
    gateway_reachable = False
    if gateway_configured:
        gateway_reachable = _check_gateway_health(gateway_url)

    blockers: list[str] = []
    if not gateway_configured:
        blockers.append(
            "HERMES_GATEWAY_URL not set — gateway attach will be unavailable."
        )
    elif not gateway_reachable:
        blockers.append(
            f"Gateway at {gateway_url} is not reachable. "
            "Start the Hermes gateway and re-run: hive integrate hermes"
        )

    return HermesProbe(
        hermes_found=True,
        hermes_home=resolved_home,
        hermes_version="",  # Populated by actual version probe when available.
        gateway_url=gateway_url,
        gateway_reachable=gateway_reachable,
        skill_installed=skill_installed,
        agents_context_intact=agents_intact,
        trajectory_export_available=True,
        notes=[
            f"Hermes detected at {hermes_binary or resolved_home}.",
        ]
        + (
            [f"Gateway at {gateway_url} is reachable."]
            if gateway_reachable
            else (
                [f"Gateway URL configured: {gateway_url}"] if gateway_configured else []
            )
        )
        + (
            ["Skill bundle found in packages/hermes-skill/."] if skill_installed else []
        ),
        blockers=blockers,
    )


# ---------------------------------------------------------------------------
# Memory privacy enforcement
# ---------------------------------------------------------------------------


def is_private_memory_path(path: str | Path) -> bool:
    """Return True if a path refers to private Hermes memory that must not be bulk-imported."""
    name = Path(path).name
    return name in PRIVATE_MEMORY_FILES


def filter_importable_files(paths: list[str | Path]) -> list[Path]:
    """Filter out private memory files from a list of paths to import."""
    return [Path(p) for p in paths if not is_private_memory_path(p)]


# ---------------------------------------------------------------------------
# Trajectory import fallback
# ---------------------------------------------------------------------------


def import_hermes_trajectory(
    base_path: str | Path,
    source_path: str | Path,
    *,
    project_id: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Import a Hermes trajectory export into Hive as a completed advisory session.

    The source file should be JSONL with Hermes-native event records.
    Events are normalized into the Hive trajectory schema.
    """
    from src.hive.trajectory.schema import TrajectoryEvent, trajectory_event
    from src.hive.trajectory.writer import append_trajectory_event

    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"Trajectory source not found: {source}")

    delegate_id = new_id("del")
    events: list[dict[str, Any]] = []
    seq = 0

    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Normalize Hermes event kinds to Hive trajectory kinds.
        kind = _normalize_hermes_event_kind(raw.get("type") or raw.get("kind", ""))
        event = trajectory_event(
            seq=seq,
            kind=kind,
            harness="hermes",
            adapter_family="delegate_gateway",
            native_session_ref=raw.get("session_id", ""),
            delegate_session_id=delegate_id,
            project_id=project_id,
            task_id=task_id,
            payload=raw.get("payload") or raw.get("data", {}),
            raw_ref=raw.get("id") or raw.get("event_id"),
            ts=raw.get("ts") or raw.get("timestamp", utc_now_iso()),
        )
        events.append(event.to_dict())
        seq += 1

    # Persist as a delegate session.
    session = SessionHandle(
        session_id=new_id("dsess"),
        adapter_name="hermes",
        adapter_family=AdapterFamily.DELEGATE_GATEWAY,
        native_session_ref=raw.get("session_id", "") if events else "imported",
        governance_mode=GovernanceMode.ADVISORY,
        integration_level=IntegrationLevel.ATTACH,
        delegate_session_id=delegate_id,
        project_id=project_id,
        task_id=task_id,
        status="imported",
    )
    persist_delegate_session(base_path, session)

    # Write trajectory events.
    for event_dict in events:
        evt = TrajectoryEvent.from_dict(event_dict)
        append_trajectory_event(base_path, evt)

    # Finalize as completed import.
    finalize_delegate_session(
        base_path,
        delegate_id,
        {
            "status": "imported",
            "imported_at": utc_now_iso(),
            "source_path": str(source),
            "event_count": len(events),
        },
    )

    return {
        "ok": True,
        "delegate_session_id": delegate_id,
        "event_count": len(events),
        "source_path": str(source),
    }


def _normalize_hermes_event_kind(hermes_kind: str) -> str:
    """Map Hermes-native event types to Hive trajectory event kinds."""
    mapping = {
        # Hermes native → Hive trajectory
        "session.start": "session_start",
        "session.end": "session_end",
        "turn.start": "turn_start",
        "turn.end": "turn_end",
        "message": "user_message",
        "user_message": "user_message",
        "assistant": "assistant_delta",
        "assistant_message": "assistant_delta",
        "assistant_delta": "assistant_delta",
        "tool.call": "tool_call_start",
        "tool.result": "tool_call_end",
        "tool_call": "tool_call_start",
        "tool_result": "tool_call_end",
        "approval": "approval_request",
        "approval_request": "approval_request",
        "approval_decision": "approval_decision",
        "steering": "steering_received",
        "artifact": "artifact_written",
        "error": "error",
        "compaction": "compaction",
        # Pass through if already in Hive format.
        "session_start": "session_start",
        "session_end": "session_end",
        "turn_start": "turn_start",
        "turn_end": "turn_end",
        "tool_call_start": "tool_call_start",
        "tool_call_update": "tool_call_update",
        "tool_call_end": "tool_call_end",
        "steering_received": "steering_received",
        "artifact_written": "artifact_written",
    }
    return mapping.get(hermes_kind, hermes_kind or "assistant_delta")


# ---------------------------------------------------------------------------
# Hermes adapter
# ---------------------------------------------------------------------------


class HermesGatewayAdapter(DelegateGatewayAdapter):
    """Skill/toolset-first adapter for Hermes.

    Hermes owns sessions, memory, and the execution sandbox. Hive attaches
    as an advisory observer/steerer via skill/toolset actions and gateway
    session binding. All sessions are advisory — Hive never owns the
    Hermes sandbox.
    """

    name = "hermes"
    adapter_family = AdapterFamily.DELEGATE_GATEWAY

    def __init__(
        self,
        base_path: str | Path | None = None,
        detector: Any | None = None,
    ) -> None:
        self._base_path = base_path
        self._detector = detector or detect_hermes
        self._sessions: dict[str, SessionHandle] = {}

    def _hermes_probe(self) -> HermesProbe:
        root = Path(self._base_path) if self._base_path else None
        return self._detector(root)

    def _capability_snapshot(self, hermes_probe: HermesProbe) -> CapabilitySnapshot:
        available = hermes_probe.hermes_found and hermes_probe.gateway_reachable
        return CapabilitySnapshot(
            driver=self.name,
            driver_version=hermes_probe.hermes_version or "0.0.0",
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
                artifacts=["transcript", "session-history", "trajectory-export"],
                reroute_export="none",
            ),
            effective=capability_surface(
                launch_mode="gateway_bridge" if available else "none",
                session_persistence="persistent" if available else "none",
                event_stream="structured_deltas" if available else "none",
                approvals=[],
                skills="file_projection",
                worktrees="host_managed",
                subagents="none",
                native_sandbox="external",
                outer_sandbox_required=False,
                artifacts=["transcript", "session-history", "trajectory-export"]
                if available
                else [],
                reroute_export="none",
            ),
            probed={
                "hermes_found": hermes_probe.hermes_found,
                "hermes_home": hermes_probe.hermes_home,
                "gateway_url": hermes_probe.gateway_url,
                "gateway_reachable": hermes_probe.gateway_reachable,
                "skill_installed": hermes_probe.skill_installed,
                "agents_context_intact": hermes_probe.agents_context_intact,
                "trajectory_export_available": hermes_probe.trajectory_export_available,
            },
            confidence={
                "launch_mode": "verified"
                if available
                else ("hermes_only" if hermes_probe.hermes_found else "unavailable"),
                "event_stream": "verified"
                if available
                else ("hermes_only" if hermes_probe.hermes_found else "unavailable"),
            },
            evidence={
                "launch_mode": "Hermes gateway provides session access."
                if available
                else (
                    "Hermes detected but gateway not reachable."
                    if hermes_probe.hermes_found
                    else "Hermes not detected."
                ),
                "sandbox": "Sandbox is owned by Hermes, not Hive.",
                "memory": "Private Hermes memory (MEMORY.md, USER.md) is never bulk-imported.",
            },
            governance_mode="advisory",
            integration_level="attach",
            adapter_family="delegate_gateway",
        )

    def probe(self) -> IntegrationInfo:
        hermes_probe = self._hermes_probe()
        return IntegrationInfo(
            adapter=self.name,
            adapter_family=self.adapter_family,
            governance_mode=GovernanceMode.ADVISORY,
            integration_level=IntegrationLevel.ATTACH,
            version=hermes_probe.hermes_version or "0.0.0",
            available=hermes_probe.hermes_found and hermes_probe.gateway_reachable,
            capability_snapshot=self._capability_snapshot(hermes_probe),
            notes=[
                *hermes_probe.notes,
                *[f"blocker: {b}" for b in hermes_probe.blockers],
                "Managed mode is deferred from v2.4.",
                "Private Hermes memory is never bulk-imported.",
            ],
        )

    def list_sessions(self) -> list[dict[str, Any]]:
        # Hermes gateway session listing — requires gateway connection.
        # In v2.4, this returns an empty list when no gateway is configured.
        return []

    def attach_delegate_session(
        self,
        native_session_ref: str,
        governance: GovernanceMode,
        project_id: str | None = None,
        task_id: str | None = None,
    ) -> SessionHandle:
        hermes_probe = self._hermes_probe()
        if not hermes_probe.hermes_found:
            raise ConnectionError(
                "Cannot attach: Hermes not found. "
                + (
                    hermes_probe.blockers[0]
                    if hermes_probe.blockers
                    else "Install Hermes first."
                )
            )
        if not hermes_probe.gateway_reachable:
            raise ConnectionError(
                "Cannot attach: Hermes gateway not reachable. "
                + (
                    hermes_probe.blockers[0]
                    if hermes_probe.blockers
                    else "Set HERMES_GATEWAY_URL."
                )
            )

        # Hermes sessions are always advisory.
        effective_governance = GovernanceMode.ADVISORY

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
                capability_snapshot=self._capability_snapshot(hermes_probe),
            )

        return session

    def stream_events(self, session: SessionHandle) -> Iterator[dict[str, Any]]:
        from src.hive.trajectory.schema import trajectory_event
        from src.hive.trajectory.writer import append_trajectory_event

        # In v2.4, events come from the gateway or skill callbacks.
        # Emit a minimal session_start for attached sessions.
        events = [
            {
                "seq": 0,
                "kind": "session_start",
                "ts": utc_now_iso(),
                "harness": "hermes",
                "adapter_family": "delegate_gateway",
                "native_session_ref": session.native_session_ref,
                "delegate_session_id": session.delegate_session_id,
                "project_id": session.project_id,
                "task_id": session.task_id,
                "payload": {"mode": "attach", "governance": "advisory"},
            },
        ]
        for event in events:
            if self._base_path and session.delegate_session_id:
                append_trajectory_event(
                    self._base_path,
                    trajectory_event(
                        seq=event["seq"],
                        kind=event["kind"],
                        harness="hermes",
                        adapter_family="delegate_gateway",
                        native_session_ref=session.native_session_ref,
                        delegate_session_id=session.delegate_session_id,
                        project_id=session.project_id,
                        task_id=session.task_id,
                        payload=event.get("payload", {}),
                    ),
                )
            yield event

    def send_steer(
        self, session: SessionHandle, request: SteeringRequest
    ) -> dict[str, Any]:
        record = {
            "ts": utc_now_iso(),
            "action": request.action,
            "reason": request.reason,
            "note": request.note,
        }
        if self._base_path and session.delegate_session_id:
            append_delegate_steering(
                self._base_path,
                session.delegate_session_id,
                record,
            )
        return {"ok": True, "adapter": self.name, **record}

    def publish_note(self, session: SessionHandle, note: str) -> dict[str, Any]:
        record = {"ts": utc_now_iso(), "action": "note", "note": note}
        if self._base_path and session.delegate_session_id:
            append_delegate_steering(
                self._base_path,
                session.delegate_session_id,
                record,
            )
        return {"ok": True, "adapter": self.name, **record}

    def collect_artifacts(self, session: SessionHandle) -> dict[str, Any]:
        from src.hive.integrations.openclaw import _delegates_dir

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
    "PRIVATE_MEMORY_FILES",
    "HermesGatewayAdapter",
    "HermesProbe",
    "detect_hermes",
    "filter_importable_files",
    "import_hermes_trajectory",
    "is_private_memory_path",
]

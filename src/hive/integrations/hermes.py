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
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    list_delegate_sessions,
    persist_delegate_session,
)
from src.hive.runtime.capabilities import CapabilitySnapshot, capability_surface


# ---------------------------------------------------------------------------
# Hermes environment detection
# ---------------------------------------------------------------------------

_ENV_HERMES_HOME = "HERMES_HOME"
_ENV_HERMES_GATEWAY_URL = "HERMES_GATEWAY_URL"
_PENDING_ACTIONS_FILE = "pending-actions.ndjson"

# Files that must NOT be bulk-imported from Hermes.
PRIVATE_MEMORY_FILES = frozenset({"MEMORY.md", "USER.md", ".memory", ".user"})


@dataclass
class HermesProbe:
    """Result of probing the local Hermes installation."""

    hermes_found: bool = False
    hermes_home: str = ""
    hermes_version: str = ""
    state_db_path: str = ""
    state_db_available: bool = False
    sessions_dir: str = ""
    attach_supported: bool = False
    gateway_url: str = ""
    gateway_reachable: bool = False
    gateway_responding: bool = False
    skill_installed: bool = False
    agents_context_intact: bool = False
    trajectory_export_available: bool = False
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class HermesGatewayHealth:
    """Status of the configured Hermes gateway endpoint."""

    hive_attach_ready: bool = False
    responding: bool = False
    detail: str = ""


def _resolve_hermes_home(hermes_binary: str | None, hermes_home: str) -> str:
    """Resolve the effective Hermes home directory."""
    if hermes_home:
        return str(Path(hermes_home).expanduser())
    if hermes_binary:
        return str((Path.home() / ".hermes").expanduser())
    return ""


def _hermes_state_db_path(hermes_home: str) -> Path:
    """Return the Hermes SQLite session store path."""
    return Path(hermes_home).expanduser() / "state.db"


def _hermes_sessions_dir(hermes_home: str) -> Path:
    """Return the Hermes session transcript directory."""
    return Path(hermes_home).expanduser() / "sessions"


def _session_transcript_path(hermes_home: str, native_session_ref: str) -> Path:
    """Return the expected JSONL transcript path for a Hermes session."""
    return _hermes_sessions_dir(hermes_home) / f"{native_session_ref}.jsonl"


def _load_jsonl_records(path: Path, *, start_line: int = 0) -> list[tuple[int, dict[str, Any]]]:
    """Load JSON records from a JSONL transcript, preserving line numbers."""
    records: list[tuple[int, dict[str, Any]]] = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if line_no <= start_line:
                continue
            raw = line.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                records.append((line_no, payload))
    return records


def _connect_state_db_readonly(path: Path) -> sqlite3.Connection:
    """Open the Hermes state DB in read-only mode."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _load_sqlite_records(
    path: Path, native_session_ref: str
) -> list[tuple[int, dict[str, Any]]]:
    """Load Hermes conversation messages from the SQLite state store."""
    if not path.exists():
        return []
    try:
        conn = _connect_state_db_readonly(path)
    except sqlite3.Error:
        return []

    try:
        rows = conn.execute(
            """
            SELECT id, role, content, tool_call_id, tool_calls, tool_name,
                   timestamp, reasoning, reasoning_details, codex_reasoning_items
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp, id
            """,
            (native_session_ref,),
        ).fetchall()
    except sqlite3.Error:
        conn.close()
        return []

    records: list[tuple[int, dict[str, Any]]] = []
    for row in rows:
        payload = {
            "role": row["role"],
            "content": row["content"],
            "tool_call_id": row["tool_call_id"],
            "tool_name": row["tool_name"],
            "timestamp": row["timestamp"],
            "reasoning": row["reasoning"],
        }
        if row["tool_calls"]:
            try:
                payload["tool_calls"] = json.loads(row["tool_calls"])
            except (TypeError, json.JSONDecodeError):
                payload["tool_calls"] = row["tool_calls"]
        if row["reasoning_details"]:
            try:
                payload["reasoning_details"] = json.loads(row["reasoning_details"])
            except (TypeError, json.JSONDecodeError):
                payload["reasoning_details"] = row["reasoning_details"]
        if row["codex_reasoning_items"]:
            try:
                payload["codex_reasoning_items"] = json.loads(
                    row["codex_reasoning_items"]
                )
            except (TypeError, json.JSONDecodeError):
                payload["codex_reasoning_items"] = row["codex_reasoning_items"]
        records.append((int(row["id"]), payload))

    conn.close()
    return records


def _sqlite_session_exists(path: Path, native_session_ref: str) -> bool:
    """Return True when the Hermes state DB contains the requested session."""
    if not path.exists():
        return False
    try:
        conn = _connect_state_db_readonly(path)
        row = conn.execute(
            "SELECT 1 FROM sessions WHERE id = ? LIMIT 1",
            (native_session_ref,),
        ).fetchone()
        conn.close()
        return row is not None
    except sqlite3.Error:
        return False


def _list_sqlite_sessions(path: Path) -> list[dict[str, Any]]:
    """List Hermes sessions from the SQLite state store."""
    if not path.exists():
        return []
    try:
        conn = _connect_state_db_readonly(path)
        rows = conn.execute(
            """
            SELECT s.id,
                   s.source,
                   s.title,
                   s.started_at,
                   s.ended_at,
                   s.message_count,
                   COALESCE(MAX(m.timestamp), s.started_at) AS updated_at
            FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.id
            GROUP BY s.id
            ORDER BY updated_at DESC
            """
        ).fetchall()
        conn.close()
    except sqlite3.Error:
        return []

    return [
        {
            "native_session_ref": str(row["id"]),
            "source": row["source"],
            "title": row["title"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "message_count": int(row["message_count"] or 0),
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def _pending_actions_path(base_path: str | Path, delegate_session_id: str) -> Path:
    """Return the pending companion-action queue for an attached session."""
    from src.hive.integrations.openclaw import _delegates_dir

    session_dir = _delegates_dir(base_path) / delegate_session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir / _PENDING_ACTIONS_FILE


def _append_pending_action(
    base_path: str | Path,
    delegate_session_id: str,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Append a pending companion action and return the queued payload."""
    queue_path = _pending_actions_path(base_path, delegate_session_id)
    seq = 0
    if queue_path.exists():
        with queue_path.open("r", encoding="utf-8") as handle:
            seq = sum(1 for line in handle if line.strip())
    entry = {"seq": seq, **record}
    with queue_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def load_pending_actions(
    base_path: str | Path,
    delegate_session_id: str,
    *,
    since_seq: int = -1,
) -> list[dict[str, Any]]:
    """Load queued companion actions after the requested sequence number."""
    queue_path = _pending_actions_path(base_path, delegate_session_id)
    items: list[dict[str, Any]] = []
    if not queue_path.exists():
        return items
    with queue_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            seq = int(payload.get("seq", -1))
            if seq <= since_seq:
                continue
            if isinstance(payload, dict):
                items.append(payload)
    return items


def load_attached_hermes_session(
    base_path: str | Path,
    native_session_ref: str,
) -> SessionHandle | None:
    """Load a persisted attached Hermes delegate session by native session ref."""
    for manifest in list_delegate_sessions(base_path):
        if manifest.get("adapter_name") != "hermes":
            continue
        if manifest.get("native_session_ref") != native_session_ref:
            continue
        if manifest.get("status") != "attached":
            continue
        return SessionHandle(
            session_id=str(manifest.get("session_id") or new_id("dsess")),
            adapter_name="hermes",
            adapter_family=AdapterFamily.DELEGATE_GATEWAY,
            native_session_ref=native_session_ref,
            governance_mode=GovernanceMode(
                str(manifest.get("governance_mode") or GovernanceMode.ADVISORY)
            ),
            integration_level=IntegrationLevel(
                str(manifest.get("integration_level") or IntegrationLevel.ATTACH)
            ),
            delegate_session_id=str(manifest.get("delegate_session_id") or ""),
            project_id=manifest.get("project_id"),
            task_id=manifest.get("task_id"),
            status=str(manifest.get("status") or "attached"),
            attached_at=str(manifest.get("attached_at") or utc_now_iso()),
            metadata=dict(manifest.get("metadata") or {}),
        )
    return None


def _gateway_advertises_hive_attach(payload: Any) -> bool:
    """Return True when a health payload looks like a Hive-aware Hermes gateway."""
    if not isinstance(payload, dict):
        return False

    gateway_name = str(
        payload.get("gateway") or payload.get("service") or payload.get("name") or ""
    ).strip().lower()
    if gateway_name not in {"hermes", "hermes-gateway"}:
        return False

    feature_names: set[str] = set()
    capabilities = payload.get("capabilities") or payload.get("features") or {}
    if isinstance(capabilities, dict):
        feature_names = {
            str(name).strip().lower()
            for name, enabled in capabilities.items()
            if enabled
        }
    elif isinstance(capabilities, list):
        feature_names = {str(name).strip().lower() for name in capabilities}

    return bool(
        payload.get("hive_attach")
        or payload.get("hive_link")
        or "hive_attach" in feature_names
        or "hive_link" in feature_names
    )


def _check_gateway_health(gateway_url: str) -> HermesGatewayHealth:
    """Attempt an HTTP health check against a Hive-compatible Hermes gateway."""
    import urllib.request
    import urllib.error

    best_detail = ""
    saw_response = False

    # Try common health endpoints.
    for path in ("/health", "/api/health", "/"):
        try:
            url = gateway_url.rstrip("/") + path
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status >= 500:
                    continue

                saw_response = True
                try:
                    payload = json.loads(resp.read().decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    best_detail = (
                        f"Gateway at {gateway_url} responded on {path} but did not "
                        "return JSON health metadata."
                    )
                    continue

                if _gateway_advertises_hive_attach(payload):
                    return HermesGatewayHealth(
                        hive_attach_ready=True,
                        responding=True,
                        detail=(
                            f"Gateway at {gateway_url} advertises Hive-compatible "
                            "Hermes attach support."
                        ),
                    )

                best_detail = (
                    f"Gateway at {gateway_url} responded on {path} but did not "
                    "advertise Hive-compatible Hermes attach support."
                )
        except (urllib.error.URLError, OSError, ValueError):
            continue

    if saw_response:
        return HermesGatewayHealth(
            hive_attach_ready=False,
            responding=True,
            detail=best_detail
            or (
                f"Gateway at {gateway_url} responded but did not advertise "
                "Hive-compatible Hermes attach support."
            ),
        )

    return HermesGatewayHealth(
        hive_attach_ready=False,
        responding=False,
        detail=(
            f"Gateway at {gateway_url} is not reachable. "
            "Start the Hermes gateway and re-run: hive integrate hermes"
        ),
    )


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

    resolved_home = _resolve_hermes_home(hermes_binary, hermes_home)
    state_db_path = _hermes_state_db_path(resolved_home)
    sessions_dir = _hermes_sessions_dir(resolved_home)
    state_db_available = state_db_path.exists() and state_db_path.is_file()
    transcripts_available = sessions_dir.exists() and sessions_dir.is_dir()
    attach_supported = state_db_available or transcripts_available

    # Check for AGENTS.md context compatibility.
    root = Path(workspace_root or Path.cwd()).resolve()
    agents_path = root / "AGENTS.md"
    agents_intact = agents_path.exists()

    # Check if the skill bundle is loadable from the workspace.
    skill_dir = root / "packages" / "hermes-skill"
    skill_installed = (skill_dir / "manifest.json").exists()

    # Gateway reachability: actually probe when a URL is configured.
    gateway_configured = bool(gateway_url)
    gateway_health = HermesGatewayHealth()
    if gateway_configured:
        gateway_health = _check_gateway_health(gateway_url)
    gateway_reachable = gateway_health.hive_attach_ready

    blockers: list[str] = []
    if not attach_supported:
        blockers.append(
            f"Hermes session stores not found at {state_db_path} or {sessions_dir}. "
            "Attach requires a Hermes home with state.db and/or sessions/."
        )

    return HermesProbe(
        hermes_found=True,
        hermes_home=resolved_home,
        hermes_version="",  # Populated by actual version probe when available.
        state_db_path=str(state_db_path),
        state_db_available=state_db_available,
        sessions_dir=str(sessions_dir),
        attach_supported=attach_supported,
        gateway_url=gateway_url,
        gateway_reachable=gateway_reachable,
        gateway_responding=gateway_health.responding,
        skill_installed=skill_installed,
        agents_context_intact=agents_intact,
        trajectory_export_available=True,
        notes=[
            f"Hermes detected at {hermes_binary or resolved_home}.",
        ]
        + (
            [f"Hermes session DB found at {state_db_path}."]
            if state_db_available
            else []
        )
        + (
            [f"Session transcripts found at {sessions_dir}."]
            if transcripts_available
            else []
        )
        + (
            [gateway_health.detail] if gateway_configured else []
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


def _message_text(message: dict[str, Any]) -> str:
    """Extract a readable text payload from a Hermes transcript message."""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(part for part in parts if part)
    return str(message.get("text") or "")


def _coerce_iso_timestamp(value: Any) -> str:
    """Normalize Hermes timestamps into ISO-8601 strings."""
    if isinstance(value, (int, float)):
        return (
            datetime.fromtimestamp(float(value), tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
    if isinstance(value, str) and value.strip():
        return value
    return utc_now_iso()


def _normalize_session_message(
    message: dict[str, Any],
    *,
    raw_ref: str,
    session: SessionHandle,
) -> list[dict[str, Any]]:
    """Convert one Hermes session message into one or more Hive events."""
    role = str(message.get("role") or "").strip().lower()
    ts = _coerce_iso_timestamp(message.get("ts") or message.get("timestamp"))
    base = {
        "ts": ts,
        "harness": "hermes",
        "adapter_family": "delegate_gateway",
        "native_session_ref": session.native_session_ref,
        "delegate_session_id": session.delegate_session_id,
        "project_id": session.project_id,
        "task_id": session.task_id,
        "raw_ref": raw_ref,
    }

    events: list[dict[str, Any]] = []
    text = _message_text(message)
    if role == "user":
        events.append(
            {
                **base,
                "kind": "user_message",
                "payload": {"content": text, "raw": message},
            }
        )
    elif role == "assistant":
        if text:
            events.append(
                {
                    **base,
                    "kind": "assistant_delta",
                    "payload": {"content": text, "raw": message},
                }
            )
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list):
            for tool_call in tool_calls:
                if not isinstance(tool_call, dict):
                    continue
                events.append(
                    {
                        **base,
                        "kind": "tool_call_start",
                        "payload": {"tool_call": tool_call, "raw": message},
                    }
                )
    elif role == "tool":
        events.append(
            {
                **base,
                "kind": "tool_call_end",
                "payload": {"content": text, "raw": message},
            }
        )
    else:
        kind = _normalize_hermes_event_kind(str(message.get("kind") or role))
        events.append(
            {
                **base,
                "kind": kind,
                "payload": {"content": text, "raw": message},
            }
        )
    return events


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
        available = hermes_probe.hermes_found and hermes_probe.attach_supported
        return CapabilitySnapshot(
            driver=self.name,
            driver_version=hermes_probe.hermes_version or "0.0.0",
            declared=capability_surface(
                launch_mode="session_store",
                session_persistence="persistent",
                event_stream="structured_deltas",
                attach_supported=True,
                steering="poll",
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
                launch_mode="session_store" if available else "none",
                session_persistence="persistent" if available else "none",
                event_stream="structured_deltas" if available else "none",
                attach_supported=available,
                steering="poll" if available else "none",
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
                "state_db_path": hermes_probe.state_db_path,
                "state_db_available": hermes_probe.state_db_available,
                "sessions_dir": hermes_probe.sessions_dir,
                "attach_supported": hermes_probe.attach_supported,
                "gateway_url": hermes_probe.gateway_url,
                "gateway_reachable": hermes_probe.gateway_reachable,
                "gateway_responding": hermes_probe.gateway_responding,
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
                "launch_mode": (
                    "Hermes session history is available via "
                    f"{hermes_probe.state_db_path or '(missing state.db)'} "
                    f"and/or {hermes_probe.sessions_dir}."
                )
                if available
                else (
                    "Hermes detected but the session store is not available."
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
            available=hermes_probe.hermes_found and hermes_probe.attach_supported,
            capability_snapshot=self._capability_snapshot(hermes_probe),
            notes=[
                *hermes_probe.notes,
                *[f"blocker: {b}" for b in hermes_probe.blockers],
                "Managed mode is deferred from v2.4.",
                "Private Hermes memory is never bulk-imported.",
            ],
        )

    def list_sessions(self) -> list[dict[str, Any]]:
        hermes_probe = self._hermes_probe()
        if not hermes_probe.attach_supported:
            return []
        sessions: dict[str, dict[str, Any]] = {}

        state_db_path = Path(hermes_probe.state_db_path)
        for row in _list_sqlite_sessions(state_db_path):
            sessions[row["native_session_ref"]] = {
                **row,
                "state_db_path": str(state_db_path),
            }

        sessions_root = Path(hermes_probe.sessions_dir)
        if sessions_root.exists():
            for transcript_path in sessions_root.glob("*.jsonl"):
                stat = transcript_path.stat()
                row = sessions.setdefault(
                    transcript_path.stem,
                    {
                        "native_session_ref": transcript_path.stem,
                        "message_count": 0,
                        "updated_at": stat.st_mtime,
                    },
                )
                row["transcript_path"] = str(transcript_path)
                row["size_bytes"] = stat.st_size
                row["updated_at"] = max(float(row.get("updated_at", 0) or 0), stat.st_mtime)

        return sorted(
            sessions.values(),
            key=lambda item: float(item.get("updated_at", 0) or 0),
            reverse=True,
        )

    def _transcript_path(self, session: SessionHandle) -> Path:
        raw = str(session.metadata.get("transcript_path") or "").strip()
        if raw:
            return Path(raw)
        hermes_probe = self._hermes_probe()
        return _session_transcript_path(hermes_probe.hermes_home, session.native_session_ref)

    def _state_db_path(self, session: SessionHandle) -> Path:
        raw = str(session.metadata.get("state_db_path") or "").strip()
        if raw:
            return Path(raw)
        hermes_probe = self._hermes_probe()
        return _hermes_state_db_path(hermes_probe.hermes_home)

    def _load_session_records(
        self, session: SessionHandle
    ) -> tuple[str, list[tuple[int, dict[str, Any]]]]:
        """Load the richest available Hermes session history for this attach."""
        sqlite_records = _load_sqlite_records(
            self._state_db_path(session),
            session.native_session_ref,
        )
        transcript_records = _load_jsonl_records(self._transcript_path(session))

        if len(sqlite_records) >= len(transcript_records) and sqlite_records:
            return "sqlite", sqlite_records
        if transcript_records:
            return "jsonl", transcript_records
        return "none", []

    def _persist_session_state(
        self,
        session: SessionHandle,
        *,
        capability_snapshot: CapabilitySnapshot | None = None,
    ) -> None:
        if not self._base_path or not session.delegate_session_id:
            return
        persist_delegate_session(
            self._base_path,
            session,
            capability_snapshot=capability_snapshot,
        )

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
        if not hermes_probe.attach_supported:
            raise ConnectionError(
                "Cannot attach: Hermes session storage not available. "
                + (
                    hermes_probe.blockers[0]
                    if hermes_probe.blockers
                    else "Set HERMES_HOME to a real Hermes home directory."
                )
            )
        state_db_path = _hermes_state_db_path(hermes_probe.hermes_home)
        transcript_path = _session_transcript_path(
            hermes_probe.hermes_home,
            native_session_ref,
        )
        transcript_exists = transcript_path.exists()
        session_in_state_db = _sqlite_session_exists(state_db_path, native_session_ref)
        if not transcript_exists and not session_in_state_db:
            raise ConnectionError(
                "Cannot attach: Hermes session not found in the configured "
                "Hermes stores. "
                f"Checked {state_db_path} and {transcript_path}."
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
            metadata={
                "hermes_home": hermes_probe.hermes_home,
                "state_db_path": str(state_db_path),
                "transcript_path": str(transcript_path) if transcript_exists else "",
                "message_cursor": 0,
                "event_seq": 0,
                "session_started_emitted": False,
            },
        )
        self._sessions[native_session_ref] = session

        self._persist_session_state(
            session,
            capability_snapshot=self._capability_snapshot(hermes_probe),
        )

        return session

    def stream_events(self, session: SessionHandle) -> Iterator[dict[str, Any]]:
        from src.hive.trajectory.schema import trajectory_event
        from src.hive.trajectory.writer import append_trajectory_event

        transcript_path = self._transcript_path(session)
        state_db_path = self._state_db_path(session)
        message_cursor = int(
            session.metadata.get("message_cursor", session.metadata.get("line_cursor", 0))
            or 0
        )
        event_seq = int(session.metadata.get("event_seq", 0) or 0)
        pending_events: list[dict[str, Any]] = []
        store_kind, records = self._load_session_records(session)
        store_ref = (
            str(state_db_path)
            if store_kind == "sqlite"
            else str(transcript_path)
        )
        session_start_payload = {
            "mode": "attach",
            "governance": "advisory",
            "store_kind": store_kind if store_kind != "none" else "unknown",
        }
        if store_kind == "sqlite":
            session_start_payload["state_db_path"] = str(state_db_path)
        else:
            session_start_payload["transcript_path"] = str(transcript_path)

        if not session.metadata.get("session_started_emitted"):
            pending_events.append(
                {
                    "seq": event_seq,
                    "kind": "session_start",
                    "ts": utc_now_iso(),
                    "harness": "hermes",
                    "adapter_family": "delegate_gateway",
                    "native_session_ref": session.native_session_ref,
                    "delegate_session_id": session.delegate_session_id,
                    "project_id": session.project_id,
                    "task_id": session.task_id,
                    "payload": session_start_payload,
                    "raw_ref": store_ref,
                }
            )
            event_seq += 1
            session.metadata["session_started_emitted"] = True

        if message_cursor > len(records):
            message_cursor = 0

        for record_ref, message in records[message_cursor:]:
            raw_ref = (
                f"sqlite:{session.native_session_ref}:{record_ref}"
                if store_kind == "sqlite"
                else f"{transcript_path}:{record_ref}"
            )
            normalized = _normalize_session_message(
                message,
                raw_ref=raw_ref,
                session=session,
            )
            for event in normalized:
                pending_events.append({"seq": event_seq, **event})
                event_seq += 1

        session.metadata["message_cursor"] = len(records)
        session.metadata["event_seq"] = event_seq
        session.metadata["last_store_kind"] = store_kind
        self._persist_session_state(session)

        for event in pending_events:
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
                        raw_ref=event.get("raw_ref"),
                        ts=str(event.get("ts") or utc_now_iso()),
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
            queued = _append_pending_action(
                self._base_path,
                session.delegate_session_id,
                {
                    "ts": record["ts"],
                    "action_type": request.action,
                    "payload": {
                        "reason": request.reason,
                        "note": request.note,
                        "target": request.target,
                    },
                },
            )
            return {
                "ok": True,
                "adapter": self.name,
                "queued": True,
                "delivered": False,
                "delivery": "pending_companion_poll",
                "pending_action": queued,
                **record,
            }
        return {
            "ok": False,
            "adapter": self.name,
            "queued": False,
            "delivered": False,
            "error": "No Hive base path configured for steering persistence.",
            **record,
        }

    def publish_note(self, session: SessionHandle, note: str) -> dict[str, Any]:
        record = {"ts": utc_now_iso(), "action": "note", "note": note}
        if self._base_path and session.delegate_session_id:
            append_delegate_steering(
                self._base_path,
                session.delegate_session_id,
                record,
            )
            queued = _append_pending_action(
                self._base_path,
                session.delegate_session_id,
                {
                    "ts": record["ts"],
                    "action_type": "note",
                    "payload": {"note": note},
                },
            )
            return {
                "ok": True,
                "adapter": self.name,
                "queued": True,
                "delivered": False,
                "delivery": "pending_companion_poll",
                "pending_action": queued,
                **record,
            }
        return {
            "ok": False,
            "adapter": self.name,
            "queued": False,
            "delivered": False,
            "error": "No Hive base path configured for note persistence.",
            **record,
        }

    def collect_artifacts(self, session: SessionHandle) -> dict[str, Any]:
        from src.hive.integrations.openclaw import _delegates_dir

        artifacts = []
        if self._base_path and session.delegate_session_id:
            session_dir = _delegates_dir(self._base_path) / session.delegate_session_id
            for name in (
                "trajectory.jsonl",
                "steering.ndjson",
                _PENDING_ACTIONS_FILE,
                "manifest.json",
            ):
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
    "load_attached_hermes_session",
    "load_pending_actions",
]

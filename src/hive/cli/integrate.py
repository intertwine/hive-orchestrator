"""CLI handler for `hive integrate` commands."""

from __future__ import annotations

from pathlib import Path

from src.hive.cli.common import emit, emit_error
from src.hive.runs.engine import load_run, start_run
from src.hive.integrations.registry import (
    get_integration,
    list_all_backends,
    list_integrations,
)
from src.hive.workspace import sync_workspace


def dispatch(args, root: Path) -> int:
    """Dispatch integrate subcommands."""
    try:
        if args.integrate_command == "list":
            backends = list_all_backends()
            return emit({"ok": True, "backends": backends}, args.json)

        if args.integrate_command == "doctor":
            if args.name:
                adapter = get_integration(args.name)
                info = adapter.probe()
                entries = [info.to_dict()]
            else:
                entries = [a.probe().to_dict() for a in list_integrations()]
                if not entries:
                    entries = []
            return emit(
                {
                    "ok": True,
                    "message": "Integration doctor inspected the v2.4 adapter surface.",
                    "integrations": entries,
                },
                args.json,
            )
        if args.integrate_command == "pi":
            adapter = get_integration("pi")
            info = adapter.probe()
            return emit(
                {
                    "ok": True,
                    "message": "Pi setup assistant inspected the local companion and workspace readiness.",
                    "integration": info.to_dict(),
                    "next_steps": info.next_steps,
                },
                args.json,
            )

        if args.integrate_command == "openclaw":
            return _integrate_openclaw(args, root)

        if args.integrate_command == "attach":
            return _attach_session(args, root)

        if args.integrate_command == "detach":
            return _detach_session(args, root)

    except (FileNotFoundError, ValueError, ConnectionError) as exc:
        return emit_error(exc, args.json)
    return 0


def _integrate_openclaw(args, root: Path) -> int:
    """Run the OpenClaw integration setup/check flow."""
    from src.hive.integrations.openclaw import OpenClawGatewayAdapter

    adapter = OpenClawGatewayAdapter(base_path=root)
    info = adapter.probe()
    probe_dict = info.to_dict()
    snapshot = info.capability_snapshot
    probed = snapshot.probed if snapshot else {}

    bridge_found = bool(
        probed.get(
            "bridge_reachable",
            snapshot.probed.get("bridge_reachable") if snapshot else False,
        )
    )
    gateway_ok = bool(probed.get("gateway_reachable"))
    sessions_ok = bool(probed.get("sessions_accessible"))
    steering_ok = bool(probed.get("steering_supported", False))
    connection_scope = str(
        probed.get("connection_scope") or probed.get("connection_mode") or ""
    )

    next_steps: list[str] = []
    if not bridge_found:
        status_msg = "bridge not found"
        next_steps.append("npm install -g openclaw-hive-bridge")
        next_steps.append("Then re-run: hive integrate openclaw")
    elif not gateway_ok:
        status_msg = "bridge found, gateway not reachable"
        next_steps.append(
            "Set OPENCLAW_GATEWAY_URL and start the bridge: "
            "openclaw-hive-bridge --gateway <url> --stdio"
        )
        next_steps.append("Then re-run: hive integrate openclaw")
    elif not sessions_ok:
        status_msg = "gateway reachable, session listing unavailable"
        next_steps.append("Verify OpenClaw gateway auth and permissions for session tools.")
        next_steps.append("Then re-run: hive integrate doctor openclaw --json")
    elif not steering_ok:
        status_msg = "gateway reachable, steering unavailable"
        next_steps.append("Verify OpenClaw gateway auth and permissions for chat tools.")
        next_steps.append("Then re-run: hive integrate doctor openclaw --json")
    else:
        status_msg = "ready"
        next_steps.append(
            "Attach a session: hive integrate attach openclaw <session-key>"
        )
        next_steps.append("hive integrate doctor openclaw --json")
    if connection_scope:
        next_steps.append(f"Connection scope detected: {connection_scope}")

    return emit(
        {
            "ok": True,
            "message": f"OpenClaw integration: {status_msg}.",
            "integration": probe_dict,
            "next_steps": next_steps,
        },
        args.json,
    )


def _attach_session(args, root: Path) -> int:
    """Manually attach a native session to Hive as a delegate."""
    from src.hive.integrations.base import DelegateGatewayAdapter, WorkerSessionAdapter
    from src.hive.integrations.models import GovernanceMode
    from src.hive.integrations.openclaw import OpenClawGatewayAdapter

    adapter = get_integration(args.harness)

    if isinstance(adapter, WorkerSessionAdapter):
        task_id = str(getattr(args, "task_id", "") or "").strip()
        if not task_id:
            return emit_error(
                ValueError(f"{args.harness} attach requires --task-id so Hive can create a run."),
                args.json,
            )
        run = start_run(
            root,
            task_id,
            driver_name=args.harness,
            attach_native_session_ref=args.native_session_ref,
        )
        sync_workspace(root)
        run_metadata = load_run(root, run.id)
        session = dict(
            (run_metadata.get("metadata_json", {}).get("driver_status", {}) or {}).get("session", {})
        )
        return emit(
            {
                "ok": True,
                "message": (
                    f"Attached {args.native_session_ref} as an advisory "
                    f"{args.harness}-backed run."
                ),
                "run": run.to_dict(),
                "session": session,
            },
            args.json,
        )

    if not isinstance(adapter, DelegateGatewayAdapter):
        return emit_error(
            ValueError(f"{args.harness} is not a delegate-gateway adapter."),
            args.json,
        )

    # Re-instantiate with base_path for delegate persistence.
    if isinstance(adapter, OpenClawGatewayAdapter):
        adapter = OpenClawGatewayAdapter(base_path=root)

    session = adapter.attach_delegate_session(
        args.native_session_ref,
        GovernanceMode.ADVISORY,
        project_id=getattr(args, "project_id", None),
        task_id=getattr(args, "task_id", None),
    )
    return emit(
        {
            "ok": True,
            "message": f"Attached {args.native_session_ref} as advisory delegate session.",
            "session": session.to_dict(),
        },
        args.json,
    )


def _detach_session(args, root: Path) -> int:
    """Detach a delegate session through the owning adapter."""
    from src.hive.integrations.models import (
        AdapterFamily,
        GovernanceMode,
        IntegrationLevel,
        SessionHandle,
    )
    from src.hive.integrations.openclaw import OpenClawGatewayAdapter, load_delegate_session

    manifest = load_delegate_session(root, args.session_id)
    if manifest is None:
        return emit_error(
            ValueError(f"No delegate session found: {args.session_id}"),
            args.json,
        )

    adapter_name = str(manifest.get("adapter_name") or "")
    if adapter_name != "openclaw":
        return emit_error(
            ValueError(f"Unsupported delegate adapter for detach: {adapter_name or '(unknown)'}"),
            args.json,
        )

    adapter = OpenClawGatewayAdapter(base_path=root)
    session = SessionHandle(
        session_id=str(manifest.get("session_id") or manifest["delegate_session_id"]),
        adapter_name=adapter_name,
        adapter_family=AdapterFamily(str(manifest.get("adapter_family") or "delegate_gateway")),
        native_session_ref=str(manifest["native_session_ref"]),
        governance_mode=GovernanceMode(
            str(manifest.get("governance_mode") or GovernanceMode.ADVISORY)
        ),
        integration_level=IntegrationLevel(
            str(manifest.get("integration_level") or IntegrationLevel.ATTACH)
        ),
        delegate_session_id=str(manifest["delegate_session_id"]),
        project_id=manifest.get("project_id"),
        task_id=manifest.get("task_id"),
        status=str(manifest.get("status") or "attached"),
        attached_at=str(manifest.get("attached_at") or ""),
        metadata=dict(manifest.get("metadata") or {}),
    )
    try:
        result = adapter.detach_delegate_session(session)
    except ConnectionError as exc:
        return emit_error(exc, args.json)

    return emit(
        {
            "ok": True,
            "message": f"Detached delegate session {args.session_id}.",
            "session_id": args.session_id,
            "result": result,
        },
        args.json,
    )

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

        if args.integrate_command == "hermes":
            return _integrate_hermes(args, root)

        if args.integrate_command == "import-trajectory":
            return _import_trajectory(args, root)

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
    else:
        status_msg = "ready"
        next_steps.append(
            "Attach a session: hive integrate attach openclaw <session-key>"
        )
        next_steps.append("hive integrate doctor openclaw --json")

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
                ValueError(
                    f"{args.harness} attach requires --task-id so Hive can create a run."
                ),
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
            (run_metadata.get("metadata_json", {}).get("driver_status", {}) or {}).get(
                "session", {}
            )
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
    from src.hive.integrations.hermes import HermesGatewayAdapter

    if isinstance(adapter, OpenClawGatewayAdapter):
        adapter = OpenClawGatewayAdapter(base_path=root)
    elif isinstance(adapter, HermesGatewayAdapter):
        adapter = HermesGatewayAdapter(base_path=root)

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
    """Detach a delegate session, updating both manifest and final state."""
    import json as _json

    from src.hive.clock import utc_now_iso
    from src.hive.integrations.openclaw import (
        _delegates_dir,
        finalize_delegate_session,
        load_delegate_session,
    )

    manifest = load_delegate_session(root, args.session_id)
    if manifest is None:
        return emit_error(
            ValueError(f"No delegate session found: {args.session_id}"),
            args.json,
        )

    ts = utc_now_iso()

    # Update manifest.json to reflect detached status.
    manifest_path = _delegates_dir(root) / args.session_id / "manifest.json"
    if manifest_path.exists():
        manifest["status"] = "detached"
        manifest_path.write_text(
            _json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    finalize_delegate_session(
        root,
        args.session_id,
        {
            "status": "detached",
            "detached_at": ts,
            "reason": "operator-initiated",
        },
    )

    return emit(
        {
            "ok": True,
            "message": f"Detached delegate session {args.session_id}.",
            "session_id": args.session_id,
        },
        args.json,
    )


def _integrate_hermes(args, root: Path) -> int:
    """Run the Hermes integration setup/check flow."""
    from src.hive.integrations.hermes import HermesGatewayAdapter

    adapter = HermesGatewayAdapter(base_path=root)
    info = adapter.probe()
    probe_dict = info.to_dict()
    snapshot = info.capability_snapshot
    probed = snapshot.probed if snapshot else {}

    hermes_found = bool(probed.get("hermes_found"))
    gateway_ok = bool(probed.get("gateway_reachable"))
    gateway_responding = bool(probed.get("gateway_responding"))

    next_steps: list[str] = []
    if not hermes_found:
        status_msg = "Hermes not found"
        next_steps.append("Install Hermes or set HERMES_HOME.")
        next_steps.append("Then re-run: hive integrate hermes")
    elif gateway_responding and not gateway_ok:
        status_msg = "Hermes found, gateway not Hive-compatible"
        next_steps.append(
            "Enable Hive-compatible attach support in the Hermes gateway and re-run: hive integrate hermes"
        )
        next_steps.append(
            "Or import an export instead: hive integrate import-trajectory hermes <path>"
        )
    elif not gateway_ok:
        status_msg = "Hermes found, gateway not reachable"
        next_steps.append("Set HERMES_GATEWAY_URL and re-run: hive integrate hermes")
    else:
        status_msg = "ready"
        if not probed.get("skill_installed"):
            next_steps.append(
                "Load the agent-hive skill in Hermes from packages/hermes-skill/"
            )
        next_steps.append("Attach a session: hive integrate attach hermes <session-id>")
        next_steps.append("hive integrate doctor hermes --json")

    return emit(
        {
            "ok": True,
            "message": f"Hermes integration: {status_msg}.",
            "integration": probe_dict,
            "next_steps": next_steps,
        },
        args.json,
    )


def _import_trajectory(args, root: Path) -> int:
    """Import a Hermes trajectory export into Hive."""
    from src.hive.integrations.hermes import import_hermes_trajectory

    result = import_hermes_trajectory(
        root,
        args.source_path,
        project_id=getattr(args, "project_id", None),
        task_id=getattr(args, "task_id", None),
    )
    return emit(
        {
            "ok": True,
            "message": f"Imported {result['event_count']} events from {args.source_path}.",
            **result,
        },
        args.json,
    )

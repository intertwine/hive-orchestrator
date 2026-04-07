"""Shared console action registry, descriptors, and execution helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from src.hive.drivers import SteeringRequest
from src.hive.runs.engine import steer_run
from src.hive.workspace import sync_workspace


_RUN_TERMINAL_STATUSES = {"accepted", "cancelled", "failed", "rejected"}
_REROUTE_BLOCKED_STATUSES = {"accepted", "cancelled", "failed"}


class ConsoleActionError(Exception):
    """Execution error that API adapters can translate into transport errors."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _read_request_field(request: Any, field: str) -> Any:
    if isinstance(request, Mapping):
        return request.get(field)
    return getattr(request, field, None)


def _live_steer_unavailable_reason(launch_mode: str, session_persistence: str) -> str:
    if launch_mode == "":
        return (
            "Unavailable because this run predates capability snapshots "
            "or the snapshot is missing, so live session status is unknown."
        )
    if launch_mode == "staged":
        return (
            "Unavailable because this run is staged rather than attached "
            "to a live driver session."
        )
    if session_persistence == "none":
        return "Unavailable because this run is not attached to a persistent live driver session."
    return "Unavailable because this run is not live-steerable."


def _action_record(
    *,
    action_id: str | None = None,
    instance_id: str,
    title: str,
    description: str,
    group: str,
    operation: str,
    availability_reason: str,
    availability_source: str,
    enabled: bool = True,
    visible: bool = True,
    tone: str = "secondary",
    button_label: str | None = None,
    keywords: list[str] | None = None,
    href: str | None = None,
    run_id: str | None = None,
    approval_id: str | None = None,
    input_mode: str = "none",
    success_message: str | None = None,
    failure_message: str | None = None,
) -> dict[str, Any]:
    record = {
        "id": instance_id,
        "title": title,
        "description": description,
        "group": group,
        "operation": operation,
        "enabled": enabled,
        "visible": visible,
        "tone": tone,
        "availability_reason": availability_reason,
        "availability_source": availability_source,
        "input_mode": input_mode,
    }
    if action_id:
        record["action_id"] = action_id
    if button_label:
        record["button_label"] = button_label
    if keywords:
        record["keywords"] = keywords
    if href:
        record["href"] = href
    if run_id:
        record["run_id"] = run_id
    if approval_id:
        record["approval_id"] = approval_id
    if success_message:
        record["success_message"] = success_message
    if failure_message:
        record["failure_message"] = failure_message
    return record


def build_run_actions(
    *,
    run_id: str,
    run_status: str,
    run_health: str,
    launch_mode: str,
    session_persistence: str,
) -> list[dict[str, Any]]:
    """Return shared action descriptors for the run-detail command surfaces."""
    can_live_steer = (
        launch_mode != ""
        and launch_mode != "staged"
        and session_persistence != "none"
    )
    live_steer_message = (
        None if can_live_steer else _live_steer_unavailable_reason(launch_mode, session_persistence)
    )
    can_pause = can_live_steer and run_health != "paused"
    can_resume = can_live_steer and run_health == "paused"
    can_note = can_live_steer
    can_cancel = run_status not in _RUN_TERMINAL_STATUSES
    can_reroute = run_status not in _REROUTE_BLOCKED_STATUSES

    return [
        _action_record(
            action_id="run.pause",
            instance_id=f"run.pause:{run_id}",
            title="Pause",
            description="Pause a live attached run without losing the current execution context.",
            group="Run controls",
            operation="execute",
            tone="primary",
            enabled=can_pause,
            visible=can_pause,
            availability_reason=(
                "Available because the run is live, steerable, and not already paused."
                if can_pause
                else live_steer_message or "Unavailable because the run is already paused."
            ),
            availability_source="run capability snapshot",
            keywords=["pause", run_status, run_health],
            run_id=run_id,
            input_mode="reason_note",
            success_message=f"Sent pause for {run_id}.",
            failure_message="Unable to pause run.",
        ),
        _action_record(
            action_id="run.resume",
            instance_id=f"run.resume:{run_id}",
            title="Resume",
            description="Resume a paused live run from the command center.",
            group="Run controls",
            operation="execute",
            enabled=can_resume,
            visible=can_resume,
            availability_reason=(
                "Available because the run is live and currently paused."
                if can_resume
                else live_steer_message or "Unavailable because the run is not paused."
            ),
            availability_source="run capability snapshot",
            keywords=["resume", run_status, run_health],
            run_id=run_id,
            input_mode="reason_note",
            success_message=f"Sent resume for {run_id}.",
            failure_message="Unable to resume run.",
        ),
        _action_record(
            action_id="run.note",
            instance_id=f"run.note:{run_id}",
            title="Add Note",
            description="Append an operator note to the live run audit trail.",
            group="Run controls",
            operation="execute",
            enabled=can_note,
            visible=can_note,
            availability_reason=(
                "Available because the run supports live annotations."
                if can_note
                else live_steer_message or "Unavailable for this run."
            ),
            availability_source="run capability snapshot",
            keywords=["note", "annotate", run_status, run_health],
            run_id=run_id,
            input_mode="reason_note",
            success_message=f"Sent note for {run_id}.",
            failure_message="Unable to add note.",
        ),
        _action_record(
            action_id="run.cancel",
            instance_id=f"run.cancel:{run_id}",
            title="Cancel",
            description="Cancel the run from Hive's side and record the operator intent.",
            group="Run controls",
            operation="execute",
            tone="danger",
            enabled=can_cancel,
            visible=can_cancel,
            availability_reason=(
                "Available because the run is not yet terminal."
                if can_cancel
                else "Unavailable for accepted, cancelled, failed, or rejected runs."
            ),
            availability_source="run status",
            keywords=["cancel", run_status, run_health],
            run_id=run_id,
            input_mode="reason_note",
            success_message=f"Sent cancel for {run_id}.",
            failure_message="Unable to cancel run.",
        ),
        _action_record(
            action_id="run.reroute",
            instance_id=f"run.reroute:{run_id}",
            title="Reroute",
            description="Reroute this run to a different driver.",
            group="Run controls",
            operation="execute",
            tone="primary",
            enabled=can_reroute,
            visible=can_reroute,
            availability_reason=(
                "Available because the run can still move to a different driver."
                if can_reroute
                else "Unavailable for accepted, cancelled, or failed runs."
            ),
            availability_source="run status",
            keywords=["reroute", run_status, run_health],
            run_id=run_id,
            input_mode="reroute",
            success_message=f"Sent reroute for {run_id}.",
            failure_message="Unable to reroute run.",
        ),
    ]


def build_approval_actions(run_id: str, approvals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annotate pending approvals with shared action descriptors."""
    annotated: list[dict[str, Any]] = []
    for approval in approvals:
        approval_copy = dict(approval)
        approval_id = str(approval.get("approval_id") or "approval")
        approval_title = str(approval.get("title") or approval_id)
        is_pending = str(approval.get("status") or "pending") == "pending"
        availability_reason = (
            f"Available because {approval_title} is still pending."
            if is_pending
            else f"Unavailable because {approval_title} has already been resolved."
        )
        approval_copy["actions"] = [
            _action_record(
                action_id="approval.approve",
                instance_id=f"approval.approve:{approval_id}",
                title=f"Approve {approval_title}",
                button_label="Approve",
                description=str(approval.get("summary") or "Approve this pending request."),
                group="Approvals",
                operation="execute",
                tone="primary",
                enabled=is_pending,
                visible=is_pending,
                availability_reason=availability_reason,
                availability_source="pending approval request",
                keywords=["approve", approval_id, approval_title],
                run_id=run_id,
                approval_id=approval_id,
                input_mode="note",
                success_message=f"Approved {approval_title} for {run_id}.",
                failure_message="Unable to approve approval.",
            ),
            _action_record(
                action_id="approval.reject",
                instance_id=f"approval.reject:{approval_id}",
                title=f"Reject {approval_title}",
                button_label="Reject",
                description=str(approval.get("summary") or "Reject this pending request."),
                group="Approvals",
                operation="execute",
                enabled=is_pending,
                visible=is_pending,
                availability_reason=availability_reason,
                availability_source="pending approval request",
                keywords=["reject", approval_id, approval_title],
                run_id=run_id,
                approval_id=approval_id,
                input_mode="note",
                success_message=f"Rejected {approval_title} for {run_id}.",
                failure_message="Unable to reject approval.",
            ),
        ]
        annotated.append(approval_copy)
    return annotated


def build_attention_actions(item: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return shared action descriptors for an attention item."""
    item_id = str(item.get("id") or "attention")
    title = str(item.get("title") or "Attention item")
    run_id = str(item.get("run_id") or "") or None
    approval_id = str(item.get("approval_id") or "") or None
    deep_link = str(item.get("deep_link") or "") or None
    actions: list[dict[str, Any]] = []

    if deep_link:
        actions.append(
            _action_record(
                instance_id=f"attention.open:{item_id}",
                title=f"Open {title}",
                button_label="Open run" if run_id else "Open details",
                description=f"Jump into the canonical detail surface for {title}.",
                group="Inbox triage",
                operation="navigate",
                availability_reason="Available because this item has a canonical deep link.",
                availability_source="attention item",
                keywords=[
                    title,
                    str(item.get("project_label") or ""),
                    str(item.get("decision_type") or ""),
                ],
                href=deep_link,
            ),
        )

    if run_id and approval_id:
        summary = str(item.get("summary") or "Resolve this pending approval.")
        actions.extend(
            [
                _action_record(
                    action_id="approval.approve",
                    instance_id=f"approval.approve:{item_id}",
                    title=f"Approve {title}",
                    button_label="Approve",
                    description=summary,
                    group="Inbox approvals",
                    operation="execute",
                    tone="primary",
                    availability_reason=(
                        "Available because this attention item is a pending approval."
                    ),
                    availability_source="pending approval",
                    keywords=[
                        title,
                        str(item.get("project_label") or ""),
                        str(item.get("run_label") or ""),
                    ],
                    run_id=run_id,
                    approval_id=approval_id,
                    input_mode="note",
                    success_message=f"Approved {title}.",
                    failure_message="Unable to approve approval.",
                ),
                _action_record(
                    action_id="approval.reject",
                    instance_id=f"approval.reject:{item_id}",
                    title=f"Reject {title}",
                    button_label="Reject",
                    description=summary,
                    group="Inbox approvals",
                    operation="execute",
                    availability_reason=(
                        "Available because this attention item is a pending approval."
                    ),
                    availability_source="pending approval",
                    keywords=[
                        title,
                        str(item.get("project_label") or ""),
                        str(item.get("run_label") or ""),
                    ],
                    run_id=run_id,
                    approval_id=approval_id,
                    input_mode="note",
                    success_message=f"Rejected {title}.",
                    failure_message="Unable to reject approval.",
                ),
            ]
        )

    return actions


def _execute_steering_request(
    root: Path, run_id: str, request: SteeringRequest, actor: str | None
) -> dict[str, Any]:
    sync_workspace(root)
    try:
        payload = steer_run(root, run_id, request, actor=actor)
    except FileNotFoundError as exc:
        raise ConsoleActionError(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise ConsoleActionError(status_code=400, detail=str(exc)) from exc
    sync_workspace(root)
    return payload


def execute_console_action(root: Path, request: Any) -> dict[str, Any]:
    """Execute a typed console action through the shared action registry."""
    action_id = str(_read_request_field(request, "action_id") or "")
    run_action_map = {
        "run.pause": "pause",
        "run.resume": "resume",
        "run.note": "note",
        "run.cancel": "cancel",
        "run.reroute": "reroute",
    }
    approval_action_map = {
        "approval.approve": "approve",
        "approval.reject": "reject",
    }

    if action_id in run_action_map:
        run_id = str(_read_request_field(request, "run_id") or "")
        if not run_id:
            raise ConsoleActionError(
                status_code=400,
                detail="run_id is required for run actions.",
            )
        payload = _execute_steering_request(
            root,
            run_id,
            SteeringRequest(
                action=run_action_map[action_id],
                reason=_read_request_field(request, "reason"),
                target=_read_request_field(request, "target"),
                budget_delta=_read_request_field(request, "budget_delta"),
                note=_read_request_field(request, "note"),
            ),
            actor=_read_request_field(request, "actor"),
        )
        return {"ok": True, "action_id": action_id, **payload}

    if action_id in approval_action_map:
        run_id = str(_read_request_field(request, "run_id") or "")
        approval_id = str(_read_request_field(request, "approval_id") or "")
        if not run_id or not approval_id:
            raise ConsoleActionError(
                status_code=400,
                detail="run_id and approval_id are required for approval actions.",
            )
        payload = _execute_steering_request(
            root,
            run_id,
            SteeringRequest(
                action=approval_action_map[action_id],
                reason=_read_request_field(request, "reason"),
                target={"approval_id": approval_id},
                note=_read_request_field(request, "note"),
            ),
            actor=_read_request_field(request, "actor") or "operator",
        )
        return {"ok": True, "action_id": action_id, **payload}

    raise ConsoleActionError(
        status_code=400,
        detail=f"Unknown console action: {action_id}",
    )

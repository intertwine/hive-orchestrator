"""Driver and steering state helpers for runs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.hive.clock import utc_now_iso
from src.hive.drivers import RunHandle, RunLaunchRequest, get_driver
from src.hive.runtime.approvals import pending_approvals, request_approval
from src.hive.runs.program import _build_reroute_launch_request, _run_program_policy
from src.hive.store.events import emit_event


def _emit_context_compiled_events(
    root: Path,
    *,
    run_id: str,
    task_id: str,
    project_id: str,
    manifest_path: str,
) -> None:
    """Emit both run-scoped and context-scoped context-compilation events."""
    payload = {"manifest_path": manifest_path}
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="run.context_compiled",
        source="run.start",
        payload=payload,
        run_id=run_id,
        task_id=task_id,
        project_id=project_id,
    )
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="context.compiled",
        source="run.start",
        payload=payload,
        run_id=run_id,
        task_id=task_id,
        project_id=project_id,
    )


def _append_transcript_entry(path: Path, record: dict[str, object]) -> None:
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    ndjson_path = path.parent.parent / "transcript.ndjson"
    with open(ndjson_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _load_driver_handles(metadata: dict) -> dict[str, object]:
    handles_path_value = metadata.get("driver_handles_path")
    if not handles_path_value:
        return {"active": None, "history": []}
    handles_path = Path(handles_path_value)
    if not handles_path.exists():
        return {"active": None, "history": []}
    return json.loads(handles_path.read_text(encoding="utf-8"))


def _save_driver_handles(metadata: dict, handles: dict[str, object]) -> None:
    handles_path = Path(metadata["driver_handles_path"])
    handles_path.write_text(json.dumps(handles, indent=2, sort_keys=True), encoding="utf-8")


def _active_driver_handle(metadata: dict) -> RunHandle:
    handles = _load_driver_handles(metadata)
    active = handles.get("active")
    if not isinstance(active, dict):
        raise ValueError(f"Run {metadata['id']} does not have an active driver handle")
    return RunHandle(**active)


def _record_driver_status(metadata: dict, status: dict[str, object]) -> None:
    metadata.setdefault("metadata_json", {})["driver_status"] = status


def _driver_imports(metadata: dict) -> dict[str, object]:
    return metadata.setdefault("metadata_json", {}).setdefault("driver_imports", {})


def _extract_text_payload(payload: dict[str, Any] | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("text", "delta"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    message = payload.get("message")
    if isinstance(message, str) and message.strip():
        return message.strip()
    if isinstance(message, dict):
        for key in ("text", "content"):
            nested = message.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    content = payload.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        if parts:
            return "\n".join(parts)
    item = payload.get("item")
    if isinstance(item, dict):
        return _extract_text_payload(item)
    return None


def _extract_usage_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    usage = payload.get("usage")
    if isinstance(usage, dict):
        return usage
    info = payload.get("info")
    if isinstance(info, dict):
        total = info.get("total_token_usage")
        if isinstance(total, dict):
            return total
    return None


def _coerce_line_cursor(value: object) -> int:
    try:
        return max(0, int(str(value or "0")))
    except ValueError:
        return 0


def _normalize_codex_event(record: dict[str, Any]) -> tuple[str | None, dict[str, Any], str]:
    payload = record
    if isinstance(record.get("msg"), dict):
        payload = record["msg"]
    elif isinstance(record.get("payload"), dict):
        payload = record["payload"]
    event_type = payload.get("type") or record.get("type")
    if event_type is not None:
        event_type = str(event_type)
    ts = str(record.get("timestamp") or record.get("ts") or utc_now_iso())
    return event_type, dict(payload), ts


def _load_json_record(path: Path) -> dict[str, Any] | None:
    """Return the last valid JSON object from a JSONL-ish output file."""
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for raw_line in reversed(lines):
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _record_driver_usage(metadata: dict, status_payload: dict[str, object], usage: dict[str, Any]) -> None:
    input_tokens = int(
        usage.get("input_tokens", 0)
        + usage.get("cached_input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
    )
    output_tokens = int(usage.get("output_tokens", 0) + usage.get("reasoning_output_tokens", 0))
    spent_tokens = int(
        usage.get("total_tokens")
        or input_tokens
        + output_tokens
    )
    spent_cost_usd = float(usage.get("cost_usd") or 0.0)
    budget = {
        "spent_tokens": spent_tokens,
        "spent_cost_usd": spent_cost_usd,
        "wall_minutes": int(
            metadata.get("metadata_json", {}).get("driver_status", {}).get("budget", {}).get(
                "wall_minutes", 0
            )
            or status_payload.get("budget", {}).get("wall_minutes", 0)
            or 0
        ),
    }
    metadata.setdefault("metadata_json", {})["driver_usage"] = {
        **budget,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
    _sync_run_budget_rollup(
        metadata,
        spent_tokens=spent_tokens,
        spent_cost_usd=spent_cost_usd,
        wall_minutes=budget["wall_minutes"],
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    status_payload["budget"] = budget


def _sync_run_budget_rollup(
    metadata: dict,
    *,
    spent_tokens: int,
    spent_cost_usd: float,
    wall_minutes: int,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> None:
    normalized_input = int(input_tokens or 0)
    normalized_output = (
        int(output_tokens)
        if output_tokens is not None
        else max(0, int(spent_tokens) - normalized_input)
    )
    metadata["tokens_in"] = normalized_input
    metadata["tokens_out"] = normalized_output
    metadata["cost_usd"] = float(spent_cost_usd)
    metadata.setdefault("metadata_json", {})["budget_rollup"] = {
        "spent_tokens": int(spent_tokens),
        "spent_cost_usd": float(spent_cost_usd),
        "wall_minutes": int(wall_minutes),
        "input_tokens": normalized_input,
        "output_tokens": normalized_output,
    }


def _sync_run_budget_from_status(metadata: dict, status_payload: dict[str, object]) -> None:
    budget = status_payload.get("budget")
    if not isinstance(budget, dict):
        return
    spent_tokens = int(budget.get("spent_tokens") or 0)
    spent_cost_usd = float(budget.get("spent_cost_usd") or 0.0)
    wall_minutes = int(budget.get("wall_minutes") or 0)
    usage = metadata.get("metadata_json", {}).get("driver_usage")
    input_tokens: int | None = None
    output_tokens: int | None = None
    if isinstance(usage, dict) and int(usage.get("spent_tokens") or 0) == spent_tokens:
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
    _sync_run_budget_rollup(
        metadata,
        spent_tokens=spent_tokens,
        spent_cost_usd=spent_cost_usd,
        wall_minutes=wall_minutes,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _request_codex_approval(
    root: Path,
    metadata: dict,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    call_id = payload.get("call_id")
    imports = _driver_imports(metadata)
    seen_ids = imports.setdefault("approval_call_ids", [])
    if call_id is not None and str(call_id) in seen_ids:
        return None
    command = payload.get("command")
    if isinstance(command, list):
        command_text = " ".join(str(part) for part in command)
    elif isinstance(command, str):
        command_text = command
    else:
        command_text = "unknown command"
    approval = request_approval(
        root,
        str(metadata["id"]),
        kind="command",
        title=f"Approve Codex command: {command_text}",
        summary=f"Codex requested approval to execute `{command_text}`.",
        requested_by="driver:codex",
        payload={
            "call_id": call_id,
            "command": command,
            "cwd": payload.get("cwd"),
            "reason": payload.get("reason"),
        },
    )
    metadata.setdefault("metadata_json", {}).setdefault("approvals", []).append(approval)
    if call_id is not None:
        seen_ids.append(str(call_id))
    return approval


def _request_codex_app_server_command_approval(
    root: Path,
    metadata: dict,
    *,
    request_id: object,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    imports = _driver_imports(metadata)
    seen_ids = imports.setdefault("app_server_command_approval_ids", [])
    approval_key = (
        str(request_id)
        if request_id is not None
        else str(payload.get("approvalId") or payload.get("itemId") or "")
    )
    if approval_key and approval_key in seen_ids:
        return None
    command_text = str(payload.get("command") or payload.get("itemId") or "command")
    approval = request_approval(
        root,
        str(metadata["id"]),
        kind="command",
        title=f"Approve Codex command: {command_text}",
        summary=f"Codex requested approval to execute `{command_text}` through app-server.",
        requested_by="driver:codex",
        payload={
            "server_request_id": str(request_id),
            "approval_id": payload.get("approvalId"),
            "item_id": payload.get("itemId"),
            "thread_id": payload.get("threadId"),
            "turn_id": payload.get("turnId"),
            "command": payload.get("command"),
            "cwd": payload.get("cwd"),
            "reason": payload.get("reason"),
            "command_actions": payload.get("commandActions"),
        },
    )
    metadata.setdefault("metadata_json", {}).setdefault("approvals", []).append(approval)
    if approval_key:
        seen_ids.append(approval_key)
    return approval


def _request_codex_app_server_file_approval(
    root: Path,
    metadata: dict,
    *,
    request_id: object,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    imports = _driver_imports(metadata)
    seen_ids = imports.setdefault("app_server_file_approval_ids", [])
    approval_key = (
        str(request_id)
        if request_id is not None
        else str(payload.get("itemId") or payload.get("callId") or "")
    )
    if approval_key and approval_key in seen_ids:
        return None
    grant_root = str(payload.get("grantRoot") or "").strip()
    reason = str(payload.get("reason") or "").strip()
    title = "Approve Codex file change"
    if grant_root:
        title = f"Approve Codex write access: {grant_root}"
    approval = request_approval(
        root,
        str(metadata["id"]),
        kind="file",
        title=title,
        summary=reason or "Codex requested permission to apply file changes.",
        requested_by="driver:codex",
        payload={
            "server_request_id": str(request_id),
            "item_id": payload.get("itemId"),
            "call_id": payload.get("callId"),
            "thread_id": payload.get("threadId") or payload.get("conversationId"),
            "turn_id": payload.get("turnId"),
            "grant_root": payload.get("grantRoot"),
            "reason": payload.get("reason"),
            "file_changes": payload.get("fileChanges"),
        },
    )
    metadata.setdefault("metadata_json", {}).setdefault("approvals", []).append(approval)
    if approval_key:
        seen_ids.append(approval_key)
    return approval


def _emit_runtime_driver_event(
    root: Path,
    metadata: dict,
    *,
    event_type: str,
    source: str,
    payload: dict[str, Any],
) -> None:
    emit_event(
        root,
        actor={"kind": "system", "id": f"driver:{metadata.get('driver', 'unknown')}"},
        entity_type="run",
        entity_id=str(metadata["id"]),
        event_type=event_type,
        source=source,
        payload=payload,
        run_id=str(metadata["id"]),
        task_id=metadata.get("task_id"),
        project_id=metadata.get("project_id"),
        campaign_id=metadata.get("campaign_id"),
    )


def _ingest_codex_exec_events(
    root: Path,
    metadata: dict,
    handle: RunHandle,
    status_payload: dict[str, object],
) -> None:
    if str(metadata.get("driver")) != "codex" or handle.launch_mode != "exec":
        return
    artifacts = status_payload.get("artifacts")
    if not isinstance(artifacts, dict):
        return
    raw_output_path = artifacts.get("raw_output_path") or handle.metadata.get("raw_output_path")
    if not isinstance(raw_output_path, str) or not raw_output_path.strip():
        return
    raw_path = Path(raw_output_path)
    if not raw_path.exists():
        return

    imports = _driver_imports(metadata)
    previous_cursor = _coerce_line_cursor(
        handle.event_cursor or imports.get("codex_exec_event_cursor") or 0
    )
    current_cursor = _coerce_line_cursor(status_payload.get("event_cursor"))
    raw_lines = [line for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if current_cursor <= 0:
        current_cursor = len(raw_lines)
    new_records = raw_lines[previous_cursor:current_cursor]

    for raw_line in new_records:
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        driver_event_type, payload, ts = _normalize_codex_event(record)
        if not driver_event_type:
            continue
        source = "driver.codex.exec"
        if driver_event_type in {"agent_message", "agent_message_delta", "agent_reasoning"}:
            text = _extract_text_payload(payload)
            if text:
                _append_transcript_entry(
                    Path(metadata["transcript_path"]),
                    {
                        "ts": ts,
                        "kind": "assistant" if driver_event_type != "agent_reasoning" else "thinking",
                        "driver": metadata.get("driver"),
                        "message": text,
                        "driver_event_type": driver_event_type,
                    },
                )
                _emit_runtime_driver_event(
                    root,
                    metadata,
                    event_type="driver.output.delta",
                    source=source,
                    payload={"driver_event_type": driver_event_type, "message": text},
                )
            continue
        if driver_event_type == "exec_approval_request":
            _request_codex_approval(root, metadata, payload)
            continue
        if driver_event_type == "item.completed":
            item = payload.get("item")
            if isinstance(item, dict):
                item_type = str(item.get("type") or item.get("item_type") or "")
                if item_type in {"todo_list", "todo", "plan"}:
                    _emit_runtime_driver_event(
                        root,
                        metadata,
                        event_type="plan.updated",
                        source=source,
                        payload={"driver_event_type": driver_event_type, "item": item},
                    )
                elif item_type in {"file_change", "patch", "diff"}:
                    _emit_runtime_driver_event(
                        root,
                        metadata,
                        event_type="diff.updated",
                        source=source,
                        payload={"driver_event_type": driver_event_type, "item": item},
                    )
                text = _extract_text_payload(item)
                if text:
                    _append_transcript_entry(
                        Path(metadata["transcript_path"]),
                        {
                            "ts": ts,
                            "kind": "assistant",
                            "driver": metadata.get("driver"),
                            "message": text,
                            "driver_event_type": f"{driver_event_type}:{item_type or 'item'}",
                        },
                    )
            continue
        usage = _extract_usage_payload(payload)
        if usage is not None:
            _record_driver_usage(metadata, status_payload, usage)
        _emit_runtime_driver_event(
            root,
            metadata,
            event_type="driver.status",
            source=source,
            payload={"driver_event_type": driver_event_type, "payload": payload},
        )

    imports["codex_exec_event_cursor"] = current_cursor
    imports["codex_exec_raw_output_path"] = str(raw_path)
    pending = pending_approvals(root, str(metadata["id"]))
    status_payload["pending_approvals"] = pending
    if pending and status_payload.get("state") == "running":
        status_payload["health"] = "blocked"
        status_payload["waiting_on"] = "approval"
        progress = dict(status_payload.get("progress") or {})
        if not progress:
            progress = {"phase": "waiting", "message": "Awaiting driver approval.", "percent": 0}
        else:
            progress["phase"] = "waiting"
            progress["message"] = "Codex is blocked on a pending approval request."
        status_payload["progress"] = progress


def _thread_token_usage_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    token_usage = payload.get("tokenUsage")
    if not isinstance(token_usage, dict):
        return None
    total = token_usage.get("total")
    if not isinstance(total, dict):
        return None
    return {
        "total_tokens": total.get("totalTokens"),
        "input_tokens": total.get("inputTokens"),
        "cached_input_tokens": total.get("cachedInputTokens"),
        "output_tokens": total.get("outputTokens"),
        "reasoning_output_tokens": total.get("reasoningOutputTokens"),
    }


def _ingest_claude_exec_output(
    root: Path,
    metadata: dict,
    handle: RunHandle,
    status_payload: dict[str, object],
) -> None:
    if str(metadata.get("driver")) != "claude-code" or handle.launch_mode != "exec":
        return
    artifacts = status_payload.get("artifacts")
    if not isinstance(artifacts, dict):
        return
    raw_output_path = artifacts.get("raw_output_path") or handle.metadata.get("raw_output_path")
    if not isinstance(raw_output_path, str) or not raw_output_path.strip():
        return
    raw_path = Path(raw_output_path)
    if not raw_path.exists():
        return
    payload = _load_json_record(raw_path)
    if payload is None:
        return

    imports = _driver_imports(metadata)
    transcript_path_value = str(metadata.get("transcript_path") or "").strip()
    usage = dict(payload.get("usage") or {})
    if usage:
        usage["cost_usd"] = float(payload.get("total_cost_usd") or usage.get("cost_usd") or 0.0)
        _record_driver_usage(metadata, status_payload, usage)

    payload_digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    if imports.get("claude_exec_result_sha256") == payload_digest:
        imports["claude_exec_raw_output_path"] = str(raw_path)
        return

    source = "driver.claude.exec"
    result_text = str(payload.get("result") or "").strip()
    driver_event_type = "claude.print_result" if result_text else "claude.print_metadata"
        if result_text:
            if transcript_path_value:
                _append_transcript_entry(
                    Path(transcript_path_value),
                    {
                    "ts": utc_now_iso(),
                    "kind": "assistant",
                    "driver": metadata.get("driver"),
                    "message": result_text,
                    "driver_event_type": "claude.print_result",
                        "state": status_payload.get("state"),
                    },
                )
                # Only mark the assistant text as imported when it was appended to
                # the transcript; without a transcript file, the legacy last-message
                # import still needs to backfill the final assistant turn.
                imports["last_message_sha256"] = hashlib.sha256(
                    result_text.encode("utf-8")
                ).hexdigest()
            _emit_runtime_driver_event(
                root,
                metadata,
                event_type="driver.output.delta",
            source=source,
            payload={"driver_event_type": "claude.print_result", "message": result_text},
        )

    _emit_runtime_driver_event(
        root,
        metadata,
        event_type="driver.status",
        source=source,
        payload={
            "driver_event_type": driver_event_type,
            "payload": {
                "session_id": payload.get("session_id"),
                "total_cost_usd": payload.get("total_cost_usd"),
                "duration_ms": payload.get("duration_ms"),
                "has_result_text": bool(result_text),
            },
        },
    )
    imports["claude_exec_result_sha256"] = payload_digest
    imports["claude_exec_raw_output_path"] = str(raw_path)


def _ingest_codex_app_server_events(
    root: Path,
    metadata: dict,
    handle: RunHandle,
    status_payload: dict[str, object],
) -> None:
    if str(metadata.get("driver")) != "codex" or handle.launch_mode != "app_server":
        return
    artifacts = status_payload.get("artifacts")
    if not isinstance(artifacts, dict):
        return
    raw_output_path = artifacts.get("raw_output_path") or handle.metadata.get("raw_output_path")
    if not isinstance(raw_output_path, str) or not raw_output_path.strip():
        return
    raw_path = Path(raw_output_path)
    if not raw_path.exists():
        return

    imports = _driver_imports(metadata)
    previous_cursor = _coerce_line_cursor(
        handle.event_cursor or imports.get("codex_app_server_event_cursor") or 0
    )
    current_cursor = _coerce_line_cursor(status_payload.get("event_cursor"))
    raw_lines = [line for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if current_cursor <= 0:
        current_cursor = len(raw_lines)
    new_records = raw_lines[previous_cursor:current_cursor]

    for raw_line in new_records:
        try:
            record = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        method = str(record.get("method") or "")
        payload = dict(record.get("params") or {})
        if not method:
            continue
        source = "driver.codex.app_server"
        if method == "item/agentMessage/delta":
            text = str(payload.get("delta") or "").strip()
            if text:
                _append_transcript_entry(
                    Path(metadata["transcript_path"]),
                    {
                        "ts": utc_now_iso(),
                        "kind": "assistant",
                        "driver": metadata.get("driver"),
                        "message": text,
                        "driver_event_type": method,
                    },
                )
                _emit_runtime_driver_event(
                    root,
                    metadata,
                    event_type="driver.output.delta",
                    source=source,
                    payload={"driver_event_type": method, "message": text},
                )
            continue
        if method in {"item/reasoning/textDelta", "item/reasoning/summaryTextDelta"}:
            text = str(payload.get("delta") or "").strip()
            if text:
                _append_transcript_entry(
                    Path(metadata["transcript_path"]),
                    {
                        "ts": utc_now_iso(),
                        "kind": "thinking",
                        "driver": metadata.get("driver"),
                        "message": text,
                        "driver_event_type": method,
                    },
                )
            continue
        if method == "item/commandExecution/requestApproval":
            _request_codex_app_server_command_approval(
                root,
                metadata,
                request_id=record.get("id"),
                payload=payload,
            )
            continue
        if method in {"item/fileChange/requestApproval", "applyPatchApproval"}:
            _request_codex_app_server_file_approval(
                root,
                metadata,
                request_id=record.get("id"),
                payload=payload,
            )
            continue
        if method == "turn/plan/updated":
            _emit_runtime_driver_event(
                root,
                metadata,
                event_type="plan.updated",
                source=source,
                payload={"driver_event_type": method, "payload": payload},
            )
            continue
        if method == "turn/diff/updated":
            _emit_runtime_driver_event(
                root,
                metadata,
                event_type="diff.updated",
                source=source,
                payload={"driver_event_type": method, "payload": payload},
            )
            continue
        usage = _thread_token_usage_payload(payload)
        if usage is not None:
            _record_driver_usage(metadata, status_payload, usage)
        _emit_runtime_driver_event(
            root,
            metadata,
            event_type="driver.status",
            source=source,
            payload={"driver_event_type": method, "payload": payload},
        )

    imports["codex_app_server_event_cursor"] = current_cursor
    imports["codex_app_server_raw_output_path"] = str(raw_path)
    pending = pending_approvals(root, str(metadata["id"]))
    status_payload["pending_approvals"] = pending
    if pending and status_payload.get("state") == "running":
        status_payload["health"] = "blocked"
        status_payload["waiting_on"] = "approval"
        progress = dict(status_payload.get("progress") or {})
        if not progress:
            progress = {"phase": "waiting", "message": "Awaiting driver approval.", "percent": 0}
        else:
            progress["phase"] = "waiting"
            progress["message"] = "Codex is blocked on a pending approval request."
        status_payload["progress"] = progress


def _update_active_handle_from_status(metadata: dict, status_payload: dict[str, object]) -> None:
    handles = _load_driver_handles(metadata)
    active = handles.get("active")
    if not isinstance(active, dict):
        return
    active["status"] = status_payload.get("state")
    if status_payload.get("event_cursor") is not None:
        active["event_cursor"] = status_payload.get("event_cursor")
    session = status_payload.get("session")
    if isinstance(session, dict):
        if session.get("transport") is not None:
            active["transport"] = session.get("transport")
        if session.get("session_id") is not None:
            active["session_id"] = session.get("session_id")
        if session.get("thread_id") is not None:
            active["thread_id"] = session.get("thread_id")
    handles["active"] = active
    history = list(handles.get("history") or [])
    if history and isinstance(history[-1], dict) and history[-1].get("driver_handle") == active.get(
        "driver_handle"
    ):
        # Keep one mutable latest-state record per live handle; events remain the audit log.
        history[-1] = dict(active)
        handles["history"] = history
    _save_driver_handles(metadata, handles)


def _import_driver_last_message(metadata: dict, status_payload: dict[str, object]) -> None:
    if status_payload.get("state") not in {"completed_candidate", "failed", "cancelled"}:
        return
    artifacts = status_payload.get("artifacts")
    if not isinstance(artifacts, dict):
        return
    message_path_value = artifacts.get("last_message_path")
    if not isinstance(message_path_value, str) or not message_path_value.strip():
        return
    message_path = Path(message_path_value)
    if not message_path.exists():
        return
    content = message_path.read_text(encoding="utf-8").strip()
    if not content:
        return
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    imports = metadata.setdefault("metadata_json", {}).setdefault("driver_imports", {})
    if imports.get("last_message_sha256") == digest:
        return
    transcript_path_value = metadata.get("transcript_path")
    if not isinstance(transcript_path_value, str) or not transcript_path_value.strip():
        return
    _append_transcript_entry(
        Path(transcript_path_value),
        {
            "ts": utc_now_iso(),
            "kind": "assistant",
            "driver": metadata.get("driver"),
            "message": content,
            "state": status_payload.get("state"),
        },
    )
    imports["last_message_sha256"] = digest


def _refresh_live_driver_status(root: Path, metadata: dict) -> dict[str, object] | None:
    handle = _active_driver_handle(metadata)
    if handle.launch_mode not in {"exec", "app_server", "sdk", "rpc"}:
        return None
    driver = get_driver(str(metadata.get("driver", handle.driver)))
    previous = dict(metadata.get("metadata_json", {}).get("driver_status") or {})
    status = driver.status(handle)
    status_payload = status.to_dict()
    _ingest_codex_exec_events(root, metadata, handle, status_payload)
    _ingest_claude_exec_output(root, metadata, handle, status_payload)
    _ingest_codex_app_server_events(root, metadata, handle, status_payload)
    _sync_run_budget_from_status(metadata, status_payload)
    _record_driver_status(metadata, status_payload)
    _update_active_handle_from_status(metadata, status_payload)
    _import_driver_last_message(metadata, status_payload)
    return {"previous": previous, "current": status_payload}


def _record_steering_history(
    metadata: dict,
    *,
    action: str,
    actor: str | None,
    reason: str | None,
    note: str | None,
    target: dict[str, object] | None,
    budget_delta: dict[str, object] | None,
    ack: dict[str, object] | None = None,
) -> dict[str, object]:
    entry: dict[str, object] = {
        "ts": utc_now_iso(),
        "action": action,
        "actor": actor or "operator",
        "reason": reason,
        "note": note,
        "target": dict(target or {}),
        "budget_delta": dict(budget_delta or {}),
    }
    if ack is not None:
        entry["driver_ack"] = ack
    metadata.setdefault("metadata_json", {}).setdefault("steering_history", []).append(entry)
    return entry


def _steering_event_type(action: str) -> str:
    if action == "note":
        return "steering.note_added"
    if action == "reroute":
        return "steering.rerouted"
    return f"steering.{action}"


def load_driver_metadata(metadata: dict) -> RunHandle:
    """Return the active driver handle for a run."""
    return _active_driver_handle(metadata)


def build_reroute_launch_request(
    root: Path,
    metadata: dict,
    *,
    driver_name: str,
    model: str | None = None,
) -> RunLaunchRequest:
    """Build a reroute launch request for a typed steering action."""
    return _build_reroute_launch_request(root, metadata, driver_name=driver_name, model=model)


def run_program_policy(program) -> dict[str, object]:
    """Return the normalized policy payload used to launch or reroute a run."""
    return _run_program_policy(program)


__all__ = [
    "build_reroute_launch_request",
    "load_driver_metadata",
    "run_program_policy",
]

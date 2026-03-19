"""Background bridge for Claude SDK-backed runs."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import shlex
import sys
from typing import Any


def _append_ndjson(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _load_channel_records(path: Path, cursor: int) -> tuple[list[dict[str, Any]], int]:
    if not path.exists():
        return [], cursor
    with open(path, "r", encoding="utf-8") as handle:
        lines = [line for line in handle.read().splitlines() if line.strip()]
    records: list[dict[str, Any]] = []
    for raw_line in lines[cursor:]:
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records, len(lines)


class ClaudeSDKBroker:
    """Small subprocess bridge that keeps Claude attached to a Hive run."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.worktree_path = Path(args.worktree).resolve()
        self.prompt_path = Path(args.prompt).resolve()
        self.raw_output_path = Path(args.raw_output).resolve()
        self.last_message_path = Path(args.last_message).resolve()
        self.exit_code_path = Path(args.exit_code).resolve()
        self.stderr_path = Path(args.stderr).resolve()
        self.approval_channel_path = Path(args.approval_channel).resolve()
        self.state_path = Path(args.state).resolve()
        self.policy_path = Path(args.policy).resolve()
        self.session_id = str(args.session_id).strip() or "default"
        self.model = str(args.model or "").strip() or None
        self.max_budget_usd = float(args.max_budget_usd or 0.0)
        self.claude_md_path = Path(args.claude_md).resolve() if args.claude_md else None
        self.driver_channel_cursor = 0
        self.pending_request_id: str | None = None
        self.pending_resolution_future: asyncio.Future[dict[str, Any]] | None = None
        self.cancel_requested = False
        self.stop_requested = False
        self.program_policy = json.loads(self.policy_path.read_text(encoding="utf-8"))
        self.state: dict[str, Any] = {
            "status": "starting",
            "session_id": self.session_id,
            "last_message": None,
            "pending_request": None,
            "usage": {},
            "total_cost_usd": 0.0,
            "duration_ms": 0,
            "result": None,
            "error": None,
        }

    def _write_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(self.state, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _write_exit_code(self, code: int) -> None:
        self.exit_code_path.parent.mkdir(parents=True, exist_ok=True)
        self.exit_code_path.write_text(f"{code}\n", encoding="utf-8")

    def _update_last_message(self, text: str | None) -> None:
        if not text:
            return
        cleaned = text.strip()
        if not cleaned:
            return
        self.state["last_message"] = cleaned
        self.last_message_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_message_path.write_text(cleaned + "\n", encoding="utf-8")

    def _tool_summary(self, tool_name: str, input_data: dict[str, Any]) -> tuple[str, str, str]:
        tool = tool_name.strip() or "tool"
        if tool in {"Write", "Edit", "MultiEdit"}:
            path_value = str(
                input_data.get("file_path")
                or input_data.get("path")
                or input_data.get("target_file")
                or ""
            ).strip()
            title = (
                f"Approve Claude file change: {path_value}"
                if path_value
                else "Approve Claude file change"
            )
            summary = (
                f"Claude requested permission to modify `{path_value}`."
                if path_value
                else "Claude requested permission to modify files."
            )
            return "file", title, summary
        if tool in {"WebFetch", "WebSearch"}:
            target = str(input_data.get("url") or input_data.get("query") or "").strip()
            title = f"Approve Claude network access: {tool}"
            summary = (
                f"Claude requested network access via {tool}: `{target}`."
                if target
                else f"Claude requested network access via {tool}."
            )
            return "network", title, summary
        command = str(
            input_data.get("command")
            or input_data.get("cmd")
            or input_data.get("shell_command")
            or ""
        ).strip()
        title = (
            f"Approve Claude command: {command}" if command else f"Approve Claude tool use: {tool}"
        )
        summary = (
            f"Claude requested permission to run `{command}`."
            if command
            else f"Claude requested permission to use {tool}."
        )
        return "command", title, summary

    @staticmethod
    def _command_matches(command: str, patterns: list[str]) -> bool:
        if not command.strip():
            return False
        try:
            argv = shlex.split(command)
        except ValueError:
            argv = command.split()
        first = argv[0] if argv else ""
        normalized = command.strip()
        for pattern in patterns:
            candidate = str(pattern).strip()
            if not candidate:
                continue
            if normalized == candidate or normalized.startswith(candidate + " "):
                return True
            if first == candidate:
                return True
        return False

    def _resolve_file_target(self, input_data: dict[str, Any]) -> Path | None:
        raw = str(
            input_data.get("file_path")
            or input_data.get("path")
            or input_data.get("target_file")
            or ""
        ).strip()
        if not raw:
            return None
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = (self.worktree_path / candidate).resolve()
        else:
            candidate = candidate.resolve()
        return candidate

    def _path_in_roots(self, target: Path | None, roots: list[str]) -> bool:
        if target is None:
            return False
        for root in roots:
            root_value = str(root).strip()
            if not root_value:
                continue
            candidate = Path(root_value)
            if not candidate.is_absolute():
                candidate = (self.worktree_path / candidate).resolve()
            else:
                candidate = candidate.resolve()
            try:
                if target.is_relative_to(candidate):
                    return True
            except ValueError:
                continue
        return False

    def _policy_decision(
        self, approval_kind: str, tool_name: str, input_data: dict[str, Any]
    ) -> str | None:
        network_mode = str(self.program_policy.get("network") or "ask").strip().lower()
        command = str(
            input_data.get("command")
            or input_data.get("cmd")
            or input_data.get("shell_command")
            or ""
        ).strip()
        command_deny = list(self.program_policy.get("commands_deny") or [])
        command_allow = list(self.program_policy.get("commands_allow") or [])
        blocked_paths = list(self.program_policy.get("blocked_paths") or [])
        allowed_paths = list(self.program_policy.get("paths") or [])
        if approval_kind == "network":
            if network_mode == "deny":
                return "deny"
            if network_mode == "allow":
                return "allow"
            return None
        if approval_kind == "command":
            if self._command_matches(command, command_deny):
                return "deny"
            if command_allow and self._command_matches(command, command_allow):
                return "allow"
            return None
        if approval_kind == "file":
            target = self._resolve_file_target(input_data)
            if self._path_in_roots(target, blocked_paths):
                return "deny"
            if allowed_paths and self._path_in_roots(target, allowed_paths):
                return "allow"
        del tool_name
        return None

    async def _wait_for_resolution(self, request_id: str) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self.pending_request_id = request_id
        self.pending_resolution_future = future
        while not future.done():
            await asyncio.sleep(0.1)
        self.pending_request_id = None
        self.pending_resolution_future = None
        return future.result()

    async def _can_use_tool(self, tool_name: str, input_data: dict[str, Any], context: Any):
        from claude_code_sdk import PermissionResultAllow, PermissionResultDeny

        approval_kind, title, summary = self._tool_summary(tool_name, input_data)
        policy_decision = self._policy_decision(approval_kind, tool_name, input_data)
        if policy_decision == "allow":
            return PermissionResultAllow()
        if policy_decision == "deny":
            return PermissionResultDeny(
                message=f"PROGRAM.md denies this Claude {approval_kind} action.",
                interrupt=False,
            )
        request_id = f"claude-sdk-{self.session_id}-{int(asyncio.get_running_loop().time() * 1000)}"
        payload = {
            "request_id": request_id,
            "approval_kind": approval_kind,
            "tool_name": tool_name,
            "input": dict(input_data or {}),
            "title": title,
            "summary": summary,
            "suggestions": list(getattr(context, "suggestions", []) or []),
        }
        self.state["status"] = "waiting_approval"
        self.state["pending_request"] = {
            "request_id": request_id,
            "approval_kind": approval_kind,
            "tool_name": tool_name,
            "title": title,
            "summary": summary,
        }
        _append_ndjson(
            self.raw_output_path,
            {"kind": "permission_request", "payload": payload},
        )
        self._write_state()
        resolution = await self._wait_for_resolution(request_id)
        decision = str(resolution.get("resolution") or "").strip().lower()
        note = str(resolution.get("resolution_note") or "").strip()
        self.state["pending_request"] = None
        self.state["status"] = "cancelled" if self.cancel_requested else "running"
        _append_ndjson(
            self.raw_output_path,
            {
                "kind": "permission_result",
                "payload": {
                    "request_id": request_id,
                    "resolution": decision,
                    "resolution_note": note or None,
                },
            },
        )
        self._write_state()
        if decision == "approved":
            return PermissionResultAllow()
        return PermissionResultDeny(
            message=note or f"Hive rejected Claude {approval_kind} approval.",
            interrupt=False,
        )

    def _claude_append_system_prompt(self) -> str | None:
        if self.claude_md_path is None or not self.claude_md_path.exists():
            return None
        content = self.claude_md_path.read_text(encoding="utf-8").strip()
        return content or None

    @staticmethod
    def _normalize_resolution_record(record: dict[str, Any]) -> dict[str, Any]:
        payload = dict(record.get("payload") or {})
        server_request_id = str(
            payload.get("server_request_id") or payload.get("request_id") or ""
        ).strip()
        normalized = {
            "approval_id": record.get("approval_id"),
            "request_id": server_request_id or None,
            "server_request_id": server_request_id or None,
            "resolution": record.get("resolution") or payload.get("resolution"),
            "resolution_note": (
                record.get("resolution_note")
                if record.get("resolution_note") is not None
                else payload.get("resolution_note")
            ),
        }
        return normalized

    async def _watch_driver_channel(self, client: Any) -> None:
        while not self.stop_requested:
            records, self.driver_channel_cursor = _load_channel_records(
                self.approval_channel_path, self.driver_channel_cursor
            )
            for record in records:
                kind = str(record.get("kind") or "")
                if kind == "approval_resolution":
                    resolution = self._normalize_resolution_record(record)
                    candidate = str(
                        resolution.get("server_request_id") or resolution.get("request_id") or ""
                    ).strip()
                    if (
                        candidate
                        and candidate == self.pending_request_id
                        and self.pending_resolution_future is not None
                        and not self.pending_resolution_future.done()
                    ):
                        self.pending_resolution_future.set_result(resolution)
                elif kind == "interrupt" and str(record.get("mode") or "") == "cancel":
                    self.cancel_requested = True
                    self.state["status"] = "cancelled"
                    self._write_state()
                    if (
                        self.pending_resolution_future is not None
                        and not self.pending_resolution_future.done()
                    ):
                        self.pending_resolution_future.set_result(
                            {
                                "resolution": "rejected",
                                "resolution_note": "Run cancelled while waiting on approval.",
                            }
                        )
                    try:
                        await client.interrupt()
                    except (
                        Exception
                    ) as exc:  # pragma: no cover - best effort during worker shutdown
                        _append_ndjson(
                            self.raw_output_path,
                            {
                                "kind": "worker_error",
                                "payload": {"message": str(exc), "phase": "interrupt"},
                            },
                        )
            await asyncio.sleep(0.1)

    async def _record_message(self, message: Any) -> None:
        from claude_code_sdk import (
            AssistantMessage,
            ResultMessage,
            StreamEvent,
            TextBlock,
            ThinkingBlock,
            ToolResultBlock,
            ToolUseBlock,
        )

        if isinstance(message, StreamEvent):
            _append_ndjson(
                self.raw_output_path,
                {
                    "kind": "stream_event",
                    "payload": {
                        "session_id": message.session_id,
                        "event": dict(message.event),
                    },
                },
            )
            return
        if isinstance(message, AssistantMessage):
            text_parts: list[str] = []
            for block in message.content:
                if isinstance(block, TextBlock):
                    text = block.text.strip()
                    if text:
                        text_parts.append(text)
                        _append_ndjson(
                            self.raw_output_path,
                            {
                                "kind": "assistant_text",
                                "payload": {"text": text, "model": message.model},
                            },
                        )
                elif isinstance(block, ThinkingBlock):
                    thinking = block.thinking.strip()
                    if thinking:
                        _append_ndjson(
                            self.raw_output_path,
                            {"kind": "assistant_thinking", "payload": {"text": thinking}},
                        )
                elif isinstance(block, ToolUseBlock):
                    _append_ndjson(
                        self.raw_output_path,
                        {
                            "kind": "tool_use",
                            "payload": {
                                "tool_use_id": block.id,
                                "tool_name": block.name,
                                "input": dict(block.input),
                            },
                        },
                    )
                elif isinstance(block, ToolResultBlock):
                    _append_ndjson(
                        self.raw_output_path,
                        {
                            "kind": "tool_result",
                            "payload": {
                                "tool_use_id": block.tool_use_id,
                                "content": block.content,
                                "is_error": block.is_error,
                            },
                        },
                    )
            if text_parts:
                self._update_last_message("\n".join(text_parts))
            self.state["status"] = "running"
            self._write_state()
            return
        if isinstance(message, ResultMessage):
            self.state["status"] = "cancelled" if self.cancel_requested else "completed"
            self.state["session_id"] = str(message.session_id or self.session_id)
            self.state["duration_ms"] = int(message.duration_ms or 0)
            self.state["total_cost_usd"] = float(message.total_cost_usd or 0.0)
            self.state["usage"] = dict(message.usage or {})
            self.state["result"] = message.result
            self._update_last_message(str(message.result or "").strip() or None)
            _append_ndjson(
                self.raw_output_path,
                {
                    "kind": "result",
                    "payload": {
                        "session_id": message.session_id,
                        "duration_ms": message.duration_ms,
                        "total_cost_usd": message.total_cost_usd,
                        "usage": dict(message.usage or {}),
                        "result": message.result,
                        "is_error": message.is_error,
                    },
                },
            )
            self._write_state()
            return
        _append_ndjson(
            self.raw_output_path,
            {
                "kind": "driver_message",
                "payload": {"repr": repr(message)},
            },
        )

    async def run(self) -> int:
        from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient

        prompt = self.prompt_path.read_text(encoding="utf-8")
        add_dirs = [self.worktree_path]
        if self.claude_md_path is not None:
            add_dirs.append(self.claude_md_path.parent)
        options = ClaudeCodeOptions(
            cwd=self.worktree_path,
            add_dirs=add_dirs,
            model=self.model,
            permission_mode="default",
            append_system_prompt=self._claude_append_system_prompt(),
            can_use_tool=self._can_use_tool,
        )
        if self.max_budget_usd > 0:
            extra_args = dict(getattr(options, "extra_args", {}) or {})
            extra_args["max-budget-usd"] = str(self.max_budget_usd)
            options.extra_args = extra_args

        self.state["status"] = "starting"
        self._write_state()
        _append_ndjson(self.raw_output_path, {"kind": "status", "payload": {"status": "starting"}})
        channel_task: asyncio.Task[None] | None = None
        try:
            async with ClaudeSDKClient(options=options) as client:
                channel_task = asyncio.create_task(self._watch_driver_channel(client))
                await client.connect()
                self.state["status"] = "running"
                self._write_state()
                _append_ndjson(
                    self.raw_output_path,
                    {"kind": "status", "payload": {"status": "connected"}},
                )
                await client.query(prompt, session_id=self.session_id)
                async for message in client.receive_response():
                    await self._record_message(message)
        except Exception as exc:  # pragma: no cover - exercised through functional tests
            self.state["status"] = "cancelled" if self.cancel_requested else "failed"
            self.state["error"] = str(exc)
            self._write_state()
            _append_ndjson(
                self.raw_output_path,
                {"kind": "worker_error", "payload": {"message": str(exc)}},
            )
            return 0 if self.cancel_requested else 1
        finally:
            self.stop_requested = True
            if channel_task is not None:
                channel_task.cancel()
                try:
                    await channel_task
                except asyncio.CancelledError:
                    pass
        return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Claude SDK worker for Hive runs")
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--raw-output", required=True)
    parser.add_argument("--last-message", required=True)
    parser.add_argument("--exit-code", required=True)
    parser.add_argument("--stderr", required=True)
    parser.add_argument("--approval-channel", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--claude-md")
    parser.add_argument("--model")
    parser.add_argument("--max-budget-usd", type=float, default=0.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    broker = ClaudeSDKBroker(args)
    try:
        exit_code = asyncio.run(broker.run())
    except Exception as exc:  # pragma: no cover - defensive top-level guard
        broker.state["status"] = "failed"
        broker.state["error"] = str(exc)
        broker._write_state()
        _append_ndjson(
            broker.raw_output_path,
            {"kind": "worker_error", "payload": {"message": str(exc), "phase": "startup"}},
        )
        exit_code = 1
    broker._write_exit_code(exit_code)
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))

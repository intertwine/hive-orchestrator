"""Background bridge for Codex app-server runs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
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


class CodexAppServerBroker:
    """Small stdio JSON-RPC broker that keeps Codex attached to a Hive run."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.binary_path = str(args.binary)
        self.worktree_path = Path(args.worktree).resolve()
        self.prompt_path = Path(args.prompt).resolve()
        self.raw_output_path = Path(args.raw_output).resolve()
        self.last_message_path = Path(args.last_message).resolve()
        self.exit_code_path = Path(args.exit_code).resolve()
        self.stderr_path = Path(args.stderr).resolve()
        self.approval_channel_path = Path(args.approval_channel).resolve()
        self.state_path = Path(args.state).resolve()
        self.model = str(args.model or "").strip() or None
        self.process: subprocess.Popen[bytes] | None = None
        self.selector = selectors.DefaultSelector()
        self.responses: dict[str, dict[str, Any]] = {}
        self.pending_requests: dict[str, dict[str, Any]] = {}
        self.pending_interrupt = False
        self.driver_channel_cursor = 0
        self.request_id = 0
        self.stdout_buffer = b""
        self.state: dict[str, Any] = {
            "thread_id": None,
            "thread_status": None,
            "turn_id": None,
            "turn_status": None,
            "token_usage": {},
            "last_message": None,
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

    def _next_request_id(self) -> int:
        self.request_id += 1
        return self.request_id

    def _send(self, payload: dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("Codex app-server process is not writable")
        self.process.stdin.write((json.dumps(payload, sort_keys=True) + "\n").encode("utf-8"))
        self.process.stdin.flush()

    def _approval_key(self, request_id: object, method: str, params: dict[str, Any]) -> str:
        if method == "item/commandExecution/requestApproval":
            for key in ("approvalId", "itemId"):
                value = params.get(key)
                if value:
                    return str(value)
        if method == "item/fileChange/requestApproval":
            value = params.get("itemId")
            if value:
                return str(value)
        if method == "execCommandApproval":
            value = params.get("approvalId") or params.get("callId")
            if value:
                return str(value)
        if method == "applyPatchApproval":
            value = params.get("callId")
            if value:
                return str(value)
        return str(request_id)

    def _command_resolution_result(self, resolution: str) -> dict[str, Any]:
        decision = "accept" if resolution == "approved" else "decline"
        return {"decision": decision}

    def _legacy_resolution_result(self, resolution: str) -> dict[str, Any]:
        decision = "approved" if resolution == "approved" else "denied"
        return {"decision": decision}

    def _resolution_result(self, method: str, resolution: str) -> dict[str, Any]:
        if method in {"item/commandExecution/requestApproval", "item/fileChange/requestApproval"}:
            return self._command_resolution_result(resolution)
        return self._legacy_resolution_result(resolution)

    def _handle_server_request(self, message: dict[str, Any]) -> None:
        request_id = message.get("id")
        method = str(message.get("method") or "")
        params = dict(message.get("params") or {})
        key = self._approval_key(request_id, method, params)
        self.pending_requests[key] = {
            "id": request_id,
            "method": method,
            "params": params,
        }
        _append_ndjson(self.raw_output_path, message)

    def _update_last_message(self, text: str | None) -> None:
        if not text:
            return
        self.state["last_message"] = text
        self.last_message_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_message_path.write_text(text + "\n", encoding="utf-8")

    def _handle_notification(self, message: dict[str, Any]) -> None:
        method = str(message.get("method") or "")
        params = dict(message.get("params") or {})
        if method.startswith("codex/event/"):
            return
        if method == "thread/started":
            thread = dict(params.get("thread") or {})
            self.state["thread_id"] = thread.get("id")
            status = dict(thread.get("status") or {})
            self.state["thread_status"] = status.get("type") or thread.get("status")
        elif method == "thread/status/changed":
            status = dict(params.get("status") or {})
            self.state["thread_id"] = params.get("threadId") or self.state.get("thread_id")
            self.state["thread_status"] = status.get("type") or params.get("status")
        elif method == "turn/started":
            turn = dict(params.get("turn") or {})
            self.state["thread_id"] = params.get("threadId") or self.state.get("thread_id")
            self.state["turn_id"] = turn.get("id") or self.state.get("turn_id")
            self.state["turn_status"] = turn.get("status") or "inProgress"
        elif method == "turn/completed":
            turn = dict(params.get("turn") or {})
            self.state["thread_id"] = params.get("threadId") or self.state.get("thread_id")
            self.state["turn_id"] = turn.get("id") or self.state.get("turn_id")
            self.state["turn_status"] = turn.get("status") or "completed"
        elif method == "thread/tokenUsage/updated":
            token_usage = dict(params.get("tokenUsage") or {})
            self.state["token_usage"] = token_usage
        elif method == "item/completed":
            item = dict(params.get("item") or {})
            if item.get("type") == "agentMessage":
                self._update_last_message(str(item.get("text") or "").strip() or None)
        _append_ndjson(self.raw_output_path, message)
        self._write_state()

    def _process_message(self, line: str) -> None:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            return
        if not isinstance(message, dict):
            return
        if "method" in message and "params" in message:
            method = str(message.get("method") or "")
            if method in {
                "item/commandExecution/requestApproval",
                "item/fileChange/requestApproval",
                "execCommandApproval",
                "applyPatchApproval",
            }:
                self._handle_server_request(message)
                return
            self._handle_notification(message)
            return
        if "id" in message and ("result" in message or "error" in message):
            self.responses[str(message.get("id"))] = message

    def _pump_messages(self, timeout: float) -> None:
        if self.process is None or self.process.stdout is None:
            return
        for key, _ in self.selector.select(timeout):
            fd = key.fileobj.fileno()
            while True:
                try:
                    chunk = os.read(fd, 65536)
                except BlockingIOError:
                    break
                if not chunk:
                    break
                self.stdout_buffer += chunk
                while b"\n" in self.stdout_buffer:
                    raw_line, self.stdout_buffer = self.stdout_buffer.split(b"\n", 1)
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if line:
                        self._process_message(line)
                if len(chunk) < 65536:
                    break

    def _wait_for_response(self, request_id: int, *, timeout: float = 15.0) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._pump_messages(0.2)
            self._check_driver_channel()
            response = self.responses.pop(str(request_id), None)
            if response is not None:
                return response
            if self.process is not None and self.process.poll() is not None:
                raise RuntimeError("Codex app-server exited before responding")
        raise TimeoutError(f"Timed out waiting for app-server response {request_id}")

    def _send_interrupt(self) -> None:
        if not self.pending_interrupt:
            return
        thread_id = str(self.state.get("thread_id") or "").strip()
        turn_id = str(self.state.get("turn_id") or "").strip()
        if not thread_id or not turn_id:
            return
        request_id = self._next_request_id()
        self._send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "turn/interrupt",
                "params": {"threadId": thread_id, "turnId": turn_id},
            }
        )
        self.pending_interrupt = False

    def _respond_to_pending_request(self, record: dict[str, Any]) -> None:
        payload = dict(record.get("payload") or {})
        resolution = str(record.get("resolution") or "")
        for candidate in (
            payload.get("approval_id"),
            payload.get("item_id"),
            payload.get("server_request_id"),
            payload.get("call_id"),
        ):
            key = str(candidate or "").strip()
            if not key:
                continue
            pending = self.pending_requests.pop(key, None)
            if pending is None:
                continue
            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": pending["id"],
                    "result": self._resolution_result(str(pending["method"]), resolution),
                }
            )
            return

    def _check_driver_channel(self) -> None:
        records, next_cursor = _load_channel_records(
            self.approval_channel_path,
            self.driver_channel_cursor,
        )
        self.driver_channel_cursor = next_cursor
        for record in records:
            kind = str(record.get("kind") or "")
            if kind == "approval_resolution":
                self._respond_to_pending_request(record)
            elif kind == "interrupt_request":
                self.pending_interrupt = True
        self._send_interrupt()

    def run(self) -> int:
        prompt = self.prompt_path.read_text(encoding="utf-8")
        self.raw_output_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_message_path.parent.mkdir(parents=True, exist_ok=True)
        self.stderr_path.parent.mkdir(parents=True, exist_ok=True)
        self.approval_channel_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_state()

        with open(self.stderr_path, "a", encoding="utf-8") as stderr_handle:
            process = subprocess.Popen(
                [self.binary_path, "app-server", "--listen", "stdio://"],
                cwd=str(self.worktree_path),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=stderr_handle,
                bufsize=0,
            )
            self.process = process
            assert process.stdout is not None
            os.set_blocking(process.stdout.fileno(), False)
            self.selector.register(process.stdout, selectors.EVENT_READ)
            try:
                initialize_id = self._next_request_id()
                self._send(
                    {
                        "jsonrpc": "2.0",
                        "id": initialize_id,
                        "method": "initialize",
                        "params": {
                            "clientInfo": {"name": "hive", "title": "Hive", "version": "2.3.0"},
                            "capabilities": None,
                        },
                    }
                )
                self._wait_for_response(initialize_id)

                thread_start_id = self._next_request_id()
                thread_params: dict[str, Any] = {
                    "cwd": str(self.worktree_path),
                    "approvalPolicy": "on-request",
                    "sandbox": "workspace-write",
                    "ephemeral": False,
                    "personality": "pragmatic",
                }
                if self.model:
                    thread_params["model"] = self.model
                self._send(
                    {
                        "jsonrpc": "2.0",
                        "id": thread_start_id,
                        "method": "thread/start",
                        "params": thread_params,
                    }
                )
                thread_response = self._wait_for_response(thread_start_id)
                thread = dict((thread_response.get("result") or {}).get("thread") or {})
                self.state["thread_id"] = thread.get("id")
                self.state["thread_status"] = dict(thread.get("status") or {}).get("type") or thread.get(
                    "status"
                )
                self._write_state()

                turn_start_id = self._next_request_id()
                self._send(
                    {
                        "jsonrpc": "2.0",
                        "id": turn_start_id,
                        "method": "turn/start",
                        "params": {
                            "threadId": self.state["thread_id"],
                            "input": [{"type": "text", "text": prompt}],
                        },
                    }
                )
                turn_response = self._wait_for_response(turn_start_id)
                turn = dict((turn_response.get("result") or {}).get("turn") or {})
                self.state["turn_id"] = turn.get("id")
                self.state["turn_status"] = turn.get("status") or "inProgress"
                self._write_state()

                completed_at: float | None = None
                while True:
                    self._pump_messages(0.2)
                    self._check_driver_channel()
                    if process.poll() is not None:
                        break
                    if self.state.get("turn_status") in {"completed", "interrupted", "cancelled", "failed"}:
                        if completed_at is None:
                            completed_at = time.monotonic()
                        elif time.monotonic() - completed_at >= 0.5 and not self.pending_requests:
                            break
                    else:
                        completed_at = None
                return 0
            except Exception as exc:  # pragma: no cover - defensive runtime reporting
                _append_ndjson(
                    self.raw_output_path,
                    {"method": "hive/error", "params": {"message": str(exc)}},
                )
                return 1
            finally:
                self.selector.close()
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=2)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Codex app-server bridge for Hive runs.")
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--worktree", required=True, type=Path)
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--raw-output", required=True, type=Path)
    parser.add_argument("--last-message", required=True, type=Path)
    parser.add_argument("--exit-code", required=True, type=Path)
    parser.add_argument("--stderr", required=True, type=Path)
    parser.add_argument("--approval-channel", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--model", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    broker = CodexAppServerBroker(_parse_args(list(argv or sys.argv[1:])))
    exit_code = broker.run()
    broker._write_exit_code(exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

"""Hive Link server — stdio NDJSON bridge for v2.4 adapter integrations."""

from __future__ import annotations

import json
from typing import IO

from src.hive.clock import utc_now_iso
from src.hive.integrations.base import (
    AdapterBase,
    DelegateGatewayAdapter,
    WorkerSessionAdapter,
)
from src.hive.integrations.models import GovernanceMode
from src.hive.link.protocol import (
    LinkActions,
    LinkAttach,
    LinkAttachOk,
    LinkClose,
    LinkHeartbeat,
    LinkHello,
    LinkMessage,
    LinkPollActions,
    parse_link_message,
)


class LinkServer:
    """Stdio NDJSON bridge between a harness and Hive.

    Accepts injectable I/O streams so tests can drive the protocol
    without subprocess overhead.
    """

    def __init__(
        self,
        adapter: AdapterBase,
        input_stream: IO[str],
        output_stream: IO[str],
    ) -> None:
        self.adapter = adapter
        self._in = input_stream
        self._out = output_stream
        self._hello_received = False
        self._session = None

    def serve(self) -> None:
        """Read NDJSON messages from input, dispatch, write responses."""
        for line in self._in:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
                msg = parse_link_message(raw)
            except (json.JSONDecodeError, ValueError):
                self._send_error(f"Invalid message: {line[:120]}")
                continue
            response = self._handle_message(msg)
            if response is not None:
                self._write(response)

    def _handle_message(self, msg: LinkMessage) -> LinkMessage | None:
        if isinstance(msg, LinkHello):
            return self._handle_hello(msg)
        if isinstance(msg, LinkAttach):
            return self._handle_attach(msg)
        if isinstance(msg, LinkPollActions):
            return self._handle_poll_actions(msg)
        if isinstance(msg, LinkHeartbeat):
            return self._handle_heartbeat(msg)
        if isinstance(msg, LinkClose):
            return self._handle_close(msg)
        return None

    def _handle_hello(self, msg: LinkHello) -> LinkAttachOk | None:
        self._hello_received = True
        info = self.adapter.probe()
        return LinkAttachOk(
            effective_governance=str(info.governance_mode),
            capabilities=info.capability_snapshot.to_dict()
            if info.capability_snapshot
            else {},
        )

    def _handle_attach(self, msg: LinkAttach) -> LinkAttachOk:
        governance = GovernanceMode(msg.requested_governance)
        if isinstance(self.adapter, WorkerSessionAdapter):
            session = self.adapter.attach_session(
                msg.native_session_ref,
                governance,
                run_id=None,
            )
        elif isinstance(self.adapter, DelegateGatewayAdapter):
            session = self.adapter.attach_delegate_session(
                msg.native_session_ref,
                governance,
                project_id=msg.project_id,
                task_id=msg.task_id,
            )
        else:
            return LinkAttachOk(
                effective_governance=str(governance),
                capabilities={},
            )
        self._session = session
        return LinkAttachOk(
            run_id=session.run_id,
            delegate_session_id=session.delegate_session_id,
            effective_governance=str(session.governance_mode),
            capabilities=session.to_dict(),
        )

    def _handle_poll_actions(self, msg: LinkPollActions) -> LinkActions:
        return LinkActions(items=[])

    def _handle_heartbeat(self, msg: LinkHeartbeat) -> None:
        return None

    def _handle_close(self, msg: LinkClose) -> None:
        if self._session is not None:
            if isinstance(self.adapter, WorkerSessionAdapter):
                self.adapter.close_session(self._session, msg.reason)
            elif isinstance(self.adapter, DelegateGatewayAdapter):
                self.adapter.detach_delegate_session(self._session)
            self._session = None
        return None

    def _write(self, msg: LinkMessage) -> None:
        self._out.write(json.dumps(msg.to_dict(), sort_keys=True) + "\n")
        self._out.flush()

    def _send_error(self, message: str) -> None:
        error = {"type": "error", "message": message, "ts": utc_now_iso()}
        self._out.write(json.dumps(error, sort_keys=True) + "\n")
        self._out.flush()


__all__ = ["LinkServer"]

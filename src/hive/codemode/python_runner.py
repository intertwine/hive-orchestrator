"""Python-side execute sandbox entrypoint."""

from __future__ import annotations

import asyncio
import inspect
import json
import socket
import sys
from pathlib import Path

from src.hive.codemode.client import HiveClient


def _disable_network() -> None:
    """Best-effort network denial for the Python execute sandbox."""

    class DeniedSocket(socket.socket):
        """Socket subclass that rejects outbound connections."""

        def connect(self, *args, **kwargs):  # type: ignore[override]
            raise RuntimeError("Network access is disabled in hive execute")

        def connect_ex(self, *args, **kwargs):  # type: ignore[override]
            raise RuntimeError("Network access is disabled in hive execute")

    def _deny(*args, **kwargs):
        raise RuntimeError("Network access is disabled in hive execute")

    socket.socket = DeniedSocket  # type: ignore[assignment]
    socket.create_connection = _deny  # type: ignore[assignment]


def _json_safe(value):
    """Convert arbitrary values into JSON-serializable data."""
    return json.loads(json.dumps(value, default=str))


def _resolve_value(namespace: dict, hive: HiveClient):
    """Resolve either `main(hive)` or a `result` variable from user code."""
    if "main" in namespace and callable(namespace["main"]):
        value = namespace["main"](hive)
        if inspect.iscoroutine(value):
            return asyncio.run(value)
        return value
    return namespace.get("result")


def main(argv: list[str] | None = None) -> int:
    """Run the Python execute payload and persist a structured result."""
    argv = list(argv or sys.argv[1:])
    payload_path = Path(argv[0])
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    result_path = Path(payload["result_path"])
    _disable_network()
    hive = HiveClient(payload["root"])
    namespace = {"hive": hive, "__builtins__": __builtins__}
    try:
        exec(payload["code"], namespace)  # pylint: disable=exec-used
        result = _resolve_value(namespace, hive)
        result_path.write_text(
            json.dumps({"ok": True, "value": _json_safe(result)}, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return 0
    except Exception as exc:  # pylint: disable=broad-except
        result_path.write_text(
            json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

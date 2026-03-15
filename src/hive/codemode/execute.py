"""Bounded execute surface for thin Code Mode-style integrations."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

MAX_EXECUTE_BYTES = 256 * 1024


def _scrubbed_env(root: Path) -> dict[str, str]:
    allowed = (
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "PYTHONPATH",
        "TMPDIR",
        "TMP",
        "TEMP",
        "VIRTUAL_ENV",
    )
    env = {key: value for key, value in os.environ.items() if key in allowed}
    env["HIVE_EXECUTE_ROOT"] = str(root)
    env["HIVE_EXECUTE_NETWORK"] = "disabled"
    return env


def _coerce_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def execute_code(
    path: str | Path | None,
    *,
    language: str,
    code: str,
    profile: str = "default",
    timeout_seconds: int = 20,
) -> dict[str, Any]:
    """Execute bounded Python code against the typed Hive client.

    This MVP isolates time and environment shape, but it does not isolate filesystem access,
    Python imports, or shelling out through forwarded executables on PATH.
    """
    root = Path(path or Path.cwd()).resolve()
    normalized = language.lower()
    if normalized not in {"python", "py"}:
        return {
            "ok": False,
            "error": (
                f"Unsupported execute language: {language}. " "MVP currently supports Python only."
            ),
            "stdout": "",
            "stderr": "",
            "language": language,
            "profile": profile,
            "timed_out": False,
        }

    with tempfile.TemporaryDirectory(prefix="hive-execute-") as temp_dir:
        payload_path = Path(temp_dir) / "payload.json"
        result_path = Path(temp_dir) / "result.json"
        payload_path.write_text(
            json.dumps(
                {
                    "root": str(root),
                    "code": code,
                    "profile": profile,
                    "result_path": str(result_path),
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "src.hive.codemode.python_runner", str(payload_path)],
                cwd=root,
                env=_scrubbed_env(root),
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "ok": False,
                "error": f"Execute timed out after {timeout_seconds}s",
                "stdout": _coerce_output(exc.stdout),
                "stderr": _coerce_output(exc.stderr),
                "language": language,
                "profile": profile,
                "timed_out": True,
            }

        payload = {
            "ok": completed.returncode == 0,
            "value": None,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "language": language,
            "profile": profile,
            "timed_out": False,
        }
        if result_path.exists():
            result_payload = json.loads(result_path.read_text(encoding="utf-8"))
            payload["ok"] = bool(result_payload.get("ok", payload["ok"]))
            payload["value"] = result_payload.get("value")
            if result_payload.get("error"):
                payload["error"] = result_payload["error"]
        elif completed.returncode != 0:
            payload["error"] = "Execute runner failed before writing a result payload"
        return payload


__all__ = ["MAX_EXECUTE_BYTES", "execute_code"]

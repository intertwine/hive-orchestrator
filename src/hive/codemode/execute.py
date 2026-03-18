"""Bounded local execute surface for thin Code Mode-style integrations."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from src.hive.sandbox import (
    container_path_for_host,
    resolve_sandbox_policy,
    sandboxed_command,
)

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
    """Execute bounded local Python code against the typed Hive client.

    This helper constrains wall-clock time, working directory, environment shape, and applies
    best-effort network denial. It does not provide a full sandbox: filesystem reads, Python
    imports, and shelling out through forwarded executables on PATH are still possible.
    """
    root = Path(path or Path.cwd()).resolve()
    normalized = language.lower()
    if normalized not in {"python", "py"}:
        return {
            "ok": False,
            "error": (
                f"Unsupported execute language: {language}. "
                "Bounded local execute currently supports Python only."
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
        try:
            sandbox_policy = resolve_sandbox_policy(
                worktree_path=str(root),
                artifacts_path=temp_dir,
                profile=profile,
            )
        except ValueError as exc:
            return {
                "ok": False,
                "error": str(exc),
                "stdout": "",
                "stderr": "",
                "language": language,
                "profile": profile,
                "timed_out": False,
            }
        sandbox_metadata = {
            "sandbox_backend": sandbox_policy.backend,
            "sandbox_profile": sandbox_policy.profile,
            "sandbox_provenance": sandbox_policy.provenance,
            "sandbox_network_mode": sandbox_policy.network.get("mode"),
        }
        payload_root = str(root)
        payload_result_path = str(result_path)
        if sandbox_policy.backend != "legacy-host":
            payload_root = container_path_for_host(sandbox_policy, root)
            payload_result_path = container_path_for_host(sandbox_policy, result_path)
        payload_path.write_text(
            json.dumps(
                {
                    "root": payload_root,
                    "code": code,
                    "profile": profile,
                    "result_path": payload_result_path,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        env: dict[str, str] | None
        runner_command: list[str] | str
        use_shell = False
        if sandbox_policy.backend == "legacy-host":
            runner_command = [
                sys.executable,
                "-m",
                "src.hive.codemode.python_runner",
                str(payload_path),
            ]
            env = _scrubbed_env(root)
        else:
            container_payload_path = container_path_for_host(sandbox_policy, payload_path)
            try:
                runner_command, use_shell = sandboxed_command(
                    sandbox_policy,
                    command=(
                        "python -m src.hive.codemode.python_runner "
                        f"{shlex.quote(container_payload_path)}"
                    ),
                    cwd=root,
                )
            except (NotImplementedError, OSError, ValueError) as exc:
                return {
                    "ok": False,
                    "error": str(exc),
                    "stdout": "",
                "stderr": "",
                "language": language,
                "profile": profile,
                "timed_out": False,
                **sandbox_metadata,
            }
            env = None
        try:
            completed = subprocess.run(
                runner_command,
                cwd=root,
                env=env,
                shell=use_shell,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
        except OSError as exc:
            return {
                "ok": False,
                "error": str(exc),
                "stdout": "",
                "stderr": "",
                "language": language,
                "profile": profile,
                "timed_out": False,
                **sandbox_metadata,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "ok": False,
                "error": f"Execute timed out after {timeout_seconds}s",
                "stdout": _coerce_output(exc.stdout),
                "stderr": _coerce_output(exc.stderr),
                "language": language,
                "profile": profile,
                "timed_out": True,
                **sandbox_metadata,
            }

        payload = {
            "ok": completed.returncode == 0,
            "value": None,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "language": language,
            "profile": profile,
            "timed_out": False,
            **sandbox_metadata,
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

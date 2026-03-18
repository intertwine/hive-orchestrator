"""Evaluator execution helpers."""

from __future__ import annotations

import json
from pathlib import Path

from src.hive.runs.executors import CommandResult, Executor


def validate_evaluator_command(command: str, commands_policy: dict | None) -> None:
    """Ensure evaluator commands stay within the program command policy."""
    policy = commands_policy or {}
    allowed = [entry.strip() for entry in policy.get("allow", []) if str(entry).strip()]
    denied = [entry.strip() for entry in policy.get("deny", []) if str(entry).strip()]
    normalized = command.strip()
    if normalized in denied:
        raise ValueError(f"Evaluator command is denied by PROGRAM.md: {command}")
    if normalized not in allowed:
        raise ValueError(f"Evaluator command is not allow-listed in PROGRAM.md: {command}")


def _append_command_log(
    command_log_path: Path,
    *,
    seq: int,
    evaluator_id: str,
    step_result: CommandResult,
) -> None:
    entry = {
        "seq": seq,
        "step_type": "eval",
        "status": (
            # Treat a missing return code as failed so command-log status matches evaluator status.
            "failed"
            if step_result.returncode is None
            or step_result.returncode != 0
            or step_result.timed_out
            else "succeeded"
        ),
        "summary": f"Evaluator {evaluator_id}",
        "command": step_result.command,
        "started_at": step_result.started_at,
        "finished_at": step_result.finished_at,
        "metadata_json": {
            "evaluator_id": evaluator_id,
            "returncode": step_result.returncode,
            "timed_out": step_result.timed_out,
            "sandbox": step_result.sandbox,
        },
    }
    with open(command_log_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def run_evaluator(
    executor: Executor,
    command: str,
    cwd: Path,
    output_dir: Path,
    evaluator_id: str,
    required: bool,
    *,
    command_log_path: Path,
    seq: int,
    timeout_seconds: int,
) -> dict:
    """Run a program evaluator and persist its outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / f"{evaluator_id}.stdout.txt"
    stderr_path = output_dir / f"{evaluator_id}.stderr.txt"
    step_result = executor.run_command(command, cwd=cwd, timeout_seconds=timeout_seconds)
    stdout_path.write_text(step_result.stdout, encoding="utf-8")
    stderr_path.write_text(step_result.stderr, encoding="utf-8")
    _append_command_log(
        command_log_path,
        seq=seq,
        evaluator_id=evaluator_id,
        step_result=step_result,
    )
    result = {
        "evaluator_id": evaluator_id,
        "command": command,
        "required": required,
        "status": "pass" if step_result.returncode == 0 and not step_result.timed_out else "fail",
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "created_at": step_result.finished_at,
        "metadata_json": {
            "returncode": step_result.returncode,
            "timed_out": step_result.timed_out,
            "started_at": step_result.started_at,
            "sandbox": step_result.sandbox,
        },
    }
    (output_dir / f"{evaluator_id}.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result


__all__ = ["run_evaluator", "validate_evaluator_command"]

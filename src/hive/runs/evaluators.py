"""Evaluator execution helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from src.hive.clock import utc_now_iso


def run_evaluator(command: str, cwd: Path, output_dir: Path, evaluator_id: str, required: bool) -> dict:
    """Run a program evaluator and persist its outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / f"{evaluator_id}.stdout.txt"
    stderr_path = output_dir / f"{evaluator_id}.stderr.txt"
    completed = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    result = {
        "evaluator_id": evaluator_id,
        "command": command,
        "required": required,
        "status": "pass" if completed.returncode == 0 else "fail",
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "created_at": utc_now_iso(),
        "metadata_json": {"returncode": completed.returncode},
    }
    (output_dir / f"{evaluator_id}.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result

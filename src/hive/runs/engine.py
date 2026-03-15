"""Minimal local run engine for Hive 2.0."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.hive.clock import utc_now_iso
from src.hive.ids import new_id
from src.hive.models.program import ProgramRecord
from src.hive.models.run import RunRecord
from src.hive.runs.evaluators import run_evaluator, validate_evaluator_command
from src.hive.store.events import emit_event
from src.hive.store.layout import runs_dir, worktrees_dir
from src.hive.store.projects import get_project
from src.hive.store.task_files import get_task, save_task
from src.security import safe_load_agency_md


def load_program(project_path: Path) -> ProgramRecord:
    """Load and validate PROGRAM.md."""
    parsed = safe_load_agency_md(project_path)
    program = ProgramRecord(path=project_path, body=parsed.content, metadata=dict(parsed.metadata))
    program.validate()
    return program


def generate_program_stub(project_dir: Path) -> Path:
    """Create a conservative PROGRAM.md stub when missing."""
    stub = """---
program_version: 1
mode: workflow
default_executor: local
budgets:
  max_wall_clock_minutes: 30
  max_steps: 25
  max_tokens: 20000
  max_cost_usd: 2.0
paths:
  allow:
    - src/**
    - tests/**
    - docs/**
  deny:
    - secrets/**
    - infra/prod/**
commands:
  allow: []
  deny:
    - rm -rf /
    - terraform apply
evaluators: []
promotion:
  requires_all: []
  review_required_when_paths_match: []
  auto_close_task: false
escalation:
  when_paths_match: []
  when_commands_match: []
---

# Goal

Define the autonomous work contract for this project.

# Constraints

- Fill in safe evaluator commands before autonomous runs.
- Commands in `commands.allow` must match evaluator commands exactly.
"""
    target = project_dir / "PROGRAM.md"
    target.write_text(stub, encoding="utf-8")
    return target


def _run_dir(path: str | Path | None, run_id: str) -> Path:
    return runs_dir(path) / run_id


def _metadata_path(path: str | Path | None, run_id: str) -> Path:
    return _run_dir(path, run_id) / "metadata.json"


def start_run(path: str | Path | None, task_id: str) -> RunRecord:
    """Create a bounded local run record and scaffold artifacts."""
    root = Path(path or Path.cwd())
    task = get_task(root, task_id)
    if task.status not in {"proposed", "ready", "claimed"}:
        raise ValueError(f"Cannot start run on task with status {task.status!r}")
    project = get_project(root, task.project_id)
    if not project.program_path.exists():
        generate_program_stub(project.directory)
    program = load_program(project.program_path)
    run_id = new_id("run")
    run_directory = _run_dir(root, run_id)
    worktree_path = worktrees_dir(root) / run_id
    run_directory.mkdir(parents=True, exist_ok=True)
    worktree_path.mkdir(parents=True, exist_ok=True)

    plan_path = run_directory / "plan.md"
    plan_json_path = run_directory / "plan.json"
    patch_path = run_directory / "patch.diff"
    summary_path = run_directory / "summary.md"
    review_path = run_directory / "review.md"
    command_log_path = run_directory / "command-log.jsonl"
    logs_dir = run_directory / "logs"
    eval_dir = run_directory / "eval"
    logs_dir.mkdir(exist_ok=True)
    eval_dir.mkdir(exist_ok=True)

    plan_path.write_text(f"# Run plan\n\nTask: `{task.title}`\n", encoding="utf-8")
    plan_json_path.write_text(
        json.dumps({"task_id": task.id, "title": task.title}, indent=2),
        encoding="utf-8",
    )
    patch_path.write_text("", encoding="utf-8")
    summary_path.write_text("# Summary\n\nPending evaluator results.\n", encoding="utf-8")
    review_path.write_text("# Review\n\nPending acceptance decision.\n", encoding="utf-8")
    command_log_path.write_text("", encoding="utf-8")
    (logs_dir / "stdout.txt").write_text("", encoding="utf-8")
    (logs_dir / "stderr.txt").write_text("", encoding="utf-8")

    run = RunRecord(
        id=run_id,
        project_id=project.id,
        task_id=task.id,
        status="running",
        executor=program.metadata.get("default_executor", "local"),
        branch_name=f"hive/{project.slug}/{task.id}/{run_id}",
        worktree_path=str(worktree_path),
        program_path=str(project.program_path),
        program_sha256=hashlib.sha256(project.program_path.read_bytes()).hexdigest(),
        plan_path=str(plan_path),
        summary_path=str(summary_path),
        review_path=str(review_path),
        patch_path=str(patch_path),
        command_log_path=str(command_log_path),
        logs_dir=str(logs_dir),
        metadata={"task_title": task.title},
    )
    _metadata_path(root, run_id).write_text(
        json.dumps(run.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    task.status = "in_progress"
    save_task(root, task)
    emit_event(
        root,
        actor="hive",
        entity_type="run",
        entity_id=run.id,
        event_type="run.started",
        source="run.start",
        payload={"task_id": task.id},
    )
    return run


def load_run(path: str | Path | None, run_id: str) -> dict:
    """Load run metadata."""
    metadata_path = _metadata_path(path, run_id)
    if not metadata_path.exists():
        raise FileNotFoundError(f"Run not found: {run_id}")
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def _save_run(path: str | Path | None, run_id: str, metadata: dict) -> dict:
    _metadata_path(path, run_id).write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return metadata


def eval_run(path: str | Path | None, run_id: str) -> dict:
    """Execute all configured evaluators for a run."""
    root = Path(path or Path.cwd())
    metadata = load_run(root, run_id)
    if metadata.get("status") != "running":
        raise ValueError(f"Cannot evaluate run with status {metadata.get('status')!r}")
    program = load_program(Path(metadata["program_path"]))
    run_directory = _run_dir(root, run_id)
    results = []
    commands_policy = program.metadata.get("commands", {})
    for evaluator in program.metadata.get("evaluators", []):
        validate_evaluator_command(evaluator["command"], commands_policy)
        result = run_evaluator(
            evaluator["command"],
            root,
            run_directory / "eval",
            evaluator["id"],
            bool(evaluator.get("required", True)),
        )
        results.append(result)
    metadata["status"] = "evaluating"
    metadata["metadata_json"] = metadata.get("metadata_json", {})
    metadata["metadata_json"]["evaluations"] = results
    _save_run(root, run_id, metadata)
    emit_event(
        root,
        actor="hive",
        entity_type="run",
        entity_id=run_id,
        event_type="run.evaluated",
        source="run.eval",
        payload={"results": results},
    )
    return {"run": metadata, "evaluations": results}


def accept_run(path: str | Path | None, run_id: str) -> dict:
    """Accept a run when all required evaluators pass."""
    root = Path(path or Path.cwd())
    metadata = load_run(root, run_id)
    if metadata.get("status") != "evaluating":
        raise ValueError(f"Cannot accept run with status {metadata.get('status')!r}")
    evaluations = metadata.get("metadata_json", {}).get("evaluations", [])
    if any(result.get("required", True) and result["status"] != "pass" for result in evaluations):
        raise ValueError("Cannot accept run with failing required evaluators")
    metadata["status"] = "accepted"
    metadata["finished_at"] = utc_now_iso()
    _save_run(root, run_id, metadata)
    task = get_task(root, metadata["task_id"])
    program = load_program(Path(metadata["program_path"]))
    auto_close = bool(program.metadata.get("promotion", {}).get("auto_close_task", False))
    task.status = "done" if auto_close else "review"
    save_task(root, task)
    emit_event(
        root,
        actor="hive",
        entity_type="run",
        entity_id=run_id,
        event_type="run.accepted",
        source="run.accept",
        payload={"task_id": task.id},
    )
    return metadata


def reject_run(path: str | Path | None, run_id: str, reason: str | None = None) -> dict:
    """Reject a run."""
    metadata = load_run(path, run_id)
    metadata["status"] = "rejected"
    metadata["finished_at"] = utc_now_iso()
    metadata["exit_reason"] = reason
    return _save_run(path, run_id, metadata)


def escalate_run(path: str | Path | None, run_id: str, reason: str | None = None) -> dict:
    """Escalate a run for human review."""
    metadata = load_run(path, run_id)
    metadata["status"] = "escalated"
    metadata["finished_at"] = utc_now_iso()
    metadata["exit_reason"] = reason
    task = get_task(path, metadata["task_id"])
    task.status = "review"
    save_task(path, task)
    return _save_run(path, run_id, metadata)

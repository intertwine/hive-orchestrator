"""Hive 2.0 run engine."""

from __future__ import annotations

from datetime import datetime, timezone
from fnmatch import fnmatch
from hashlib import sha256
import json
from pathlib import Path

from src.hive.clock import utc_now_iso
from src.hive.ids import new_id
from src.hive.models.program import ProgramRecord
from src.hive.models.run import RunRecord
from src.hive.runs.evaluators import run_evaluator, validate_evaluator_command
from src.hive.runs.executors import get_executor
from src.hive.runs.worktree import capture_worktree_state, create_run_worktree, current_head
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


def _task_display(task_id: str) -> str:
    suffix = task_id.removeprefix("task_")
    return f"t-{suffix[:8].lower()}"


def _branch_name(project_slug: str, task_id: str, run_id: str) -> str:
    return f"hive/{project_slug}/{_task_display(task_id)}/{run_id}"


def _read_command_log(command_log_path: Path) -> list[dict]:
    if not command_log_path.exists():
        return []
    entries: list[dict] = []
    for line in command_log_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _matches_path(path: str, pattern: str) -> bool:
    return fnmatch(path, pattern)


def _refresh_workspace_state(root: Path, metadata: dict) -> dict[str, object]:
    state = capture_worktree_state(
        metadata["worktree_path"],
        patch_path=metadata["patch_path"],
    )
    metadata_json = metadata.setdefault("metadata_json", {})
    command_log = _read_command_log(Path(metadata["command_log_path"]))
    metadata_json["touched_paths"] = state["touched_paths"]
    metadata_json["has_changes"] = state["has_changes"]
    metadata_json["commands"] = [entry["command"] for entry in command_log if entry.get("command")]
    metadata_json["command_count"] = len(command_log)
    metadata_json["base_commit"] = metadata_json.get("base_commit") or current_head(root)
    return metadata_json


def _artifact_exists(path_value: str | None) -> bool:
    if not path_value:
        return False
    path = Path(path_value)
    return path.exists() and bool(path.read_text(encoding="utf-8").strip())


def _promotion_decision(program: ProgramRecord, metadata: dict) -> dict[str, object]:
    metadata_json = metadata.setdefault("metadata_json", {})
    evaluations = metadata_json.get("evaluations", [])
    evaluation_by_id = {entry["evaluator_id"]: entry for entry in evaluations}
    touched_paths = list(metadata_json.get("touched_paths", []))
    commands = list(metadata_json.get("commands", []))
    reject_reasons: list[str] = []
    escalate_reasons: list[str] = []

    if not _artifact_exists(metadata.get("summary_path")):
        reject_reasons.append("summary.md is missing or empty")
    if not _artifact_exists(metadata.get("review_path")):
        reject_reasons.append("review.md is missing or empty")

    for result in evaluations:
        if result.get("required", True) and result["status"] != "pass":
            reject_reasons.append(f"Required evaluator failed: {result['evaluator_id']}")

    for evaluator_id in program.metadata.get("promotion", {}).get("requires_all", []):
        result = evaluation_by_id.get(evaluator_id)
        if result is None:
            reject_reasons.append(f"Required promotion evaluator missing: {evaluator_id}")
        elif result["status"] != "pass":
            reject_reasons.append(f"Required promotion evaluator did not pass: {evaluator_id}")

    paths_policy = program.metadata.get("paths", {})
    allow_paths = list(paths_policy.get("allow", []))
    deny_paths = list(paths_policy.get("deny", []))
    for touched_path in touched_paths:
        if any(_matches_path(touched_path, pattern) for pattern in deny_paths):
            reject_reasons.append(f"Touched denied path: {touched_path}")
        elif allow_paths and not any(
            _matches_path(touched_path, pattern) for pattern in allow_paths
        ):
            reject_reasons.append(f"Touched path outside allow-list: {touched_path}")

    review_patterns = program.metadata.get("promotion", {}).get(
        "review_required_when_paths_match", []
    )
    for touched_path in touched_paths:
        if any(_matches_path(touched_path, pattern) for pattern in review_patterns):
            escalate_reasons.append(f"Touched path requires review: {touched_path}")

    for touched_path in touched_paths:
        if any(
            _matches_path(touched_path, pattern)
            for pattern in program.metadata.get("escalation", {}).get("when_paths_match", [])
        ):
            escalate_reasons.append(f"Escalation rule matched path: {touched_path}")

    for command in commands:
        if command in program.metadata.get("escalation", {}).get("when_commands_match", []):
            escalate_reasons.append(f"Escalation rule matched command: {command}")

    budgets = program.metadata.get("budgets", {})
    started_at = _parse_iso(metadata.get("started_at"))
    if started_at is not None:
        duration_seconds = (datetime.now(timezone.utc) - started_at).total_seconds()
        max_seconds = float(budgets.get("max_wall_clock_minutes", 0)) * 60
        if max_seconds and duration_seconds > max_seconds:
            reject_reasons.append(
                f"Run exceeded wall clock budget ({duration_seconds:.1f}s > {max_seconds:.1f}s)"
            )
    max_steps = int(budgets.get("max_steps", 0))
    if max_steps and int(metadata_json.get("command_count", 0)) > max_steps:
        reject_reasons.append(
            f"Run exceeded step budget ({metadata_json.get('command_count', 0)} > {max_steps})"
        )
    total_tokens = int(metadata.get("tokens_in") or 0) + int(metadata.get("tokens_out") or 0)
    max_tokens = int(budgets.get("max_tokens", 0))
    if max_tokens and total_tokens > max_tokens:
        reject_reasons.append(f"Run exceeded token budget ({total_tokens} > {max_tokens})")
    max_cost = float(budgets.get("max_cost_usd", 0))
    cost_usd = float(metadata.get("cost_usd") or 0.0)
    if max_cost and cost_usd > max_cost:
        reject_reasons.append(f"Run exceeded cost budget ({cost_usd:.2f} > {max_cost:.2f})")

    reasons = reject_reasons if reject_reasons else escalate_reasons
    decision = "reject" if reject_reasons else "escalate" if escalate_reasons else "accept"
    return {
        "decision": decision,
        "reasons": reasons,
        "touched_paths": touched_paths,
        "commands": commands,
    }


def _write_review_and_summary(metadata: dict, promotion: dict[str, object]) -> None:
    summary_lines = [
        "# Summary",
        "",
        f"- Run: `{metadata['id']}`",
        f"- Executor: `{metadata['executor']}`",
        f"- Status: `{metadata['status']}`",
        "",
        "## Touched Paths",
    ]
    touched_paths = promotion.get("touched_paths", [])
    if touched_paths:
        summary_lines.extend(f"- `{path}`" for path in touched_paths)
    else:
        summary_lines.append("- No code changes detected.")

    review_lines = [
        "# Review",
        "",
        f"- Promotion decision: `{promotion['decision']}`",
        "",
        "## Reasons",
    ]
    reasons = promotion.get("reasons", [])
    if reasons:
        review_lines.extend(f"- {reason}" for reason in reasons)
    else:
        review_lines.append("- All promotion gates passed.")

    eval_results = metadata.setdefault("metadata_json", {}).get("evaluations", [])
    if eval_results:
        summary_lines.extend(["", "## Evaluators"])
        summary_lines.extend(
            f"- `{result['evaluator_id']}`: {result['status']}" for result in eval_results
        )

    Path(metadata["summary_path"]).write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    Path(metadata["review_path"]).write_text("\n".join(review_lines) + "\n", encoding="utf-8")


def start_run(path: str | Path | None, task_id: str) -> RunRecord:
    """Create a bounded run record and scaffold worktree artifacts."""
    root = Path(path or Path.cwd()).resolve()
    task = get_task(root, task_id)
    if task.status not in {"proposed", "ready", "claimed"}:
        raise ValueError(f"Cannot start run on task with status {task.status!r}")
    project = get_project(root, task.project_id)
    if not project.program_path.exists():
        generate_program_stub(project.directory)
    program = load_program(project.program_path)
    executor_name = program.metadata.get("default_executor", "local")
    # Validate executor name eagerly so invalid PROGRAM.md contracts fail before scaffolding.
    get_executor(executor_name)

    run_id = new_id("run")
    run_directory = _run_dir(root, run_id)
    branch_name = _branch_name(project.slug, task.id, run_id)
    worktree_path = create_run_worktree(
        root,
        branch_name=branch_name,
        worktree_path=worktrees_dir(root) / run_id,
    )
    base_commit = current_head(root)

    run_directory.mkdir(parents=True, exist_ok=True)
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

    plan_path.write_text(
        "\n".join(
            [
                "# Run plan",
                "",
                f"Task: `{task.title}`",
                f"Branch: `{branch_name}`",
                f"Worktree: `{worktree_path}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    plan_json_path.write_text(
        json.dumps(
            {
                "task_id": task.id,
                "title": task.title,
                "branch_name": branch_name,
                "worktree_path": str(worktree_path),
                "executor": executor_name,
                "base_commit": base_commit,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    patch_path.write_text("", encoding="utf-8")
    summary_path.write_text("# Summary\n\nPending evaluator results.\n", encoding="utf-8")
    review_path.write_text("# Review\n\nPending promotion decision.\n", encoding="utf-8")
    command_log_path.write_text("", encoding="utf-8")
    (logs_dir / "stdout.txt").write_text("", encoding="utf-8")
    (logs_dir / "stderr.txt").write_text("", encoding="utf-8")

    run = RunRecord(
        id=run_id,
        project_id=project.id,
        task_id=task.id,
        status="running",
        executor=executor_name,
        branch_name=branch_name,
        worktree_path=str(worktree_path),
        program_path=str(project.program_path),
        program_sha256=sha256(project.program_path.read_bytes()).hexdigest(),
        plan_path=str(plan_path),
        summary_path=str(summary_path),
        review_path=str(review_path),
        patch_path=str(patch_path),
        command_log_path=str(command_log_path),
        logs_dir=str(logs_dir),
        metadata={
            "task_title": task.title,
            "base_commit": base_commit,
            "touched_paths": [],
            "commands": [],
            "command_count": 0,
        },
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
        payload={
            "task_id": task.id,
            "branch_name": branch_name,
            "executor": executor_name,
        },
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
    root = Path(path or Path.cwd()).resolve()
    metadata = load_run(root, run_id)
    if metadata.get("status") != "running":
        raise ValueError(f"Cannot evaluate run with status {metadata.get('status')!r}")
    program = load_program(Path(metadata["program_path"]))
    run_directory = _run_dir(root, run_id)
    command_log_path = Path(metadata["command_log_path"])
    timeout_seconds = max(
        1,
        int(float(program.metadata.get("budgets", {}).get("max_wall_clock_minutes", 30)) * 60),
    )
    executor = get_executor(metadata.get("executor", program.metadata["default_executor"]))
    results = []
    seq = len(_read_command_log(command_log_path)) + 1
    commands_policy = program.metadata.get("commands", {})
    for evaluator in program.metadata.get("evaluators", []):
        validate_evaluator_command(evaluator["command"], commands_policy)
        result = run_evaluator(
            executor,
            evaluator["command"],
            Path(metadata["worktree_path"]),
            run_directory / "eval",
            evaluator["id"],
            bool(evaluator.get("required", True)),
            command_log_path=command_log_path,
            seq=seq,
            timeout_seconds=timeout_seconds,
        )
        seq += 1
        results.append(result)

    metadata["status"] = "evaluating"
    metadata_json = _refresh_workspace_state(root, metadata)
    metadata_json["evaluations"] = results
    promotion = _promotion_decision(program, metadata)
    metadata_json["promotion_decision"] = promotion
    _write_review_and_summary(metadata, promotion)
    _save_run(root, run_id, metadata)
    emit_event(
        root,
        actor="hive",
        entity_type="run",
        entity_id=run_id,
        event_type="run.evaluated",
        source="run.eval",
        payload={"results": results, "promotion_decision": promotion},
    )
    return {"run": metadata, "evaluations": results, "promotion_decision": promotion}


def accept_run(path: str | Path | None, run_id: str) -> dict:
    """Accept a run when all promotion gates pass."""
    root = Path(path or Path.cwd()).resolve()
    metadata = load_run(root, run_id)
    if metadata.get("status") != "evaluating":
        raise ValueError(f"Cannot accept run with status {metadata.get('status')!r}")

    program = load_program(Path(metadata["program_path"]))
    # Re-evaluate at accept time because worktree state may have changed since eval_run.
    metadata_json = _refresh_workspace_state(root, metadata)
    promotion = _promotion_decision(program, metadata)
    metadata_json["promotion_decision"] = promotion
    _write_review_and_summary(metadata, promotion)
    if promotion["decision"] != "accept":
        reasons = "; ".join(promotion["reasons"]) or "promotion gates failed"
        _save_run(root, run_id, metadata)
        raise ValueError(f"Run cannot be accepted: {reasons}")

    metadata["status"] = "accepted"
    metadata["finished_at"] = utc_now_iso()
    _save_run(root, run_id, metadata)
    # TODO: prune terminal run worktrees once downstream review tooling no longer depends on them.
    task = get_task(root, metadata["task_id"])
    auto_close = bool(program.metadata.get("promotion", {}).get("auto_close_task", False))
    task.status = "done" if auto_close else "review"
    task.owner = None
    task.claimed_until = None
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
    root = Path(path or Path.cwd()).resolve()
    metadata = load_run(root, run_id)
    if metadata.get("status") not in {"running", "evaluating"}:
        raise ValueError(f"Cannot reject run with status {metadata.get('status')!r}")
    _refresh_workspace_state(root, metadata)
    metadata["status"] = "rejected"
    metadata["finished_at"] = utc_now_iso()
    metadata["exit_reason"] = reason
    _save_run(root, run_id, metadata)
    task = get_task(root, metadata["task_id"])
    task.status = "ready"
    task.owner = None
    task.claimed_until = None
    save_task(root, task)
    emit_event(
        root,
        actor="hive",
        entity_type="run",
        entity_id=run_id,
        event_type="run.rejected",
        source="run.reject",
        payload={"task_id": task.id, "reason": reason},
    )
    return metadata


def escalate_run(path: str | Path | None, run_id: str, reason: str | None = None) -> dict:
    """Escalate a run for human review."""
    root = Path(path or Path.cwd()).resolve()
    metadata = load_run(root, run_id)
    if metadata.get("status") not in {"running", "evaluating"}:
        raise ValueError(f"Cannot escalate run with status {metadata.get('status')!r}")
    _refresh_workspace_state(root, metadata)
    metadata["status"] = "escalated"
    metadata["finished_at"] = utc_now_iso()
    metadata["exit_reason"] = reason
    _save_run(root, run_id, metadata)
    task = get_task(root, metadata["task_id"])
    task.status = "review"
    task.owner = None
    task.claimed_until = None
    save_task(root, task)
    emit_event(
        root,
        actor="hive",
        entity_type="run",
        entity_id=run_id,
        event_type="run.escalated",
        source="run.escalate",
        payload={"task_id": task.id, "reason": reason},
    )
    return metadata

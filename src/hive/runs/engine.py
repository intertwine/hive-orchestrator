"""Hive 2.0 run engine."""

from __future__ import annotations

from datetime import datetime, timezone
from fnmatch import fnmatch
from hashlib import sha256
import json
from pathlib import Path
from typing import cast

from src.hive.clock import utc_now_iso
from src.hive.constants import RUN_ACTIVE_STATUSES, RUN_TERMINAL_STATUSES
from src.hive.drivers import (
    RunBudget,
    RunHandle,
    RunLaunchRequest,
    RunWorkspace,
    SteeringRequest,
    get_driver,
)
from src.hive.ids import new_id
from src.hive.models.program import ProgramRecord
from src.hive.models.run import RunRecord
from src.hive.runs.context import compile_run_context
from src.hive.runs.evaluators import run_evaluator, validate_evaluator_command
from src.hive.runs.executors import get_executor
from src.hive.runs.worktree import (
    capture_worktree_state,
    commit_paths,
    create_run_worktree,
    current_branch,
    current_head,
    delete_branch,
    ensure_clean_repo,
    merge_branch,
    remove_worktree,
    restore_derived_state,
    split_dirty_paths,
)
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


def _program_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load_run_program(metadata: dict) -> ProgramRecord:
    """Load the recorded run contract and reject policy drift."""
    program_path = Path(metadata["program_path"])
    if not program_path.exists():
        raise FileNotFoundError(
            "PROGRAM.md no longer exists for this run. Restore it or start a new run under the "
            "current project contract."
        )
    current_sha = _program_sha(program_path)
    expected_sha = metadata.get("program_sha256")
    if expected_sha and current_sha != expected_sha:
        raise ValueError(
            "PROGRAM.md changed after this run started. Start a new run so evaluation uses the "
            "current contract."
        )
    return load_program(program_path)


def _preflight_program_for_run(root: Path, project_path: Path) -> ProgramRecord:
    """Validate the run contract and repo state before scaffolding."""
    issues: list[str] = []
    if not project_path.exists():
        raise FileNotFoundError(
            f"Run start requires PROGRAM.md at {project_path}. "
            "Create or restore the project contract before starting autonomous work."
        )
    try:
        program = load_program(project_path)
    except ValueError as exc:
        program = None
        issues.append(str(exc))

    try:
        ensure_clean_repo(root)
    except ValueError as exc:
        issues.append(str(exc))

    if issues:
        raise ValueError("Run start preflight failed:\n- " + "\n- ".join(issues))
    assert program is not None  # pragma: no cover - guarded by the issues check above.
    return program


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
        base_ref=metadata.setdefault("metadata_json", {}).get("base_commit"),
    )
    metadata_json = metadata.setdefault("metadata_json", {})
    command_log = _read_command_log(Path(metadata["command_log_path"]))
    metadata_json["touched_paths"] = state["touched_paths"]
    metadata_json["has_changes"] = state["has_changes"]
    metadata_json["commands"] = [entry["command"] for entry in command_log if entry.get("command")]
    metadata_json["command_count"] = len(command_log)
    metadata_json["base_commit"] = metadata_json.get("base_commit") or current_head(root)
    metadata_json["base_branch"] = metadata_json.get("base_branch") or current_branch(root)
    changed_files_path = metadata.get("workspace_changed_files_path")
    if changed_files_path:
        Path(changed_files_path).write_text(
            json.dumps({"files": state["touched_paths"]}, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    patch_path = metadata.get("patch_path")
    if patch_path:
        patch_file = Path(patch_path)
        legacy_patch = _run_dir(root, str(metadata["id"])) / "patch.diff"
        if legacy_patch != patch_file:
            legacy_patch.write_text(patch_file.read_text(encoding="utf-8"), encoding="utf-8")
    return metadata_json


def _task_title(metadata: dict) -> str:
    return metadata.setdefault("metadata_json", {}).get("task_title") or metadata["task_id"]


def _filtered_dirty_paths(root: Path, metadata: dict) -> dict[str, list[str]]:
    """Filter local manager-generated artifacts out of dirty-path checks."""
    dirty = split_dirty_paths(root)
    context_output_path = metadata.get("metadata_json", {}).get("context_output_path")
    if not context_output_path:
        return dirty
    context_path = Path(str(context_output_path)).expanduser()
    candidates = {str(context_path)}
    try:
        candidates.add(str(context_path.resolve()))
    except OSError:  # pragma: no cover - defensive
        pass
    try:
        candidates.add(str(context_path.resolve().relative_to(root)))
    except (OSError, ValueError):  # pragma: no cover - path outside repo or unresolved.
        pass
    dirty["noncanonical"] = [path for path in dirty["noncanonical"] if path not in candidates]
    return dirty


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
    has_changes = bool(metadata_json.get("has_changes", False))
    reject_reasons: list[str] = []
    escalate_reasons: list[str] = []

    if not _artifact_exists(metadata.get("summary_path")):
        reject_reasons.append("summary.md is missing or empty")
    if not _artifact_exists(metadata.get("review_path")):
        reject_reasons.append("review.md is missing or empty")
    if not has_changes and not program.allow_accept_without_changes():
        reject_reasons.append(
            "Run did not produce workspace changes. Add a real change or set "
            "promotion.allow_accept_without_changes: true for deliberate no-op flows."
        )
    if not evaluations and not program.unsafe_without_evaluators():
        reject_reasons.append(
            "No evaluator results recorded. Add required evaluators to PROGRAM.md or opt into "
            "promotion.allow_unsafe_without_evaluators explicitly."
        )

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
        f"- Driver: `{metadata.get('driver', metadata.get('executor', 'local'))}`",
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
        if promotion["decision"] == "accept":
            review_lines.append("- All promotion gates passed.")
        else:
            review_lines.append("- No promotion gates passed cleanly.")

    eval_results = metadata.setdefault("metadata_json", {}).get("evaluations", [])
    if eval_results:
        summary_lines.extend(["", "## Evaluators"])
        summary_lines.extend(
            f"- `{result['evaluator_id']}`: {result['status']}" for result in eval_results
        )

    summary_content = "\n".join(summary_lines) + "\n"
    review_content = "\n".join(review_lines) + "\n"
    Path(metadata["summary_path"]).write_text(summary_content, encoding="utf-8")
    Path(metadata["review_path"]).write_text(review_content, encoding="utf-8")
    run_root = Path(metadata["summary_path"]).resolve().parents[1]
    (run_root / "summary.md").write_text(summary_content, encoding="utf-8")
    (run_root / "review.md").write_text(review_content, encoding="utf-8")


def _run_paths(run_directory: Path) -> dict[str, Path]:
    plan_dir = run_directory / "plan"
    review_dir = run_directory / "review"
    context_dir = run_directory / "context"
    transcript_dir = run_directory / "transcript"
    workspace_dir = run_directory / "workspace"
    driver_dir = run_directory / "driver"
    logs_dir = run_directory / "logs"
    eval_dir = run_directory / "eval"
    for directory in (
        plan_dir,
        review_dir,
        context_dir / "compiled",
        transcript_dir / "raw",
        workspace_dir,
        driver_dir,
        logs_dir,
        eval_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    return {
        "plan_path": plan_dir / "plan.md",
        "plan_json_path": plan_dir / "plan.json",
        "legacy_plan_json_path": run_directory / "plan.json",
        "launch_path": run_directory / "launch.json",
        "summary_path": review_dir / "summary.md",
        "legacy_summary_path": run_directory / "summary.md",
        "review_path": review_dir / "review.md",
        "legacy_review_path": run_directory / "review.md",
        "patch_path": workspace_dir / "patch.diff",
        "legacy_patch_path": run_directory / "patch.diff",
        "changed_files_path": workspace_dir / "changed_files.json",
        "command_log_path": logs_dir / "command-log.jsonl",
        "stdout_path": logs_dir / "stdout.txt",
        "stderr_path": logs_dir / "stderr.txt",
        "logs_dir": logs_dir,
        "eval_dir": eval_dir,
        "transcript_path": transcript_dir / "normalized.jsonl",
        "transcript_raw_dir": transcript_dir / "raw",
        "driver_metadata_path": driver_dir / "driver-metadata.json",
        "driver_handles_path": driver_dir / "handles.json",
        "events_path": run_directory / "events.jsonl",
    }


def _run_program_policy(program: ProgramRecord) -> dict[str, object]:
    commands = program.metadata.get("commands", {})
    paths = program.metadata.get("paths", {})
    return {
        "network": program.metadata.get("network", "ask"),
        "paths": list(paths.get("allow", [])),
        "blocked_paths": list(paths.get("deny", [])),
        "commands_allow": list(commands.get("allow", [])),
        "commands_deny": list(commands.get("deny", [])),
        "evaluator_policy": (
            "unsafe"
            if program.unsafe_without_evaluators()
            else "required"
        ),
    }


def _emit_context_compiled_events(
    root: Path,
    *,
    run_id: str,
    task_id: str,
    project_id: str,
    manifest_path: str,
) -> None:
    """Emit both run-scoped and context-scoped context-compilation events.

    ``run.context_compiled`` is the run-timeline event operators inspect directly.
    ``context.compiled`` remains the cross-cutting alias used by context and memory consumers.
    """
    payload = {"manifest_path": manifest_path}
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="run.context_compiled",
        source="run.start",
        payload=payload,
        run_id=run_id,
        task_id=task_id,
        project_id=project_id,
    )
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="context.compiled",
        source="run.start",
        payload=payload,
        run_id=run_id,
        task_id=task_id,
        project_id=project_id,
    )


def _append_transcript_entry(path: Path, record: dict[str, object]) -> None:
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _load_driver_handles(metadata: dict) -> dict[str, object]:
    handles_path = Path(metadata.get("driver_handles_path", ""))
    if not handles_path.exists():
        return {"active": None, "history": []}
    return json.loads(handles_path.read_text(encoding="utf-8"))


def _save_driver_handles(metadata: dict, handles: dict[str, object]) -> None:
    handles_path = Path(metadata["driver_handles_path"])
    handles_path.write_text(json.dumps(handles, indent=2, sort_keys=True), encoding="utf-8")


def _active_driver_handle(metadata: dict) -> RunHandle:
    handles = _load_driver_handles(metadata)
    active = handles.get("active")
    if not isinstance(active, dict):
        raise ValueError(f"Run {metadata['id']} does not have an active driver handle")
    return RunHandle(**active)


def _record_driver_status(metadata: dict, status: dict[str, object]) -> None:
    metadata.setdefault("metadata_json", {})["driver_status"] = status


def _record_steering_history(
    metadata: dict,
    *,
    action: str,
    actor: str | None,
    reason: str | None,
    note: str | None,
    target: dict[str, object] | None,
    budget_delta: dict[str, object] | None,
    ack: dict[str, object] | None = None,
) -> dict[str, object]:
    entry: dict[str, object] = {
        "ts": utc_now_iso(),
        "action": action,
        "actor": actor or "operator",
        "reason": reason,
        "note": note,
        "target": dict(target or {}),
        "budget_delta": dict(budget_delta or {}),
    }
    if ack is not None:
        entry["driver_ack"] = ack
    metadata.setdefault("metadata_json", {}).setdefault("steering_history", []).append(entry)
    return entry


def _steering_event_type(action: str) -> str:
    if action == "note":
        return "steering.note_added"
    if action == "reroute":
        return "steering.rerouted"
    return f"steering.{action}"


def _build_reroute_launch_request(
    root: Path,
    metadata: dict,
    *,
    driver_name: str,
    model: str | None = None,
) -> RunLaunchRequest:
    program = _load_run_program(metadata)
    return RunLaunchRequest(
        run_id=str(metadata["id"]),
        task_id=str(metadata["task_id"]),
        project_id=str(metadata["project_id"]),
        campaign_id=metadata.get("campaign_id"),
        driver=driver_name,
        model=model or metadata.get("model"),
        budget=RunBudget(
            max_tokens=int(program.metadata.get("budgets", {}).get("max_tokens", 0)),
            max_cost_usd=float(program.metadata.get("budgets", {}).get("max_cost_usd", 0.0)),
            max_wall_minutes=int(
                float(program.metadata.get("budgets", {}).get("max_wall_clock_minutes", 0))
            ),
        ),
        workspace=RunWorkspace(
            repo_root=str(root),
            worktree_path=str(metadata["worktree_path"]),
            base_branch=str(
                metadata.get("metadata_json", {}).get("base_branch") or current_branch(root)
            ),
        ),
        compiled_context_path=str(metadata.get("context_compiled_dir")),
        artifacts_path=str(_run_dir(root, str(metadata["id"]))),
        program_policy=_run_program_policy(program),
        steering_notes=[
            str(item.get("note", ""))
            for item in metadata.get("metadata_json", {}).get("steering_history", [])
            if isinstance(item, dict) and str(item.get("note", "")).strip()
        ],
        metadata={
            "initiator": "human",
            "source": "hive steer reroute",
            "task_title": (
                metadata.get("metadata_json", {}).get("task_title") or metadata["task_id"]
            ),
        },
    )


def _artifact_payload(metadata: dict) -> dict[str, object]:
    return {
        "plan": metadata.get("plan_path"),
        "launch": metadata.get("launch_path"),
        "context_manifest": metadata.get("context_manifest_path"),
        "context_compiled_dir": metadata.get("context_compiled_dir"),
        "transcript": metadata.get("transcript_path"),
        "transcript_raw_dir": metadata.get("transcript_raw_dir"),
        "patch": metadata.get("workspace_patch_path") or metadata.get("patch_path"),
        "changed_files": metadata.get("workspace_changed_files_path"),
        "summary": metadata.get("summary_path"),
        "review": metadata.get("review_path"),
        "driver_metadata": metadata.get("driver_metadata_path"),
        "driver_handles": metadata.get("driver_handles_path"),
        "events": metadata.get("events_path"),
        "logs": metadata.get("logs_dir"),
    }


def start_run(
    path: str | Path | None,
    task_id: str,
    *,
    driver_name: str | None = None,
    model: str | None = None,
    campaign_id: str | None = None,
    profile: str = "default",
) -> RunRecord:
    """Create a bounded run record and scaffold worktree artifacts."""
    root = Path(path or Path.cwd()).resolve()
    task = get_task(root, task_id)
    if task.status not in {"proposed", "ready", "claimed"}:
        raise ValueError(f"Cannot start run on task with status {task.status!r}")
    project = get_project(root, task.project_id)
    program = _preflight_program_for_run(root, project.program_path)
    executor_name = program.metadata.get("default_executor", "local")
    # Validate executor name eagerly so invalid PROGRAM.md contracts fail before scaffolding.
    get_executor(executor_name)
    driver = get_driver(driver_name or "local")
    driver_info = driver.probe()

    run_id = new_id("run")
    run_directory = _run_dir(root, run_id)
    branch_name = _branch_name(project.slug, task.id, run_id)
    base_branch = current_branch(root)
    worktree_path = create_run_worktree(
        root,
        branch_name=branch_name,
        worktree_path=worktrees_dir(root) / run_id,
    )
    base_commit = current_head(root)

    run_directory.mkdir(parents=True, exist_ok=True)
    paths = _run_paths(run_directory)
    context_bundle = compile_run_context(
        root,
        run_id=run_id,
        project=project,
        task=task,
        run_directory=run_directory,
        driver=driver.name,
        profile=profile,
    )

    paths["plan_path"].write_text(
        "\n".join(
            [
                "# Run plan",
                "",
                f"Task: `{task.title}`",
                f"Driver: `{driver.name}`",
                f"Branch: `{branch_name}`",
                f"Worktree: `{worktree_path}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    paths["plan_json_path"].write_text(
        json.dumps(
            {
                "task_id": task.id,
                "title": task.title,
                "branch_name": branch_name,
                "worktree_path": str(worktree_path),
                "executor": executor_name,
                "driver": driver.name,
                "base_branch": base_branch,
                "base_commit": base_commit,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    paths["legacy_plan_json_path"].write_text(
        paths["plan_json_path"].read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    paths["patch_path"].write_text("", encoding="utf-8")
    paths["legacy_patch_path"].write_text("", encoding="utf-8")
    paths["changed_files_path"].write_text('{\n  "files": []\n}\n', encoding="utf-8")
    paths["summary_path"].write_text(
        "# Summary\n\nPending evaluator results.\n",
        encoding="utf-8",
    )
    paths["legacy_summary_path"].write_text(
        "# Summary\n\nPending evaluator results.\n",
        encoding="utf-8",
    )
    paths["review_path"].write_text(
        "# Review\n\nPending promotion decision.\n",
        encoding="utf-8",
    )
    paths["legacy_review_path"].write_text(
        "# Review\n\nPending promotion decision.\n",
        encoding="utf-8",
    )
    paths["command_log_path"].write_text("", encoding="utf-8")
    paths["stdout_path"].write_text("", encoding="utf-8")
    paths["stderr_path"].write_text("", encoding="utf-8")
    paths["transcript_path"].write_text("", encoding="utf-8")

    launch_request = RunLaunchRequest(
        run_id=run_id,
        task_id=task.id,
        project_id=project.id,
        campaign_id=campaign_id,
        driver=driver.name,
        model=model,
        budget=RunBudget(
            max_tokens=int(program.metadata.get("budgets", {}).get("max_tokens", 0)),
            max_cost_usd=float(program.metadata.get("budgets", {}).get("max_cost_usd", 0.0)),
            max_wall_minutes=int(
                float(program.metadata.get("budgets", {}).get("max_wall_clock_minutes", 0))
            ),
        ),
        workspace=RunWorkspace(
            repo_root=str(root),
            worktree_path=str(worktree_path),
            base_branch=base_branch,
        ),
        compiled_context_path=str(context_bundle["compiled_dir"]),
        artifacts_path=str(run_directory),
        program_policy=_run_program_policy(program),
        metadata={
            "initiator": "human",
            "source": "hive run start",
            "task_title": task.title,
        },
    )
    handle = driver.launch(launch_request)
    run_status = driver.status(handle)
    paths["launch_path"].write_text(
        json.dumps(launch_request.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    paths["driver_metadata_path"].write_text(
        json.dumps(driver_info.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    paths["driver_handles_path"].write_text(
        json.dumps(
            {"active": handle.to_dict(), "history": [handle.to_dict()]},
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _append_transcript_entry(
        paths["transcript_path"],
        {
            "ts": utc_now_iso(),
            "kind": "system",
            "driver": driver.name,
            "message": run_status.progress.message,
            "state": run_status.state,
        },
    )

    run = RunRecord(
        id=run_id,
        project_id=project.id,
        task_id=task.id,
        driver=driver.name,
        driver_handle=handle.driver_handle,
        campaign_id=campaign_id,
        status=run_status.state,
        health=run_status.health,
        executor=executor_name,
        branch_name=branch_name,
        worktree_path=str(worktree_path),
        program_path=str(project.program_path),
        program_sha256=_program_sha(project.program_path),
        launch_path=str(paths["launch_path"]),
        context_manifest_path=str(context_bundle["manifest_path"]),
        context_compiled_dir=str(context_bundle["compiled_dir"]),
        transcript_path=str(paths["transcript_path"]),
        transcript_raw_dir=str(paths["transcript_raw_dir"]),
        workspace_patch_path=str(paths["patch_path"]),
        workspace_changed_files_path=str(paths["changed_files_path"]),
        driver_metadata_path=str(paths["driver_metadata_path"]),
        driver_handles_path=str(paths["driver_handles_path"]),
        events_path=str(paths["events_path"]),
        plan_path=str(paths["plan_path"]),
        summary_path=str(paths["summary_path"]),
        review_path=str(paths["review_path"]),
        patch_path=str(paths["patch_path"]),
        command_log_path=str(paths["command_log_path"]),
        logs_dir=str(paths["logs_dir"]),
        metadata={
            "task_title": task.title,
            "base_branch": base_branch,
            "base_commit": base_commit,
            "touched_paths": [],
            "commands": [],
            "command_count": 0,
            "driver_status": run_status.to_dict(),
            "context_manifest": context_bundle["manifest"],
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
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run.id,
        event_type="run.queued",
        source="run.start",
        payload={
            "task_id": task.id,
            "branch_name": branch_name,
            "executor": executor_name,
            "driver": driver.name,
        },
        run_id=run.id,
        task_id=task.id,
        project_id=project.id,
    )
    _emit_context_compiled_events(
        root,
        run_id=run.id,
        task_id=task.id,
        project_id=project.id,
        manifest_path=str(context_bundle["manifest_path"]),
    )
    emit_event(
        root,
        actor={"kind": "system", "id": f"driver:{driver.name}"},
        entity_type="run",
        entity_id=run.id,
        event_type="run.launch_started",
        source="run.start",
        payload={"launch_path": str(paths["launch_path"])},
        run_id=run.id,
        task_id=task.id,
        project_id=project.id,
    )
    emit_event(
        root,
        actor={"kind": "system", "id": f"driver:{driver.name}"},
        entity_type="run",
        entity_id=run.id,
        event_type="run.launched",
        source="run.start",
        payload={"handle": handle.to_dict()},
        run_id=run.id,
        task_id=task.id,
        project_id=project.id,
    )
    emit_event(
        root,
        actor={"kind": "system", "id": f"driver:{driver.name}"},
        entity_type="run",
        entity_id=run.id,
        event_type="run.status.changed",
        source="run.start",
        payload={"state": run_status.state, "health": run_status.health},
        run_id=run.id,
        task_id=task.id,
        project_id=project.id,
    )
    if run_status.state == "awaiting_input":
        emit_event(
            root,
            actor={"kind": "system", "id": f"driver:{driver.name}"},
            entity_type="run",
            entity_id=run.id,
            event_type="run.awaiting_input",
            source="run.start",
            payload={"waiting_on": run_status.waiting_on, "message": run_status.progress.message},
            run_id=run.id,
            task_id=task.id,
            project_id=project.id,
        )
    return run


def load_run(path: str | Path | None, run_id: str) -> dict:
    """Load run metadata."""
    metadata_path = _metadata_path(path, run_id)
    if not metadata_path.exists():
        raise FileNotFoundError(f"Run not found: {run_id}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.setdefault("driver", metadata.get("executor", "local"))
    metadata.setdefault("health", "healthy")
    metadata.setdefault("workspace_patch_path", metadata.get("patch_path"))
    metadata.setdefault("workspace_changed_files_path", None)
    metadata.setdefault("events_path", str(_run_dir(path, run_id) / "events.jsonl"))
    metadata.setdefault("metadata_json", {})
    metadata.setdefault("campaign_id", None)
    if metadata.get("status") == "evaluating":
        metadata["status"] = "awaiting_review"
    return metadata


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
    if metadata.get("status") not in {"running", "awaiting_input", "completed_candidate"}:
        raise ValueError(f"Cannot evaluate run with status {metadata.get('status')!r}")
    program = _load_run_program(metadata)
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
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="eval.started",
        source="run.eval",
        payload={},
        run_id=run_id,
        task_id=metadata.get("task_id"),
        project_id=metadata.get("project_id"),
    )
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

    metadata["status"] = "awaiting_review"
    metadata_json = _refresh_workspace_state(root, metadata)
    metadata_json["evaluations"] = results
    promotion = _promotion_decision(program, metadata)
    metadata_json["promotion_decision"] = promotion
    _write_review_and_summary(metadata, promotion)
    _save_run(root, run_id, metadata)
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="eval.completed",
        source="run.eval",
        payload={"results": results, "promotion_decision": promotion},
        run_id=run_id,
        task_id=metadata.get("task_id"),
        project_id=metadata.get("project_id"),
    )
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="run.completed_candidate",
        source="run.eval",
        payload={"promotion_decision": promotion},
        run_id=run_id,
        task_id=metadata.get("task_id"),
        project_id=metadata.get("project_id"),
    )
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="run.awaiting_review",
        source="run.eval",
        payload={"promotion_decision": promotion},
        run_id=run_id,
        task_id=metadata.get("task_id"),
        project_id=metadata.get("project_id"),
    )
    emit_event(
        root,
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="review.summary_generated",
        source="run.eval",
        payload={"summary_path": metadata.get("summary_path"), "review_path": metadata.get("review_path")},
        run_id=run_id,
        task_id=metadata.get("task_id"),
        project_id=metadata.get("project_id"),
    )
    return {"run": metadata, "evaluations": results, "promotion_decision": promotion}


def accept_run(path: str | Path | None, run_id: str) -> dict:
    """Accept a run when all promotion gates pass."""
    root = Path(path or Path.cwd()).resolve()
    metadata = load_run(root, run_id)
    if metadata.get("status") != "awaiting_review":
        raise ValueError(f"Cannot accept run with status {metadata.get('status')!r}")

    program = _load_run_program(metadata)
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
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="run.accepted",
        source="run.accept",
        payload={"task_id": task.id},
        run_id=run_id,
        task_id=task.id,
        project_id=metadata.get("project_id"),
    )
    return metadata


def run_artifacts(path: str | Path | None, run_id: str) -> dict[str, object]:
    """Return the normalized artifact map for a run."""
    metadata = load_run(path, run_id)
    return {
        "run": metadata,
        "artifacts": _artifact_payload(metadata),
    }


def promote_run(
    path: str | Path | None,
    run_id: str,
    *,
    cleanup_worktree: bool = False,
) -> dict[str, object]:
    """Commit canonical run state and merge an accepted run branch into the workspace."""
    root = Path(path or Path.cwd()).resolve()
    metadata = load_run(root, run_id)
    if metadata.get("status") != "accepted":
        raise ValueError(f"Cannot promote run with status {metadata.get('status')!r}")

    branch_name = metadata.get("branch_name")
    if not branch_name:
        raise ValueError(f"Run {run_id} does not have a mergeable branch")

    dirty = _filtered_dirty_paths(root, metadata)
    if dirty["noncanonical"]:
        details = ", ".join(dirty["noncanonical"][:5])
        raise ValueError(
            "Run promotion requires a clean repo outside of canonical Hive state files. "
            f"Dirty paths: {details}"
        )

    title = _task_title(metadata)
    state_commit = commit_paths(
        root,
        paths=dirty["canonical"],
        message=f"Accept {title} run",
    )
    merge_result = merge_branch(root, branch_name=branch_name, message=f"Merge {title} run")
    cleanup_result = None
    worktree_path = metadata.get("worktree_path")
    if cleanup_worktree and worktree_path:
        cleanup_result = cleanup_run(root, run_id)
    can_delete_branch = cleanup_worktree or not worktree_path or not Path(worktree_path).exists()
    if can_delete_branch:
        branch_cleanup = delete_branch(root, branch_name)
    else:
        branch_cleanup = {
            "deleted": False,
            "already_missing": False,
            "branch_name": branch_name,
            "warning": (
                "Branch kept because the linked run worktree still exists. "
                "Re-run promotion with `--cleanup-worktree` or remove the worktree first."
            ),
        }
    derived_cleanup = restore_derived_state(root)

    return {
        "run": metadata,
        "branch_name": branch_name,
        "state_commit": state_commit,
        "merge": merge_result,
        "branch_cleanup": branch_cleanup,
        "cleanup": cleanup_result,
        "derived_cleanup": derived_cleanup,
    }


def reject_run(path: str | Path | None, run_id: str, reason: str | None = None) -> dict:
    """Reject a run."""
    root = Path(path or Path.cwd()).resolve()
    metadata = load_run(root, run_id)
    if metadata.get("status") not in RUN_ACTIVE_STATUSES:
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
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="run.rejected",
        source="run.reject",
        payload={"task_id": task.id, "reason": reason},
        run_id=run_id,
        task_id=task.id,
        project_id=metadata.get("project_id"),
    )
    return metadata


def escalate_run(path: str | Path | None, run_id: str, reason: str | None = None) -> dict:
    """Escalate a run for human review."""
    root = Path(path or Path.cwd()).resolve()
    metadata = load_run(root, run_id)
    if metadata.get("status") not in RUN_ACTIVE_STATUSES:
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
        actor={"kind": "system", "id": "hive"},
        entity_type="run",
        entity_id=run_id,
        event_type="run.escalated",
        source="run.escalate",
        payload={"task_id": task.id, "reason": reason},
        run_id=run_id,
        task_id=task.id,
        project_id=metadata.get("project_id"),
    )
    return metadata


def steer_run(
    path: str | Path | None,
    run_id: str,
    request: SteeringRequest,
    *,
    actor: str | None = None,
) -> dict[str, object]:
    """Apply a typed steering action to a run and persist its audit trail."""
    root = Path(path or Path.cwd()).resolve()
    metadata = load_run(root, run_id)
    action = request.action
    if action not in {
        "pause",
        "resume",
        "cancel",
        "reroute",
        "note",
        "approve",
        "reject",
    }:
        raise ValueError(f"Unsupported steering action {action!r}")
    if action != "note" and metadata.get("status") in RUN_TERMINAL_STATUSES:
        raise ValueError(f"Cannot steer terminal run with status {metadata.get('status')!r}")

    driver = get_driver(str(metadata.get("driver", "local")))
    handle = _active_driver_handle(metadata)
    timeline_entry = _record_steering_history(
        metadata,
        action=action,
        actor=actor,
        reason=request.reason,
        note=request.note,
        target=cast(dict[str, object] | None, request.target),
        budget_delta=cast(dict[str, object] | None, request.budget_delta),
    )
    ack: dict[str, object] | None = None

    if action in {"pause", "resume", "cancel"}:
        ack = driver.interrupt(handle, action)
        timeline_entry["driver_ack"] = ack
        if action == "pause":
            metadata["health"] = "paused"
            metadata.setdefault("metadata_json", {})["paused"] = True
        elif action == "resume":
            metadata["health"] = "healthy"
            metadata.setdefault("metadata_json", {})["paused"] = False
        else:
            metadata["status"] = "cancelled"
            metadata["health"] = "cancelled"
            metadata["finished_at"] = utc_now_iso()
            metadata["exit_reason"] = request.reason
            task = get_task(root, metadata["task_id"])
            task.status = "ready"
            task.owner = None
            task.claimed_until = None
            save_task(root, task)
    elif action == "note":
        ack = driver.steer(handle, request)
        timeline_entry["driver_ack"] = ack
    elif action == "reroute":
        target_driver = str((request.target or {}).get("driver", "")).strip()
        if not target_driver:
            raise ValueError("Reroute requires target.driver")
        emit_event(
            root,
            actor={"kind": "human", "id": actor or "operator"},
            entity_type="run",
            entity_id=run_id,
            event_type="steering.reroute_requested",
            source="run.steer",
            payload={"request": request.to_dict()},
            run_id=run_id,
            task_id=metadata.get("task_id"),
            project_id=metadata.get("project_id"),
            campaign_id=metadata.get("campaign_id"),
        )
        new_driver = get_driver(target_driver)
        new_request = _build_reroute_launch_request(
            root,
            metadata,
            driver_name=target_driver,
            model=str((request.target or {}).get("model") or "") or None,
        )
        new_handle = new_driver.launch(new_request)
        new_status = new_driver.status(new_handle)
        handles = _load_driver_handles(metadata)
        history = list(handles.get("history", []))
        history.append(
            {
                "driver": metadata.get("driver"),
                "driver_handle": metadata.get("driver_handle"),
                "status": metadata.get("status"),
                "rerouted_at": utc_now_iso(),
            }
        )
        history.append(new_handle.to_dict())
        handles["active"] = new_handle.to_dict()
        handles["history"] = history
        _save_driver_handles(metadata, handles)
        Path(metadata["driver_metadata_path"]).write_text(
            json.dumps(new_driver.probe().to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        metadata["driver"] = target_driver
        metadata["driver_handle"] = new_handle.driver_handle
        metadata["status"] = new_status.state
        metadata["health"] = new_status.health
        _record_driver_status(metadata, new_status.to_dict())
        ack = {
            "ok": True,
            "from": driver.name,
            "to": target_driver,
            "new_handle": new_handle.to_dict(),
        }
        timeline_entry["driver_ack"] = ack
        _append_transcript_entry(
            Path(metadata["transcript_path"]),
            {
                "ts": utc_now_iso(),
                "kind": "system",
                "driver": target_driver,
                "message": f"Run rerouted from {driver.name} to {target_driver}",
                "state": new_status.state,
            },
        )
    elif action == "approve":
        emit_event(
            root,
            actor={"kind": "human", "id": actor or "operator"},
            entity_type="run",
            entity_id=run_id,
            event_type="steering.approve",
            source="run.steer",
            payload={"request": request.to_dict()},
            run_id=run_id,
            task_id=metadata.get("task_id"),
            project_id=metadata.get("project_id"),
            campaign_id=metadata.get("campaign_id"),
        )
        accepted = accept_run(root, run_id)
        accepted.setdefault("metadata_json", {}).setdefault("steering_history", []).append(timeline_entry)
        _save_run(root, run_id, accepted)
        return {"run": accepted, "action": action, "request": request.to_dict()}
    elif action == "reject":
        emit_event(
            root,
            actor={"kind": "human", "id": actor or "operator"},
            entity_type="run",
            entity_id=run_id,
            event_type="steering.reject",
            source="run.steer",
            payload={"request": request.to_dict()},
            run_id=run_id,
            task_id=metadata.get("task_id"),
            project_id=metadata.get("project_id"),
            campaign_id=metadata.get("campaign_id"),
        )
        rejected = reject_run(root, run_id, reason=request.reason)
        rejected.setdefault("metadata_json", {}).setdefault("steering_history", []).append(timeline_entry)
        _save_run(root, run_id, rejected)
        return {"run": rejected, "action": action, "request": request.to_dict()}

    if ack is not None:
        timeline_entry["driver_ack"] = ack
    emit_event(
        root,
        actor={"kind": "human", "id": actor or "operator"},
        entity_type="run",
        entity_id=run_id,
        event_type=_steering_event_type(action),
        source="run.steer",
        payload={"request": request.to_dict(), "ack": ack},
        run_id=run_id,
        task_id=metadata.get("task_id"),
        project_id=metadata.get("project_id"),
        campaign_id=metadata.get("campaign_id"),
    )
    if action == "cancel":
        emit_event(
            root,
            actor={"kind": "human", "id": actor or "operator"},
            entity_type="run",
            entity_id=run_id,
            event_type="run.cancelled",
            source="run.steer",
            payload={"reason": request.reason},
            run_id=run_id,
            task_id=metadata.get("task_id"),
            project_id=metadata.get("project_id"),
            campaign_id=metadata.get("campaign_id"),
        )
    if action in {"pause", "resume", "reroute"}:
        emit_event(
            root,
            actor={"kind": "human", "id": actor or "operator"},
            entity_type="run",
            entity_id=run_id,
            event_type="run.status.changed",
            source="run.steer",
            payload={"state": metadata.get("status"), "health": metadata.get("health")},
            run_id=run_id,
            task_id=metadata.get("task_id"),
            project_id=metadata.get("project_id"),
            campaign_id=metadata.get("campaign_id"),
        )
    _save_run(root, run_id, metadata)
    return {
        "run": metadata,
        "action": action,
        "request": request.to_dict(),
        "driver_ack": ack,
    }


def cleanup_run(path: str | Path | None, run_id: str) -> dict[str, object]:
    """Remove a terminal run's linked worktree."""
    root = Path(path or Path.cwd()).resolve()
    metadata = load_run(root, run_id)
    if metadata.get("status") not in RUN_TERMINAL_STATUSES:
        raise ValueError(f"Cannot clean up run with status {metadata.get('status')!r}")
    worktree_path = metadata.get("worktree_path")
    if not worktree_path:
        return {"run_id": run_id, "cleaned": False, "already_missing": True, "path": None}
    result = remove_worktree(root, worktree_path)
    return {
        "run_id": run_id,
        "cleaned": bool(result["removed"]),
        "already_missing": bool(result["already_missing"]),
        "manual_cleanup": bool(result["manual_cleanup"]),
        "path": result["path"],
        "warnings": list(result["warnings"]),
    }


def cleanup_terminal_runs(path: str | Path | None) -> list[dict[str, object]]:
    """Remove linked worktrees for all terminal runs in the workspace."""
    root = Path(path or Path.cwd()).resolve()
    results: list[dict[str, object]] = []
    for metadata_path in sorted(runs_dir(root).glob("run_*/metadata.json")):
        run_id = metadata_path.parent.name
        metadata = load_run(root, run_id)
        if metadata.get("status") in RUN_TERMINAL_STATUSES:
            results.append(cleanup_run(root, run_id))
    return results

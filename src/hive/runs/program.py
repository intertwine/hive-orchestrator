"""Program contract helpers for runs."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from src.hive.drivers import RunBudget, RunLaunchRequest, RunWorkspace
from src.hive.runs.handoff import export_reroute_bundle
from src.hive.models.program import ProgramRecord
from src.hive.runs.worktree import current_branch, ensure_clean_repo
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


def _run_program_policy(program: ProgramRecord) -> dict[str, object]:
    commands = program.metadata.get("commands", {})
    paths = program.metadata.get("paths", {})
    return {
        "network": program.metadata.get("network", "ask"),
        "paths": list(paths.get("allow", [])),
        "blocked_paths": list(paths.get("deny", [])),
        "commands_allow": list(commands.get("allow", [])),
        "commands_deny": list(commands.get("deny", [])),
        "evaluator_policy": "unsafe" if program.unsafe_without_evaluators() else "required",
    }


def _build_reroute_launch_request(
    root: Path,
    metadata: dict,
    *,
    driver_name: str,
    model: str | None = None,
) -> RunLaunchRequest:
    program = _load_run_program(metadata)
    reroute_bundle = export_reroute_bundle(
        root,
        metadata,
        target_driver=driver_name,
        target_model=model or metadata.get("model"),
    )
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
                (metadata.get("metadata_json") or {}).get("base_branch") or current_branch(root)
            ),
        ),
        compiled_context_path=str(metadata.get("context_compiled_dir")),
        artifacts_path=str(root / ".hive" / "runs" / str(metadata["id"])),
        program_policy=_run_program_policy(program),
        steering_notes=[
            str(item.get("note", ""))
            for item in (metadata.get("metadata_json") or {}).get("steering_history", [])
            if isinstance(item, dict) and str(item.get("note", "")).strip()
        ],
        metadata={
            "initiator": "human",
            "source": "hive steer reroute",
            "task_title": (
                (metadata.get("metadata_json") or {}).get("task_title") or metadata["task_id"]
            ),
            "reroute_bundle_path": reroute_bundle["bundle_path"],
            "reroute_summary_path": reroute_bundle["summary_path"],
            "reroute_bundle": json.loads(json.dumps(reroute_bundle["bundle"])),
        },
    )


__all__ = [
    "load_program",
    "_build_reroute_launch_request",
    "_load_run_program",
    "_preflight_program_for_run",
    "_program_sha",
    "_run_program_policy",
]

"""Run state and promotion helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from fnmatch import fnmatch
import json
from pathlib import Path

from src.hive.models.program import ProgramRecord
from src.hive.runs.worktree import (
    capture_worktree_state,
    current_branch,
    current_head,
    split_dirty_paths,
)


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


def _task_title(metadata: dict) -> str:
    return metadata.setdefault("metadata_json", {}).get("task_title") or metadata["task_id"]


def _matches_path(path: str, pattern: str) -> bool:
    return fnmatch(path, pattern)


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


def _promotion_artifact_reasons(metadata: dict) -> list[str]:
    reasons: list[str] = []
    if not _artifact_exists(metadata.get("summary_path")):
        reasons.append("summary.md is missing or empty")
    if not _artifact_exists(metadata.get("review_path")):
        reasons.append("review.md is missing or empty")
    return reasons


def _promotion_requirement_reasons(
    program: ProgramRecord,
    evaluations: list[dict],
    evaluation_by_id: dict[str, dict],
    metadata_json: dict,
) -> list[str]:
    reasons: list[str] = []
    if not evaluations and not program.unsafe_without_evaluators():
        reasons.append(
            "No evaluator results recorded. Add required evaluators to PROGRAM.md or opt into "
            "promotion.allow_unsafe_without_evaluators explicitly."
        )

    for result in evaluations:
        if result.get("required", True) and result["status"] != "pass":
            reasons.append(f"Required evaluator failed: {result['evaluator_id']}")

    for evaluator_id in program.metadata.get("promotion", {}).get("requires_all", []):
        result = evaluation_by_id.get(evaluator_id)
        if result is None:
            reasons.append(f"Required promotion evaluator missing: {evaluator_id}")
        elif result["status"] != "pass":
            reasons.append(f"Required promotion evaluator did not pass: {evaluator_id}")

    if (
        not bool(metadata_json.get("has_changes", False))
        and not program.allow_accept_without_changes()
    ):
        reasons.append(
            "Run did not produce workspace changes. Add a real change or set "
            "promotion.allow_accept_without_changes: true for deliberate no-op flows."
        )
    return reasons


def _promotion_path_reasons(
    program: ProgramRecord,
    touched_paths: list[str],
) -> tuple[list[str], list[str]]:
    reject_reasons: list[str] = []
    escalate_reasons: list[str] = []

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
    return reject_reasons, escalate_reasons


def _promotion_budget_reasons(
    program: ProgramRecord,
    metadata: dict,
    metadata_json: dict,
) -> list[str]:
    reasons: list[str] = []
    budgets = program.metadata.get("budgets", {})
    started_at = _parse_iso(metadata.get("started_at"))
    if started_at is not None:
        duration_seconds = (datetime.now(timezone.utc) - started_at).total_seconds()
        max_seconds = float(budgets.get("max_wall_clock_minutes", 0)) * 60
        if max_seconds and duration_seconds > max_seconds:
            reasons.append(
                f"Run exceeded wall clock budget ({duration_seconds:.1f}s > {max_seconds:.1f}s)"
            )
    max_steps = int(budgets.get("max_steps", 0))
    if max_steps and int(metadata_json.get("command_count", 0)) > max_steps:
        reasons.append(
            f"Run exceeded step budget ({metadata_json.get('command_count', 0)} > {max_steps})"
        )
    total_tokens = int(metadata.get("tokens_in") or 0) + int(metadata.get("tokens_out") or 0)
    max_tokens = int(budgets.get("max_tokens", 0))
    if max_tokens and total_tokens > max_tokens:
        reasons.append(f"Run exceeded token budget ({total_tokens} > {max_tokens})")
    max_cost = float(budgets.get("max_cost_usd", 0))
    cost_usd = float(metadata.get("cost_usd") or 0.0)
    if max_cost and cost_usd > max_cost:
        reasons.append(f"Run exceeded cost budget ({cost_usd:.2f} > {max_cost:.2f})")
    return reasons


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
        legacy_patch = patch_file
        if patch_file.parent.name == "workspace":
            legacy_patch = patch_file.parent.parent / "patch.diff"
        if legacy_patch != patch_file:
            legacy_patch.write_text(patch_file.read_text(encoding="utf-8"), encoding="utf-8")
    return metadata_json


def _promotion_decision(program: ProgramRecord, metadata: dict) -> dict[str, object]:
    metadata_json = metadata.setdefault("metadata_json", {})
    evaluations = metadata_json.get("evaluations", [])
    evaluation_by_id = {entry["evaluator_id"]: entry for entry in evaluations}
    touched_paths = list(metadata_json.get("touched_paths", []))
    commands = list(metadata_json.get("commands", []))
    reject_reasons = _promotion_artifact_reasons(metadata)
    reject_reasons.extend(
        _promotion_requirement_reasons(program, evaluations, evaluation_by_id, metadata_json)
    )
    path_reject_reasons, escalate_reasons = _promotion_path_reasons(program, touched_paths)
    reject_reasons.extend(path_reject_reasons)
    for command in commands:
        if command in program.metadata.get("escalation", {}).get("when_commands_match", []):
            escalate_reasons.append(f"Escalation rule matched command: {command}")
    reject_reasons.extend(_promotion_budget_reasons(program, metadata, metadata_json))
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


__all__ = [
    "_artifact_exists",
    "_filtered_dirty_paths",
    "_parse_iso",
    "_promotion_decision",
    "_read_command_log",
    "_refresh_workspace_state",
    "_task_title",
    "_write_review_and_summary",
]

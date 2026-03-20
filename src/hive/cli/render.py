"""Human-friendly text rendering for Hive CLI payloads."""

# pylint: disable=too-many-branches

from __future__ import annotations

import json
from pprint import pformat


def _render_checks(checks: dict[str, object]) -> str:
    lines = ["Checks:"]
    for name, value in checks.items():
        marker = "OK" if value else "MISSING"
        lines.append(f"- {name}: {marker}")
    return "\n".join(lines)


def _render_next_steps(next_steps: list[str]) -> str:
    if not next_steps:
        return ""
    lines = ["Next steps:"]
    lines.extend(f"- {step}" for step in next_steps)
    return "\n".join(lines)


def _render_project(project: dict[str, object]) -> str:
    lines = [
        f"Project: {project.get('id')} - {project.get('title')}",
        f"Status: {project.get('status')} | Priority: {project.get('priority')}",
    ]
    path = project.get("path")
    if path:
        lines.append(f"Path: {path}")
    program_path = project.get("program_path")
    if program_path:
        lines.append(f"PROGRAM.md: {program_path}")
    return "\n".join(lines)


def _render_projects(projects: list[dict[str, object]]) -> str:
    if not projects:
        return "No projects found."
    lines = ["Projects:"]
    for project in projects:
        status = project.get("status", "unknown")
        ready = project.get("ready_tasks")
        summary = f"- {project.get('project_id') or project.get('id')} [{status}]"
        if ready is not None:
            summary += f" ready={ready}"
        title = project.get("title")
        if title:
            summary += f" {title}"
        lines.append(summary)
    return "\n".join(lines)


def _render_task(task: dict[str, object]) -> str:
    lines = [
        f"Task: {task.get('id')} - {task.get('title')}",
        f"Status: {task.get('status')} | Priority: {task.get('priority')}",
    ]
    project_id = task.get("project_id")
    if project_id:
        lines.append(f"Project: {project_id}")
    owner = task.get("owner")
    if owner:
        lines.append(f"Owner: {owner}")
    path = task.get("path")
    if path:
        lines.append(f"Path: {path}")
    return "\n".join(lines)


def _render_tasks(tasks: list[dict[str, object]]) -> str:
    if not tasks:
        return "No tasks found."
    lines = ["Tasks:"]
    for task in tasks:
        project_id = task.get("project_id", "-")
        lines.append(
            f"- {task.get('id')} [{task.get('status')}] "
            f"p{task.get('priority')} {project_id}: {task.get('title')}"
        )
    return "\n".join(lines)


def _render_results(results: list[dict[str, object]]) -> str:
    if not results:
        return "No results found."
    lines = ["Results:"]
    for result in results:
        title = result.get("title", "untitled")
        kind = result.get("kind", "result")
        line = f"- [{kind}] {title}"
        path = result.get("path")
        if path:
            line += f" ({path})"
        lines.append(line)
        snippet = result.get("summary") or result.get("snippet")
        if snippet:
            lines.append(f"  {str(snippet).strip()}")
        why = result.get("why") or result.get("matches")
        if isinstance(why, list) and why:
            lines.append(f"  why: {', '.join(str(item) for item in why)}")
    return "\n".join(lines)


def _render_dependency_summary(summary: dict[str, object]) -> str:
    projects = summary.get("projects", [])
    if not projects:
        return "No project dependencies found."
    lines = ["Dependency summary:"]
    for project in projects:
        blocked_by = project.get("blocked_by") or []
        deps = ", ".join(blocked_by) if blocked_by else "-"
        state = "blocked" if project.get("effectively_blocked") else "ready"
        lines.append(
            f"- {project.get('project_id')} [{project.get('status')}] {state} (depends on: {deps})"
        )
    return "\n".join(lines)


def _render_run(run: dict[str, object]) -> str:
    lines = [
        f"Run: {run.get('id')}",
        f"Task: {run.get('task_id')} | Status: {run.get('status')}",
    ]
    executor = run.get("executor")
    if executor:
        lines.append(f"Executor: {executor}")
    run_dir = run.get("run_dir") or run.get("path")
    if run_dir:
        lines.append(f"Path: {run_dir}")
    worktree_path = run.get("worktree_path")
    if worktree_path:
        lines.append(f"Worktree: {worktree_path}")
    return "\n".join(lines)


def _render_runs(label: str, runs: list[dict[str, object]]) -> str:
    if not runs:
        return ""
    lines = [label + ":"]
    for run in runs:
        lines.append(
            f"- {run.get('id')} [{run.get('status')}] "
            f"{run.get('project_id')}/{run.get('task_id')}"
        )
    return "\n".join(lines)


def _render_recommendation(recommendation: dict[str, object]) -> str:
    task = recommendation.get("task", {})
    lines = [
        "Recommendation:",
        f"- {task.get('id')} [{task.get('status')}] "
        f"p{task.get('priority')} {task.get('project_id')}: {task.get('title')}",
    ]
    reasons = recommendation.get("reasons") or []
    for reason in reasons:
        lines.append(f"  reason: {reason}")
    return "\n".join(lines)


def _render_steering(steering: dict[str, object]) -> str:
    lines = ["Steering:"]
    for key in ("paused", "focus_task_id", "boost", "force_review", "note", "updated_by"):
        value = steering.get(key)
        if value in (None, "", False, 0):
            continue
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _render_events(events: list[dict[str, object]]) -> str:
    if not events:
        return ""
    lines = ["Recent events:"]
    for event in events:
        lines.append(
            f"- {event.get('occurred_at')} {event.get('event_type')} "
            f"{event.get('entity_type')}:{event.get('entity_id')}"
        )
    return "\n".join(lines)


def _render_promotion_decision(decision: dict[str, object]) -> str:
    lines = [f"Promotion decision: {decision.get('decision')}"]
    reasons = decision.get("reasons") or []
    if reasons:
        lines.append("Reasons:")
        lines.extend(f"- {reason}" for reason in reasons)
    return "\n".join(lines)


def _render_summary_lines(headline: object, summary_lines: list[object]) -> str:
    lines: list[str] = []
    if headline:
        lines.append(str(headline))
    lines.extend(f"- {str(line)}" for line in summary_lines)
    return "\n".join(lines)


def render_payload(payload: dict[str, object]) -> str:
    """Render a CLI payload for humans."""
    if not payload.get("ok", True) and payload.get("error"):
        return f"Error: {payload['error']}"
    if payload.get("rendered_context"):
        return str(payload["rendered_context"]).rstrip()

    sections: list[str] = []
    message = payload.get("message")
    if message:
        sections.append(str(message))

    if isinstance(payload.get("checks"), dict):
        sections.append(_render_checks(payload["checks"]))
    if isinstance(payload.get("project"), dict):
        sections.append(_render_project(payload["project"]))
    if isinstance(payload.get("projects"), list):
        sections.append(_render_projects(payload["projects"]))
    if isinstance(payload.get("task"), dict):
        sections.append(_render_task(payload["task"]))
    if isinstance(payload.get("tasks"), list):
        sections.append(_render_tasks(payload["tasks"]))
    if isinstance(payload.get("results"), list):
        sections.append(_render_results(payload["results"]))
    if isinstance(payload.get("summary"), dict):
        sections.append(_render_dependency_summary(payload["summary"]))
    if isinstance(payload.get("run"), dict):
        sections.append(_render_run(payload["run"]))
    if isinstance(payload.get("active_runs"), list):
        sections.append(_render_runs("Active runs", payload["active_runs"]))
    if isinstance(payload.get("evaluating_runs"), list):
        sections.append(_render_runs("Evaluating runs", payload["evaluating_runs"]))
    if isinstance(payload.get("recommendation"), dict):
        sections.append(_render_recommendation(payload["recommendation"]))
    if isinstance(payload.get("steering"), dict):
        sections.append(_render_steering(payload["steering"]))
    if isinstance(payload.get("recent_events"), list):
        sections.append(_render_events(payload["recent_events"]))
    if isinstance(payload.get("promotion_decision"), dict):
        sections.append(_render_promotion_decision(payload["promotion_decision"]))
    if isinstance(payload.get("summary_lines"), list) and payload["summary_lines"]:
        sections.append(_render_summary_lines(payload.get("headline"), payload["summary_lines"]))
    if isinstance(payload.get("next_steps"), list):
        sections.append(_render_next_steps(payload["next_steps"]))

    if not sections:
        try:
            return json.dumps(payload, indent=2, sort_keys=True)
        except TypeError:
            return pformat(payload, sort_dicts=True)
    return "\n\n".join(section for section in sections if section).strip()

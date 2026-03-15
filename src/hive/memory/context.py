"""Startup and handoff context assembly."""

from __future__ import annotations

from pathlib import Path

from src.hive.memory.search import iter_accepted_runs, search
from src.hive.store.layout import global_memory_dir, memory_project_dir
from src.hive.store.projects import get_project
from src.hive.store.task_files import get_task


def _load_if_exists(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def _recent_accepted_runs(root: Path, *, project_id: str, limit: int) -> list[dict[str, str]]:
    runs: list[dict[str, str]] = []
    for metadata, _, summary_path in sorted(
        iter_accepted_runs(root, project_id=project_id),
        key=lambda item: item[0].get("finished_at") or str(item[1]),
        reverse=True,
    ):
        runs.append(
            {
                "id": metadata.get("id", ""),
                "summary_path": str(summary_path),
                "content": summary_path.read_text(encoding="utf-8").strip(),
            }
        )
        if len(runs) >= limit:
            break
    return runs


def startup_context(
    path: str | Path | None,
    *,
    project_id: str,
    profile: str = "default",
    query: str | None = None,
    task_id: str | None = None,
) -> dict[str, object]:
    """Assemble startup context in the v2 order."""
    root = Path(path or Path.cwd()).resolve()
    project = get_project(root, project_id)
    memory_root = memory_project_dir(root)
    agents_text = _load_if_exists(root / "AGENTS.md")
    profile_text = _load_if_exists(memory_root / "profile.md")
    active_text = _load_if_exists(memory_root / "active.md")
    global_profile_text = _load_if_exists(global_memory_dir() / "profile.md")
    global_active_text = _load_if_exists(global_memory_dir() / "active.md")
    program_text = _load_if_exists(project.program_path)
    task_query = get_task(root, task_id).title if task_id else None
    query_text = query or task_query
    search_limits = {"light": 2, "default": 4, "deep": 6}
    run_limits = {"light": 1, "default": 2, "deep": 4}
    search_hits = (
        search(
            root,
            query_text,
            scope="all",
            project_id=project_id,
            task_id=task_id,
            limit=search_limits.get(profile, 4),
        )
        if query_text
        else []
    )
    recent_runs = _recent_accepted_runs(
        root,
        project_id=project_id,
        limit=run_limits.get(profile, 2),
    )
    sections = [
        {"name": "agents", "content": agents_text},
        {"name": "agency", "content": project.content},
        {"name": "program", "content": program_text},
        {"name": "project-profile", "content": profile_text},
        {"name": "project-active", "content": active_text},
    ]
    if search_hits:
        sections.append(
            {
                "name": "search",
                "content": "\n".join(
                    f"- [{hit['kind']}/{hit['scope']}] {hit['title']}: {hit['snippet']}"
                    for hit in search_hits
                ),
            }
        )
    if recent_runs:
        sections.append(
            {
                "name": "recent-runs",
                "content": "\n\n".join(
                    f"## {run['id']}\n\n{run['content']}" for run in recent_runs
                ),
            }
        )
    if global_profile_text:
        sections.append({"name": "global-profile", "content": global_profile_text})
    if global_active_text:
        sections.append({"name": "global-active", "content": global_active_text})
    combined = "\n\n".join(section["content"] for section in sections if section["content"])
    token_targets = {"light": 2000, "default": 4000, "deep": 8000}
    return {
        "project_id": project.id,
        "profile": profile,
        "task_id": task_id,
        "query": query_text,
        "target_tokens": token_targets.get(profile, 4000),
        "sections": sections,
        "search_hits": search_hits,
        "recent_runs": recent_runs,
        "content": combined,
    }


def handoff_context(path: str | Path | None, *, project_id: str) -> dict[str, object]:
    """Build a compact handoff bundle."""
    context = startup_context(path, project_id=project_id, profile="light")
    context["handoff"] = True
    return context

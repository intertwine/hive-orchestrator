"""Startup and handoff context assembly."""

from __future__ import annotations

from pathlib import Path

from src.hive.memory.search import search
from src.hive.store.projects import get_project


def _load_if_exists(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def startup_context(
    path: str | Path | None,
    *,
    project_id: str,
    profile: str = "default",
    query: str | None = None,
) -> dict[str, object]:
    """Assemble startup context in the v2 order."""
    root = Path(path or Path.cwd())
    project = get_project(root, project_id)
    memory_root = root / ".hive" / "memory" / "project"
    agents_text = _load_if_exists(root / "AGENTS.md")
    profile_text = _load_if_exists(memory_root / "profile.md")
    active_text = _load_if_exists(memory_root / "active.md")
    program_text = _load_if_exists(project.program_path)
    search_hits = search(root, query) if query else []
    sections = [
        {"name": "agents", "content": agents_text},
        {"name": "agency", "content": project.content},
        {"name": "program", "content": program_text},
        {"name": "profile", "content": profile_text},
        {"name": "active", "content": active_text},
    ]
    if search_hits:
        sections.append({"name": "search", "content": "\n".join(hit["snippet"] for hit in search_hits)})
    combined = "\n\n".join(section["content"] for section in sections if section["content"])
    token_targets = {"light": 2000, "default": 4000, "deep": 8000}
    return {
        "project_id": project.id,
        "profile": profile,
        "target_tokens": token_targets.get(profile, 4000),
        "sections": sections,
        "search_hits": search_hits,
        "content": combined,
    }


def handoff_context(path: str | Path | None, *, project_id: str) -> dict[str, object]:
    """Build a compact handoff bundle."""
    context = startup_context(path, project_id=project_id, profile="light")
    context["handoff"] = True
    return context

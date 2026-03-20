"""Helpers for rendering shareable Hive context bundles."""

from __future__ import annotations

from pathlib import Path

from src.hive.common import isoformat_z
from src.hive.memory.context import handoff_context, startup_context
from src.hive.payloads import project_payload
from src.hive.scheduler.query import ready_tasks
from src.hive.store.projects import get_project
from src.hive.store.task_files import get_task
from src.hive.workspace import sync_workspace
from src.security import safe_dump_agency_md


def generate_file_tree(
    directory: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0
) -> str:
    """Generate a text file tree for a project directory."""
    if current_depth >= max_depth:
        return ""

    tree = ""
    try:
        items = sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name))
        items = [
            item
            for item in items
            if not item.name.startswith(".") and item.name != "__pycache__"
        ]

        for index, item in enumerate(items):
            is_last = index == len(items) - 1
            current_prefix = "└── " if is_last else "├── "
            tree += f"{prefix}{current_prefix}{item.name}\n"

            if item.is_dir() and current_depth < max_depth - 1:
                extension = "    " if is_last else "│   "
                tree += generate_file_tree(item, prefix + extension, max_depth, current_depth + 1)
    except PermissionError:
        pass

    return tree


def _render_ready_task_lines(tasks: list[dict[str, object]], *, current_task_id: str | None = None) -> str:
    if not tasks:
        if current_task_id:
            return "*No canonical ready tasks found right now. See CURRENT TASK below.*"
        return "*No canonical ready tasks found for this project.*"
    return "\n".join(
        f"- `{task['id']}` | p{task['priority']} | {task['title']}" for task in tasks
    )


def _render_current_task(task: dict[str, object] | None) -> str:
    if not task:
        return ""
    owner = str(task.get("owner") or "unassigned")
    return (
        f"- `{task['id']}` | {task['status']} | p{task['priority']} | {task['title']}\n"
        f"- owner: {owner}"
    )


def _render_context_sections(context: dict[str, object]) -> str:
    sections: list[str] = []
    for section in context.get("sections", []):
        content = str(section.get("content", "")).strip()
        if not content:
            continue
        sections.append(
            f"""## {str(section.get("name", "context")).upper()}

```markdown
{content}
```"""
        )

    search_hits = context.get("search_hits", [])
    if search_hits:
        sections.append(
            "## SEARCH HITS\n\n"
            + "\n".join(
                f"- `{hit.get('kind', 'result')}` {hit.get('title', 'untitled')}"
                for hit in search_hits
            )
        )

    return "\n\n---\n\n".join(sections) if sections else "*No v2 context sections available.*"

# pylint: disable-next=too-many-arguments
def build_context_bundle(
    path: str | Path | None,
    *,
    project_ref: str,
    mode: str = "startup",
    profile: str = "light",
    query: str | None = None,
    task_id: str | None = None,
    refresh: bool = True,
) -> dict[str, object]:
    """Build a rendered startup or handoff bundle for a project."""
    root = Path(path or Path.cwd()).resolve()
    if refresh:
        sync_workspace(root)
    project = get_project(root, project_ref)
    ready = ready_tasks(root, project_id=project.id, limit=5)
    current_task = None
    if task_id:
        task = get_task(root, task_id)
        current_task = task.to_frontmatter() | {"path": str(task.path) if task.path else None}
    context = (
        handoff_context(root, project_id=project.id)
        if mode == "handoff"
        else startup_context(
            root,
            project_id=project.id,
            profile=profile,
            query=query,
            task_id=task_id,
        )
    )
    mode_label = "HANDOFF" if context.get("handoff") else "STARTUP"
    project_dir = project.agency_path.parent
    agency_document = safe_dump_agency_md(project.metadata, project.content)
    current_task_section = ""
    rendered_current_task = _render_current_task(current_task)
    if rendered_current_task:
        current_task_section = f"""

---

## CURRENT TASK

{rendered_current_task}"""
    rendered = f"""# HIVE {mode_label} CONTEXT
# Project: {project.id}
# Profile: {context.get('profile', profile)}
# Target Tokens: {context.get('target_tokens', 'n/a')}
# Generated: {isoformat_z()}

---

## YOUR ROLE

You are entering a Hive v2 {mode_label.lower()} session for **{project.id}**.
Use canonical tasks, `PROGRAM.md`, and the assembled context below as the source of truth.

---

## READY TASKS

{_render_ready_task_lines(ready, current_task_id=task_id)}
{current_task_section}

---

## AGENCY.md

```yaml
{agency_document}
```

---

## HIVE CONTEXT

{_render_context_sections(context)}

---

## PROJECT FILE STRUCTURE

{generate_file_tree(project_dir)}

---

## HANDOFF PROTOCOL

Before ending your session:
1. Update the relevant canonical task in `.hive/tasks/`
2. Sync projections if task state or notes changed: `hive sync projections`
3. Release or transition the task appropriately in Hive
4. Create a PR or leave a clear handoff note
""".strip()
    return {
        "project": project,
        "project_payload": project_payload(project),
        "ready_tasks": ready,
        "current_task": current_task,
        "context": context,
        "agency_document": agency_document,
        "project_dir": project_dir,
        "rendered": rendered,
    }

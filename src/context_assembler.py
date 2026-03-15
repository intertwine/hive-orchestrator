#!/usr/bin/env python3
"""
Agent Hive Context Assembler

Builds rich context for manual GitHub issue dispatch using the Hive v2
canonical substrate. Legacy project-shaped inputs are still accepted as a
compatibility path, but canonical task data is preferred whenever available.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from src.hive.memory.context import startup_context
from src.hive.models.task import TaskRecord
from src.hive.scheduler.query import ready_tasks as scheduler_ready_tasks
from src.hive.store.projects import get_project
from src.hive.store.task_files import get_task
from src.security import safe_dump_agency_md


def generate_file_tree(
    directory: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0
) -> str:
    """
    Generate a text-based file tree.

    Args:
        directory: Directory to generate tree for
        prefix: Prefix for tree lines (used for indentation)
        max_depth: Maximum depth to traverse
        current_depth: Current depth in traversal

    Returns:
        String representation of file tree
    """
    if current_depth >= max_depth:
        return ""

    tree = ""
    try:
        items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        items = [i for i in items if not i.name.startswith(".") and i.name != "__pycache__"]

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


def clone_external_repo(url: str, branch: str = "main") -> Optional[Path]:
    """
    Clone an external repository to a temporary directory.

    Args:
        url: Git repository URL (must be https://)
        branch: Branch to clone (default: main)

    Returns:
        Path to cloned repo, or None on failure
    """
    if not url.startswith("https://"):
        return None

    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix="hive_external_")
        result = subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                branch,
                url,
                temp_dir,
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

        if result.returncode != 0:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        return Path(temp_dir)

    except (subprocess.TimeoutExpired, OSError):
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return None


def get_external_repo_context(
    repo_path: Path,
    key_files: Optional[list[str]] = None,
) -> tuple[str, str]:
    """
    Generate context from an external repository.

    Args:
        repo_path: Path to the cloned repository
        key_files: Optional list of specific files to read

    Returns:
        Tuple of (file_tree, key_files_content)
    """

    def filtered_tree(directory: Path, prefix: str = "", depth: int = 0, max_depth: int = 4) -> str:
        if depth >= max_depth:
            return ""
        result = ""
        try:
            items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            noise = {"node_modules", "__pycache__", "dist", "build", ".git", ".venv", "venv"}
            items = [i for i in items if not i.name.startswith(".") and i.name not in noise]

            for index, item in enumerate(items):
                is_last = index == len(items) - 1
                current_prefix = "└── " if is_last else "├── "
                result += f"{prefix}{current_prefix}{item.name}\n"
                if item.is_dir():
                    extension = "    " if is_last else "│   "
                    result += filtered_tree(
                        item,
                        prefix + extension,
                        depth + 1,
                        max_depth,
                    )
        except PermissionError:
            pass
        return result

    file_tree = filtered_tree(repo_path)

    default_files = [
        "package.json",
        "pyproject.toml",
        "README.md",
        "src/index.ts",
        "src/main.ts",
        "src/index.js",
        "src/main.py",
    ]

    files_to_read = key_files if key_files else default_files
    content_parts = []

    for file_pattern in files_to_read:
        file_path = repo_path / file_pattern
        if file_path.exists() and file_path.is_file():
            try:
                file_content = file_path.read_text(encoding="utf-8")
                if len(file_content) > 15000:
                    file_content = file_content[:15000] + "\n\n... (truncated)"
                file_content_escaped = file_content.replace("```", "`\u200b`\u200b`")
                content_parts.append(f"### `{file_pattern}`\n\n```\n{file_content_escaped}\n```")
            except (UnicodeDecodeError, PermissionError):
                pass

    key_files_content = "\n\n".join(content_parts) if content_parts else ""
    return file_tree, key_files_content


def cleanup_external_repo(repo_path: Path) -> None:
    """Clean up a cloned external repository."""
    if repo_path and repo_path.exists():
        shutil.rmtree(repo_path, ignore_errors=True)


def get_relevant_files_content(
    project_dir: Path, relevant_files: list[str], base_path: Path
) -> str:
    """
    Read and format content from relevant files.

    Args:
        project_dir: Project directory path
        relevant_files: List of file paths (relative to base_path or project_dir)
        base_path: Base path of the hive

    Returns:
        Formatted string with file contents
    """
    content_parts = []

    for file_path in relevant_files:
        full_path = None

        candidate = project_dir / file_path
        if candidate.exists():
            full_path = candidate
        else:
            candidate = base_path / file_path
            if candidate.exists():
                full_path = candidate

        if full_path and full_path.is_file():
            try:
                file_content = full_path.read_text(encoding="utf-8")
                if len(file_content) > 10000:
                    file_content = file_content[:10000] + "\n\n... (truncated)"

                relative_path = full_path.relative_to(base_path)
                content_parts.append(f"### `{relative_path}`\n\n```\n{file_content}\n```")
            except (UnicodeDecodeError, PermissionError, OSError) as exc:
                error_type = type(exc).__name__
                content_parts.append(f"### `{file_path}`\n\n*Error reading file: {error_type}*")
        else:
            content_parts.append(f"### `{file_path}`\n\n*File not found*")

    return "\n\n".join(content_parts) if content_parts else "*No relevant files specified*"


def get_next_task(content: str) -> Optional[str]:
    """
    Extract the next uncompleted checkbox task from markdown content.

    This is only used when importing or rendering legacy project-shaped inputs.
    """
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- [ ]"):
            return stripped[5:].strip()
    return None


def build_issue_title(project_id: str, next_task: Optional[str]) -> str:
    """
    Build a descriptive issue title.

    Args:
        project_id: Project identifier
        next_task: The next task to work on (if identified)

    Returns:
        Issue title string
    """
    if next_task:
        task_preview = next_task[:60] + "..." if len(next_task) > 60 else next_task
        return f"[Agent Hive] {project_id}: {task_preview}"
    return f"[Agent Hive] Work on {project_id}"


def _priority_name(priority: object) -> str:
    if isinstance(priority, str):
        return priority.lower()
    mapping = {0: "critical", 1: "high", 2: "medium", 3: "low"}
    return mapping.get(int(priority), "medium") if isinstance(priority, int) else "medium"


def _render_task_sections(task: TaskRecord) -> str:
    parts = [
        "## Summary",
        task.summary_md.strip() or f"Track work for `{task.title}`.",
        "",
        "## Notes",
        task.notes_md.strip() or "- Imported or created by Hive 2.0.",
        "",
        "## History",
        task.history_md.strip() or f"- {task.created_at} bootstrap created.",
    ]
    for name, content in task.extra_sections:
        parts.extend(["", f"## {name}", content.strip()])
    return "\n".join(parts).strip()


def _render_task_markdown(task: TaskRecord) -> str:
    return safe_dump_agency_md(task.to_frontmatter(), _render_task_sections(task))


def _render_context_sections(context: dict[str, object]) -> str:
    rendered = []
    for section in context.get("sections", []):
        content = str(section.get("content", "")).strip()
        if not content:
            continue
        rendered.append(
            f"""### {str(section.get("name", "context")).upper()}

```markdown
{content}
```"""
        )
    search_hits = context.get("search_hits", [])
    if search_hits:
        rendered.append(
            "### SEARCH HITS\n\n"
            + "\n".join(
                f"- `{hit.get('kind', 'result')}` {hit.get('title', 'untitled')}"
                for hit in search_hits
            )
        )
    return "\n\n".join(rendered) if rendered else "*No Hive v2 context was assembled.*"


def _relative_display(path: Path, base_path: Path) -> str:
    try:
        return str(path.relative_to(base_path))
    except ValueError:
        return str(path)


def _resolve_dispatch_item(
    item: dict[str, Any],
    base_path: Path,
    next_task: Optional[str],
) -> dict[str, Any]:
    metadata = dict(item.get("metadata", {}))
    project_id = item.get("project_id") or metadata.get("project_id", "unknown")
    task_id = item.get("task_id") or item.get("id")

    task = None
    if task_id:
        try:
            task = get_task(base_path, task_id)
        except FileNotFoundError:
            task = None
    elif project_id:
        ready = scheduler_ready_tasks(base_path, project_id=project_id, limit=1)
        if ready:
            task_id = str(ready[0]["id"])
            try:
                task = get_task(base_path, task_id)
            except FileNotFoundError:
                task = None

    if task:
        project = get_project(base_path, task.project_id)
        project_id = project.id
        task_title = next_task or task.title
        task_markdown = _render_task_markdown(task)
        raw_agency = safe_dump_agency_md(project.metadata, project.content)
        try:
            context = startup_context(
                base_path, project_id=project.id, profile="light", query=task.title
            )
        except FileNotFoundError:
            context = {"sections": [], "search_hits": []}
        return {
            "project_id": project.id,
            "project_title": project.title,
            "project_dir": project.directory,
            "project_path": project.agency_path,
            "agency_markdown": raw_agency,
            "task_id": task.id,
            "task_title": task_title,
            "task_markdown": task_markdown,
            "priority": task.priority,
            "labels": list(dict.fromkeys(task.labels + list(project.metadata.get("tags", [])))),
            "relevant_files": task.relevant_files
            or list(project.metadata.get("relevant_files", [])),
            "target_repo": dict(project.metadata.get("target_repo", {})),
            "context": context,
            "acceptance": list(task.acceptance),
        }

    project_path = Path(item["path"])
    project_dir = project_path.parent
    task_title = next_task or get_next_task(item.get("content", "")) or project_id
    return {
        "project_id": project_id,
        "project_title": project_id,
        "project_dir": project_dir,
        "project_path": project_path,
        "agency_markdown": safe_dump_agency_md(metadata, item.get("content", "")),
        "task_id": None,
        "task_title": task_title,
        "task_markdown": "",
        "priority": metadata.get("priority", "medium"),
        "labels": list(metadata.get("tags", [])),
        "relevant_files": list(metadata.get("relevant_files", [])),
        "target_repo": dict(metadata.get("target_repo", {})),
        "context": {"sections": [], "search_hits": []},
        "acceptance": [],
    }


def build_issue_body(
    project: dict[str, Any],
    base_path: Path,
    next_task: Optional[str] = None,
) -> str:
    """
    Build a comprehensive GitHub issue body for agent assignment.

    Prefers canonical task data and v2 startup context, while still accepting
    legacy project-shaped inputs as a compatibility path.
    """
    resolved = _resolve_dispatch_item(project, base_path, next_task)
    project_dir = resolved["project_dir"]
    relevant_files = resolved["relevant_files"]
    target_repo = resolved["target_repo"]
    context = resolved["context"]

    relevant_content = ""
    if relevant_files:
        relevant_content = (
            "\n### Relevant Files\n\n"
            + get_relevant_files_content(project_dir, relevant_files, base_path)
            + "\n"
        )

    external_repo_section = ""
    cloned_repo_path = None
    if target_repo.get("url"):
        repo_url = target_repo["url"]
        repo_branch = target_repo.get("branch", "main")
        cloned_repo_path = clone_external_repo(repo_url, repo_branch)
        if cloned_repo_path:
            try:
                ext_tree, ext_files = get_external_repo_context(cloned_repo_path)
                parsed_url = urlparse(repo_url)
                repo_name = parsed_url.path.rstrip("/").split("/")[-1].replace(".git", "")
                external_repo_section = f"""
### Target Repository

**URL**: {repo_url}
**Branch**: {repo_branch}

<details>
<summary>Click to expand repository structure</summary>

```
{repo_name}/
{ext_tree}```

</details>

{f'''<details>
<summary>Click to expand key files</summary>

{ext_files}

</details>''' if ext_files else ''}
"""
            finally:
                cleanup_external_repo(cloned_repo_path)

    task_section = f"""
## Immediate Task

Focus on this canonical Hive task first:
> {resolved["task_title"]}
"""

    task_details = ""
    if resolved["task_markdown"]:
        task_details = f"""
## Canonical Task

<details>
<summary>Click to expand canonical task file</summary>

```yaml
{resolved["task_markdown"]}
```

</details>
"""

    acceptance_section = ""
    if resolved["acceptance"]:
        acceptance_section = (
            "\n## Acceptance Criteria\n\n"
            + "\n".join(f"- [ ] {item}" for item in resolved["acceptance"])
            + "\n"
        )

    instructions = """
## Instructions

1. Treat the canonical Hive task as the source of truth for task state and notes
2. Implement the requested change and satisfy any acceptance criteria
3. Run the relevant tests and/or PROGRAM.md evaluators for the touched work
4. Sync projections after changing task state or notes: `uv run hive sync projections --json`
5. Create a PR and include any follow-up items in the task history or notes

## Success Criteria

- [ ] Canonical task updated in `.hive/tasks/`
- [ ] Relevant tests/evaluators run
- [ ] Projections synced
- [ ] PR opened or clear handoff left
"""

    if target_repo.get("url"):
        instructions = """
## Instructions

1. Treat the canonical Hive task as the source of truth for task state and notes
2. Implement the requested change in the target repository
3. Run the relevant tests and/or PROGRAM.md evaluators for the touched work
4. Sync projections after changing task state or notes: `uv run hive sync projections --json`
5. Create a PR to the target repository and record the result in the task history

## Success Criteria

- [ ] Canonical task updated in `.hive/tasks/`
- [ ] Relevant tests/evaluators run
- [ ] Projections synced
- [ ] PR opened against the target repository
"""

    rendered_context = _render_context_sections(context)
    file_tree = generate_file_tree(project_dir, max_depth=3)
    relative_project_path = _relative_display(resolved["project_path"], base_path)
    priority_name = _priority_name(resolved["priority"])

    body = f"""@claude Please work on this Agent Hive task.

## Task Assignment

| Field | Value |
|-------|-------|
| **Project** | `{resolved["project_id"]}` |
| **Task** | {resolved["task_title"]} |
| **Task ID** | `{resolved["task_id"] or "legacy-project-task"}` |
| **Priority** | {priority_name} |
| **Path** | `{relative_project_path}` |

{task_section}
{task_details}
## AGENCY.md Projection

<details>
<summary>Click to expand AGENCY.md</summary>

```yaml
{resolved["agency_markdown"]}
```

</details>

## Hive Context

{rendered_context}

## Project File Structure

```
{project_dir.name}/
{file_tree}```
{relevant_content}{external_repo_section}
{acceptance_section}
{instructions}

## Handoff Protocol

When you complete your work:
1. Update `.hive/tasks/{resolved["task_id"] or '<task-id>'}.md`
2. Sync projections: `uv run hive sync projections --json`
3. Release or transition the task appropriately in Hive
4. Link the PR or leave a clear handoff note in the canonical task

---
*Generated by Agent Hive Dispatcher at {datetime.now(timezone.utc).isoformat()}*
"""
    return body


def build_issue_labels(project: dict[str, Any]) -> list[str]:
    """
    Build labels for the GitHub issue.

    Args:
        project: Dispatch candidate or compatibility project dict

    Returns:
        List of label strings
    """
    metadata = project.get("metadata", {})
    project_id = project.get("project_id") or metadata.get("project_id", "unknown")
    task_id = project.get("task_id") or project.get("id")
    priority = project.get("priority", metadata.get("priority", "medium"))

    labels = ["agent-hive", "automated", f"priority:{_priority_name(priority)}"]
    labels.append(f"project:{project_id}")
    if task_id:
        labels.append(f"task:{task_id}")
    return labels

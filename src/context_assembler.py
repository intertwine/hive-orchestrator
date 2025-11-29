#!/usr/bin/env python3
"""
Agent Hive Context Assembler

Builds rich context for agent work assignments, including AGENCY.md content,
relevant files, and structured instructions for Claude Code.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import frontmatter


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

        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            current_prefix = "    " if is_last else "    "
            tree += f"{prefix}{current_prefix}{item.name}\n"

            if item.is_dir() and current_depth < max_depth - 1:
                extension = "    " if is_last else "    "
                tree += generate_file_tree(item, prefix + extension, max_depth, current_depth + 1)

    except PermissionError:
        pass

    return tree


def get_relevant_files_content(
    project_dir: Path, relevant_files: List[str], base_path: Path
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
        # Try to resolve the file path
        full_path = None

        # First try relative to project dir
        candidate = project_dir / file_path
        if candidate.exists():
            full_path = candidate
        else:
            # Try relative to base path
            candidate = base_path / file_path
            if candidate.exists():
                full_path = candidate

        if full_path and full_path.is_file():
            try:
                file_content = full_path.read_text(encoding="utf-8")
                # Truncate very large files
                if len(file_content) > 10000:
                    file_content = file_content[:10000] + "\n\n... (truncated)"

                relative_path = full_path.relative_to(base_path)
                content_parts.append(f"### `{relative_path}`\n\n```\n{file_content}\n```")
            except Exception as e:
                content_parts.append(f"### `{file_path}`\n\n*Error reading file: {e}*")
        else:
            content_parts.append(f"### `{file_path}`\n\n*File not found*")

    return "\n\n".join(content_parts) if content_parts else "*No relevant files specified*"


def get_next_task(content: str) -> Optional[str]:
    """
    Extract the next uncompleted task from AGENCY.md content.

    Args:
        content: Markdown content from AGENCY.md

    Returns:
        The next uncompleted task, or None if all tasks are complete
    """
    lines = content.split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- [ ]"):
            # Extract task text
            task = stripped[5:].strip()
            return task
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
        # Truncate long task names
        task_preview = next_task[:60] + "..." if len(next_task) > 60 else next_task
        return f"[Agent Hive] {project_id}: {task_preview}"
    return f"[Agent Hive] Work on {project_id}"


def build_issue_body(
    project: Dict[str, Any],
    base_path: Path,
    next_task: Optional[str] = None,
) -> str:
    """
    Build a comprehensive GitHub issue body for agent assignment.

    Args:
        project: Project data dictionary with path, metadata, content
        base_path: Base path of the hive
        next_task: The specific task to focus on (if identified)

    Returns:
        Formatted issue body as markdown string
    """
    project_path = Path(project["path"])
    project_dir = project_path.parent
    metadata = project["metadata"]
    content = project["content"]
    project_id = metadata.get("project_id", "unknown")
    priority = metadata.get("priority", "medium")
    tags = metadata.get("tags", [])
    relevant_files = metadata.get("relevant_files", [])

    # Build the raw AGENCY.md content
    raw_agency = frontmatter.dumps(frontmatter.Post(content, **metadata))

    # Get file tree for project
    file_tree = generate_file_tree(project_dir, max_depth=3)

    # Get relevant files content if specified
    relevant_content = ""
    if relevant_files:
        relevant_content = f"""
### Relevant Files

{get_relevant_files_content(project_dir, relevant_files, base_path)}
"""

    # Build task focus section
    task_section = ""
    if next_task:
        task_section = f"""
## Immediate Task

Focus on completing this task first:
> {next_task}

"""

    # Build the issue body
    body = f"""@claude Please work on this Agent Hive project.

## Task Assignment

| Field | Value |
|-------|-------|
| **Project** | `{project_id}` |
| **Priority** | {priority} |
| **Tags** | {', '.join(tags) if tags else 'none'} |
| **Path** | `{project_path.relative_to(base_path)}` |

{task_section}## Context

### AGENCY.md

<details>
<summary>Click to expand full AGENCY.md</summary>

```yaml
{raw_agency}
```

</details>

### Project File Structure

```
{project_dir.name}/
{file_tree}```
{relevant_content}

## Instructions

1. **Read the AGENCY.md** to understand the project objectives and current state
2. **Work on the highest priority uncompleted task**
3. **Write tests** for any new functionality
4. **Ensure quality**: Run `make test` and `make lint` - all must pass
5. **Update AGENCY.md** when done:
   - Mark completed tasks with `[x]`
   - Add timestamped notes to "Agent Notes" section
   - Set `owner: null` to release the project
6. **Create a PR** referencing this issue

## Success Criteria

- [ ] Task(s) completed as described in AGENCY.md
- [ ] Tests pass (`make test`)
- [ ] Linting passes (`make lint` with score > 9.0)
- [ ] AGENCY.md updated with progress
- [ ] PR created and linked to this issue

## Handoff Protocol

When you complete your work:
1. Update AGENCY.md: mark tasks `[x]`, add agent notes, set `owner: null`
2. Commit all changes including AGENCY.md updates
3. Push to a feature branch
4. Create a PR that closes this issue

---
*Generated by Agent Hive Dispatcher at {datetime.utcnow().isoformat()}Z*
"""

    return body


def build_issue_labels(project: Dict[str, Any]) -> List[str]:
    """
    Build labels for the GitHub issue.

    Args:
        project: Project data dictionary

    Returns:
        List of label strings
    """
    metadata = project["metadata"]
    labels = ["agent-hive", "automated"]

    # Add priority label
    priority = metadata.get("priority", "medium")
    labels.append(f"priority:{priority}")

    # Add project label
    project_id = metadata.get("project_id", "unknown")
    labels.append(f"project:{project_id}")

    return labels

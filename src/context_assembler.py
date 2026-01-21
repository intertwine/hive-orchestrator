#!/usr/bin/env python3
"""
Agent Hive Context Assembler

Builds rich context for agent work assignments, including AGENCY.md content,
relevant files, and structured instructions for Claude Code.

Supports both local projects and external GitHub repositories via the
`target_repo` metadata field.
"""

import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from urllib.parse import urlparse

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

        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            current_prefix = "└── " if is_last else "├── "
            tree += f"{prefix}{current_prefix}{item.name}\n"

            if item.is_dir() and current_depth < max_depth - 1:
                extension = "    " if is_last else "│   "
                tree += generate_file_tree(item, prefix + extension, max_depth, current_depth + 1)

    except PermissionError:
        # Intentionally ignore directories/files that cannot be accessed due to permission issues
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
    # Validate URL - only allow https:// for security
    if not url.startswith("https://"):
        return None

    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix="hive_external_")
        result = subprocess.run(
            [
                "git", "clone",
                "--depth", "1",
                "--branch", branch,
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
        # Clean up temp directory on exception to prevent resource leaks
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return None


def get_external_repo_context(
    repo_path: Path,
    key_files: Optional[List[str]] = None,
) -> Tuple[str, str]:
    """
    Generate context from an external repository.

    Args:
        repo_path: Path to the cloned repository
        key_files: Optional list of specific files to read

    Returns:
        Tuple of (file_tree, key_files_content)
    """
    # Generate file tree (exclude common noise)
    def filtered_tree(directory: Path, prefix: str = "", depth: int = 0, max_d: int = 4) -> str:
        if depth >= max_d:
            return ""
        result = ""
        try:
            items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            noise = {"node_modules", "__pycache__", "dist", "build", ".git", ".venv", "venv"}
            items = [i for i in items if not i.name.startswith(".") and i.name not in noise]

            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "
                result += f"{prefix}{current_prefix}{item.name}\n"
                if item.is_dir() and depth < max_d - 1:
                    extension = "    " if is_last else "│   "
                    result += filtered_tree(item, prefix + extension, depth + 1, max_d)
        except PermissionError:
            # Intentionally skip directories/files we cannot access to avoid breaking
            # the file tree generation
            pass
        return result

    file_tree = filtered_tree(repo_path)

    # Default key files to look for
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
                # Escape triple backticks to prevent markdown injection
                file_content_escaped = file_content.replace("```", "`\u200B`\u200B`")
                content_parts.append(
                    f"### `{file_pattern}`\n\n```\n{file_content_escaped}\n```"
                )
            except (UnicodeDecodeError, PermissionError):
                # Intentionally ignore files that cannot be read due to encoding
                # or permission errors
                pass

    key_files_content = "\n\n".join(content_parts) if content_parts else ""

    return file_tree, key_files_content


def cleanup_external_repo(repo_path: Path) -> None:
    """Clean up a cloned external repository."""
    if repo_path and repo_path.exists():
        shutil.rmtree(repo_path, ignore_errors=True)


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
            except (UnicodeDecodeError, PermissionError, OSError) as e:
                # Log specific file access errors without exposing full exception details
                error_type = type(e).__name__
                content_parts.append(f"### `{file_path}`\n\n*Error reading file: {error_type}*")
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
    agent_name: Optional[str] = None,
    agent_mention: Optional[str] = "@claude",
) -> str:
    """
    Build a comprehensive GitHub issue body for agent assignment.

    Supports both local projects and external GitHub repositories.
    External repos are detected via `target_repo` in metadata.

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
    target_repo = metadata.get("target_repo", {})

    # Build the raw AGENCY.md content using safe dump (prevents injection via frontmatter)
    raw_agency = safe_dump_agency_md(metadata, content)

    # Get file tree for project
    file_tree = generate_file_tree(project_dir, max_depth=3)

    # Get relevant files content if specified
    relevant_content = ""
    if relevant_files:
        relevant_content = f"""
### Relevant Files

{get_relevant_files_content(project_dir, relevant_files, base_path)}
"""

    # Handle external repository context
    external_repo_section = ""
    cloned_repo_path = None

    if target_repo and target_repo.get("url"):
        repo_url = target_repo["url"]
        repo_branch = target_repo.get("branch", "main")

        # Clone and get context
        cloned_repo_path = clone_external_repo(repo_url, repo_branch)
        if cloned_repo_path:
            try:
                ext_tree, ext_files = get_external_repo_context(cloned_repo_path)
                # Use urllib.parse for robust URL parsing
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
                # Clean up after getting context (or on exception)
                cleanup_external_repo(cloned_repo_path)

    # Build task focus section
    task_section = ""
    if next_task:
        task_section = f"""
## Immediate Task

Focus on completing this task first:
> {next_task}

"""

    # Determine instructions based on project type
    if target_repo and target_repo.get("url"):
        instructions = """
## Instructions

1. **Read the AGENCY.md** to understand the project objectives and current state
2. **Work on the highest priority uncompleted task**
3. **For external repository work**:
   - Fork the target repository if needed
   - Make the changes as specified in AGENCY.md
   - Write the implementation details to the appropriate Phase section
4. **Update AGENCY.md** when done:
   - Mark completed tasks with `[x]`
   - Write output to the appropriate section (Phase 1/2/3)
   - Add timestamped notes to "Agent Notes" section
   - Set `owner: null` to release the project
5. **Create a PR** to the target repository when implementation is complete

## Success Criteria

- [ ] Task(s) completed as described in AGENCY.md
- [ ] Implementation written to the appropriate Phase section
- [ ] AGENCY.md updated with progress
- [ ] PR created to target repository (when ready)"""
    else:
        instructions = """
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
- [ ] PR created and linked to this issue"""

    mention_line = (
        f"{agent_mention} Please work on this Agent Hive project."
        if agent_mention
        else "Please work on this Agent Hive project."
    )
    agent_label = agent_name or "unassigned"

    # Build the issue body
    body = f"""{mention_line}

## Task Assignment

| Field | Value |
|-------|-------|
| **Project** | `{project_id}` |
| **Agent** | {agent_label} |
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
{relevant_content}{external_repo_section}
{instructions}

## Handoff Protocol

When you complete your work:
1. Update AGENCY.md: mark tasks `[x]`, add agent notes, set `owner: null`
2. Commit all changes including AGENCY.md updates
3. Push to a feature branch
4. Create a PR that closes this issue

---
*Generated by Agent Hive Dispatcher at {datetime.now(timezone.utc).isoformat()}*
"""

    return body


def build_issue_labels(
    project: Dict[str, Any], extra_labels: Optional[List[str]] = None
) -> List[str]:
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

    if extra_labels:
        labels.extend(extra_labels)

    return list(dict.fromkeys(labels))

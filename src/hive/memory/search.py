"""Memory search backend."""

from __future__ import annotations

import json
from pathlib import Path

from src.hive.store.layout import global_memory_dir, memory_project_dir, runs_dir
from src.hive.store.task_files import list_tasks


def _snippet(body: str, query_lower: str, *, width: int = 280) -> str:
    lowered = body.lower()
    index = lowered.find(query_lower)
    if index < 0:
        return body[:width]
    start = max(0, index - width // 3)
    end = min(len(body), start + width)
    return body[start:end].strip()


def _memory_docs(
    root: Path,
    *,
    include_project: bool,
    include_global: bool,
) -> list[dict[str, object]]:
    docs: list[dict[str, object]] = []
    if include_project:
        for file_path in sorted(memory_project_dir(root).glob("**/*.md")):
            docs.append(
                {
                    "kind": "memory",
                    "scope": "project",
                    "path": str(file_path),
                    "title": str(file_path.relative_to(memory_project_dir(root))),
                    "body": file_path.read_text(encoding="utf-8"),
                }
            )
    if include_global:
        global_root = global_memory_dir()
        if global_root.exists():
            for file_path in sorted(global_root.glob("*.md")):
                docs.append(
                    {
                        "kind": "memory",
                        "scope": "global",
                        "path": str(file_path),
                        "title": file_path.name,
                        "body": file_path.read_text(encoding="utf-8"),
                    }
                )
    return docs


def _task_docs(root: Path, *, project_id: str | None) -> list[dict[str, object]]:
    docs: list[dict[str, object]] = []
    for task in list_tasks(root):
        if project_id and task.project_id != project_id:
            continue
        body = "\n".join(
            part
            for part in [
                task.title,
                task.summary_md,
                task.notes_md,
                task.history_md,
            ]
            if part.strip()
        )
        docs.append(
            {
                "kind": "task",
                "scope": "project",
                "path": str(task.path) if task.path else task.id,
                "title": task.title,
                "body": body,
                "task_id": task.id,
            }
        )
    return docs


def _accepted_run_docs(root: Path, *, project_id: str | None) -> list[dict[str, object]]:
    docs: list[dict[str, object]] = []
    for metadata_path in sorted(runs_dir(root).glob("*/metadata.json")):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("status") != "accepted":
            continue
        if project_id and metadata.get("project_id") != project_id:
            continue
        summary_path = Path(metadata["summary_path"]) if metadata.get("summary_path") else None
        if summary_path is None or not summary_path.exists():
            continue
        docs.append(
            {
                "kind": "run_summary",
                "scope": "run",
                "path": str(summary_path),
                "title": f"{metadata.get('id', 'run')} summary",
                "body": summary_path.read_text(encoding="utf-8"),
                "run_id": metadata.get("id"),
            }
        )
    return docs


def search(
    path: str | Path | None,
    query: str,
    *,
    scope: str = "all",
    project_id: str | None = None,
    task_id: str | None = None,
    limit: int = 8,
) -> list[dict[str, object]]:
    """Search project/global memory plus task and accepted-run context."""
    root = Path(path or Path.cwd()).resolve()
    query_lower = query.lower()
    include_global = scope in {"all", "global"}
    include_project = scope in {"all", "project"}

    docs: list[dict[str, object]] = []
    if include_project or include_global:
        docs.extend(
            _memory_docs(
                root,
                include_project=include_project,
                include_global=include_global,
            )
        )
    if include_project:
        docs.extend(_task_docs(root, project_id=project_id))
        docs.extend(_accepted_run_docs(root, project_id=project_id))

    results: list[dict[str, object]] = []
    for doc in docs:
        body = str(doc["body"])
        score = body.lower().count(query_lower)
        if task_id and doc.get("task_id") == task_id:
            score += 2
        if score <= 0:
            continue
        results.append(
            {
                "path": doc["path"],
                "title": doc["title"],
                "kind": doc["kind"],
                "scope": doc["scope"],
                "score": score,
                "snippet": _snippet(body, query_lower),
            }
        )
    return sorted(
        results,
        key=lambda item: (-int(item["score"]), str(item["kind"]), str(item["path"])),
    )[:limit]

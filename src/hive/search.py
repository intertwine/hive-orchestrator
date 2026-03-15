"""Workspace and API search surfaces for Hive 2.0."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from src.hive.scheduler.query import dependency_summary, project_summary
from src.hive.store.cache import rebuild_cache

WORKSPACE_SCOPES = {"workspace", "task", "run", "memory", "program", "agency", "global"}
API_DOC_FILES = (
    ("api", "README", "README.md"),
    ("api", "AGENT_INTERFACE", "docs/hive-v2-spec/AGENT_INTERFACE.md"),
    ("api", "HIVE_V2_SPEC", "docs/hive-v2-spec/HIVE_V2_SPEC.md"),
    ("schema", "SCHEMA", "docs/hive-v2-spec/SCHEMA.sql"),
)
COMMAND_DOCS = (
    {
        "title": "hive init",
        "summary": "Initialize the .hive substrate layout for a workspace.",
        "example": "hive init --json",
    },
    {
        "title": "hive doctor",
        "summary": "Inspect workspace health, project count, task count, and cache presence.",
        "example": "hive doctor --json",
    },
    {
        "title": "hive project create",
        "summary": "Scaffold a new project with AGENCY.md and PROGRAM.md.",
        "example": 'hive project create demo --title "Demo project" --json',
    },
    {
        "title": "hive search",
        "summary": "Search workspace state, API docs, schemas, examples, and project summaries.",
        "example": 'hive search "claim a task" --scope api --limit 8 --json',
    },
    {
        "title": "hive task claim",
        "summary": "Claim a task lease with an owner and optional TTL.",
        "example": "hive task claim task_... --owner codex --ttl-minutes 30 --json",
    },
    {
        "title": "hive task ready",
        "summary": "Return ranked ready tasks for the workspace or a single project.",
        "example": "hive task ready --project-id demo --limit 5 --json",
    },
    {
        "title": "hive run start",
        "summary": "Create a run scaffold for a task and move the task into progress.",
        "example": "hive run start task_... --json",
    },
    {
        "title": "hive run eval",
        "summary": "Execute configured evaluators for a run under PROGRAM.md policy.",
        "example": "hive run eval run_... --json",
    },
    {
        "title": "hive memory search",
        "summary": "Search project-local observational memory documents.",
        "example": 'hive memory search "migration" --json',
    },
    {
        "title": "hive context startup",
        "summary": "Assemble startup context from AGENTS, AGENCY, PROGRAM, and memory.",
        "example": "hive context startup --project demo --profile light --json",
    },
)
EXAMPLE_TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".py", ".sql", ".txt", ".yaml", ".yml"}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _normalized_scopes(scopes: Iterable[str] | None) -> set[str]:
    requested = {scope.lower() for scope in (scopes or [])}
    if not requested:
        return {"workspace", "api", "examples", "project"}
    expanded = set(requested)
    if requested & {"workspace"}:
        expanded |= WORKSPACE_SCOPES
    return expanded


def _score(text: str, query: str) -> int:
    haystack = text.lower()
    terms = [term for term in query.lower().split() if term]
    if not terms:
        return 0
    return sum(haystack.count(term) for term in terms)


def _snippet(text: str, query: str, width: int = 220) -> str:
    lowered = text.lower()
    terms = [term for term in query.lower().split() if term]
    first_index = min((lowered.find(term) for term in terms if lowered.find(term) >= 0), default=0)
    start = max(0, first_index - 40)
    end = min(len(text), start + width)
    return text[start:end].strip()


def _search_cache(root: Path, query: str, scopes: set[str], limit: int) -> list[dict[str, object]]:
    db_path = root / ".hive" / "cache" / "index.sqlite"
    if not db_path.exists():
        db_path = rebuild_cache(root)

    doc_type_map = {
        "task": "task",
        "run": "run_summary",
        "memory": "memory",
        "program": "program",
        "agency": "agency",
        "global": "global",
    }
    doc_types = {
        doc_type
        for scope, doc_type in doc_type_map.items()
        if scope in scopes or "workspace" in scopes
    }
    if not doc_types:
        return []

    placeholders = ",".join("?" for _ in sorted(doc_types))
    connection = sqlite3.connect(db_path)
    try:
        # NOTE: This still fetches all matching doc types before scoring in Python.
        # Move to SQLite FTS5 or at least a LIKE pre-filter once workspace corpora get larger.
        rows = list(
            connection.execute(
                f"""
                SELECT doc_type, path, title, body, metadata_json
                FROM search_docs
                WHERE doc_type IN ({placeholders})
                """,
                tuple(sorted(doc_types)),
            )
        )
    finally:
        connection.close()

    results: list[dict[str, object]] = []
    for doc_type, path, title, body, metadata_json in rows:
        score = _score(f"{title}\n{body}", query)
        if not score:
            continue
        metadata = json.loads(metadata_json or "{}")
        snippet = _snippet(body, query)
        results.append(
            {
                "kind": doc_type,
                "title": title,
                "path": path,
                "score": score,
                "snippet": snippet,
                "metadata": metadata,
            }
        )
    return sorted(results, key=lambda item: (-int(item["score"]), str(item["title"])))[:limit]


def _search_api_docs(query: str, scopes: set[str], limit: int) -> list[dict[str, object]]:
    if "api" not in scopes and "schema" not in scopes:
        return []
    repo_root = _repo_root()
    results: list[dict[str, object]] = []

    for command in COMMAND_DOCS:
        text = "\n".join([command["title"], command["summary"], command["example"]])
        score = _score(text, query)
        if not score:
            continue
        results.append(
            {
                "kind": "command",
                "title": command["title"],
                "score": score,
                "summary": command["summary"],
                "example": command["example"],
            }
        )

    for kind, title, relative_path in API_DOC_FILES:
        if kind == "schema" and "schema" not in scopes:
            continue
        file_path = repo_root / relative_path
        if not file_path.exists():
            continue
        body = file_path.read_text(encoding="utf-8")
        score = _score(body, query)
        if not score:
            continue
        snippet = _snippet(body, query)
        results.append(
            {
                "kind": kind,
                "title": title,
                "path": str(file_path),
                "score": score,
                "snippet": snippet,
            }
        )

    return sorted(results, key=lambda item: (-int(item["score"]), str(item["title"])))[:limit]


def _search_examples(query: str, scopes: set[str], limit: int) -> list[dict[str, object]]:
    if "examples" not in scopes:
        return []
    examples_root = _repo_root() / "docs" / "hive-v2-spec" / "examples"
    if not examples_root.exists():
        return []

    results: list[dict[str, object]] = []
    for file_path in sorted(
        path
        for path in examples_root.rglob("*")
        if path.is_file() and path.suffix.lower() in EXAMPLE_TEXT_SUFFIXES
    ):
        try:
            body = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        score = _score(body, query)
        if not score:
            continue
        snippet = _snippet(body, query)
        results.append(
            {
                "kind": "example",
                "title": str(file_path.relative_to(examples_root)),
                "path": str(file_path),
                "score": score,
                "snippet": snippet,
            }
        )
    return sorted(results, key=lambda item: (-int(item["score"]), str(item["title"])))[:limit]


def _search_project_summary(
    root: Path, query: str, scopes: set[str], limit: int
) -> list[dict[str, object]]:
    if "project" not in scopes:
        return []
    results: list[dict[str, object]] = []

    workspace_graph = {
        "projects": project_summary(root),
        "dependencies": dependency_summary(root),
    }
    graph_text = json.dumps(workspace_graph, indent=2, sort_keys=True)
    graph_score = _score(graph_text, query)
    if graph_score:
        graph_snippet = _snippet(graph_text, query)
        results.append(
            {
                "kind": "project",
                "title": "Workspace Graph Summary",
                "score": graph_score,
                "snippet": graph_snippet,
            }
        )

    for project in workspace_graph["projects"]:
        body = json.dumps(project, indent=2, sort_keys=True)
        score = _score(body, query)
        if not score:
            continue
        snippet = _snippet(body, query)
        results.append(
            {
                "kind": "project",
                "title": project["title"],
                "score": score,
                "snippet": snippet,
                "metadata": project,
            }
        )

    return sorted(results, key=lambda item: (-int(item["score"]), str(item["title"])))[:limit]


def search_workspace(
    path: str | Path | None,
    query: str,
    *,
    scopes: Iterable[str] | None = None,
    limit: int = 8,
) -> list[dict[str, object]]:
    """Search workspace state, API docs, examples, and project summaries."""
    root = Path(path or Path.cwd()).resolve()
    normalized_scopes = _normalized_scopes(scopes)
    results: list[dict[str, object]] = []
    results.extend(_search_cache(root, query, normalized_scopes, limit))
    results.extend(_search_api_docs(query, normalized_scopes, limit))
    results.extend(_search_examples(query, normalized_scopes, limit))
    results.extend(_search_project_summary(root, query, normalized_scopes, limit))
    results.sort(key=lambda item: (-int(item["score"]), str(item["title"])))
    return results[:limit]


__all__ = ["search_workspace"]

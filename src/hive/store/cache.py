"""Derived SQLite cache builder."""

from __future__ import annotations

import json
import sqlite3
from hashlib import sha256
from pathlib import Path

from src.hive.store.events import load_events
from src.hive.store.layout import cache_dir
from src.hive.store.projects import discover_projects
from src.hive.store.task_files import list_tasks

KNOWN_MEMORY_KINDS = {"observations", "reflections", "profile", "active", "summary"}


def _json(value) -> str:
    """Serialize values for cache storage."""
    return json.dumps(value, sort_keys=True, default=str)


def _schema_sql() -> str:
    schema_path = Path(__file__).resolve().parents[3] / "docs" / "hive-v2-spec" / "SCHEMA.sql"
    return schema_path.read_text(encoding="utf-8")


def _memory_scope_parts(relative_path: Path) -> tuple[str, str]:
    """Infer memory scope and scope key from the .hive/memory relative path."""
    parts = relative_path.parts
    if len(parts) < 2:
        raise ValueError(f"Unsupported memory doc path: {relative_path}")
    scope = parts[0]
    if scope not in {"project", "global", "run", "agent"}:
        raise ValueError(f"Unsupported memory scope: {scope}")
    scope_key = "/".join(parts[1:-1]) or scope
    return scope, scope_key


def _load_jsonl_entries(file_path: Path) -> list[dict]:
    if not file_path.exists():
        return []
    entries: list[dict] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def rebuild_cache(path: str | Path | None = None) -> Path:
    """Rebuild the derived SQLite cache from canonical files."""
    root = Path(path or Path.cwd())
    target_dir = cache_dir(root)
    target_dir.mkdir(parents=True, exist_ok=True)
    db_path = target_dir / "index.sqlite"
    if db_path.exists():
        db_path.unlink()

    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(_schema_sql())

        projects = discover_projects(root)
        tasks = list_tasks(root)
        task_by_id = {task.id: task for task in tasks}
        search_docs: list[tuple[str, Path, str, str]] = []

        for project in projects:
            connection.execute(
                """
                INSERT INTO projects
                (id, slug, path, title, status, priority, owner, metadata_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project.id,
                    project.slug,
                    str(project.agency_path),
                    project.title,
                    project.status,
                    project.priority,
                    project.owner,
                    _json(project.metadata),
                    project.metadata.get("created_at", project.metadata.get("last_updated", "")),
                    project.metadata.get("updated_at", project.metadata.get("last_updated", "")),
                ),
            )

        for display_order, task in enumerate(tasks):
            connection.execute(
                """
                INSERT INTO tasks
                (id, project_id, title, kind, status, priority, parent_id, owner, claimed_until,
                 display_order, display_path, labels_json, relevant_files_json, acceptance_json,
                 summary_md, notes_md, source_json, metadata_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    task.project_id,
                    task.title,
                    task.kind,
                    task.status,
                    task.priority,
                    task.parent_id,
                    task.owner,
                    task.claimed_until,
                    display_order,
                    task.path.name if task.path else task.id,
                    _json(task.labels),
                    _json(task.relevant_files),
                    _json(task.acceptance),
                    task.summary_md,
                    task.notes_md,
                    _json(task.source),
                    _json(task.metadata),
                    task.created_at,
                    task.updated_at,
                ),
            )
            if task.parent_id and task.parent_id in task_by_id:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO task_edges
                    (id, src_task_id, edge_type, dst_task_id, created_at, metadata_json)
                    VALUES (?, ?, 'parent_of', ?, ?, ?)
                    """,
                    (
                        f"{task.parent_id}:parent_of:{task.id}",
                        task.parent_id,
                        task.id,
                        task.updated_at,
                        "{}",
                    ),
                )
            for edge_type, targets in task.edges.items():
                for target in targets:
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO task_edges
                        (id, src_task_id, edge_type, dst_task_id, created_at, metadata_json)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            f"{task.id}:{edge_type}:{target}",
                            task.id,
                            edge_type,
                            target,
                            task.updated_at,
                            "{}",
                        ),
                    )
            if task.owner and task.claimed_until:
                connection.execute(
                    """
                    INSERT INTO claims
                    (id, task_id, owner, acquired_at, expires_at, status, metadata_json)
                    VALUES (?, ?, ?, ?, ?, 'active', ?)
                    """,
                    (
                        f"claim_{task.id}",
                        task.id,
                        task.owner,
                        task.updated_at,
                        task.claimed_until,
                        "{}",
                    ),
                )

        runs_root = root / ".hive" / "runs"
        if runs_root.exists():
            for metadata_path in sorted(runs_root.glob("*/metadata.json")):
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                if metadata.get("task_id") not in task_by_id:
                    continue
                summary_path = (
                    Path(metadata["summary_path"]) if metadata.get("summary_path") else None
                )
                if summary_path and summary_path.exists():
                    search_docs.append(
                        (
                            "run_summary",
                            summary_path,
                            summary_path.name,
                            summary_path.read_text(encoding="utf-8"),
                        )
                    )
                connection.execute(
                    """
                    INSERT INTO runs
                    (id, project_id, task_id, mode, status, executor, branch_name, worktree_path,
                     program_path, program_sha256, plan_path, summary_path, review_path, patch_path,
                     command_log_path, logs_dir, tokens_in, tokens_out, cost_usd, started_at,
                     finished_at, exit_reason, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        metadata["id"],
                        metadata["project_id"],
                        metadata["task_id"],
                        metadata.get("mode", "workflow"),
                        metadata.get("status", "planned"),
                        metadata.get("executor", "local"),
                        metadata.get("branch_name"),
                        metadata.get("worktree_path"),
                        metadata.get("program_path"),
                        metadata.get("program_sha256"),
                        metadata.get("plan_path"),
                        metadata.get("summary_path"),
                        metadata.get("review_path"),
                        metadata.get("patch_path"),
                        metadata.get("command_log_path"),
                        metadata.get("logs_dir"),
                        metadata.get("tokens_in"),
                        metadata.get("tokens_out"),
                        metadata.get("cost_usd"),
                        metadata.get("started_at"),
                        metadata.get("finished_at"),
                        metadata.get("exit_reason"),
                        _json(metadata.get("metadata_json", {})),
                    ),
                )
                command_log_path = (
                    Path(metadata["command_log_path"]) if metadata.get("command_log_path") else None
                )
                if command_log_path and command_log_path.exists():
                    for entry in _load_jsonl_entries(command_log_path):
                        connection.execute(
                            """
                            INSERT INTO run_steps
                            (id, run_id, seq, step_type, status, summary, artifact_path,
                             started_at, finished_at, metadata_json)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                f"{metadata['id']}:{entry.get('seq', 0)}",
                                metadata["id"],
                                int(entry.get("seq", 0)),
                                entry.get("step_type", "command"),
                                entry.get("status", "succeeded"),
                                entry.get("summary", ""),
                                entry.get("artifact_path"),
                                entry.get("started_at"),
                                entry.get("finished_at"),
                                _json(entry.get("metadata_json", {})),
                            ),
                        )
                eval_dir = metadata_path.parent / "eval"
                if eval_dir.exists():
                    for eval_path in sorted(eval_dir.glob("*.json")):
                        evaluation = json.loads(eval_path.read_text(encoding="utf-8"))
                        connection.execute(
                            """
                            INSERT INTO evaluations
                            (id, run_id, evaluator_id, command, required, status, metric_name,
                             metric_value, stdout_path, stderr_path, created_at, metadata_json)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                f"{metadata['id']}:{evaluation['evaluator_id']}",
                                metadata["id"],
                                evaluation["evaluator_id"],
                                evaluation["command"],
                                1 if evaluation.get("required", True) else 0,
                                evaluation["status"],
                                evaluation.get("metric_name"),
                                evaluation.get("metric_value"),
                                evaluation.get("stdout_path"),
                                evaluation.get("stderr_path"),
                                evaluation.get("created_at"),
                                _json(evaluation.get("metadata_json", {})),
                            ),
                        )

        memory_root = root / ".hive" / "memory"
        if memory_root.exists():
            for file_path in sorted(memory_root.glob("**/*.md")):
                relative_path = file_path.relative_to(memory_root)
                try:
                    scope, scope_key = _memory_scope_parts(relative_path)
                except ValueError:
                    continue
                kind = file_path.stem
                if kind not in KNOWN_MEMORY_KINDS:
                    continue
                content = file_path.read_text(encoding="utf-8")
                search_docs.append(("memory", file_path, f"{scope_key}/{kind}", content))
                connection.execute(
                    """
                    INSERT INTO memory_docs
                    (id, scope, scope_key, kind, path, updated_at, source_hash, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"{scope}:{scope_key}:{kind}",
                        scope,
                        scope_key,
                        kind,
                        str(file_path),
                        file_path.stat().st_mtime_ns,
                        sha256(content.encode("utf-8")).hexdigest(),
                        _json({"relative_path": relative_path.as_posix()}),
                    ),
                )

        global_path = root / "GLOBAL.md"
        if global_path.exists():
            search_docs.append(
                ("global", global_path, "GLOBAL.md", global_path.read_text(encoding="utf-8"))
            )
        for project in projects:
            search_docs.append(("agency", project.agency_path, project.title, project.content))
            if project.program_path.exists():
                search_docs.append(
                    (
                        "program",
                        project.program_path,
                        project.program_path.name,
                        project.program_path.read_text(encoding="utf-8"),
                    )
                )
        for task in tasks:
            search_docs.append(("task", task.path or Path(task.id), task.title, task.summary_md))
        for doc_type, file_path, title, body in search_docs:
            connection.execute(
                """
                INSERT INTO search_docs (id, doc_type, path, title, body, metadata_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{doc_type}:{file_path}",
                    doc_type,
                    str(file_path),
                    title,
                    body,
                    "{}",
                    file_path.stat().st_mtime_ns if file_path.exists() else 0,
                ),
            )

        for event in load_events(root):
            connection.execute(
                """
                INSERT INTO events
                (id, occurred_at, actor, entity_type, entity_id, event_type, source, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["id"],
                    event["occurred_at"],
                    event["actor"],
                    event["entity_type"],
                    event["entity_id"],
                    event["event_type"],
                    event["source"],
                    _json(event.get("payload_json", {})),
                ),
            )

        connection.commit()
    finally:
        connection.close()
    return db_path

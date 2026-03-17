"""Derived SQLite cache builder."""

from __future__ import annotations

from contextlib import contextmanager
import os
import json
import re
import sqlite3
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
import time

try:  # pragma: no cover - fcntl is always available on macOS/Linux, but keep import-safe.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]

from src.hive.store.events import load_events
from src.hive.store.layout import cache_dir, global_memory_dir
from src.hive.store.projects import discover_projects
from src.hive.store.task_files import list_tasks

KNOWN_MEMORY_KINDS = {"observations", "reflections", "profile", "active", "summary"}
WORKSPACE_DOC_SUFFIXES = {".md", ".markdown", ".rst", ".txt"}
WORKSPACE_ROOT_DOC_STEMS = {"README", "CHANGELOG", "CONTRIBUTING", "RELEASING", "RELEASE_NOTES"}


class CacheBusyError(RuntimeError):
    """Raised when the derived cache stays locked for too long."""


def _json(value) -> str:
    """Serialize values for cache storage."""
    return json.dumps(value, sort_keys=True, default=str)


def _schema_sql() -> str:
    return files("src.hive.store").joinpath("SCHEMA.sql").read_text(encoding="utf-8")


@contextmanager
def _cache_lock(lock_path: Path, *, timeout_seconds: float = 15.0):
    """Serialize cache rebuilds across processes with a simple file lock."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as handle:
        if fcntl is None:  # pragma: no cover - fallback for non-posix environments.
            yield
            return
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    raise CacheBusyError(
                        "Hive is already rebuilding the cache for this workspace. "
                        "Wait a moment, then retry the command."
                    ) from exc
                time.sleep(0.05)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _memory_scope_parts(relative_path: Path) -> tuple[str, str]:
    """Infer memory scope and scope key from the .hive/memory relative path."""
    parts = relative_path.parts
    if len(parts) < 2:
        raise ValueError(f"Unsupported memory doc path: {relative_path}")
    scope = parts[0]
    if scope not in {"project", "global", "run", "agent"}:
        raise ValueError(f"Unsupported memory scope: {scope}")
    if len(parts) == 2:
        scope_key = "workspace" if scope == "project" else scope
    else:
        scope_key = "/".join(parts[1:-1])
    return scope, scope_key


def _load_jsonl_entries(file_path: Path) -> list[dict]:
    if not file_path.exists():
        return []
    entries: list[dict] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def _resolve_run_artifact_path(metadata_path: Path, value: str | None, root: Path) -> Path | None:
    if not value:
        return None
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    metadata_dir = metadata_path.parent
    run_root = metadata_dir.parent.parent
    if candidate.name in {"summary.md", "review.md"}:
        canonical_review = (metadata_dir / "review" / candidate.name).resolve()
        if canonical_review.exists():
            return canonical_review
    if candidate.name == "patch.diff":
        canonical_patch = (metadata_dir / "workspace" / candidate.name).resolve()
        if canonical_patch.exists():
            return canonical_patch
    for base in (metadata_dir, run_root, root):
        resolved = (base / candidate).resolve()
        if resolved.exists():
            return resolved
    legacy_resolved = (metadata_dir / candidate).resolve()
    if legacy_resolved.exists():
        return legacy_resolved
    return legacy_resolved


def _task_search_body(task) -> str:
    acceptance = "\n".join(f"- {item}" for item in task.acceptance)
    relevant_files = "\n".join(f"- {item}" for item in task.relevant_files)
    labels = ", ".join(task.labels)
    parts = [
        f"# {task.title}",
        "",
        f"Status: {task.status}",
        f"Kind: {task.kind}",
        f"Priority: {task.priority}",
    ]
    if labels:
        parts.extend(["", "Labels:", labels])
    if task.summary_md.strip():
        parts.extend(["", "Summary:", task.summary_md.strip()])
    if acceptance:
        parts.extend(["", "Acceptance:", acceptance])
    if relevant_files:
        parts.extend(["", "Relevant Files:", relevant_files])
    if task.notes_md.strip():
        parts.extend(["", "Notes:", task.notes_md.strip()])
    if task.history_md.strip():
        parts.extend(["", "History:", task.history_md.strip()])
    return "\n".join(parts).strip()


def _task_search_metadata(task) -> dict[str, object]:
    return {
        "project_id": task.project_id,
        "task_id": task.id,
        "status": task.status,
        "priority": task.priority,
        "labels": task.labels,
        "relevant_files": task.relevant_files,
        "acceptance": task.acceptance,
        "summary": task.summary_md,
        "notes": task.notes_md,
        "history": task.history_md,
    }


def _project_search_metadata(project) -> dict[str, object]:
    return {
        "project_id": project.id,
        "project_slug": project.slug,
        "status": project.status,
        "priority": project.priority,
        "owner": project.owner,
    }


def _memory_search_metadata(scope: str, scope_key: str, kind: str, relative_path: Path) -> dict[str, object]:
    project_id = None
    shared = False
    if scope == "project":
        if scope_key == "workspace":
            shared = True
        else:
            project_id = scope_key.split("/", 1)[0]
    elif scope == "global":
        shared = True
    return {
        "entity_id": f"{scope}:{scope_key}:{kind}",
        "scope": scope,
        "scope_key": scope_key,
        "kind": kind,
        "relative_path": relative_path.as_posix(),
        "project_id": project_id,
        "shared_project_memory": shared,
    }


def _workspace_doc_paths(root: Path) -> list[Path]:
    """Return project-facing docs worth indexing for generic workspace search."""
    seen: set[Path] = set()
    paths: list[Path] = []

    for file_path in sorted(root.iterdir()):
        if not file_path.is_file():
            continue
        if file_path.name in {"GLOBAL.md", "AGENTS.md"}:
            continue
        if file_path.suffix.lower() not in WORKSPACE_DOC_SUFFIXES:
            continue
        if file_path.stem.upper() not in WORKSPACE_ROOT_DOC_STEMS:
            continue
        resolved = file_path.resolve()
        seen.add(resolved)
        paths.append(file_path)

    docs_root = root / "docs"
    if not docs_root.exists():
        return paths

    for file_path in sorted(docs_root.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in WORKSPACE_DOC_SUFFIXES:
            continue
        relative_to_docs = file_path.relative_to(docs_root)
        if relative_to_docs.parts and relative_to_docs.parts[0] == "hive-v2-spec":
            continue
        resolved = file_path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        paths.append(file_path)

    for hive_subdir in (root / ".hive" / "campaigns", root / ".hive" / "briefs"):
        if not hive_subdir.exists():
            continue
        for file_path in sorted(hive_subdir.rglob("*.md")):
            resolved = file_path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            paths.append(file_path)
    return paths


def _workspace_doc_metadata(root: Path, file_path: Path) -> dict[str, object]:
    """Return search metadata for generic workspace documents."""
    try:
        relative_path = file_path.relative_to(root).as_posix()
    except ValueError:  # pragma: no cover - defensive
        relative_path = file_path.name
    return {
        "entity_id": relative_path,
        "entity_key": f"workspace_doc:{relative_path}",
        "relative_path": relative_path,
        "scope": "workspace",
    }


def _memory_search_title(scope: str, relative_path: Path) -> str:
    """Return a human-facing title for indexed memory docs."""
    if scope == "project" and relative_path.parts and relative_path.parts[0] == "project":
        if len(relative_path.parts) > 2:
            return "/".join(relative_path.parts[1:])
        return f"workspace/{relative_path.name}"
    return relative_path.as_posix()


def _slugify_heading(value: str) -> str:
    """Return a stable slug for chunked search entities."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "section"


def _chunk_markdown_sections(content: str, *, observations: bool) -> list[tuple[str, str]]:
    """Split markdown into coherent top-level search chunks."""
    pattern = r"(?=^## \d{4}-\d{2}-\d{2})" if observations else r"(?=^## )"
    sections = [section.strip() for section in re.split(pattern, content, flags=re.MULTILINE)]
    chunks: list[tuple[str, str]] = []
    for index, section in enumerate(sections, start=1):
        if not section:
            continue
        heading_match = re.match(r"^##\s+(.+)$", section, flags=re.MULTILINE)
        heading = heading_match.group(1).strip() if heading_match else f"Section {index}"
        chunks.append((heading, section))
    return chunks


def _memory_search_docs(
    scope: str,
    scope_key: str,
    kind: str,
    relative_path: Path,
    file_path: Path,
    content: str,
) -> list[tuple[str, Path, str, str, dict]]:
    """Build memory search docs using section-level chunks when possible."""
    base_title = _memory_search_title(scope, relative_path)
    base_metadata = _memory_search_metadata(scope, scope_key, kind, relative_path)
    chunks = _chunk_markdown_sections(content, observations=(kind == "observations"))
    if not chunks:
        return [
            _search_doc_payload(
                doc_type="memory",
                file_path=_search_doc_chunk_path(file_path),
                title=base_title,
                body=content,
                metadata={"entity_key": f"memory:{scope}:{scope_key}:{kind}"} | base_metadata,
            )
        ]

    search_docs: list[tuple[str, Path, str, str, dict]] = []
    for index, (heading, body) in enumerate(chunks, start=1):
        chunk_slug = f"{_slugify_heading(heading)}-{index}"
        search_docs.append(
            _search_doc_payload(
                doc_type="memory",
                file_path=_search_doc_chunk_path(file_path, chunk_slug),
                title=f"{base_title} :: {heading}",
                body=body,
                metadata={
                    "entity_key": f"memory:{scope}:{scope_key}:{kind}:{chunk_slug}",
                    "memory_heading": heading,
                }
                | base_metadata,
            )
        )
    return search_docs


def _search_doc_payload(
    *,
    doc_type: str,
    file_path: Path,
    title: str,
    body: str,
    metadata: dict | None = None,
) -> tuple[str, Path, str, str, dict]:
    return (doc_type, file_path, title, body, metadata or {})


def _search_doc_chunk_path(file_path: Path, fragment: str | None = None) -> Path:
    """Return a unique cache path for a document, optionally with a chunk fragment."""
    if not fragment:
        return file_path
    return Path(f"{file_path}#{fragment}")


def _search_doc_stat_path(file_path: Path) -> Path:
    """Return the underlying file path used for timestamps when cache paths carry fragments."""
    return Path(str(file_path).split("#", 1)[0])


def rebuild_cache(path: str | Path | None = None) -> Path:
    """Rebuild the derived SQLite cache from canonical files."""
    root = Path(path or Path.cwd())
    target_dir = cache_dir(root)
    target_dir.mkdir(parents=True, exist_ok=True)
    db_path = target_dir / "index.sqlite"
    lock_path = target_dir / "index.lock"

    with _cache_lock(lock_path):
        temp_db_path = target_dir / f"index.sqlite.tmp.{os.getpid()}.{time.time_ns()}"
        if temp_db_path.exists():
            temp_db_path.unlink()

        connection = None
        try:
            connection = sqlite3.connect(temp_db_path)
            connection.executescript(_schema_sql())
            projects = discover_projects(root)
            tasks = list_tasks(root)
            task_by_id = {task.id: task for task in tasks}
            pending_edges: list[tuple[str, str, str, str, str, str]] = []
            search_docs: list[tuple[str, Path, str, str, dict]] = []

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
                    pending_edges.append(
                        (
                            f"{task.parent_id}:parent_of:{task.id}",
                            task.parent_id,
                            "parent_of",
                            task.id,
                            task.updated_at,
                            "{}",
                        )
                    )
                for edge_type, targets in task.edges.items():
                    for target in targets:
                        pending_edges.append(
                            (
                                f"{task.id}:{edge_type}:{target}",
                                task.id,
                                edge_type,
                                target,
                                task.updated_at,
                                "{}",
                            )
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

            for edge_row in pending_edges:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO task_edges
                    (id, src_task_id, edge_type, dst_task_id, created_at, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    edge_row,
                )

            runs_root = root / ".hive" / "runs"
            if runs_root.exists():
                for metadata_path in sorted(runs_root.glob("*/metadata.json")):
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                    if metadata.get("task_id") not in task_by_id:
                        continue
                    summary_path = _resolve_run_artifact_path(
                        metadata_path,
                        metadata.get("summary_path"),
                        root,
                    )
                    if summary_path and summary_path.exists():
                        search_docs.append(
                            _search_doc_payload(
                                doc_type="run_summary",
                                file_path=summary_path,
                                title=summary_path.name,
                                body=summary_path.read_text(encoding="utf-8"),
                                metadata={
                                    "entity_key": f"run:{metadata['id']}",
                                    "entity_id": metadata["id"],
                                    "run_id": metadata["id"],
                                    "project_id": metadata.get("project_id"),
                                    "task_id": metadata.get("task_id"),
                                    "status": metadata.get("status"),
                                },
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
                        Path(metadata["command_log_path"])
                        if metadata.get("command_log_path")
                        else None
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
                    content = file_path.read_text(encoding="utf-8")
                    search_metadata = _memory_search_metadata(scope, scope_key, kind, relative_path)
                    search_docs.extend(
                        _memory_search_docs(
                            scope,
                            scope_key,
                            kind,
                            relative_path,
                            file_path,
                            content,
                        )
                    )
                    if kind not in KNOWN_MEMORY_KINDS:
                        continue
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
                            _json(search_metadata),
                        ),
                    )
            global_memory_root = global_memory_dir()
            if global_memory_root.exists():
                for file_path in sorted(global_memory_root.glob("**/*.md")):
                    relative_path = file_path.relative_to(global_memory_root)
                    kind = file_path.stem
                    content = file_path.read_text(encoding="utf-8")
                    scope_key = "/".join(relative_path.parts[:-1]) or "global"
                    search_metadata = _memory_search_metadata("global", scope_key, kind, relative_path)
                    search_docs.extend(
                        _memory_search_docs(
                            "global",
                            scope_key,
                            kind,
                            relative_path,
                            file_path,
                            content,
                        )
                    )
                    if kind not in KNOWN_MEMORY_KINDS:
                        continue
                    connection.execute(
                        """
                        INSERT INTO memory_docs
                        (id, scope, scope_key, kind, path, updated_at, source_hash, metadata_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            f"global:{scope_key}:{kind}",
                            "global",
                            scope_key,
                            kind,
                            str(file_path),
                            file_path.stat().st_mtime_ns,
                            sha256(content.encode("utf-8")).hexdigest(),
                            _json(search_metadata),
                        ),
                    )

            global_path = root / "GLOBAL.md"
            if global_path.exists():
                search_docs.append(
                    _search_doc_payload(
                        doc_type="global",
                        file_path=global_path,
                        title="GLOBAL.md",
                        body=global_path.read_text(encoding="utf-8"),
                        metadata={"entity_key": "global:workspace"},
                    )
                )
            for project in projects:
                search_docs.append(
                    _search_doc_payload(
                        doc_type="agency",
                        file_path=project.agency_path,
                        title=project.title,
                        body=project.content,
                        metadata={
                            "entity_key": f"agency:{project.id}",
                            "entity_id": project.id,
                        }
                        | _project_search_metadata(project),
                    )
                )
                if project.program_path.exists():
                    search_docs.append(
                        _search_doc_payload(
                            doc_type="program",
                            file_path=project.program_path,
                            title=project.program_path.name,
                            body=project.program_path.read_text(encoding="utf-8"),
                            metadata={
                                "entity_key": f"program:{project.id}",
                                "entity_id": project.id,
                            }
                            | _project_search_metadata(project),
                        )
                    )
            for file_path in _workspace_doc_paths(root):
                relative_path = file_path.relative_to(root)
                search_docs.append(
                    _search_doc_payload(
                        doc_type="workspace_doc",
                        file_path=file_path,
                        title=relative_path.as_posix(),
                        body=file_path.read_text(encoding="utf-8"),
                        metadata=_workspace_doc_metadata(root, file_path),
                    )
                )
            for task in tasks:
                search_docs.append(
                    _search_doc_payload(
                        doc_type="task",
                        file_path=task.path or Path(task.id),
                        title=task.title,
                        body=_task_search_body(task),
                        metadata={"entity_key": f"task:{task.id}", "entity_id": task.id}
                        | _task_search_metadata(task)
                        | {"task_kind": task.kind},
                    )
                )
            for doc_type, file_path, title, body, metadata in search_docs:
                stat_path = _search_doc_stat_path(file_path)
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
                        _json(metadata),
                        stat_path.stat().st_mtime_ns if stat_path.exists() else 0,
                    ),
                )

            for event in load_events(root):
                connection.execute(
                    """
                    INSERT INTO events
                    (
                      id,
                      occurred_at,
                      actor,
                      actor_json,
                      entity_type,
                      entity_id,
                      event_type,
                      source,
                      payload_json,
                      ts,
                      type,
                      run_id,
                      task_id,
                      project_id,
                      campaign_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event["id"],
                        event["occurred_at"],
                        event.get("actor_text", event.get("actor", "hive")),
                        _json(event.get("actor", {})),
                        event["entity_type"],
                        event["entity_id"],
                        event["event_type"],
                        event["source"],
                        _json(event.get("payload_json", {})),
                        event.get("ts", event["occurred_at"]),
                        event.get("type", event["event_type"]),
                        event.get("run_id"),
                        event.get("task_id"),
                        event.get("project_id"),
                        event.get("campaign_id"),
                    ),
                )

            connection.commit()
            connection.close()
            connection = None
            os.replace(temp_db_path, db_path)
        finally:
            if connection is not None:
                connection.close()
            if temp_db_path.exists():
                temp_db_path.unlink()
    return db_path

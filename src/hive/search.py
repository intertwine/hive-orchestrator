"""Workspace and API search surfaces for the Hive v2 substrate."""

from __future__ import annotations

from importlib.resources import files
import json
import re
import sqlite3
from pathlib import Path
from typing import Iterable

import logging

from src.hive.scheduler.query import dependency_summary, project_summary
from src.hive.store.cache import rebuild_cache
from src.hive.store.layout import cache_dir
from src.hive.retrieval_trace import classify_retrieval_intent, retrieval_explanation

logger = logging.getLogger(__name__)

# "doc" keeps explicit doc-only searches aligned with the broader "workspace" umbrella.
# The greenfield brief-search miss was caused by cache indexing, not scope expansion here.
WORKSPACE_SCOPES = {"workspace", "task", "run", "memory", "program", "agency", "global", "doc"}
API_DOC_FILES = (
    ("api", "START_HERE", "docs/START_HERE.md"),
    ("api", "QUICKSTART", "docs/QUICKSTART.md"),
    ("api", "ADOPT_EXISTING_REPO", "docs/ADOPT_EXISTING_REPO.md"),
    ("api", "README", "README.md"),
    ("api", "AGENT_INTERFACE", "docs/hive-v2-spec/AGENT_INTERFACE.md"),
    ("api", "HIVE_V2_SPEC", "docs/hive-v2-spec/HIVE_V2_SPEC.md"),
    ("api", "HIVE_V2_2_RFC", "docs/hive-v2.2-rfc/HIVE_V2_2_RFC.md"),
    ("api", "HIVE_V2_2_DRIVER_SPEC", "docs/hive-v2.2-rfc/HIVE_V2_2_DRIVER_SPEC.md"),
    ("api", "HIVE_V2_3_RFC", "docs/hive-v2.3-rfc/HIVE_V2_3_RFC.md"),
    (
        "api",
        "HIVE_V2_3_RUNTIME_AND_SANDBOX_SPEC",
        "docs/hive-v2.3-rfc/HIVE_V2_3_RUNTIME_AND_SANDBOX_SPEC.md",
    ),
    (
        "api",
        "HIVE_V2_3_RETRIEVAL_AND_CAMPAIGNS_SPEC",
        "docs/hive-v2.3-rfc/HIVE_V2_3_RETRIEVAL_AND_CAMPAIGNS_SPEC.md",
    ),
    (
        "api",
        "HIVE_V2_3_IMPLEMENTATION_PLAN",
        "docs/hive-v2.3-rfc/HIVE_V2_3_IMPLEMENTATION_PLAN.md",
    ),
    (
        "api",
        "HIVE_V2_3_ACCEPTANCE_TESTS",
        "docs/hive-v2.3-rfc/HIVE_V2_3_ACCEPTANCE_TESTS.md",
    ),
    ("schema", "SCHEMA", "docs/hive-v2-spec/SCHEMA.sql"),
)
COMMAND_DOCS = (
    {
        "title": "hive onboard",
        "summary": "Recommended fresh-workspace bootstrap with a starter project and task chain.",
        "example": 'hive onboard demo --prompt "Create a small React website about bees."',
    },
    {
        "title": "hive quickstart",
        "summary": "Legacy compatibility alias for `hive onboard`; prefer `hive onboard`.",
        "example": 'hive quickstart demo --prompt "Create a small React website about bees."',
    },
    {
        "title": "hive init",
        "summary": "Initialize only the .hive substrate layout without creating a starter project.",
        "example": "hive init",
    },
    {
        "title": "hive doctor",
        "summary": "Inspect workspace health, project count, task count, and cache presence.",
        "example": "hive doctor",
    },
    {
        "title": "hive project create",
        "summary": "Scaffold a new project with AGENCY.md and PROGRAM.md.",
        "example": 'hive project create demo --title "Demo project"',
    },
    {
        "title": "hive search",
        "summary": "Search workspace state, API docs, schemas, examples, and project summaries.",
        "example": 'hive search "claim a task" --scope api --limit 8 --json',
    },
    {
        "title": "hive next",
        "summary": "Recommend the next task for an agent-manager loop.",
        "example": "hive next --json",
    },
    {
        "title": "hive work",
        "summary": "Claim a task, checkpoint the repo, start a governed run, and build context.",
        "example": "hive work --project-id demo --owner codex --json",
    },
    {
        "title": "hive finish",
        "summary": "Evaluate, close, promote, and optionally clean up a run in one step.",
        "example": "hive finish run_... --owner codex --json",
    },
    {
        "title": "hive task ready",
        "summary": "Return ranked ready tasks for the workspace or a single project.",
        "example": "hive task ready --project-id demo --limit 5",
    },
    {
        "title": "hive run eval",
        "summary": "Execute configured evaluators for a run under PROGRAM.md policy.",
        "example": "hive run eval run_... --json",
    },
    {
        "title": "hive memory search",
        "summary": "Search project-local observational memory documents.",
        "example": 'hive memory search "migration"',
    },
    {
        "title": "hive context startup",
        "summary": (
            "Assemble startup context from AGENTS, AGENCY, PROGRAM, memory, and recent runs."
        ),
        "example": "hive context startup --project demo --profile light",
    },
)
EXAMPLE_TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".py", ".sql", ".txt", ".yaml", ".yml"}
DOC_TYPE_BOOST = {
    "task": 60,
    "memory": 36,
    "run_summary": 30,
    "workspace_doc": 26,
    "program": 16,
    "agency": 12,
    "global": 8,
}

# Keep a stable view of the checkout root for tests that monkeypatch `_repo_root()`
# to simulate installed-package behavior without a source docs tree.
_CHECKOUT_ROOT = Path(__file__).resolve().parents[2]


def _repo_root() -> Path:
    return _CHECKOUT_ROOT


def _packaged_docs_root():
    return files("src.hive.resources").joinpath("docs")


def _read_doc_resource(relative_path: str) -> tuple[str, str] | None:
    source_path = _repo_root() / relative_path
    if source_path.exists():
        return str(source_path), source_path.read_text(encoding="utf-8")

    packaged = _packaged_docs_root().joinpath(relative_path.removeprefix("docs/"))
    if packaged.is_file():
        return f"package:{relative_path}", packaged.read_text(encoding="utf-8")

    source_checkout = _CHECKOUT_ROOT / relative_path
    if source_checkout.exists():
        return f"package:{relative_path}", source_checkout.read_text(encoding="utf-8")
    return None


def _iter_text_resources(relative_dir: str):
    source_root = _repo_root() / relative_dir
    if source_root.exists():
        for file_path in sorted(source_root.rglob("*")):
            if file_path.is_file() and file_path.suffix.lower() in EXAMPLE_TEXT_SUFFIXES:
                yield str(file_path), str(file_path.relative_to(source_root)), file_path.read_text(
                    encoding="utf-8"
                )
        return

    packaged_root = _packaged_docs_root().joinpath(relative_dir.removeprefix("docs/"))
    if packaged_root.is_dir():
        stack = [(packaged_root, "")]
        while stack:
            current, prefix = stack.pop()
            children = sorted(current.iterdir(), key=lambda item: item.name, reverse=True)
            for child in children:
                relative_name = f"{prefix}{child.name}"
                if child.is_dir():
                    stack.append((child, relative_name + "/"))
                    continue
                suffix = Path(child.name).suffix.lower()
                if suffix not in EXAMPLE_TEXT_SUFFIXES:
                    continue
                yield f"package:{relative_dir}/{relative_name}", relative_name, child.read_text(
                    encoding="utf-8"
                )
        return

    source_root = _CHECKOUT_ROOT / relative_dir
    if not source_root.is_dir():
        return

    for file_path in sorted(source_root.rglob("*")):
        if file_path.is_file() and file_path.suffix.lower() in EXAMPLE_TEXT_SUFFIXES:
            yield (
                f"package:{relative_dir}/{file_path.relative_to(source_root)}",
                str(file_path.relative_to(source_root)),
                file_path.read_text(encoding="utf-8"),
            )


def _normalized_scopes(scopes: Iterable[str] | None) -> set[str]:
    requested = {scope.lower() for scope in (scopes or [])}
    if not requested:
        return {"workspace", "api", "examples", "project"}
    expanded = set(requested)
    if requested & {"workspace"}:
        expanded |= WORKSPACE_SCOPES
    return expanded


def _query_terms(query: str) -> list[str]:
    return [term.casefold() for term in re.findall(r"[A-Za-z0-9_-]+", query) if term.strip()]


def _fts_query(query: str) -> str:
    terms = _query_terms(query)
    if not terms:
        return ""
    return " OR ".join(f'"{term}"*' for term in terms)


def _count_term_hits(text: str, terms: list[str]) -> int:
    haystack = text.casefold()
    return sum(haystack.count(term) for term in terms)


def _snippet(text: str, query: str, width: int = 220) -> str:
    lowered = text.casefold()
    terms = _query_terms(query)
    first_index = min((lowered.find(term) for term in terms if lowered.find(term) >= 0), default=0)
    start = max(0, first_index - 40)
    end = min(len(text), start + width)
    return text[start:end].strip()


def _match_reasons(
    *,
    doc_type: str,
    title: str,
    body: str,
    query: str,
    metadata: dict[str, object],
) -> list[str]:
    terms = _query_terms(query)
    title_hits = [term for term in terms if term in title.casefold()]
    body_hits = [term for term in terms if term in body.casefold() and term not in title_hits]
    reasons: list[str] = []
    if doc_type == "task":
        reasons.append("canonical task record")
    elif doc_type == "memory":
        reasons.append("project memory record")
    elif doc_type == "run_summary":
        reasons.append("accepted run summary")
    elif doc_type == "workspace_doc":
        reasons.append("workspace document")
    if title_hits:
        reasons.append("matched title terms: " + ", ".join(title_hits))
    acceptance_hits = [
        term
        for term in terms
        if term in " ".join(str(item) for item in metadata.get("acceptance", [])).casefold()
    ]
    if acceptance_hits:
        reasons.append("matched acceptance criteria")
    file_hits = [
        term
        for term in terms
        if term in " ".join(str(item) for item in metadata.get("relevant_files", [])).casefold()
    ]
    if file_hits:
        reasons.append("matched relevant files")
    note_hits = [
        term
        for term in terms
        if term
        in " ".join(
            str(metadata.get(key, "")) for key in ("summary", "notes", "history")
        ).casefold()
    ]
    if note_hits and not body_hits:
        reasons.append("matched task narrative")
    if body_hits:
        reasons.append("matched body terms: " + ", ".join(body_hits[:4]))
    if metadata.get("project_id") and not metadata.get("shared_project_memory"):
        reasons.append("project-local")
    if metadata.get("project_id"):
        reasons.append(f"project: {metadata['project_id']}")
    return reasons or ["matched indexed workspace content"]


# pylint: disable-next=too-many-arguments
def _cache_result(
    *,
    doc_type: str,
    path: str,
    title: str,
    body: str,
    metadata: dict[str, object],
    fts_rank: float,
    query: str,
    intent: str,
    dense_distance: float | None = None,
) -> dict[str, object]:
    terms = _query_terms(query)
    title_hits = _count_term_hits(title, terms)
    body_hits = _count_term_hits(body, terms)
    phrase_bonus = 12 if query.casefold() in body.casefold() else 0
    score = DOC_TYPE_BOOST.get(doc_type, 6) + (title_hits * 14) + (body_hits * 3) + phrase_bonus
    score += max(0.0, 12.0 - min(abs(fts_rank), 12.0))
    # Dense-only results (no FTS match) use a flat base score instead of DOC_TYPE_BOOST,
    # since they were found purely via semantic similarity and need high similarity to
    # compete with FTS-matched results that have term-level evidence.
    if dense_distance is not None and fts_rank == 0.0:
        dense_similarity = max(0.0, 1.0 - min(dense_distance, 1.5) / 1.5)
        score = 20.0 + dense_similarity * 30.0  # 20-50 range, below typical FTS scores
    if intent == "policy" and doc_type == "program":
        score += 18
    elif intent == "history" and doc_type == "run_summary":
        score += 18
    elif intent == "memory" and doc_type == "memory":
        score += 12
    elif intent == "task" and doc_type == "task":
        score += 12
    reasons = _match_reasons(
        doc_type=doc_type,
        title=title,
        body=body,
        query=query,
        metadata=metadata,
    )
    if dense_distance is not None:
        reasons.append(f"semantic similarity (distance: {dense_distance:.3f})")
    if intent == "policy" and doc_type == "program":
        reasons.append("policy intent boosted PROGRAM.md over general docs")
    elif intent == "history" and doc_type == "run_summary":
        reasons.append("history intent boosted accepted run summaries")
    scope = str(metadata.get("scope") or ("project" if doc_type in {"task", "run_summary"} else ""))
    result: dict[str, object] = {
        "kind": doc_type,
        "title": title,
        "path": path,
        "score": round(score, 3),
        "snippet": _snippet(body, query),
        "why": reasons,
        "matches": reasons,
        "explanation": retrieval_explanation({"kind": doc_type, "why": reasons}),
        "metadata": metadata,
    }
    if scope:
        result["scope"] = scope
    if dense_distance is not None:
        result["dense_match"] = True
    return result


def _matches_project_filter(metadata: dict[str, object], project_id: str | None) -> bool:
    if not project_id:
        return True
    if metadata.get("scope") == "global":
        return True
    if metadata.get("project_id") == project_id:
        return True
    return bool(metadata.get("shared_project_memory"))


def _matches_task_filter(metadata: dict[str, object], task_id: str | None) -> bool:
    if not task_id:
        return True
    return metadata.get("task_id") == task_id or metadata.get("entity_id") == task_id


# pylint: disable-next=too-many-arguments,too-many-locals,too-many-branches,too-many-statements
def search_cache_documents(
    root: Path,
    query: str,
    *,
    scopes: Iterable[str] | None = None,
    limit: int = 8,
    project_id: str | None = None,
    task_id: str | None = None,
) -> list[dict[str, object]]:
    """Search cache-backed workspace documents using SQLite FTS and optional dense vectors."""
    normalized_scopes = _normalized_scopes(scopes)
    db_path = rebuild_cache(root)

    doc_type_map = {
        "task": "task",
        "run": "run_summary",
        "memory": "memory",
        "doc": "workspace_doc",
        "program": "program",
        "agency": "agency",
        "global": "global",
    }
    doc_types = {
        doc_type
        for scope, doc_type in doc_type_map.items()
        if scope in normalized_scopes or "workspace" in normalized_scopes
    }
    if not doc_types:
        return []

    fts_query = _fts_query(query)
    if not fts_query:
        return []
    intent = classify_retrieval_intent(query)

    where_clause = f"d.doc_type IN ({','.join('?' for _ in sorted(doc_types))})"
    params: list[object] = [fts_query, *sorted(doc_types)]

    # ---- Dense vector search (optional) ----
    dense_hits: dict[str, float] = {}
    try:
        from src.hive.retrieval.dense import is_dense_available, search_dense

        if is_dense_available():
            for hit in search_dense(cache_dir(root), query, limit=max(limit * 3, 24)):
                dense_hits[hit.doc_id] = hit.distance
    except Exception:  # pylint: disable=broad-except
        pass

    # ---- FTS5 lexical search ----
    connection = sqlite3.connect(db_path)
    try:
        rows = list(
            connection.execute(
                f"""
                SELECT
                  d.doc_type,
                  d.path,
                  d.title,
                  d.body,
                  d.metadata_json,
                  bm25(search_docs_fts, 2.0, 1.0) AS fts_rank
                FROM search_docs_fts
                JOIN search_docs d ON d.rowid = search_docs_fts.rowid
                WHERE search_docs_fts MATCH ?
                  AND {where_clause}
                ORDER BY fts_rank ASC, d.updated_at DESC
                LIMIT ?
                """,
                (*params, max(limit * 8, 24)),
            )
        )

        # ---- Fuse lexical + dense results ----
        deduped: list[dict[str, object]] = []
        seen_keys: set[str] = set()
        seen_ids: set[str] = set()
        for doc_type, path, title, body, metadata_json, fts_rank in rows:
            metadata = json.loads(metadata_json or "{}")
            if not _matches_project_filter(metadata, project_id):
                continue
            if not _matches_task_filter(metadata, task_id):
                continue
            entity_key = str(metadata.get("entity_key") or f"{doc_type}:{path}")
            if entity_key in seen_keys:
                continue
            seen_keys.add(entity_key)
            doc_id = f"{doc_type}:{path}"
            seen_ids.add(doc_id)
            deduped.append(
                _cache_result(
                    doc_type=doc_type,
                    path=path,
                    title=title,
                    body=body,
                    metadata=metadata,
                    fts_rank=float(fts_rank),
                    query=query,
                    intent=intent,
                    dense_distance=dense_hits.get(doc_id),
                )
            )

        # ---- Add dense-only hits that FTS missed ----
        # Only include results with strong semantic similarity.  For BGE-small L2
        # distances, < 0.5 is very relevant, 0.5-0.8 is moderately relevant.
        for doc_id, distance in dense_hits.items():
            if doc_id in seen_ids:
                continue
            if distance >= 0.5:
                continue
            row = connection.execute(
                "SELECT doc_type, path, title, body, metadata_json FROM search_docs WHERE id = ?",
                (doc_id,),
            ).fetchone()
            if not row:
                continue
            d_doc_type, d_path, d_title, d_body, d_metadata_json = row
            if d_doc_type not in doc_types:
                continue
            d_metadata = json.loads(d_metadata_json or "{}")
            if not _matches_project_filter(d_metadata, project_id):
                continue
            if not _matches_task_filter(d_metadata, task_id):
                continue
            d_entity_key = str(d_metadata.get("entity_key") or f"{d_doc_type}:{d_path}")
            if d_entity_key in seen_keys:
                continue
            seen_keys.add(d_entity_key)
            seen_ids.add(doc_id)
            deduped.append(
                _cache_result(
                    doc_type=d_doc_type,
                    path=d_path,
                    title=d_title,
                    body=d_body,
                    metadata=d_metadata,
                    fts_rank=0.0,
                    query=query,
                    intent=intent,
                    dense_distance=distance,
                )
            )
    finally:
        connection.close()

    deduped.sort(
        key=lambda item: (-float(item["score"]), str(item["title"]).lower(), str(item["path"]))
    )
    return deduped[:limit]


def _score(text: str, query: str) -> int:
    haystack = text.casefold()
    terms = _query_terms(query)
    if not terms:
        return 0
    return sum(haystack.count(term) for term in terms)


def _search_api_docs(query: str, scopes: set[str], limit: int) -> list[dict[str, object]]:
    if "api" not in scopes and "schema" not in scopes:
        return []
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
                "why": ["command reference", "matched command docs"],
                "matches": ["command reference", "matched command docs"],
                "explanation": "command reference; matched command docs",
            }
        )

    for kind, title, relative_path in API_DOC_FILES:
        if kind == "schema" and "schema" not in scopes:
            continue
        resource = _read_doc_resource(relative_path)
        if resource is None:
            continue
        resolved_path, body = resource
        score = _score(body, query)
        if not score:
            continue
        results.append(
            {
                "kind": kind,
                "title": title,
                "path": resolved_path,
                "score": score,
                "snippet": _snippet(body, query),
                "why": [f"matched {kind} docs"],
                "matches": [f"matched {kind} docs"],
                "explanation": f"matched {kind} docs",
            }
        )

    return sorted(results, key=lambda item: (-int(item["score"]), str(item["title"])))[:limit]


def _search_examples(query: str, scopes: set[str], limit: int) -> list[dict[str, object]]:
    if "examples" not in scopes:
        return []
    results: list[dict[str, object]] = []
    for relative_dir, reason in (
        ("docs/hive-v2-spec/examples", "matched spec example"),
        ("docs/recipes", "matched packaged recipe"),
    ):
        for resolved_path, title, body in _iter_text_resources(relative_dir):
            score = _score(body, query)
            if not score:
                continue
            results.append(
                {
                    "kind": "example",
                    "title": title,
                    "path": resolved_path,
                    "score": score,
                    "snippet": _snippet(body, query),
                    "why": [reason],
                    "matches": [reason],
                    "explanation": reason,
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
        results.append(
            {
                "kind": "project",
                "title": "Workspace Graph Summary",
                "score": graph_score,
                "snippet": _snippet(graph_text, query),
                "why": ["matched project graph summary"],
                "matches": ["matched project graph summary"],
                "explanation": "matched project graph summary",
            }
        )

    for project in workspace_graph["projects"]:
        body = json.dumps(project, indent=2, sort_keys=True)
        score = _score(body, query)
        if not score:
            continue
        results.append(
            {
                "kind": "project",
                "title": project["title"],
                "score": score,
                "snippet": _snippet(body, query),
                "metadata": project,
                "why": ["matched project summary"],
                "matches": ["matched project summary"],
                "explanation": "matched project summary",
            }
        )

    return sorted(results, key=lambda item: (-int(item["score"]), str(item["title"])))[:limit]


# pylint: disable-next=too-many-arguments
def search_workspace(
    path: str | Path | None,
    query: str,
    *,
    scopes: Iterable[str] | None = None,
    limit: int = 8,
    project_id: str | None = None,
    task_id: str | None = None,
) -> list[dict[str, object]]:
    """Search workspace state, API docs, examples, and project summaries."""
    root = Path(path or Path.cwd()).resolve()
    normalized_scopes = _normalized_scopes(scopes)
    results: list[dict[str, object]] = []
    results.extend(
        search_cache_documents(
            root,
            query,
            scopes=normalized_scopes,
            limit=limit,
            project_id=project_id,
            task_id=task_id,
        )
    )
    results.extend(_search_api_docs(query, normalized_scopes, limit))
    results.extend(_search_examples(query, normalized_scopes, limit))
    results.extend(_search_project_summary(root, query, normalized_scopes, limit))

    deduped: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in sorted(
        results,
        key=lambda result: (-float(result["score"]), str(result["title"])),
    ):
        metadata = item.get("metadata")
        key = str(metadata.get("entity_key") if isinstance(metadata, dict) else "")
        if not key:
            key = str(item.get("path") or f"{item.get('kind')}:{item.get('title')}")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:limit]


# pylint: disable-next=too-many-arguments
def search_workspace_corpus(
    path: str | Path | None,
    query: str,
    *,
    scopes: Iterable[str] | None = None,
    limit: int = 8,
    project_id: str | None = None,
    task_id: str | None = None,
) -> list[dict[str, object]]:
    """Search only the cache-backed canonical workspace corpus."""
    root = Path(path or Path.cwd()).resolve()
    return search_cache_documents(
        root,
        query,
        scopes=scopes,
        limit=limit,
        project_id=project_id,
        task_id=task_id,
    )


__all__ = ["search_cache_documents", "search_workspace", "search_workspace_corpus"]

"""Workspace and API search surfaces for the Hive v2 substrate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import lru_cache
from importlib.resources import files
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Iterable

import logging

from src.hive.delegates import list_delegate_entries
from src.hive.scheduler.query import dependency_summary, project_summary
from src.hive.store.campaigns import list_campaigns
from src.hive.store.cache import rebuild_cache
from src.hive.store.layout import cache_dir
from src.hive.store.projects import discover_projects
from src.hive.retrieval_trace import classify_retrieval_intent, retrieval_explanation

logger = logging.getLogger(__name__)

# "doc" keeps explicit doc-only searches aligned with the broader "workspace" umbrella.
# The greenfield brief-search miss was caused by cache indexing, not scope expansion here.
WORKSPACE_SCOPES = {
    "workspace",
    "task",
    "run",
    "memory",
    "program",
    "agency",
    "global",
    "doc",
}
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
    ("api", "V2_4_STATUS", "docs/V2_4_STATUS.md"),
    ("api", "V2_5_STATUS", "docs/V2_5_STATUS.md"),
    ("api", "HIVE_V2_4_RFC", "docs/hive-v2.4-rfc/HIVE_V2_4_RFC.md"),
    (
        "api",
        "HIVE_V2_4_ADAPTER_MODEL_AND_LINK_SPEC",
        "docs/hive-v2.4-rfc/HIVE_V2_4_ADAPTER_MODEL_AND_LINK_SPEC.md",
    ),
    (
        "api",
        "HIVE_V2_4_HARNESS_PACKAGES_AND_ONBOARDING",
        "docs/hive-v2.4-rfc/HIVE_V2_4_HARNESS_PACKAGES_AND_ONBOARDING.md",
    ),
    (
        "api",
        "HIVE_V2_4_IMPLEMENTATION_PLAN",
        "docs/hive-v2.4-rfc/HIVE_V2_4_IMPLEMENTATION_PLAN.md",
    ),
    (
        "api",
        "HIVE_V2_4_ACCEPTANCE_TESTS",
        "docs/hive-v2.4-rfc/HIVE_V2_4_ACCEPTANCE_TESTS.md",
    ),
    (
        "api",
        "POST_V2_4_HANDOFF_TO_CODEX",
        "docs/hive-post-v2.4-rfcs/docs/HANDOFF_TO_CODEX.md",
    ),
    (
        "api",
        "HIVE_V2_5_COMMAND_CENTER_RFC",
        "docs/hive-post-v2.4-rfcs/docs/hive-v2.5-rfc/HIVE_V2_5_COMMAND_CENTER_RFC.md",
    ),
    (
        "api",
        "HIVE_V2_5_DESKTOP_SHELL_DECISION",
        "docs/hive-post-v2.4-rfcs/docs/hive-v2.5-rfc/HIVE_V2_5_DESKTOP_SHELL_DECISION.md",
    ),
    (
        "api",
        "POST_V2_4_ACCEPTANCE_MATRIX",
        "docs/hive-post-v2.4-rfcs/docs/POST_V2_4_ACCEPTANCE_MATRIX.md",
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
EXAMPLE_TEXT_SUFFIXES = {
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".sql",
    ".txt",
    ".yaml",
    ".yml",
}
DOC_TYPE_BOOST = {
    "task": 60,
    "memory": 36,
    "run_summary": 30,
    "workspace_doc": 26,
    "program": 16,
    "agency": 12,
    "global": 8,
}
SEARCH_SOURCE_LABELS = {
    "task": "Tasks",
    "run": "Runs",
    "memory": "Memory",
    "docs": "Docs",
    "command": "Commands",
    "recipe": "Recipes",
    "project": "Projects",
    "campaign": "Campaigns",
    "delegate": "Delegates",
}
SOURCE_FILTER_KINDS = {
    "task": {"task"},
    "run": {"run_summary"},
    "memory": {"memory"},
    "docs": {"workspace_doc", "program", "agency", "global", "api", "schema"},
    "command": {"command"},
    "recipe": {"example"},
    "project": {"project"},
    "campaign": {"campaign"},
    "delegate": {"delegate"},
}
TIME_WINDOW_DELTAS = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}

# Keep a stable view of the checkout root for tests that monkeypatch `_repo_root()`
# to simulate installed-package behavior without a source docs tree.
_CHECKOUT_ROOT = Path(__file__).resolve().parents[2]


def _repo_root() -> Path:
    return _CHECKOUT_ROOT


def _iso_from_ns(updated_at_ns: int | float | None) -> str:
    if not updated_at_ns:
        return ""
    try:
        return (
            datetime.fromtimestamp(float(updated_at_ns) / 1_000_000_000, tz=UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
    except (OverflowError, OSError, TypeError, ValueError):
        return ""


def _project_title_map(root: Path) -> dict[str, str]:
    return {project.id: project.title for project in discover_projects(root)}


def _search_source(kind: str) -> str:
    if kind in {"task", "run_summary", "memory", "project", "command", "campaign", "delegate"}:
        return {
            "task": "task",
            "run_summary": "run",
            "memory": "memory",
            "project": "project",
            "command": "command",
            "campaign": "campaign",
            "delegate": "delegate",
        }[kind]
    if kind == "example":
        return "recipe"
    return "docs"


def _search_open_label(kind: str) -> str | None:
    if kind == "task":
        return "Open project context"
    if kind == "run_summary":
        return "Open run"
    if kind in {"program", "agency", "project"}:
        return "Open project"
    if kind == "campaign":
        return "Open campaign"
    if kind == "delegate":
        return "Open session"
    return None


def _search_deep_link(kind: str, metadata: dict[str, object]) -> str | None:
    if kind == "run_summary" and metadata.get("run_id"):
        return f"/runs/{metadata['run_id']}"
    if kind == "delegate" and metadata.get("delegate_session_id"):
        return f"/runs/{metadata['delegate_session_id']}"
    if kind == "campaign" and metadata.get("campaign_id"):
        return f"/campaigns/{metadata['campaign_id']}"
    if metadata.get("project_id"):
        return f"/projects/{metadata['project_id']}"
    return None


def _normalize_harness(value: object) -> str:
    return str(value or "").strip()


def _within_time_window(occurred_at: str, time_window: str | None, now: datetime) -> bool:
    if not time_window:
        return True
    delta = TIME_WINDOW_DELTAS.get(time_window)
    if delta is None:
        return True
    if not occurred_at:
        return True
    try:
        observed = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    return observed >= (now - delta)


@lru_cache(maxsize=1)
def _refresh_run_driver_state():
    # Import lazily once so console search can enrich runs without recreating the
    # search <-> run inspection import cycle on every result.
    from src.hive.runs.engine import refresh_run_driver_state

    return refresh_run_driver_state


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
            if (
                file_path.is_file()
                and file_path.suffix.lower() in EXAMPLE_TEXT_SUFFIXES
            ):
                yield (
                    str(file_path),
                    str(file_path.relative_to(source_root)),
                    file_path.read_text(encoding="utf-8"),
                )
        return

    packaged_root = _packaged_docs_root().joinpath(relative_dir.removeprefix("docs/"))
    if packaged_root.is_dir():
        stack = [(packaged_root, "")]
        while stack:
            current, prefix = stack.pop()
            children = sorted(
                current.iterdir(), key=lambda item: item.name, reverse=True
            )
            for child in children:
                relative_name = f"{prefix}{child.name}"
                if child.is_dir():
                    stack.append((child, relative_name + "/"))
                    continue
                suffix = Path(child.name).suffix.lower()
                if suffix not in EXAMPLE_TEXT_SUFFIXES:
                    continue
                yield (
                    f"package:{relative_dir}/{relative_name}",
                    relative_name,
                    child.read_text(encoding="utf-8"),
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
    return [
        term.casefold() for term in re.findall(r"[A-Za-z0-9_-]+", query) if term.strip()
    ]


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
    first_index = min(
        (lowered.find(term) for term in terms if lowered.find(term) >= 0), default=0
    )
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
    body_hits = [
        term for term in terms if term in body.casefold() and term not in title_hits
    ]
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
        if term
        in " ".join(str(item) for item in metadata.get("acceptance", [])).casefold()
    ]
    if acceptance_hits:
        reasons.append("matched acceptance criteria")
    file_hits = [
        term
        for term in terms
        if term
        in " ".join(str(item) for item in metadata.get("relevant_files", [])).casefold()
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
    updated_at_ns: int | float | None = None,
    dense_distance: float | None = None,
) -> dict[str, object]:
    terms = _query_terms(query)
    title_hits = _count_term_hits(title, terms)
    body_hits = _count_term_hits(body, terms)
    phrase_bonus = 12 if query.casefold() in body.casefold() else 0
    score = (
        DOC_TYPE_BOOST.get(doc_type, 6)
        + (title_hits * 14)
        + (body_hits * 3)
        + phrase_bonus
    )
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
    scope = str(
        metadata.get("scope")
        or ("project" if doc_type in {"task", "run_summary"} else "")
    )
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
    occurred_at = _iso_from_ns(updated_at_ns)
    if occurred_at:
        result["occurred_at"] = occurred_at
    return result


def _matches_project_filter(
    metadata: dict[str, object], project_id: str | None
) -> bool:
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

        if is_dense_available() and not os.environ.get("HIVE_SKIP_DENSE_INDEX"):
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
                  d.updated_at,
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
        for doc_type, path, title, body, metadata_json, updated_at, fts_rank in rows:
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
                    updated_at_ns=updated_at,
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
                    updated_at_ns=None,
                    dense_distance=distance,
                )
            )
    finally:
        connection.close()

    deduped.sort(
        key=lambda item: (
            -float(item["score"]),
            str(item["title"]).lower(),
            str(item["path"]),
        )
    )
    return deduped[:limit]


def _score(text: str, query: str) -> int:
    haystack = text.casefold()
    terms = _query_terms(query)
    if not terms:
        return 0
    return sum(haystack.count(term) for term in terms)


def _result_key(item: dict[str, object]) -> str:
    metadata = item.get("metadata")
    key = str(metadata.get("entity_key") if isinstance(metadata, dict) else "")
    if key:
        return key
    return str(item.get("path") or f"{item.get('kind')}:{item.get('title')}")


def _result_family_kinds(scopes: set[str]) -> list[set[str]]:
    families: list[set[str]] = []
    if "api" in scopes:
        families.append({"api", "command"})
    if "schema" in scopes:
        families.append({"schema"})
    if "examples" in scopes:
        families.append({"example"})
    if "project" in scopes:
        families.append({"project"})
    return families


def _ensure_scope_diversity(
    ranked_results: list[dict[str, object]], scopes: set[str], limit: int
) -> list[dict[str, object]]:
    if limit <= 0 or len(ranked_results) <= limit:
        return ranked_results[:limit]

    selected = list(ranked_results[:limit])
    selected_keys = {_result_key(item) for item in selected}
    rank_by_key = {_result_key(item): index for index, item in enumerate(ranked_results)}

    representative_keys: set[str] = set()
    representatives: list[dict[str, object]] = []
    for family in _result_family_kinds(scopes):
        candidate = next(
            (item for item in ranked_results if str(item.get("kind")) in family),
            None,
        )
        if candidate is None:
            continue
        key = _result_key(candidate)
        representatives.append(candidate)
        representative_keys.add(key)

    missing = [item for item in representatives if _result_key(item) not in selected_keys]
    if not missing:
        return selected

    for candidate in missing:
        replacement_index = next(
            (
                index
                for index in range(len(selected) - 1, -1, -1)
                if _result_key(selected[index]) not in representative_keys
            ),
            None,
        )
        if replacement_index is None:
            break
        dropped_key = _result_key(selected[replacement_index])
        selected_keys.discard(dropped_key)
        selected[replacement_index] = candidate
        selected_keys.add(_result_key(candidate))

    selected.sort(key=lambda item: rank_by_key[_result_key(item)])
    return selected


def _search_api_docs(
    query: str, scopes: set[str], limit: int
) -> list[dict[str, object]]:
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

    return sorted(results, key=lambda item: (-int(item["score"]), str(item["title"])))[
        :limit
    ]


def _search_examples(
    query: str, scopes: set[str], limit: int
) -> list[dict[str, object]]:
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
    return sorted(results, key=lambda item: (-int(item["score"]), str(item["title"])))[
        :limit
    ]


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

    return sorted(results, key=lambda item: (-int(item["score"]), str(item["title"])))[
        :limit
    ]


def _search_campaign_records(
    root: Path, query: str, limit: int
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for campaign in list_campaigns(root):
        record = campaign.to_frontmatter()
        record["notes_md"] = campaign.notes_md
        record["path"] = str(campaign.path) if campaign.path else ""
        body = json.dumps(record, indent=2, sort_keys=True)
        score = _score(body, query)
        if not score:
            continue
        title = str(record.get("title") or record.get("id") or "Campaign")
        reasons = ["matched campaign plan"]
        title_hits = [term for term in _query_terms(query) if term in title.casefold()]
        if title_hits:
            reasons.append("matched title terms: " + ", ".join(title_hits))
        results.append(
            {
                "kind": "campaign",
                "title": title,
                "path": f"campaign:{record.get('id')}",
                "score": score,
                "summary": str(record.get("goal") or "Campaign configuration matched the query."),
                "snippet": _snippet(body, query),
                "why": reasons,
                "matches": reasons,
                "explanation": "; ".join(reasons),
                "metadata": {
                    "entity_key": f"campaign:{record.get('id')}",
                    "campaign_id": record.get("id"),
                    "project_id": (record.get("project_ids") or [None])[0],
                    "status": record.get("status"),
                    "driver": record.get("driver"),
                    "cadence": record.get("cadence"),
                },
                "occurred_at": str(record.get("updated_at") or record.get("created_at") or ""),
            }
        )
    return sorted(results, key=lambda item: (-float(item["score"]), str(item["title"])))[:limit]


def _search_delegate_records(root: Path, query: str, limit: int) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for entry in list_delegate_entries(root):
        metadata_json = (
            entry.get("metadata_json") if isinstance(entry.get("metadata_json"), dict) else {}
        )
        body = json.dumps(
            {
                "entry": entry,
                "metadata_json": metadata_json,
            },
            indent=2,
            sort_keys=True,
        )
        score = _score(body, query)
        if not score:
            continue
        title = str(
            metadata_json.get("task_title")
            or entry.get("delegate_session_id")
            or entry.get("id")
            or "Delegate session"
        )
        reasons = ["matched delegate session record"]
        title_hits = [term for term in _query_terms(query) if term in title.casefold()]
        if title_hits:
            reasons.append("matched title terms: " + ", ".join(title_hits))
        delegate_session_id = str(entry.get("delegate_session_id") or entry.get("id") or "")
        results.append(
            {
                "kind": "delegate",
                "title": title,
                "path": str(entry.get("manifest_path") or delegate_session_id),
                "score": score,
                "summary": (
                    f"{entry.get('driver', 'delegate')} session "
                    f"{entry.get('driver_handle') or delegate_session_id}"
                ),
                "snippet": _snippet(body, query),
                "why": reasons,
                "matches": reasons,
                "explanation": "; ".join(reasons),
                "metadata": {
                    "entity_key": f"delegate:{delegate_session_id}",
                    "delegate_session_id": delegate_session_id,
                    "project_id": entry.get("project_id"),
                    "task_id": entry.get("task_id"),
                    "status": entry.get("status"),
                    "driver": entry.get("driver"),
                    "native_session_ref": entry.get("native_session_ref"),
                },
                "occurred_at": str(entry.get("finished_at") or entry.get("started_at") or ""),
            }
        )
    return sorted(results, key=lambda item: (-float(item["score"]), str(item["title"])))[:limit]


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
        key = _result_key(item)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return _ensure_scope_diversity(deduped, normalized_scopes, limit)


def _console_result_metadata(
    root: Path, item: dict[str, object], project_titles: dict[str, str]
) -> dict[str, object]:
    metadata = dict(item.get("metadata") or {})
    kind = str(item.get("kind") or "")

    if kind == "run_summary" and metadata.get("run_id"):
        try:
            run = _refresh_run_driver_state()(root, str(metadata["run_id"]))
            metadata.setdefault("driver", run.get("driver"))
            metadata.setdefault("status", run.get("status"))
            metadata.setdefault("health", run.get("health"))
            metadata.setdefault("project_id", run.get("project_id"))
            metadata.setdefault("task_id", run.get("task_id"))
            metadata.setdefault(
                "occurred_at",
                run.get("finished_at") or run.get("updated_at") or run.get("started_at"),
            )
        except FileNotFoundError:
            pass

    project_id = str(metadata.get("project_id") or "")
    occurred_at = str(item.get("occurred_at") or metadata.get("occurred_at") or "")
    source = _search_source(kind)
    deep_link = _search_deep_link(kind, metadata)
    open_label = _search_open_label(kind) if deep_link else None
    harness = _normalize_harness(metadata.get("driver"))
    summary = str(
        item.get("summary")
        or metadata.get("summary")
        or item.get("snippet")
        or "No preview available."
    )

    return {
        "id": str(
            metadata.get("entity_key")
            or item.get("path")
            or f"{kind}:{item.get('title') or 'result'}"
        ),
        "kind": kind,
        "source": source,
        "source_label": SEARCH_SOURCE_LABELS.get(source, source.title()),
        "title": str(item.get("title") or item.get("path") or "Result"),
        "summary": summary,
        "snippet": str(item.get("snippet") or ""),
        "preview": str(item.get("snippet") or summary),
        "why": list(item.get("why") or []),
        "matches": list(item.get("matches") or []),
        "explanation": str(item.get("explanation") or ""),
        "path": str(item.get("path") or ""),
        "score": float(item.get("score") or 0.0),
        "project_id": project_id,
        "project_label": project_titles.get(project_id, project_id or "Workspace"),
        "task_id": str(metadata.get("task_id") or (metadata.get("entity_id") if kind == "task" else "") or ""),
        "run_id": str(metadata.get("run_id") or ""),
        "campaign_id": str(metadata.get("campaign_id") or ""),
        "delegate_session_id": str(metadata.get("delegate_session_id") or ""),
        "harness": harness,
        "status": str(metadata.get("status") or ""),
        "occurred_at": occurred_at,
        "deep_link": deep_link,
        "open_label": open_label,
        "dedupe_count": 1,
        "dedupe_note": "",
        "metadata": metadata,
    }


def _matches_source_filter(kind: str, source: str | None) -> bool:
    """Map a user-facing source filter onto the internal search kinds it covers."""
    if not source:
        return True
    return kind in SOURCE_FILTER_KINDS.get(source, set())


def search_console_workspace(
    path: str | Path | None,
    query: str,
    *,
    scopes: Iterable[str] | None = None,
    limit: int = 12,
    project_id: str | None = None,
    source: str | None = None,
    harness: str | None = None,
    time_window: str | None = None,
) -> list[dict[str, object]]:
    """Return command-center search results with filters, previews, and deep links."""
    root = Path(path or Path.cwd()).resolve()
    normalized_scopes = _normalized_scopes(scopes)
    base_limit = max(limit * 4, 24)
    project_titles = _project_title_map(root)
    combined: list[dict[str, object]] = []
    combined.extend(
        search_cache_documents(
            root,
            query,
            scopes=normalized_scopes,
            limit=base_limit,
            project_id=project_id,
        )
    )
    combined.extend(_search_api_docs(query, normalized_scopes, base_limit))
    combined.extend(_search_examples(query, normalized_scopes, base_limit))
    combined.extend(_search_project_summary(root, query, normalized_scopes, base_limit))
    combined.extend(_search_campaign_records(root, query, base_limit))
    combined.extend(_search_delegate_records(root, query, base_limit))

    ranked = sorted(
        combined,
        key=lambda result: (-float(result.get("score") or 0.0), str(result.get("title") or "")),
    )
    now = datetime.now(tz=UTC)
    seen: dict[str, dict[str, object]] = {}
    ordered: list[dict[str, object]] = []
    requested_harness = _normalize_harness(harness)
    for item in ranked:
        console_item = _console_result_metadata(root, item, project_titles)
        if project_id and str(console_item["project_id"]) not in {"", project_id}:
            continue
        if not _matches_source_filter(str(console_item["kind"]), source):
            continue
        if requested_harness and _normalize_harness(console_item.get("harness")) != requested_harness:
            continue
        if not _within_time_window(str(console_item["occurred_at"]), time_window, now):
            continue
        key = f"{console_item['source']}:{console_item['id']}"
        existing = seen.get(key)
        if existing is not None:
            existing["dedupe_count"] = int(existing.get("dedupe_count") or 1) + 1
            dedupe_count = int(existing["dedupe_count"])
            existing["dedupe_note"] = f"Collapsed {dedupe_count - 1} related projection(s)."
            continue
        seen[key] = console_item
        ordered.append(console_item)
    return ordered[:limit]


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

__all__ = [
    "search_cache_documents",
    "search_console_workspace",
    "search_workspace",
    "search_workspace_corpus",
]

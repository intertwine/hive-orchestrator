"""Memory search backend."""

from __future__ import annotations

import json
from pathlib import Path

from src.hive.search import search_workspace_corpus
from src.hive.store.layout import runs_dir


def _resolve_run_artifact_path(root: Path, metadata_path: Path, value: str | None) -> Path | None:
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


def iter_accepted_runs(
    root: Path,
    *,
    project_id: str | None,
) -> list[tuple[dict[str, object], Path, Path]]:
    """Return accepted run metadata plus resolved summary paths."""
    accepted: list[tuple[dict[str, object], Path, Path]] = []
    for metadata_path in sorted(runs_dir(root).glob("*/metadata.json")):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("status") != "accepted":
            continue
        if project_id and metadata.get("project_id") != project_id:
            continue
        summary_path = _resolve_run_artifact_path(root, metadata_path, metadata.get("summary_path"))
        if summary_path is None or not summary_path.exists():
            continue
        accepted.append((metadata, metadata_path, summary_path))
    return accepted


def search(
    path: str | Path | None,
    query: str,
    *,
    scope: str = "all",
    project_id: str | None = None,
    task_id: str | None = None,
    limit: int = 8,
) -> list[dict[str, object]]:
    """Search synthesized memory plus canonical task and accepted-run context."""
    normalized_scopes = ["memory"]
    if scope in {"all", "project"}:
        normalized_scopes.extend(["task", "run"])
    if scope == "global":
        normalized_scopes = ["memory"]
    raw_limit = limit if scope == "all" else max(limit * 4, 24)
    raw_results = search_workspace_corpus(
        path,
        query,
        scopes=normalized_scopes,
        limit=raw_limit,
        project_id=project_id if scope != "global" else None,
        task_id=task_id if scope != "global" else None,
    )
    results: list[dict[str, object]] = []
    for item in raw_results:
        metadata = item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {}
        enriched = dict(item)
        if enriched.get("kind") == "memory":
            enriched["scope"] = str(metadata.get("scope") or "project")
        elif enriched.get("kind") == "run_summary":
            enriched["scope"] = "run"
        else:
            enriched["scope"] = "project"
        results.append(enriched)
    kind_priority = {"memory": 0, "run_summary": 1, "task": 2}
    results.sort(
        key=lambda item: (
            kind_priority.get(str(item.get("kind")), 9),
            -float(item.get("score", 0)),
            str(item.get("title", "")),
        )
    )
    if scope == "project":
        return [item for item in results if item.get("scope") != "global"][:limit]
    if scope == "global":
        return [item for item in results if item.get("scope") == "global"][:limit]
    return results[:limit]

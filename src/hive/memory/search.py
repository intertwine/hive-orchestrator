"""Simple memory search backend."""

from __future__ import annotations

from pathlib import Path

from src.hive.store.layout import memory_project_dir


def search(path: str | Path | None, query: str) -> list[dict[str, object]]:
    """Search project-local memory docs with simple term scoring."""
    query_lower = query.lower()
    results: list[dict[str, object]] = []
    for file_path in sorted(memory_project_dir(path).glob("*.md")):
        body = file_path.read_text(encoding="utf-8")
        score = body.lower().count(query_lower)
        if score:
            results.append(
                {
                    "path": str(file_path),
                    "title": file_path.name,
                    "score": score,
                    "snippet": body[:280],
                }
            )
    return sorted(results, key=lambda item: (-int(item["score"]), str(item["path"])))

"""Retrieval intent and trace helpers for v2.3 run artifacts."""

from __future__ import annotations

from typing import Any

_INTENT_HINTS = {
    "policy": {
        "policy",
        "program",
        "budget",
        "sandbox",
        "approval",
        "allow",
        "deny",
        "evaluator",
        "promotion",
        "review",
    },
    "history": {"history", "accepted", "previous", "recent", "summary", "retro", "past"},
    "memory": {"memory", "observation", "reflection", "profile", "context"},
    "skill": {"skill", "agent", "workflow", "playbook", "instructions"},
    "task": {"task", "fix", "implement", "ship", "deliver", "build"},
}


def classify_retrieval_intent(query: str) -> str:
    """Return a coarse retrieval intent for scoring and trace output."""
    terms = {term.casefold() for term in query.split() if term.strip()}
    best_intent = "mixed"
    best_score = 0
    for intent, hints in _INTENT_HINTS.items():
        score = len(terms & hints)
        if score > best_score:
            best_intent = intent
            best_score = score
    return best_intent


def retrieval_provenance(hit: dict[str, Any]) -> str:
    """Return a human-meaningful provenance label for one retrieval hit."""
    kind = str(hit.get("kind") or "").strip()
    path = str(hit.get("path") or "").strip()
    if kind == "program":
        return "program_policy"
    if kind == "task":
        return "canonical_task"
    if kind == "run_summary":
        return "accepted_run_summary"
    if kind == "memory":
        return "project_memory"
    if kind == "project":
        return "project_graph"
    if path.startswith("package:"):
        return "packaged_docs"
    if kind in {"api", "command", "example", "schema"}:
        return "packaged_docs"
    if kind == "workspace_doc":
        return "workspace_doc"
    return "workspace_search"


def retrieval_explanation(hit: dict[str, Any]) -> str:
    """Collapse the existing search reasons into one explanation string."""
    reasons = hit.get("why") or hit.get("matches") or []
    if isinstance(reasons, list):
        text = "; ".join(str(reason).strip() for reason in reasons if str(reason).strip())
        if text:
            return text
    snippet = str(hit.get("snippet") or "").strip()
    if snippet:
        return snippet
    return f"matched {str(hit.get('kind') or 'workspace')} search content"


def _candidate_sources(hit: dict[str, Any]) -> list[str]:
    """Derive retrieval source tags for a candidate hit."""
    kind = str(hit.get("kind") or "")
    if kind == "project":
        return ["graph"]
    sources = ["lexical"]
    if hit.get("dense_match"):
        sources.append("dense")
    return sources


def build_retrieval_artifacts(
    query: str,
    *,
    selected_hits: list[dict[str, Any]],
    candidate_hits: list[dict[str, Any]] | None = None,
    dense_candidate_count: int = 0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build normalized retrieval hits and trace payloads for a run."""
    candidates = list(candidate_hits or selected_hits)
    selected = list(selected_hits)
    intent = classify_retrieval_intent(query)
    selected_ids = {
        str(hit.get("path") or hit.get("title") or index)
        for index, hit in enumerate(selected)
    }
    graph_candidates = sum(1 for hit in candidates if str(hit.get("kind") or "") == "project")
    normalized_candidates = [
        {
            "chunk_id": str(hit.get("path") or hit.get("title") or index),
            "kind": str(hit.get("kind") or "unknown"),
            "title": str(hit.get("title") or hit.get("path") or "result"),
            "path": hit.get("path"),
            "score": float(hit.get("score") or 0.0),
            "explanation": retrieval_explanation(hit),
            "provenance": retrieval_provenance(hit) or "workspace_search",
        }
        for index, hit in enumerate(candidates)
    ]
    hits_payload = {
        "query": query,
        "intent": intent,
        "candidate_count": len(normalized_candidates),
        "selected_count": len(selected),
        "results": normalized_candidates,
    }
    trace_payload = {
        "query": query,
        "intent": intent,
        "candidate_counts": {
            "lexical": len(normalized_candidates),
            "dense": dense_candidate_count,
            "graph": graph_candidates,
        },
        "fused": [
            {
                "chunk_id": item["chunk_id"],
                "kind": item["kind"],
                "sources": _candidate_sources(candidates[index] if index < len(candidates) else {}),
                "pre_rerank_rank": index + 1,
                "explanation": item["explanation"],
                "provenance": item["provenance"],
            }
            for index, item in enumerate(normalized_candidates)
        ],
        "reranked": [
            {
                "chunk_id": item["chunk_id"],
                "kind": item["kind"],
                "rank": index + 1,
                "score": item["score"],
                "explanation": item["explanation"],
                "provenance": item["provenance"],
            }
            for index, item in enumerate(normalized_candidates)
        ],
        "selected_context": [
            {
                "chunk_id": item["chunk_id"],
                "kind": item["kind"],
                "title": item["title"],
                "path": item["path"],
                "explanation": item["explanation"],
                "provenance": item["provenance"],
            }
            for item in normalized_candidates
            if item["chunk_id"] in selected_ids
        ],
        "dropped": [
            {
                "chunk_id": item["chunk_id"],
                "kind": item["kind"],
                "title": item["title"],
                "path": item["path"],
                "explanation": item["explanation"],
                "provenance": item["provenance"],
            }
            for item in normalized_candidates
            if item["chunk_id"] not in selected_ids
        ],
    }
    return hits_payload, trace_payload

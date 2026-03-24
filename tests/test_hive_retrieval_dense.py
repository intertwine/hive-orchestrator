"""Tests for hybrid dense retrieval (LanceDB + FastEmbed)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.hive.retrieval.dense import (
    DenseDoc,
    DenseScoredHit,
    is_dense_available,
)


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------


def test_is_dense_available_reflects_import_status():
    """is_dense_available returns a boolean without crashing."""
    result = is_dense_available()
    assert isinstance(result, bool)


def test_is_dense_available_returns_false_when_deps_missing():
    """When fastembed or lancedb cannot be imported, the flag is False."""
    import src.hive.retrieval.dense as mod

    original = mod._available
    try:
        mod._available = None
        with patch.dict("sys.modules", {"fastembed": None}):
            mod._available = None
            assert not mod.is_dense_available()
    finally:
        mod._available = original


# ---------------------------------------------------------------------------
# Graceful degradation in search
# ---------------------------------------------------------------------------


def test_search_cache_documents_works_without_dense_deps(temp_hive_dir, temp_project):
    """search_cache_documents must return results even when dense deps are absent."""
    from src.hive.search import search_cache_documents

    results = search_cache_documents(Path(temp_hive_dir), "test")
    assert isinstance(results, list)


# ---------------------------------------------------------------------------
# Retrieval trace dense count
# ---------------------------------------------------------------------------


def test_retrieval_trace_accepts_dense_candidate_count():
    """build_retrieval_artifacts passes through the dense count."""
    from src.hive.retrieval_trace import build_retrieval_artifacts

    hits_payload, trace_payload = build_retrieval_artifacts(
        "test query",
        selected_hits=[{"kind": "task", "title": "Task A", "score": 10}],
        dense_candidate_count=5,
    )
    assert trace_payload["candidate_counts"]["dense"] == 5


def test_retrieval_trace_dense_zero_by_default():
    """When dense_candidate_count is omitted, dense count is 0."""
    from src.hive.retrieval_trace import build_retrieval_artifacts

    _, trace_payload = build_retrieval_artifacts(
        "test query",
        selected_hits=[{"kind": "task", "title": "Task A", "score": 10}],
    )
    assert trace_payload["candidate_counts"]["dense"] == 0


def test_retrieval_trace_source_includes_dense_for_dense_matches():
    """Fused items should include 'dense' in sources when dense_match is set."""
    from src.hive.retrieval_trace import build_retrieval_artifacts

    candidate = {"kind": "task", "title": "Task A", "score": 10, "dense_match": True}
    _, trace_payload = build_retrieval_artifacts(
        "test query",
        selected_hits=[candidate],
        candidate_hits=[candidate],
        dense_candidate_count=1,
    )
    fused = trace_payload["fused"]
    assert len(fused) == 1
    assert "dense" in fused[0]["sources"]


# ---------------------------------------------------------------------------
# Dense module unit tests (only run when deps are available)
# ---------------------------------------------------------------------------

_dense_available = is_dense_available()


@pytest.mark.skipif(not _dense_available, reason="lancedb/fastembed not installed")
class TestDenseWithDeps:
    """Tests that require lancedb + fastembed to be installed."""

    def test_build_dense_index_creates_vectors_dir(self, tmp_path):
        from src.hive.retrieval.dense import build_dense_index

        docs = [
            DenseDoc("task:t1", "task", "Fix auth bug", "The auth module has a null check issue"),
            DenseDoc("task:t2", "task", "Add search", "Implement full-text search with SQLite"),
            DenseDoc("memory:m1", "memory", "Reflection", "The team prefers semantic search"),
        ]
        count = build_dense_index(tmp_path, docs)
        assert count == 3
        assert (tmp_path / "vectors").exists()

    def test_search_dense_returns_results(self, tmp_path):
        from src.hive.retrieval.dense import build_dense_index, search_dense

        docs = [
            DenseDoc("task:t1", "task", "Fix auth bug", "The auth module has a null check issue"),
            DenseDoc("task:t2", "task", "Add search", "Implement full-text search with SQLite"),
            DenseDoc("memory:m1", "memory", "Reflection", "The team prefers semantic search"),
        ]
        build_dense_index(tmp_path, docs)
        results = search_dense(tmp_path, "semantic search", limit=3)
        assert len(results) > 0
        assert all(isinstance(r, DenseScoredHit) for r in results)
        # Semantic match: "semantic search" should rank memory:m1 or task:t2 higher
        doc_ids = [r.doc_id for r in results]
        assert any("t2" in did or "m1" in did for did in doc_ids)

    def test_search_dense_returns_empty_when_no_index(self, tmp_path):
        from src.hive.retrieval.dense import search_dense

        results = search_dense(tmp_path, "anything")
        assert results == []

    def test_rerank_candidates_reorders(self):
        from src.hive.retrieval.dense import rerank_candidates

        candidates = [
            ("doc1", "The cat sat on the mat"),
            ("doc2", "Vector databases enable semantic search over documents"),
            ("doc3", "Python is a programming language"),
        ]
        ranked = rerank_candidates("semantic search", candidates)
        assert len(ranked) == 3
        # doc2 should score highest for "semantic search"
        assert ranked[0][0] == "doc2"

    def test_build_dense_index_empty_list(self, tmp_path):
        from src.hive.retrieval.dense import build_dense_index

        count = build_dense_index(tmp_path, [])
        assert count == 0

    def test_build_dense_index_skips_when_corpus_unchanged(self, tmp_path):
        from src.hive.retrieval.dense import build_dense_index

        docs = [
            DenseDoc("task:t1", "task", "Fix auth bug", "The auth module has a null check issue"),
            DenseDoc("task:t2", "task", "Add search", "Implement full-text search with SQLite"),
        ]
        first = build_dense_index(tmp_path, docs)
        assert first == 2
        # Second build with same docs should skip (returns 0)
        second = build_dense_index(tmp_path, docs)
        assert second == 0

    def test_build_dense_index_rebuilds_when_doc_added(self, tmp_path):
        from src.hive.retrieval.dense import build_dense_index

        docs = [DenseDoc("task:t1", "task", "Fix auth bug", "Null check issue")]
        build_dense_index(tmp_path, docs)
        # Add a new doc — corpus changed, should rebuild
        docs.append(DenseDoc("task:t2", "task", "Add search", "Full-text search"))
        count = build_dense_index(tmp_path, docs)
        assert count == 2

    def test_build_dense_index_rebuilds_when_doc_content_changes(self, tmp_path):
        """Editing a doc's title or body must invalidate the dense index."""
        from src.hive.retrieval.dense import build_dense_index

        docs = [DenseDoc("task:t1", "task", "Fix auth bug", "Null check issue")]
        assert build_dense_index(tmp_path, docs) == 1
        # Same doc_id, different body — must rebuild
        edited = [DenseDoc("task:t1", "task", "Fix auth bug", "The session token is expired")]
        assert build_dense_index(tmp_path, edited) == 1
        # Same doc_id, different title — must rebuild
        retitled = [DenseDoc("task:t1", "task", "Fix session expiry", "The session token is expired")]
        assert build_dense_index(tmp_path, retitled) == 1
        # Unchanged — must skip
        assert build_dense_index(tmp_path, retitled) == 0

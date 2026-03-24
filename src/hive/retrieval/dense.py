"""Dense vector retrieval via LanceDB + FastEmbed.

Optional layer that activates when ``lancedb`` and ``fastembed`` are installed.
All imports are lazy so the module can be loaded even without the dependencies.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any, NamedTuple

logger = logging.getLogger(__name__)

EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"
RERANKER_MODEL_NAME = "Xenova/ms-marco-MiniLM-L-6-v2"
TABLE_NAME = "search_docs"
VECTORS_DIR = "vectors"


class DenseDoc(NamedTuple):
    doc_id: str
    doc_type: str
    title: str
    body: str


class DenseScoredHit(NamedTuple):
    doc_id: str
    distance: float


# ---------------------------------------------------------------------------
# Availability check
# ---------------------------------------------------------------------------

_available: bool | None = None


def is_dense_available() -> bool:
    """Return True if lancedb and fastembed are both importable."""
    global _available  # noqa: PLW0603
    if _available is None:
        try:
            import fastembed  # noqa: F401
            import lancedb  # noqa: F401

            _available = True
        except ImportError:
            _available = False
    return _available


# ---------------------------------------------------------------------------
# Singleton model holders — initialised on first use
# ---------------------------------------------------------------------------

_embed_model: Any = None
_reranker: Any = None


def _get_embed_model() -> Any:
    global _embed_model  # noqa: PLW0603
    if _embed_model is None:
        from fastembed import TextEmbedding

        _embed_model = TextEmbedding(model_name=EMBED_MODEL_NAME)
    return _embed_model


def _get_reranker() -> Any:
    global _reranker  # noqa: PLW0603
    if _reranker is None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        _reranker = TextCrossEncoder(model_name=RERANKER_MODEL_NAME)
    return _reranker


# ---------------------------------------------------------------------------
# Index build
# ---------------------------------------------------------------------------


CORPUS_HASH_FILE = ".corpus_hash"


def _corpus_fingerprint(documents: list[DenseDoc]) -> str:
    """Compute a lightweight fingerprint of the document set.

    Uses sorted doc_ids so the fingerprint is stable regardless of insertion order.
    """
    hasher = hashlib.sha256()
    for doc_id in sorted(doc.doc_id for doc in documents):
        hasher.update(doc_id.encode())
    return hasher.hexdigest()


def _read_stored_fingerprint(cache_dir: Path) -> str | None:
    marker = cache_dir / VECTORS_DIR / CORPUS_HASH_FILE
    if marker.exists():
        return marker.read_text(encoding="utf-8").strip()
    return None


def _write_fingerprint(cache_dir: Path, fingerprint: str) -> None:
    marker = cache_dir / VECTORS_DIR / CORPUS_HASH_FILE
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(fingerprint, encoding="utf-8")


def build_dense_index(
    cache_dir: Path,
    documents: list[DenseDoc],
) -> int:
    """Embed *documents* and write a LanceDB table to *cache_dir*/*VECTORS_DIR*.

    Returns the number of documents indexed, or 0 if the index is already fresh.
    Skips the expensive embedding step when the document set has not changed
    (detected via a SHA-256 fingerprint of sorted doc IDs).
    """
    import lancedb

    if not documents:
        return 0

    fingerprint = _corpus_fingerprint(documents)
    if _read_stored_fingerprint(cache_dir) == fingerprint:
        logger.debug("Dense index is fresh (fingerprint unchanged), skipping rebuild")
        return 0

    model = _get_embed_model()
    texts = [f"{doc.title}\n{doc.body}" for doc in documents]
    vectors = list(model.embed(texts))

    data = [
        {
            "doc_id": doc.doc_id,
            "doc_type": doc.doc_type,
            "text": texts[i][:512],  # store truncated text for debug
            "vector": vectors[i].tolist(),
        }
        for i, doc in enumerate(documents)
    ]

    vectors_path = cache_dir / VECTORS_DIR
    db = lancedb.connect(str(vectors_path))
    db.create_table(TABLE_NAME, data, mode="overwrite")
    _write_fingerprint(cache_dir, fingerprint)
    logger.info("Dense index built: %d documents in %s", len(documents), vectors_path)
    return len(documents)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def search_dense(
    cache_dir: Path,
    query: str,
    *,
    limit: int = 24,
) -> list[DenseScoredHit]:
    """Return the nearest *limit* documents by vector similarity."""
    import lancedb

    vectors_path = cache_dir / VECTORS_DIR
    if not vectors_path.exists():
        return []

    model = _get_embed_model()
    query_vec = list(model.query_embed([query]))[0]

    db = lancedb.connect(str(vectors_path))
    try:
        table = db.open_table(TABLE_NAME)
    except Exception:
        return []

    results = table.search(query_vec.tolist()).limit(limit).to_list()
    return [
        DenseScoredHit(doc_id=row["doc_id"], distance=float(row["_distance"]))
        for row in results
    ]


# ---------------------------------------------------------------------------
# Reranking
# ---------------------------------------------------------------------------


def rerank_candidates(
    query: str,
    candidates: list[tuple[str, str]],
) -> list[tuple[str, float]]:
    """Cross-encoder rerank *candidates* against *query*.

    *candidates* is a list of ``(doc_id, text)`` pairs.
    Returns ``(doc_id, relevance_score)`` sorted by score descending.
    """
    if not candidates:
        return []
    reranker = _get_reranker()
    doc_ids = [cid for cid, _ in candidates]
    texts = [text for _, text in candidates]
    scores = list(reranker.rerank(query, texts))
    paired = list(zip(doc_ids, scores))
    paired.sort(key=lambda pair: pair[1], reverse=True)
    return paired

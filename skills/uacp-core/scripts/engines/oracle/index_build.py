"""Oracle index-build path — turn the OKF corpus into a vector+FTS index.

This is the WRITE/BUILD counterpart to the read pipeline (``pipeline.py``).
``build_index`` loads the on-disk OKF corpus (lessons + knowledge) via
``corpus_io``, embeds each item's canonical text through the resolved embedding
serving, assembles store rows whose schema matches exactly what the read path
(``dense_search`` / ``fts_search`` / ``_row_to_dict`` -> the pipeline + packets)
expects, and ``upsert``s them into the configured ``VectorStore``.

Why a dedicated module (not store.py / pipeline.py):
  * ``store.py`` stays a backend-pure thin protocol impl (no corpus knowledge).
  * ``pipeline.py`` is the pure READ orchestration (never writes).
  * The build is the only place that crosses corpus-shape -> store-row-shape and
    pulls in embedding serving, so it gets its own home.

Floor / degrade philosophy (mirrors the rest of the Oracle):
  * Heavy deps are lazily reached only through the embedding client + store,
    which are themselves dep-gated. This module imports clean on the floor.
  * When the embedding serving resolves to FLOOR (oracle disabled, no URL, no
    embedded binding) there is NO vector to build, so we DO NOT build an index:
    ``build_index`` returns 0 and logs a reason. The floor retrieval path uses
    keyword + structured + BES with no vector index, so this is a clean no-op,
    not an error.
  * When the store dep (lancedb) is absent, ``store.upsert`` raises
    ``StoreUnavailable``; we surface that as ``IndexBuildUnavailable``.

ROW SCHEMA (canonical — must match the read path)
-------------------------------------------------
Each upserted row is a flat dict::

    {
      "id":         str,            # corpus item id (primary/merge key)
      "type":       str,            # "lesson" | pattern|digest|analysis|contract
      "text":       str,            # canonical text: title + body (embedded + FTS'd)
      "vector":     list[float],    # dense embedding of "text"
      "domains":    list[str],      # for the BES relevance gate
      "invariants": list[str],      # for the BES relevance gate (lessons)
      "bes":        float,          # BES score (lessons; 0.5 default for knowledge)
      "severity":   str,            # lesson severity (knowledge -> "")
      "eligible":   int,            # lesson eligibility count (knowledge -> 0)
      "source":     str,            # source kind: "lesson" | "knowledge"
      "source_path": str,           # relative-or-absolute disk path of the OKF file
    }

The ``text`` field is BOTH what the dense leg embeds at build time AND what the
native FTS index covers AND what a reranker scores against — one canonical text
per item keeps build and retrieval consistent.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from engines.domain.corpus import KnowledgeItem, Lesson
from engines.oracle.corpus_io import load_knowledge_dir, load_lessons_dir
from engines.oracle.serving import RoleServing, ServingMode

logger = logging.getLogger(__name__)


class IndexBuildUnavailable(RuntimeError):
    """Raised when the index cannot be built (store dep absent / embed failure)."""


def item_text(item: Lesson | KnowledgeItem) -> str:
    """Canonical text for an OKF item: title + body, whitespace-normalised.

    This is the single text used for BOTH dense embedding and FTS indexing, so
    build-time and query-time stay consistent. Title is included so a one-line
    lesson/knowledge title still embeds meaningfully even with a short body.
    """
    title = (item.title or "").strip()
    body = (item.body or "").strip()
    if title and body:
        return f"{title}\n\n{body}"
    return title or body


def _lesson_row(lesson: Lesson, vector: list[float], path: Path) -> dict[str, Any]:
    return {
        "id": lesson.id,
        "type": "lesson",
        "text": item_text(lesson),
        "vector": vector,
        "domains": list(lesson.domains),
        "invariants": list(lesson.invariants),
        "bes": float(lesson.bes),
        "severity": str(lesson.severity),
        "eligible": int(lesson.eligible),
        "source": "lesson",
        "source_path": str(path),
    }


def _knowledge_row(item: KnowledgeItem, vector: list[float], path: Path) -> dict[str, Any]:
    return {
        "id": item.id,
        "type": str(item.type),
        "text": item_text(item),
        "vector": vector,
        "domains": list(item.domains),
        "invariants": [],  # knowledge items carry no invariants
        "bes": 0.5,  # knowledge skips BES; keep the column present + uniform
        "severity": "",
        "eligible": 0,
        "source": "knowledge",
        "source_path": str(path),
    }


def _embedding_serving(root: Path, embedding_serving: RoleServing | None) -> RoleServing:
    """Resolve the embedding serving: explicit arg wins, else from workspace config."""
    if embedding_serving is not None:
        return embedding_serving
    try:
        from config import get_config
        from engines.oracle.serving import resolve_role

        oracle_cfg = get_config(root).model_extra.get("oracle", {}) or {}
        return resolve_role("embedding", oracle_cfg)
    except Exception:
        return RoleServing("embedding", ServingMode.FLOOR)


def build_index(
    root: Path,
    *,
    embedding_serving: RoleServing | None = None,
    backend: str = "lancedb",
    index_path: Path | str | None = None,
    lessons_dirname: str = "lessons",
    knowledge_dirname: str = "knowledge",
) -> int:
    """Build (or refresh) the Oracle vector+FTS index from the OKF corpus.

    Args:
        root: workspace ``.uacp`` directory holding ``lessons/`` and
            ``knowledge/`` (the corpus roots). The index is written under
            ``<root>/knowledge/indexes/`` unless ``index_path`` overrides it.
        embedding_serving: explicit embedding ``RoleServing``. When ``None`` it
            is resolved from the workspace config (``resolve_role("embedding")``).
            A FLOOR serving means NO index is built (returns 0).
        backend: store backend name (``"lancedb"`` default).
        index_path: override the index directory (defaults to
            ``<root>/knowledge/indexes``).
        lessons_dirname / knowledge_dirname: corpus subdir names under ``root``.

    Returns:
        Number of items indexed (0 when the corpus is empty or embedding is on
        the FLOOR — both clean no-ops, not errors).

    Raises:
        IndexBuildUnavailable: when the store dependency is absent or embedding
            of the corpus fails for a non-FLOOR serving (a real failure, not a
            graceful degrade).
    """
    root = Path(root)
    serving = _embedding_serving(root, embedding_serving)

    if serving.mode is ServingMode.FLOOR:
        logger.info(
            "oracle index build skipped: embedding serving is FLOOR "
            "(keyword + BES floor needs no vector index)"
        )
        return 0

    lessons = load_lessons_dir(root / lessons_dirname)
    knowledge = load_knowledge_dir(root / knowledge_dirname)
    items: list[tuple[Lesson | KnowledgeItem, str, Path]] = []
    for lesson in lessons:
        items.append((lesson, "lesson", root / lessons_dirname / f"{lesson.id}.md"))
    for k in knowledge:
        items.append((k, "knowledge", root / knowledge_dirname / f"{k.id}.md"))

    if not items:
        logger.info("oracle index build: corpus is empty, nothing to index")
        return 0

    texts = [item_text(item) for item, _kind, _path in items]

    # Embed every item's canonical text through the resolved serving.
    from engines.oracle.clients.embedding import EmbeddingUnavailable, embed_texts

    try:
        vectors = embed_texts(texts, serving)
    except EmbeddingUnavailable as exc:
        raise IndexBuildUnavailable(f"embedding unavailable for index build: {exc}") from exc

    if len(vectors) != len(items):
        raise IndexBuildUnavailable(
            f"embedding returned {len(vectors)} vectors for {len(items)} items"
        )

    rows: list[dict[str, Any]] = []
    for (item, kind, path), vector in zip(items, vectors, strict=True):
        vec = [float(x) for x in vector]
        if kind == "lesson":
            rows.append(_lesson_row(item, vec, path))  # type: ignore[arg-type]
        else:
            rows.append(_knowledge_row(item, vec, path))  # type: ignore[arg-type]

    # Resolve the store + upsert. Store dep absent -> StoreUnavailable.
    from engines.oracle.store import StoreUnavailable, get_store

    if index_path is None:
        index_path = root / "knowledge" / "indexes"
    try:
        store = get_store(backend, index_path=str(index_path))
        store.upsert(rows)
    except StoreUnavailable as exc:
        raise IndexBuildUnavailable(f"vector store unavailable for index build: {exc}") from exc

    logger.info("oracle index built: %d items indexed at %s", len(rows), index_path)
    return len(rows)

"""Oracle semantic pipeline: hybrid(dense+keyword) → RRF → rerank → BES overlay.

QMD-shaped retrieval pipeline for the Oracle semantic leg. Pure orchestration;
never raises to the caller (degrade to fewer stages / empty list on any error).

Lazy imports only — the floor must import and run clean with lancedb, llama_cpp,
and httpx all absent. The store.available() gate is the single dep check.

Pipeline steps:
  1. Dense retrieval  (only when embedding is usable; else skip dense leg)
  2. FTS / keyword retrieval
  3. RRF fusion        (k=60, canonical QMD constant)
  4. Rerank            (via reranker if usable; RerankUnavailable -> keep RRF order)
  5. BES overlay       (lessons only: gate relevance>=1, then rank by relevance + bes_bonus)
     Knowledge items skip BES; they pass through as normative packets.
"""

from __future__ import annotations

from typing import Any

from engines.domain.corpus import bes_bonus
from engines.oracle.packets import ProviderPacket, TrustClass

# ---------------------------------------------------------------------------
# RRF fusion (pure, testable independently)
# ---------------------------------------------------------------------------


def rrf_fuse(
    dense: list[dict[str, Any]],
    fts: list[dict[str, Any]],
    *,
    k: int = 60,
) -> list[dict[str, Any]]:
    """Reciprocal Rank Fusion over two ranked lists.

    Each document is identified by its ``id`` field. When ``id`` is absent the
    whole dict is used as a key (so that tests with id-less dicts still work,
    though callers should always include id).

    Returns a deduplicated list ordered by descending RRF score.
    """
    scores: dict[Any, float] = {}
    index: dict[Any, dict[str, Any]] = {}

    for rank, doc in enumerate(dense):
        key = doc.get("id", id(doc))
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        index.setdefault(key, doc)

    for rank, doc in enumerate(fts):
        key = doc.get("id", id(doc))
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        index.setdefault(key, doc)

    ordered = sorted(scores.keys(), key=lambda key: scores[key], reverse=True)
    return [index[key] for key in ordered]


# ---------------------------------------------------------------------------
# BES overlay (lessons only, pure)
# ---------------------------------------------------------------------------

_KNOWLEDGE_TYPES = frozenset(("pattern", "digest", "analysis", "contract"))


def _relevance(
    doc: dict[str, Any],
    query_domains: list[str],
    query_invariants: list[str],
) -> int:
    """Compute relevance score for a lesson document (pure).

    Scoring:
      +1 per matching domain
      +2 per matching invariant

    The ``+3 affected_path`` term described in early design notes is not
    implemented: corpus docs do not carry a consistent ``affected_path`` field
    and the query string is not pre-tokenised into paths here. If the corpus
    schema adds that field, wire it as ``+3 * len(doc_paths & query_paths)``.

    Returns 0 when there is no overlap (gate: relevance >= 1 to include).
    """
    doc_domains = set(doc.get("domains") or [])
    doc_invariants = set(doc.get("invariants") or [])
    q_domains = set(query_domains or [])
    q_invariants = set(query_invariants or [])

    score = len(doc_domains & q_domains) + 2 * len(doc_invariants & q_invariants)
    return score


def apply_bes_overlay(
    docs: list[dict[str, Any]],
    *,
    query_domains: list[str],
    query_invariants: list[str],
) -> list[tuple[float, dict[str, Any]]]:
    """Apply BES/tag overlay and return (composite_score, doc) pairs.

    Lessons: gate relevance >= 1, then composite = relevance + bes_bonus().
    Knowledge: pass through with a composite score of 1.0 (no BES).
    Docs of unknown type: treated like knowledge (pass through).

    The list is sorted descending by composite score.
    """
    scored: list[tuple[float, dict[str, Any]]] = []

    for doc in docs:
        doc_type = doc.get("type", "")

        if doc_type == "lesson":
            rel = _relevance(doc, query_domains, query_invariants)
            if rel < 1:
                continue  # gate: no relevance -> exclude
            bonus = bes_bonus(
                bes=float(doc.get("bes", 0.5)),
                severity=str(doc.get("severity", "MEDIUM")),
                eligible=int(doc.get("eligible", 0)),
            )
            composite = float(rel + bonus)
            scored.append((composite, doc))
        else:
            # Knowledge / unknown type: pass through, no BES filter
            scored.append((1.0, doc))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------


def semantic_retrieve(
    query: str,
    store: Any,
    *,
    domains: list[str] | None = None,
    invariants: list[str] | None = None,
    embedding: Any | None = None,
    reranker: Any | None = None,
    k: int = 60,
) -> list[ProviderPacket]:
    """Run the full QMD-shaped semantic pipeline.

    Args:
        query:      Search query string.
        store:      A VectorStore instance (must implement available(),
                    dense_search(), fts_search(), rrf_hybrid()).
        domains:    Optional domain filter for BES overlay.
        invariants: Optional invariant filter for BES overlay.
        embedding:  Optional embedding callable with .embed(texts) -> vectors.
                    When None or unavailable, the dense leg is skipped.
        reranker:   Optional reranker with .rerank(query, docs) -> docs.
                    When None or unavailable, RRF order is kept.
        k:          RRF k constant (default 60).

    Returns:
        Ranked list of ProviderPackets. Empty list on any unrecoverable error.
        Never raises.
    """
    if not store.available():
        return []

    _domains = list(domains or [])
    _invariants = list(invariants or [])

    try:
        # Step 1: Dense leg (only when embedding is usable)
        dense_results: list[dict[str, Any]] = []
        if embedding is not None:
            try:
                vectors = embedding.embed([query])
                if vectors:
                    dense_results = store.dense_search(vectors[0], k)
            except Exception:
                dense_results = []

        # Step 2: FTS / keyword leg
        try:
            fts_results = store.fts_search(query, k)
        except Exception:
            fts_results = []

        # Step 3: RRF fusion
        fused = rrf_fuse(dense_results, fts_results, k=k)

        # Step 4: Rerank (degrade to RRF order on any failure)
        if reranker is not None and fused:
            try:
                reranked = reranker.rerank(query, fused)
                fused = reranked
            except Exception:
                pass  # keep RRF order

        # Step 5: BES overlay
        scored = apply_bes_overlay(fused, query_domains=_domains, query_invariants=_invariants)

        # Convert to ProviderPackets
        packets: list[ProviderPacket] = []
        for _score, doc in scored:
            doc_type = doc.get("type", "")
            if doc_type == "lesson":
                trust = TrustClass.advisory
            else:
                trust = TrustClass.normative
            packets.append(
                ProviderPacket(
                    source="corpus",
                    trust_class=trust,
                    payload=doc,
                    score=_score,
                )
            )

        return packets

    except Exception:
        return []

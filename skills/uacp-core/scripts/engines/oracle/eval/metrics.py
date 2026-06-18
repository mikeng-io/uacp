"""Pure metric functions for the reranker bake-off harness (Task 14).

No ML deps, no I/O. Usable in unit tests with known inputs/expected outputs.

Functions
---------
ndcg_at_k(ranked_ids, relevant_ids, k)
    Normalised Discounted Cumulative Gain at cut-off k.
mrr(ranked_ids, relevant_ids)
    Mean Reciprocal Rank (single-query variant).
latency_percentile(timings, p)
    p-th percentile of a list of latency timings (seconds or ms).
    Supports p=50 (median) and p=95 as the primary use-cases.
"""

from __future__ import annotations

import math
from collections.abc import Collection


def ndcg_at_k(
    ranked_ids: list[str],
    relevant_ids: Collection[str],
    k: int,
) -> float:
    """Compute nDCG@k.

    Parameters
    ----------
    ranked_ids:
        Ordered list of document IDs produced by the reranker (best first).
    relevant_ids:
        Set (or any collection) of IDs that are truly relevant for this query.
    k:
        Cut-off rank.  Only the top-k items of ``ranked_ids`` are considered.
        If k <= 0, returns 0.0.  If k > len(ranked_ids), uses the full list.

    Returns
    -------
    float in [0.0, 1.0].  Returns 0.0 when ``relevant_ids`` is empty (ideal
    DCG is 0, so nDCG is undefined; we define it as 0 to keep callers simple).
    """
    if k <= 0 or not relevant_ids or not ranked_ids:
        return 0.0

    rel_set = set(relevant_ids)
    top_k = ranked_ids[:k]

    # DCG of the ranked list
    dcg = sum(
        1.0 / math.log2(rank + 2)  # rank is 0-indexed; log2(1+1)=1 for rank 0
        for rank, doc_id in enumerate(top_k)
        if doc_id in rel_set
    )

    # Ideal DCG: the best possible ordering — place all relevant docs first
    ideal_hits = min(len(rel_set), k)
    idcg = sum(1.0 / math.log2(rank + 2) for rank in range(ideal_hits))

    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def mrr(
    ranked_ids: list[str],
    relevant_ids: Collection[str],
) -> float:
    """Compute Mean Reciprocal Rank (single-query form: just Reciprocal Rank).

    Returns 1 / rank_of_first_relevant_doc (1-indexed), or 0.0 if no relevant
    doc appears in the ranked list or if either input is empty.
    """
    if not ranked_ids or not relevant_ids:
        return 0.0
    rel_set = set(relevant_ids)
    for rank, doc_id in enumerate(ranked_ids, start=1):
        if doc_id in rel_set:
            return 1.0 / rank
    return 0.0


def latency_percentile(timings: list[float], p: float | int) -> float:
    """Return the p-th percentile of ``timings``.

    Uses linear interpolation (the same method as ``numpy.percentile`` with
    ``method='linear'``), implemented with pure stdlib so no NumPy is required.

    Parameters
    ----------
    timings:
        List of latency measurements (any consistent unit: seconds, ms, …).
        Does not need to be sorted.
    p:
        Percentile in [0, 100].  Typical values: 50 (median) and 95.

    Returns
    -------
    float. Returns 0.0 for an empty list.
    """
    if not timings:
        return 0.0

    sorted_t = sorted(timings)
    n = len(sorted_t)

    if n == 1:
        return float(sorted_t[0])

    # Linear interpolation: index = p/100 * (n-1)
    index = (float(p) / 100.0) * (n - 1)
    lo = int(math.floor(index))
    hi = int(math.ceil(index))
    if lo == hi:
        return float(sorted_t[lo])

    frac = index - lo
    return float(sorted_t[lo]) + frac * (float(sorted_t[hi]) - float(sorted_t[lo]))

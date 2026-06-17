"""Tests for the reranker bake-off metric module (Task 14a — pure functions).

All functions are pure — no models, no network, no ML deps required.
"""
from __future__ import annotations

import math


from engines.oracle.eval.metrics import mrr, ndcg_at_k, latency_percentile


# ---------------------------------------------------------------------------
# ndcg_at_k
# ---------------------------------------------------------------------------


def test_ndcg_perfect_ranking_is_one():
    # Plan-specified: ranked ids vs relevant set, perfect = 1.0
    assert round(ndcg_at_k(["a", "b", "c"], {"a", "b"}, k=3), 6) == 1.0


def test_ndcg_worse_ranking_is_lower():
    good = ndcg_at_k(["a", "b", "c"], {"a"}, k=3)
    bad = ndcg_at_k(["c", "b", "a"], {"a"}, k=3)
    assert good > bad


def test_ndcg_no_relevant_docs_is_zero():
    # Edge case: relevant set empty → nDCG undefined; return 0.0 (not NaN)
    assert ndcg_at_k(["a", "b", "c"], set(), k=3) == 0.0


def test_ndcg_none_in_ranked_list_are_relevant():
    # None of the ranked docs is relevant
    assert ndcg_at_k(["x", "y", "z"], {"a", "b"}, k=3) == 0.0


def test_ndcg_k_larger_than_list_uses_full_list():
    # k=10 but only 2 items: should not crash, just use what's there
    result = ndcg_at_k(["a", "b"], {"a"}, k=10)
    assert 0.0 <= result <= 1.0


def test_ndcg_k_equals_one_first_hit():
    # k=1: only first position matters
    assert ndcg_at_k(["a", "b", "c"], {"a"}, k=1) == 1.0
    assert ndcg_at_k(["b", "a", "c"], {"a"}, k=1) == 0.0


def test_ndcg_k_equals_zero_returns_zero():
    # Degenerate: k=0 → 0.0, no crash
    assert ndcg_at_k(["a", "b"], {"a"}, k=0) == 0.0


def test_ndcg_empty_ranked_list_is_zero():
    assert ndcg_at_k([], {"a"}, k=5) == 0.0


def test_ndcg_single_relevant_at_rank_two():
    # DCG = 1/log2(3); IDCG = 1/log2(2) = 1.0; nDCG = 1/log2(3)
    expected = 1.0 / math.log2(3)
    assert abs(ndcg_at_k(["x", "a", "b"], {"a"}, k=3) - expected) < 1e-9


# ---------------------------------------------------------------------------
# mrr
# ---------------------------------------------------------------------------


def test_mrr_first_relevant_at_rank_two():
    # Plan-specified
    assert mrr(["x", "a", "b"], {"a"}) == 0.5  # first relevant at rank 2


def test_mrr_first_position():
    assert mrr(["a"], {"a"}) == 1.0


def test_mrr_no_relevant_in_list():
    assert mrr(["x", "y"], {"a"}) == 0.0


def test_mrr_multiple_relevant_uses_first_hit():
    # MRR: only the rank of the FIRST relevant doc matters
    # "b" is at rank 1 (1-indexed), "a" at rank 2 → MRR = 1.0
    assert mrr(["b", "a", "c"], {"a", "b"}) == 1.0


def test_mrr_empty_ranked_list_is_zero():
    assert mrr([], {"a"}) == 0.0


def test_mrr_empty_relevant_set_is_zero():
    assert mrr(["a", "b"], set()) == 0.0


# ---------------------------------------------------------------------------
# latency_percentile helper (p50 / p95)
# ---------------------------------------------------------------------------


def test_p50_single_value():
    assert latency_percentile([42.0], 50) == 42.0


def test_p95_standard_list():
    timings = list(range(1, 21))  # [1..20]
    p95 = latency_percentile(timings, 95)
    # p95 of [1..20] ≈ 19.something
    assert 19.0 <= p95 <= 20.0


def test_p50_even_list():
    # Median of [1,2,3,4] — exact value depends on interpolation; just in range
    result = latency_percentile([1.0, 2.0, 3.0, 4.0], 50)
    assert 1.0 <= result <= 4.0


def test_p0_is_minimum():
    timings = [5.0, 2.0, 8.0, 1.0]
    assert latency_percentile(timings, 0) == 1.0


def test_p100_is_maximum():
    timings = [5.0, 2.0, 8.0, 1.0]
    assert latency_percentile(timings, 100) == 8.0


def test_latency_empty_list_returns_zero():
    # No timings recorded → 0.0, not a crash
    assert latency_percentile([], 95) == 0.0


def test_latency_accepts_percentile_as_float():
    timings = [1.0, 2.0, 3.0, 4.0, 5.0]
    # 50.0 should work the same as 50
    assert latency_percentile(timings, 50.0) == latency_percentile(timings, 50)

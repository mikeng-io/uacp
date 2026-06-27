"""P5 eval harness — recall@K over the labeled seed-set (CF-D5 / 05-benchmark).

Non-vacuous: the recall-correctness tests assert exact fractions (full/absent/partial);
the seed-set tests assert the >=20-pair + per-pair-derivation non-fiction floor; the
determinism test asserts byte-identical numbers across runs.
"""

from pathlib import Path

import pytest

from codeflair.eval import (
    EvalReport,
    SeedSet,
    build_fixture_store,
    evaluate,
    load_seed_set,
    load_yaml_subset,
    parse_seed_set,
    recall_at_k,
    run_pair,
)

_SEED_SET = Path(__file__).resolve().parents[2] / "design" / "codeflair" / "eval" / "seed-set.yaml"


# -- the metric (the tiny known case — full / absent / partial) -------------------------


def test_recall_full_set_in_topk_is_one():
    assert recall_at_k(["B", "C", "D"], ["B", "C"], k=5) == 1.0


def test_recall_absent_ground_truth_is_zero():
    assert recall_at_k(["B", "C"], ["Z"], k=5) == 0.0


def test_recall_partial_is_the_right_fraction():
    # 2 of 4 ground-truth nodes present -> 0.5
    assert recall_at_k(["B", "C", "Q"], ["B", "C", "Y", "Z"], k=5) == 0.5


def test_recall_respects_topk_cut():
    # ground truth D sits at rank 4; k=2 drops it -> 1 of 2 found
    assert recall_at_k(["A", "B", "C", "D"], ["A", "D"], k=2) == 0.5


def test_recall_empty_ground_truth_raises():
    with pytest.raises(ValueError):
        recall_at_k(["A"], [], k=5)


def test_recall_dedups_ground_truth():
    assert recall_at_k(["A"], ["A", "A"], k=5) == 1.0


# -- exercising a fixture pair (end-to-end against the real engine) ----------------------


def _pair(seed_set: SeedSet, pair_id: str):
    return next(p for p in seed_set.pairs if p.id == pair_id)


def test_fixture_store_is_built_and_queryable():
    fixture = {
        "seed": "A",
        "k": 5,
        "symbols": {"A": "a.py", "B": "b.py"},
        "edges": [["B", "A", "calls", "scip", "parsed"]],
    }
    store = build_fixture_store(fixture)
    assert store.count_symbols() == 2
    assert store.count_edges() == 1


def test_run_pair_full_recall_on_constructed_pair():
    ss = load_seed_set(_SEED_SET)
    res = run_pair(_pair(ss, "construct--full-recall-parsed"))
    assert res.exercised
    assert res.recall_overall == 1.0
    assert res.recall_parsed == 1.0


def test_run_pair_truncation_lowers_recall():
    ss = load_seed_set(_SEED_SET)
    res = run_pair(_pair(ss, "construct--topk-truncation"))
    # k=1 keeps only the hop-1 caller; the hop-2 GT node is cut -> 1 of 2.
    assert res.recall_overall == 0.5


def test_run_pair_hop_limit_misses_distant_node():
    ss = load_seed_set(_SEED_SET)
    res = run_pair(_pair(ss, "construct--hop-limit-miss"))
    assert res.recall_overall == 0.5


def test_run_pair_absent_ground_truth_scores_zero():
    ss = load_seed_set(_SEED_SET)
    res = run_pair(_pair(ss, "construct--absent-ground-truth-zero"))
    assert res.recall_overall == 0.0


def test_run_pair_inferred_node_recall_is_split_out():
    ss = load_seed_set(_SEED_SET)
    res = run_pair(_pair(ss, "fixture-inferred--query-cochange-store"))
    assert res.recall_inferred == 1.0  # co-change coupling surfaces the inferred symbol
    assert res.recall_parsed is None  # no parsed GT in this pair


def test_gated_pair_is_not_exercised():
    ss = load_seed_set(_SEED_SET)
    res = run_pair(_pair(ss, "governance-orphan--code-without-anchor"))
    assert not res.exercised
    assert "requires" in res.reason
    assert res.recall_overall is None


# -- non-vacuity: the same graph with a wider K recovers the truncated node -------------


def test_widening_k_recovers_the_truncated_node():
    ss = load_seed_set(_SEED_SET)
    pair = _pair(ss, "construct--topk-truncation")
    assert run_pair(pair).recall_overall == 0.5
    # break the truncation: same fixture, k large enough to keep both callers
    widened = dict(pair.fixture)  # type: ignore[arg-type]
    widened["k"] = 5
    store = build_fixture_store(widened)
    from codeflair.expand import expand  # noqa: PLC0415 — local to the non-vacuity probe

    found = [e.symbol for e in expand(store, "A", k=5, max_hops=3).heatmap]
    assert recall_at_k(found, ["B", "C"], k=5) == 1.0


# -- the seed-set: >=20 pairs, every pair grounded (the non-fiction floor) ---------------


def test_seed_set_has_at_least_20_pairs():
    ss = load_seed_set(_SEED_SET)
    assert len(ss.pairs) >= 20


def test_every_pair_has_a_derivation():
    ss = load_seed_set(_SEED_SET)
    missing = [p.id for p in ss.pairs if not p.derivation.strip()]
    assert missing == [], f"pairs missing a derivation (non-fiction rule): {missing}"


def test_every_pair_has_an_adjudication():
    ss = load_seed_set(_SEED_SET)
    missing = [p.id for p in ss.pairs if not p.adjudication.strip()]
    assert missing == []


def test_some_pairs_are_exercised_and_some_gated():
    ss = load_seed_set(_SEED_SET)
    report = evaluate(ss)
    assert report.n_exercised >= 10
    assert report.n_gated >= 1
    assert report.n_exercised + report.n_gated == report.n_pairs


# -- the Policy-D baseline: a real number, split by provenance --------------------------


def test_baseline_is_reported_split_by_provenance():
    report = evaluate(load_seed_set(_SEED_SET))
    assert isinstance(report, EvalReport)
    for value in (report.baseline_overall, report.baseline_parsed, report.baseline_inferred):
        assert value is not None
        assert 0.0 <= value <= 1.0
    # both provenance subsets actually carry ground-truth nodes (the split is meaningful)
    assert report.parsed_gt > 0
    assert report.inferred_gt > 0


def test_baseline_is_non_vacuous():
    # the constructed truncation/hop-limit/absence pairs pull the baseline strictly below
    # 1.0 — proving the metric discriminates rather than always passing.
    report = evaluate(load_seed_set(_SEED_SET))
    assert report.baseline_overall is not None
    assert report.baseline_overall < 1.0


def test_evaluate_is_deterministic():
    ss = load_seed_set(_SEED_SET)
    a = evaluate(ss)
    b = evaluate(ss)
    assert (a.baseline_overall, a.baseline_parsed, a.baseline_inferred) == (
        b.baseline_overall,
        b.baseline_parsed,
        b.baseline_inferred,
    )
    assert [(r.pair_id, r.recall_overall) for r in a.results] == [
        (r.pair_id, r.recall_overall) for r in b.results
    ]


# -- the dependency-free YAML subset reader (guard the parser) --------------------------


def test_yaml_subset_parses_nested_blocks_flow_lists_and_quotes():
    text = """
key: value
num: 7
flag: true
empties: []
flow: [a, b, c]
nested:
  child: "has: a colon and # not-a-comment inside"
  items:
    - one
    - two
maps:
  - name: x
    n: 1
  - name: y
    n: 2
""".lstrip()
    data = load_yaml_subset(text)
    assert data["key"] == "value"
    assert data["num"] == 7
    assert data["flag"] is True
    assert data["empties"] == []
    assert data["flow"] == ["a", "b", "c"]
    assert data["nested"]["child"] == "has: a colon and # not-a-comment inside"
    assert data["nested"]["items"] == ["one", "two"]
    assert data["maps"] == [{"name": "x", "n": 1}, {"name": "y", "n": 2}]


def test_parse_seed_set_reads_fixture_and_ground_truth():
    text = """
default_k: 5
pairs:
  - id: demo
    layer: core
    basis: constructed
    derivation: "by construction"
    requires: []
    k: 5
    ground_truth:
      must_find:
        - node: B
          provenance: parsed
        - node: X
          provenance: inferred
    fixture:
      seed: A
      k: 5
      symbols:
        A: a.py
        B: b.py
      edges:
        - [B, A, calls, scip, parsed]
    adjudication: by-construction
""".lstrip()
    ss = parse_seed_set(text)
    assert len(ss.pairs) == 1
    pair = ss.pairs[0]
    assert pair.id == "demo"
    assert pair.exercised
    assert [n.provenance for n in pair.must_find] == ["parsed", "inferred"]
    assert pair.fixture is not None and pair.fixture["seed"] == "A"

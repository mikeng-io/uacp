"""Tests for the reranker bake-off script (Task 14c).

Scope: import-clean, arg-parsing, eval-set loading, Ollama refusal.
Does NOT call real endpoints. The rerank client is mocked.
"""
from __future__ import annotations

import pathlib
import sys


# ---------------------------------------------------------------------------
# Confirm the script module imports without any ML deps present
# ---------------------------------------------------------------------------


def test_script_imports_without_ml_deps(monkeypatch):
    """The bake-off script must importable with lancedb and FlagEmbedding absent."""
    monkeypatch.setitem(sys.modules, "lancedb", None)
    monkeypatch.setitem(sys.modules, "FlagEmbedding", None)
    # If the import raises, pytest will report the error and the test fails.
    import scripts.oracle_reranker_bakeoff as bakeoff  # noqa: F401

    assert bakeoff is not None


# ---------------------------------------------------------------------------
# Ollama refusal
# ---------------------------------------------------------------------------


def test_script_refuses_ollama():
    """--harness ollama must raise SystemExit or ValueError with a clear message."""
    import scripts.oracle_reranker_bakeoff as bakeoff

    try:
        bakeoff.validate_harness("ollama")
        assert False, "expected an error"
    except (SystemExit, ValueError) as exc:
        msg = str(exc).lower()
        assert "ollama" in msg
        # Confirm the message tells user what to use instead
        assert any(alt in msg for alt in ("tei", "vllm", "direct"))


# ---------------------------------------------------------------------------
# Eval-set loading
# ---------------------------------------------------------------------------

_EVAL_SET_PATH = (
    pathlib.Path(__file__).resolve().parents[3]
    / "skills/uacp-core/scripts/engines/oracle/eval/seed_evalset.json"
)


def test_load_eval_set_from_seed_fixture():
    """load_eval_set reads the bundled seed fixture without errors."""
    import scripts.oracle_reranker_bakeoff as bakeoff

    entries = bakeoff.load_eval_set(_EVAL_SET_PATH)
    assert isinstance(entries, list)
    assert len(entries) >= 4  # at least 4 scenarios represented
    # Each entry has the required fields
    for e in entries:
        assert "query" in e
        assert "relevant_doc_ids" in e
        assert "scenario" in e


def test_load_eval_set_all_scenarios_present():
    """Seed fixture must cover the four scenario types named in the plan."""
    import scripts.oracle_reranker_bakeoff as bakeoff

    entries = bakeoff.load_eval_set(_EVAL_SET_PATH)
    scenarios = {e["scenario"] for e in entries}
    expected = {"short_query", "long_doc_chunk", "multilingual_cjk", "keyword_vs_paraphrase"}
    assert expected.issubset(scenarios), f"missing scenarios: {expected - scenarios}"


def test_load_eval_set_missing_file_raises():
    """A missing eval set path raises a clear error (not a cryptic traceback)."""
    import scripts.oracle_reranker_bakeoff as bakeoff

    try:
        bakeoff.load_eval_set(pathlib.Path("/nonexistent/eval.json"))
        assert False, "expected an error"
    except (FileNotFoundError, ValueError):
        pass  # any of these is fine


# ---------------------------------------------------------------------------
# Arg-parsing
# ---------------------------------------------------------------------------


def test_arg_parser_parses_known_harness_values():
    """parse_args accepts tei, vllm, direct as valid harness values."""
    import scripts.oracle_reranker_bakeoff as bakeoff

    for harness in ("tei", "vllm", "direct"):
        args = bakeoff.parse_args(
            [
                "--eval", str(_EVAL_SET_PATH),
                "--harness", harness,
                "--rerankers", "qwen3-reranker-0.6b",
            ]
        )
        assert args.harness == harness


def test_arg_parser_has_required_flags():
    """parse_args defines --eval, --harness, --rerankers and --k flags."""
    import scripts.oracle_reranker_bakeoff as bakeoff


    # If required args missing, argparse raises SystemExit(2)
    try:
        bakeoff.parse_args([])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        assert False, "expected SystemExit(2) when required args missing"


# ---------------------------------------------------------------------------
# compute_scores unit test (mock client, no endpoint)
# ---------------------------------------------------------------------------


def test_compute_scores_with_mocked_rerank_client(monkeypatch):
    """compute_scores calls the rerank client and returns metric dicts per scenario."""
    import scripts.oracle_reranker_bakeoff as bakeoff

    # Build a minimal eval entry
    eval_entry = {
        "query_id": "test-001",
        "query": "worktree isolation",
        "scenario": "short_query",
        "relevant_doc_ids": ["doc-a", "doc-b"],
        "candidate_doc_ids": ["doc-a", "doc-c", "doc-b"],
        "docs": {
            "doc-a": "worktree isolation pattern",
            "doc-b": "parallel agent worktree",
            "doc-c": "unrelated content",
        },
    }

    # Mock the rerank call: return docs reordered as [doc-a, doc-b, doc-c]
    def _mock_rerank(query, docs, serving, **_kwargs):
        order = {"doc-a": 0, "doc-b": 1, "doc-c": 2}
        return sorted(docs, key=lambda d: order.get(d.get("id", ""), 99))

    monkeypatch.setattr(bakeoff, "_call_reranker", _mock_rerank)

    from engines.oracle.serving import RoleServing, ServingMode

    serving = RoleServing("rerank", ServingMode.URL, model="test-model", url="http://mock/rerank")
    result = bakeoff.compute_scores(eval_entry, serving=serving, k=3)

    assert "ndcg" in result
    assert "mrr" in result
    assert "latency_p50" in result
    assert "latency_p95" in result
    assert result["scenario"] == "short_query"
    assert 0.0 <= result["ndcg"] <= 1.0
    assert 0.0 <= result["mrr"] <= 1.0

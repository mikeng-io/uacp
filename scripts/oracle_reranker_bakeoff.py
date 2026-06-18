"""Oracle reranker bake-off harness (Task 14 — EXECUTE-phase validation tool).

Compares reranker models on a seed eval set (nDCG@k, MRR, p50/p95 latency)
and prints a comparison table. Reuses engines.oracle.clients.rerank for the
URL-mode rerank call.

Usage
-----
Once a live rerank endpoint is running (TEI or vLLM) and a real eval set exists:

    python scripts/oracle_reranker_bakeoff.py \\
        --eval skills/uacp-core/scripts/engines/oracle/eval/seed_evalset.json \\
        --harness tei \\
        --rerankers qwen3-reranker-0.6b,bge-reranker-v2-m3 \\
        --url http://localhost:8080 \\
        --k 5

Supported harnesses:
  tei    — HuggingFace Text Embeddings Inference, POST /rerank → [{index, score}]
  vllm   — vLLM Cohere-compat, POST /v1/rerank → {results: [{index, relevance_score}]}
  direct — In-process FlagEmbedding/sentence-transformers (no server needed)

NOT SUPPORTED:
  ollama — Ollama has no /rerank endpoint. Use tei, vllm, or direct instead.

Prerequisites (not installed by this repo):
  - A running TEI or vLLM instance with a cross-encoder/reranker model loaded, OR
  - FlagEmbedding / sentence-transformers installed for direct mode.
  - A labeled eval set (the bundled seed_evalset.json is synthetic / bootstrap only).

Design note: lazy imports throughout — this module must import with ZERO ML deps
installed. Heavy imports (httpx, FlagEmbedding, sentence-transformers) are deferred
to the point of actual use.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from typing import Any

# ---------------------------------------------------------------------------
# Path setup: make engines.oracle importable when run as a standalone script
# (pytest already does this via conftest; this guard handles `python scripts/...`)
# ---------------------------------------------------------------------------
_HERE = pathlib.Path(__file__).resolve().parent.parent
_CORE_SCRIPTS = _HERE / "skills" / "uacp-core" / "scripts"
if str(_CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CORE_SCRIPTS))

# ---------------------------------------------------------------------------
# Metric functions (pure — no ML deps, safe at import time)
# ---------------------------------------------------------------------------
from engines.oracle.eval.metrics import latency_percentile, mrr, ndcg_at_k  # noqa: E402

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

_VALID_HARNESSES = ("tei", "vllm", "direct")
_OLLAMA_MSG = (
    "Ollama has no rerank endpoint and is not supported as a harness. "
    "Use one of: tei | vllm | direct"
)

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def validate_harness(harness: str) -> str:
    """Validate the harness name. Raises ValueError for 'ollama'; returns name otherwise."""
    if harness.lower() == "ollama":
        raise ValueError(_OLLAMA_MSG)
    if harness.lower() not in _VALID_HARNESSES:
        raise ValueError(
            f"Unknown harness {harness!r}. Valid values: {', '.join(_VALID_HARNESSES)}"
        )
    return harness.lower()


# ---------------------------------------------------------------------------
# Eval-set loading
# ---------------------------------------------------------------------------


def load_eval_set(path: str | pathlib.Path) -> list[dict[str, Any]]:
    """Load an eval set from a JSON file. Returns a list of entry dicts.

    Parameters
    ----------
    path:
        Path to a JSON file whose top-level ``"entries"`` key holds the list,
        or whose top-level is a list directly.

    Raises
    ------
    FileNotFoundError  if the file does not exist.
    ValueError         if the JSON cannot be parsed or entries cannot be located.
    """
    path = pathlib.Path(path)
    if not path.exists():
        raise FileNotFoundError(f"eval set not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Could not parse eval set JSON at {path}: {exc}") from exc

    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and "entries" in raw:
        entries = raw["entries"]
        if not isinstance(entries, list):
            raise ValueError(f"'entries' in {path} is not a list")
        return entries
    raise ValueError(
        f"Eval set at {path} must be a JSON list or a dict with an 'entries' key"
    )


# ---------------------------------------------------------------------------
# Rerank client delegation
# This thin wrapper exists so tests can monkeypatch `bakeoff._call_reranker`
# without touching the real client module.
# ---------------------------------------------------------------------------


def _call_reranker(
    query: str,
    docs: list[dict[str, Any]],
    serving: Any,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Delegate to engines.oracle.clients.rerank.rerank. Lazy import."""
    from engines.oracle.clients.rerank import rerank as _rerank

    return _rerank(query, docs, serving, **kwargs)


# ---------------------------------------------------------------------------
# Score computation (per eval entry)
# ---------------------------------------------------------------------------


def compute_scores(
    entry: dict[str, Any],
    *,
    serving: Any,
    k: int = 5,
) -> dict[str, Any]:
    """Run rerank for one eval entry and return metric + timing data.

    Parameters
    ----------
    entry:
        A single entry dict with ``query``, ``relevant_doc_ids``,
        ``candidate_doc_ids``, ``docs``, and ``scenario`` keys.
    serving:
        A :class:`~engines.oracle.serving.RoleServing` describing the
        reranker endpoint/mode to use.
    k:
        nDCG cut-off.

    Returns
    -------
    dict with keys: ``query_id``, ``scenario``, ``ndcg``, ``mrr``,
    ``latency_p50``, ``latency_p95``, ``latency_ms``.
    """
    query = entry["query"]
    relevant_ids: set[str] = set(entry.get("relevant_doc_ids") or [])
    candidate_ids: list[str] = entry.get("candidate_doc_ids") or []
    docs_map: dict[str, str] = entry.get("docs") or {}

    # Build candidate docs as dicts that the rerank client can accept
    candidate_docs = [
        {"id": cid, "text": docs_map.get(cid, "")}
        for cid in candidate_ids
    ]

    # Call the reranker, measuring latency
    t0 = time.monotonic()
    try:
        reranked = _call_reranker(query, candidate_docs, serving)
    except Exception as exc:
        # Surface clearly in the table rather than crashing the whole bake-off
        return {
            "query_id": entry.get("query_id", "?"),
            "scenario": entry.get("scenario", "unknown"),
            "ndcg": None,
            "mrr": None,
            "latency_p50": None,
            "latency_p95": None,
            "latency_ms": [],
            "error": str(exc),
        }
    elapsed_ms = (time.monotonic() - t0) * 1000.0

    ranked_ids = [d.get("id", "") for d in reranked]
    ndcg_score = ndcg_at_k(ranked_ids, relevant_ids, k=k)
    mrr_score = mrr(ranked_ids, relevant_ids)

    return {
        "query_id": entry.get("query_id", "?"),
        "scenario": entry.get("scenario", "unknown"),
        "ndcg": round(ndcg_score, 4),
        "mrr": round(mrr_score, 4),
        "latency_p50": None,  # populated by run_bakeoff after aggregation
        "latency_p95": None,
        "latency_ms": [round(elapsed_ms, 2)],
        "error": None,
    }


# ---------------------------------------------------------------------------
# Bake-off orchestration
# ---------------------------------------------------------------------------


# Sentinel model name: score the ORIGINAL candidate order with no reranking.
# Lets a single bake-off run include a no-rerank baseline alongside real models,
# answering "does reranking even help on this set?".
_BASELINE_MODEL = "none"


def compute_scores_baseline(entry: dict[str, Any], *, k: int = 5) -> dict[str, Any]:
    """Score one eval entry using the ORIGINAL ``candidate_doc_ids`` order.

    No reranker is invoked — this is the no-rerank baseline. Metrics are computed
    with the exact same ``ndcg_at_k`` / ``mrr`` functions and aggregated the same
    way as the reranked rows, so the comparison is apples-to-apples.
    """
    relevant_ids: set[str] = set(entry.get("relevant_doc_ids") or [])
    candidate_ids: list[str] = entry.get("candidate_doc_ids") or []
    ndcg_score = ndcg_at_k(candidate_ids, relevant_ids, k=k)
    mrr_score = mrr(candidate_ids, relevant_ids)
    return {
        "query_id": entry.get("query_id", "?"),
        "scenario": entry.get("scenario", "unknown"),
        "ndcg": round(ndcg_score, 4),
        "mrr": round(mrr_score, 4),
        "latency_p50": None,
        "latency_p95": None,
        "latency_ms": [0.0],  # no model call; latency is definitionally ~0
        "error": None,
    }


def _serving_for_model(model: str, harness: str, base_url: str, api_key_env: str | None) -> Any:
    """Build a RoleServing for the given model + harness combination.

    Lazy import of serving so the module itself stays dep-free.
    """
    from engines.oracle.serving import RoleServing, ServingMode

    if harness in ("tei", "vllm"):
        if not base_url:
            print(
                f"  [SKIP] {model} — no --url provided for {harness} harness",
                file=sys.stderr,
            )
            return None
        # TEI: POST /rerank  |  vLLM: POST /v1/rerank (Cohere-compat, same client)
        suffix = "/rerank" if harness == "tei" else "/v1/rerank"
        url = base_url.rstrip("/") + suffix
        return RoleServing("rerank", ServingMode.URL, model=model, url=url)

    if harness == "direct":
        return RoleServing("rerank", ServingMode.EMBEDDED, model=model)

    return None


def run_bakeoff(
    eval_set: list[dict[str, Any]],
    *,
    rerankers: list[str],
    harness: str,
    base_url: str = "",
    api_key_env: str | None = None,
    k: int = 5,
) -> list[dict[str, Any]]:
    """Run the bake-off over all entries for each reranker. Returns result rows.

    Each row: {reranker, scenario, ndcg_mean, mrr_mean, p50_ms, p95_ms, errors}.
    """
    from collections import defaultdict

    all_results: list[dict[str, Any]] = []

    for model in rerankers:
        is_baseline = model.lower() == _BASELINE_MODEL
        if is_baseline:
            print(f"\n[bakeoff] model={model!r} (NO-RERANK baseline — original candidate order)")
            serving = None
        else:
            print(f"\n[bakeoff] model={model!r} harness={harness!r}")
            serving = _serving_for_model(model, harness, base_url, api_key_env)
            if serving is None:
                continue

        per_scenario: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entry in eval_set:
            if is_baseline:
                result = compute_scores_baseline(entry, k=k)
            else:
                result = compute_scores(entry, serving=serving, k=k)
            result["model"] = model
            per_scenario[result["scenario"]].append(result)

        # Aggregate per scenario
        for scenario, rows in per_scenario.items():
            valid = [r for r in rows if r["error"] is None]
            errors = [r["error"] for r in rows if r["error"]]
            all_latencies = [lat for r in valid for lat in r.get("latency_ms", [])]
            ndcg_mean = sum(r["ndcg"] for r in valid) / len(valid) if valid else None
            mrr_mean = sum(r["mrr"] for r in valid) / len(valid) if valid else None
            p50 = latency_percentile(all_latencies, 50) if all_latencies else None
            p95 = latency_percentile(all_latencies, 95) if all_latencies else None

            all_results.append({
                "model": model,
                "harness": harness,
                "scenario": scenario,
                "ndcg_mean": round(ndcg_mean, 4) if ndcg_mean is not None else None,
                "mrr_mean": round(mrr_mean, 4) if mrr_mean is not None else None,
                "p50_ms": round(p50, 1) if p50 is not None else None,
                "p95_ms": round(p95, 1) if p95 is not None else None,
                "n_queries": len(rows),
                "n_errors": len(errors),
                "errors": errors,
            })

    return all_results


def _print_table(results: list[dict[str, Any]]) -> None:
    """Print a comparison table to stdout."""
    if not results:
        print("No results to display.")
        return

    header = f"{'model':<32} {'harness':<8} {'scenario':<24} {'nDCG':<8} {'MRR':<8} {'p50ms':<8} {'p95ms':<8} {'n':<4} {'err'}"
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)

    for r in results:
        ndcg = f"{r['ndcg_mean']:.4f}" if r["ndcg_mean"] is not None else "N/A"
        mrr_ = f"{r['mrr_mean']:.4f}" if r["mrr_mean"] is not None else "N/A"
        p50 = f"{r['p50_ms']:.1f}" if r["p50_ms"] is not None else "N/A"
        p95 = f"{r['p95_ms']:.1f}" if r["p95_ms"] is not None else "N/A"
        print(
            f"{r['model']:<32} {r['harness']:<8} {r['scenario']:<24} "
            f"{ndcg:<8} {mrr_:<8} {p50:<8} {p95:<8} "
            f"{r['n_queries']:<4} {r['n_errors']}"
        )
    print(sep)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments. Exposed for unit-testing parse logic without running main."""
    parser = argparse.ArgumentParser(
        prog="oracle_reranker_bakeoff",
        description=(
            "Oracle reranker bake-off: compare reranker models on a labeled eval set. "
            "Requires a live rerank endpoint (TEI or vLLM) or FlagEmbedding installed. "
            "Ollama is NOT supported (no /rerank endpoint)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--eval",
        required=True,
        metavar="PATH",
        help="Path to eval set JSON (entries with query/relevant_doc_ids/scenario).",
    )
    parser.add_argument(
        "--harness",
        required=True,
        choices=list(_VALID_HARNESSES),
        help="Serving backend: tei (TEI /rerank), vllm (vLLM /v1/rerank), direct (in-process).",
    )
    parser.add_argument(
        "--rerankers",
        required=True,
        metavar="MODEL[,MODEL...]",
        help="Comma-separated list of model names to compare.",
    )
    parser.add_argument(
        "--url",
        default="",
        metavar="BASE_URL",
        help="Base URL of the rerank server (e.g. http://localhost:8080). Required for tei/vllm.",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        metavar="K",
        help="nDCG cut-off rank (default: 5).",
    )
    parser.add_argument(
        "--api-key-env",
        default=None,
        metavar="ENV_VAR",
        help="Name of env var holding the API key for the rerank endpoint (optional).",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        metavar="PATH",
        help="If set, write full results as JSON to this path in addition to printing the table.",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:  # pragma: no cover — live endpoint required
    args = parse_args(argv)

    # Refuse Ollama explicitly (argparse choices already block it, but validate_harness
    # is the testable surface for this contract)
    validate_harness(args.harness)

    eval_set = load_eval_set(args.eval)
    rerankers = [m.strip() for m in args.rerankers.split(",") if m.strip()]

    print(f"[bakeoff] eval_set={args.eval!r}  entries={len(eval_set)}")
    print(f"[bakeoff] rerankers={rerankers}  harness={args.harness!r}  k={args.k}")

    results = run_bakeoff(
        eval_set,
        rerankers=rerankers,
        harness=args.harness,
        base_url=args.url,
        api_key_env=args.api_key_env,
        k=args.k,
    )

    _print_table(results)

    if args.output_json:
        pathlib.Path(args.output_json).write_text(
            json.dumps(results, indent=2), encoding="utf-8"
        )
        print(f"\n[bakeoff] full results written to {args.output_json!r}")


if __name__ == "__main__":
    main()

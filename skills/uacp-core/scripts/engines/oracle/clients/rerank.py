"""Rerank client for the Oracle semantic leg (URL + embedded modes).

Cross-encoder / LLM rerank, selected by serving.resolve_role():
  * URL      — POST the TEI-style {query, texts} shape to a /rerank endpoint via
               a lazily imported httpx client. Cohere/vLLM /v1/rerank is the same
               client (it returns a {"results": [...]} envelope, also handled).
               Ollama has NO rerank endpoint and is not a target here.
  * EMBEDDED — a lazily loaded in-process reranker binding (Qwen3-Reranker-0.6B
               default). Degrades to RerankUnavailable when the binding is absent.
  * FLOOR    — always raises RerankUnavailable; the pipeline catches it and keeps
               the RRF-fused order untouched (design Degradation).

Both deps are lazy: no top-level httpx / binding import, so the floor imports
clean with neither installed.
"""

from __future__ import annotations

import os
from typing import Any

from engines.oracle.serving import RoleServing, ServingMode


class RerankUnavailable(RuntimeError):
    """Raised when no reranker is reachable for the requested serving mode."""


def _httpx_client(*a: Any, **k: Any) -> Any:
    """Create an httpx client. Lazy import — returns None if httpx is not installed."""
    try:
        import httpx

        return httpx.Client(*a, **k)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Embedded (in-process) reranker support.
#
# Two model families are supported, dispatched on the resolved HF repo id:
#   * bge-reranker-v2-m3 (and any cross-encoder) — a standard sequence-
#     classification cross-encoder. Scored via sentence-transformers'
#     ``CrossEncoder.predict([(query, text), ...])``, which returns one
#     relevance logit per pair.
#   * Qwen3-Reranker-0.6B — NOT a cross-encoder. It is a generative (causal-LM)
#     reranker that emits a yes/no judgement; relevance is the softmax weight of
#     the "yes" token over {"yes","no"} at the final position, using Qwen's
#     documented chat/instruction prompt format. Scored via transformers.
#
# Both paths expose the same ``.score(query, texts) -> list[float]`` surface the
# rerank() caller (and the bake-off harness) expect. Heavy imports stay lazy.
# ---------------------------------------------------------------------------

# Short config-name → HF repo id. Full "org/repo" ids pass through unchanged.
_MODEL_ALIASES: dict[str, str] = {
    "qwen3-reranker-0.6b": "Qwen/Qwen3-Reranker-0.6B",
    "bge-reranker-v2-m3": "BAAI/bge-reranker-v2-m3",
}


def _resolve_repo_id(model: str) -> str:
    """Map a short config name to its HF repo id; pass full ids through."""
    if "/" in model:
        return model
    return _MODEL_ALIASES.get(model.lower(), model)


class _CrossEncoderReranker:
    """Adapter over a sentence-transformers CrossEncoder (bge-reranker family)."""

    def __init__(self, repo_id: str) -> None:
        from sentence_transformers import CrossEncoder

        self._ce = CrossEncoder(repo_id)

    def score(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        preds = self._ce.predict([(query, t) for t in texts])
        return [float(s) for s in preds]


class _Qwen3GenerativeReranker:
    """Adapter over the Qwen3-Reranker yes/no-logit generative format.

    Implements the model-card prompt: a system instruction framing the
    relevance judgement, a user turn carrying <Instruct>/<Query>/<Document>,
    and an assistant prefix that primes a single yes/no token. The relevance
    score is softmax(yes_logit, no_logit)[yes] at the final position.
    """

    _PREFIX = (
        "<|im_start|>system\nJudge whether the Document meets the requirements "
        "based on the Query and the Instruct provided. Note that the answer can "
        'only be "yes" or "no".<|im_end|>\n<|im_start|>user\n'
    )
    _SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
    _INSTRUCT = "Given a web search query, retrieve relevant passages that answer the query"

    def __init__(self, repo_id: str) -> None:
        import torch  # noqa: F401
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._torch = __import__("torch")
        self._tok = AutoTokenizer.from_pretrained(repo_id, padding_side="left")
        self._model = AutoModelForCausalLM.from_pretrained(repo_id).eval()
        # Token ids for the "yes"/"no" judgement.
        self._yes_id = self._tok.convert_tokens_to_ids("yes")
        self._no_id = self._tok.convert_tokens_to_ids("no")

    def _format(self, query: str, doc: str) -> str:
        body = f"<Instruct>: {self._INSTRUCT}\n<Query>: {query}\n<Document>: {doc}"
        return self._PREFIX + body + self._SUFFIX

    def score(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        torch = self._torch
        out: list[float] = []
        with torch.no_grad():
            for doc in texts:
                prompt = self._format(query, doc)
                enc = self._tok(prompt, return_tensors="pt", truncation=True, max_length=8192)
                logits = self._model(**enc).logits[0, -1, :]
                pair = torch.stack([logits[self._no_id], logits[self._yes_id]])
                prob_yes = torch.softmax(pair, dim=0)[1].item()
                out.append(float(prob_yes))
        return out


# Process-lifetime cache of loaded embedded rerankers, keyed by model name.
# Loading a multi-GB reranker is expensive; rerank() is called once per query,
# so without this every query would reload the model from the HF cache. The
# cache also keeps the EMBEDDED latency measured by the bake-off representative
# of inference (not repeated model load). Cleared via _reset_embedded_cache().
_EMBEDDED_CACHE: dict[str, Any] = {}


def _reset_embedded_cache() -> None:
    """Drop all cached embedded rerankers (test/seam helper)."""
    _EMBEDDED_CACHE.clear()


def _load_embedded_reranker(model: str) -> Any | None:
    """Lazily load (and memoize) the in-process reranker binding for ``model``.

    Returns an adapter exposing ``.score(query, texts) -> list[float]``, or
    ``None`` when the required ML deps are not installed (the caller then raises
    RerankUnavailable, which the pipeline catches to keep the RRF-fused order).
    Dispatch is by resolved HF repo id: the Qwen3-Reranker generative family
    uses the yes/no-logit format; everything else is treated as a standard
    cross-encoder. A successful load is cached for the process lifetime so
    repeated rerank() calls do not reload multi-GB weights.
    """
    if model in _EMBEDDED_CACHE:
        return _EMBEDDED_CACHE[model]

    repo_id = _resolve_repo_id(model)
    is_qwen3_reranker = "qwen3-reranker" in repo_id.lower()
    try:
        if is_qwen3_reranker:
            reranker: Any = _Qwen3GenerativeReranker(repo_id)
        else:
            reranker = _CrossEncoderReranker(repo_id)
    except Exception:
        # Deps absent (sentence-transformers / transformers / torch) or the
        # model failed to load — degrade to "binding unavailable". Not cached so
        # a later load (deps installed mid-process) can still succeed.
        return None

    _EMBEDDED_CACHE[model] = reranker
    return reranker


def _doc_text(doc: dict[str, Any]) -> str:
    """Extract the text to rerank from a candidate doc (pure)."""
    for key in ("text", "body", "content", "payload"):
        val = doc.get(key)
        if isinstance(val, str) and val:
            return val
    return str(doc)


def _rerank_url(
    query: str,
    docs: list[dict[str, Any]],
    serving: RoleServing,
    *,
    api_key_env: str | None,
    timeout: float,
) -> list[dict[str, Any]]:
    client = _httpx_client(timeout=timeout)
    if client is None:
        raise RerankUnavailable("httpx not installed for URL rerank mode")
    headers: dict[str, str] = {}
    if api_key_env:
        key = os.environ.get(api_key_env, "")
        if key:
            headers["Authorization"] = f"Bearer {key}"
    texts = [_doc_text(d) for d in docs]
    try:
        with client:
            resp = client.post(
                serving.url,
                json={"query": query, "texts": texts, "model": serving.model},
                headers=headers or None,
            )
            resp.raise_for_status()
            data = resp.json()
    except RerankUnavailable:
        raise
    except Exception as exc:
        raise RerankUnavailable(f"URL rerank request failed: {exc}") from exc

    results = data.get("results", []) if isinstance(data, dict) else data
    scored: list[tuple[float, dict[str, Any]]] = []
    for item in results:
        idx = item.get("index")
        score = item.get("score", item.get("relevance_score", 0.0))
        if idx is None or not (0 <= idx < len(docs)):
            continue
        scored.append((float(score), docs[idx]))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [doc for _, doc in scored]


def rerank(
    query: str,
    docs: list[dict[str, Any]],
    serving: RoleServing,
    *,
    api_key_env: str | None = None,
    timeout: float = 30.0,
) -> list[dict[str, Any]]:
    """Rerank ``docs`` against ``query`` per the resolved ``serving`` mode.

    Raises RerankUnavailable for FLOOR, an unreachable URL endpoint, or a missing
    embedded binding — the pipeline catches it and keeps the RRF-fused order.
    """
    if serving.mode is ServingMode.FLOOR:
        raise RerankUnavailable("floor mode has no reranker")

    if serving.mode is ServingMode.URL:
        return _rerank_url(query, docs, serving, api_key_env=api_key_env, timeout=timeout)

    # EMBEDDED
    reranker = _load_embedded_reranker(serving.model)
    if reranker is None:
        raise RerankUnavailable(
            f"embedded reranker binding unavailable for model {serving.model!r}"
        )
    scores = reranker.score(query, [_doc_text(d) for d in docs])
    order = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)
    return [docs[i] for i in order]

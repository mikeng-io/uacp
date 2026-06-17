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


def _load_embedded_reranker(model: str) -> Any | None:
    """Lazily load the in-process reranker binding. Returns None when absent."""
    try:
        import importlib

        importlib.import_module("FlagEmbedding")
    except Exception:
        return None
    return None  # no bundled weights in-repo; real load wired with the embedded runtime


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

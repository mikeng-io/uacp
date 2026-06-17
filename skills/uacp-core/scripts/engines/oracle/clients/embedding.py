"""Embedding client for the Oracle semantic leg (URL + embedded modes).

Two serving modes, selected by serving.resolve_role():
  * URL      — POST to an OpenAI-style /v1/embeddings endpoint via a lazily
               imported httpx client (TEI /embed and Ollama are URL variants).
  * EMBEDDED — a lazily loaded in-process llama.cpp / GGUF binding (BGE-M3
               default). Degrades to EmbeddingUnavailable when the binding is absent.
  * FLOOR    — always raises EmbeddingUnavailable; the pipeline catches it and
               runs the keyword/FTS leg only (zero ML deps).

Both deps are lazy: no top-level httpx / llama binding import, so the floor
imports clean with neither installed. The API key is read from the named env
var in URL mode only — the key value itself is never logged or stored.
"""
from __future__ import annotations

import os
from typing import Any

from engines.oracle.serving import RoleServing, ServingMode


class EmbeddingUnavailable(RuntimeError):
    """Raised when no embedding model is reachable for the requested serving mode."""


def _httpx_client(*a: Any, **k: Any) -> Any:
    """Create an httpx client. Lazy import — returns None if httpx is not installed."""
    try:
        import httpx

        return httpx.Client(*a, **k)
    except Exception:
        return None


def _load_embedded_model(model: str) -> Any | None:
    """Lazily load the in-process embedding binding. Returns None when absent."""
    try:
        import importlib

        # Exact binding settled at impl-time; kept behind this helper so tests
        # monkeypatch it and the floor never imports a heavy dep.
        importlib.import_module("llama_cpp")
    except Exception:
        return None
    return None  # no bundled GGUF in-repo; real load wired with the embedded runtime


def _embed_url(
    texts: list[str],
    serving: RoleServing,
    *,
    api_key_env: str | None,
    timeout: float,
) -> list[list[float]]:
    client = _httpx_client(timeout=timeout)
    if client is None:
        raise EmbeddingUnavailable("httpx not installed for URL embedding mode")
    headers: dict[str, str] = {}
    if api_key_env:
        key = os.environ.get(api_key_env, "")
        if key:
            headers["Authorization"] = f"Bearer {key}"
    try:
        with client:
            resp = client.post(
                serving.url,
                json={"input": texts, "model": serving.model},
                headers=headers or None,
            )
            resp.raise_for_status()
            data = resp.json()
    except EmbeddingUnavailable:
        raise
    except Exception as exc:  # network/parse failure -> unavailable, never crash caller
        raise EmbeddingUnavailable(f"URL embedding request failed: {exc}") from exc
    items = data.get("data", []) if isinstance(data, dict) else []
    return [item["embedding"] for item in items]


def embed_texts(
    texts: list[str],
    serving: RoleServing,
    *,
    api_key_env: str | None = None,
    timeout: float = 30.0,
) -> list[list[float]]:
    """Embed ``texts`` according to the resolved ``serving`` mode.

    Raises EmbeddingUnavailable for FLOOR, an unreachable URL endpoint, or a
    missing embedded binding — the pipeline catches it and uses the keyword leg.
    """
    if serving.mode is ServingMode.FLOOR:
        raise EmbeddingUnavailable("floor mode has no embedding model")

    if serving.mode is ServingMode.URL:
        return _embed_url(texts, serving, api_key_env=api_key_env, timeout=timeout)

    # EMBEDDED
    model = _load_embedded_model(serving.model)
    if model is None:
        raise EmbeddingUnavailable(
            f"embedded embedding binding unavailable for model {serving.model!r}"
        )
    return [list(v) for v in model.embed(texts)]

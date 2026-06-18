"""Shared helpers for the GATED Oracle real-model e2e tests.

Imported only by the gated e2e modules (which have already asserted the
``UACP_ORACLE_E2E=1`` opt-in + importorskip'd the heavy deps), so this module
may import the oracle clients at top level. It carries NO module-level skip and
NO heavy-dep import of its own beyond what the importing test already gated;
``sentence_transformers`` is imported lazily inside the model fixtures' callers,
not here.

Provides:
  * model id / dim constants
  * an in-process OpenAI-compatible /v1/embeddings stub backed by a real model
  * an in-process TEI-style /rerank stub backed by a real cross-encoder
  * the ``serve`` thread helper + URL-mode embedding/reranker adapters
These were previously inlined in test_oracle_realmodel_e2e.py; extracted so the
index-build e2e reuses the exact same plumbing rather than reinventing it.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from engines.oracle.clients.embedding import embed_texts
from engines.oracle.clients.rerank import rerank
from engines.oracle.serving import RoleServing, ServingMode

# Small, real, pure-pip models (~80MB each, no compile). Downloaded once to the
# HF cache; never committed to the repo.
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
EMBED_DIM = 384


def make_embed_server(model: Any) -> tuple[HTTPServer, str]:
    """OpenAI-compatible /v1/embeddings stub backed by a real ST model."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_: Any) -> None:  # silence
            pass

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            texts = body.get("input") or []
            if isinstance(texts, str):
                texts = [texts]
            vecs = model.encode(texts, normalize_embeddings=True)
            data = [
                {"object": "embedding", "index": i, "embedding": [float(x) for x in v]}
                for i, v in enumerate(vecs)
            ]
            payload = json.dumps({"object": "list", "data": data}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    return server, f"http://127.0.0.1:{port}/v1/embeddings"


def make_rerank_server(model: Any) -> tuple[HTTPServer, str]:
    """TEI-style /rerank stub backed by a real cross-encoder."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_: Any) -> None:
            pass

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            query = body.get("query", "")
            texts = body.get("texts") or []
            scores = model.predict([(query, t) for t in texts])
            data = [{"index": i, "score": float(s)} for i, s in enumerate(scores)]
            payload = json.dumps(data).encode()  # TEI returns a bare list
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    return server, f"http://127.0.0.1:{port}/rerank"


class UrlEmbedding:
    """Pipeline-facing embedding adapter delegating to the real URL client."""

    def __init__(self, url: str) -> None:
        self._serving = RoleServing("embedding", ServingMode.URL, model=EMBED_MODEL, url=url)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return embed_texts(texts, self._serving)


class UrlReranker:
    """Pipeline-facing reranker adapter delegating to the real URL client."""

    def __init__(self, url: str) -> None:
        self._serving = RoleServing("rerank", ServingMode.URL, model=RERANK_MODEL, url=url)

    def rerank(self, query: str, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return rerank(query, docs, self._serving)

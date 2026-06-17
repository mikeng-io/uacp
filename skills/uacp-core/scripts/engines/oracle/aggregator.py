"""Oracle aggregator: compose per-phase retrieval sources and apply PHASE_TIERS gating.

The aggregator is the main entry point for oracle_query(). It:
1. Looks up the OracleMode for the requested phase via PHASE_TIERS
2. For NONE/WRITEBACK modes, returns empty packets with metadata note
3. For FULL/ADVISORY modes, collects packets from all enabled sources:
     - runstate (deterministic, always available)
     - honcho   (advisory, optional — skipped when disabled or unreachable)
     - semantic  (C-semantic: pipeline over .uacp/lessons + .uacp/knowledge)
4. Each source is wrapped in try/except — failures append to sources_skipped,
   never raise to the caller.

Semantic source (Task 8b):
  _semantic_packets resolves the store + embedding/rerank clients via resolve_role()
  and get_store(). When the store is unavailable (lancedb absent / enabled=false) it
  returns [] and the aggregator records "semantic" in sources_skipped — NOT an error.
  When available, it runs the pipeline (engines.oracle.pipeline.semantic_retrieve)
  over the workspace corpus and returns ranked ProviderPackets (advisory trust class).

Floor guarantee: the aggregator must import and run clean with lancedb, llama_cpp,
and httpx all poisoned. All heavy imports are lazy (inside _semantic_packets).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Bootstrap core scripts on path
_AGG_DIR = Path(__file__).resolve().parent
_ENGINES_DIR = _AGG_DIR.parent
_CORE_DIR = _ENGINES_DIR.parent
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from engines.oracle.packets import ProviderPacket  # noqa: E402
from engines.oracle.tier_config import OracleMode, mode_for_phase  # noqa: E402


def _get_oracle_store(oracle_cfg: dict, workspace: Path) -> Any:
    """Resolve and return the configured vector store. Lazy import — never raises.

    Returns a store object (which may have available()==False) or None on
    any configuration/import error.
    """
    try:
        from engines.oracle.store import get_store

        backend = oracle_cfg.get("store", "lancedb")
        raw_index = oracle_cfg.get("index_path", ".uacp/knowledge/indexes/")
        index_path = str(workspace / raw_index)
        return get_store(backend, index_path=index_path)
    except Exception:
        return None


class _SemanticUnavailable(RuntimeError):
    """Raised by _semantic_packets when the vector store is unavailable.

    The aggregator catches this (as Exception) and records "semantic" in
    sources_skipped — NOT an error, but a graceful degradation signal.
    """


def _semantic_packets(
    workspace: Path,
    phase: str,
    project: str,
    domains: list[str] | None = None,
    query: str = "",
    oracle_cfg: dict | None = None,
) -> list[ProviderPacket]:
    """Run the semantic retrieval pipeline and return ranked ProviderPackets.

    Behaviour by case:
      - oracle disabled (enabled=false) → return [] silently (aggregator already
        short-circuited before calling us when oracle is disabled; this guard is
        here for callers that invoke _semantic_packets directly).
      - store unavailable (lancedb absent / index not built) → raise
        _SemanticUnavailable so the aggregator records "semantic" in sources_skipped.
      - any other transient failure → same raise path (aggregator catches Exception).
      - store available → run pipeline, return ProviderPackets.

    Floor guarantee: all heavy imports are lazy; this function must import clean
    with lancedb, llama_cpp, and httpx all poisoned.
    """
    cfg = oracle_cfg or {}
    if not cfg.get("enabled", False):
        return []

    # Lazy imports — all heavy deps guarded here
    try:
        from engines.oracle.pipeline import semantic_retrieve
        from engines.oracle.serving import ServingMode, resolve_role
    except Exception as exc:
        raise _SemanticUnavailable(f"semantic pipeline import failed: {exc}") from exc

    # Resolve store — unavailable store raises so aggregator records sources_skipped
    store = _get_oracle_store(cfg, workspace)
    if store is None or not store.available():
        raise _SemanticUnavailable(
            "semantic store unavailable (deps absent or backend not ready)"
        )

    # Resolve embedding client (FLOOR -> None, pipeline skips dense leg)
    embedding = None
    try:
        emb_serving = resolve_role("embedding", cfg)
        if emb_serving.mode is not ServingMode.FLOOR:
            from engines.oracle.clients.embedding import embed_texts

            class _EmbedAdapter:
                def __init__(self, serving: Any) -> None:
                    self._serving = serving

                def embed(self, texts: list[str]) -> list[list[float]]:
                    return embed_texts(texts, self._serving)

            embedding = _EmbedAdapter(emb_serving)
    except Exception:
        embedding = None  # degrade: dense leg skipped, FTS still runs

    # Resolve rerank client (FLOOR -> None, pipeline keeps RRF order)
    reranker = None
    try:
        rr_serving = resolve_role("rerank", cfg)
        if rr_serving.mode is not ServingMode.FLOOR:
            from engines.oracle.clients.rerank import rerank

            class _RerankAdapter:
                def __init__(self, serving: Any) -> None:
                    self._serving = serving

                def rerank(
                    self, query: str, docs: list[dict[str, Any]]
                ) -> list[dict[str, Any]]:
                    return rerank(query, docs, self._serving)

            reranker = _RerankAdapter(rr_serving)
    except Exception:
        reranker = None  # degrade: RRF order kept

    # Run pipeline (never raises)
    packets = semantic_retrieve(
        query=query,
        store=store,
        domains=list(domains or []),
        invariants=[],
        embedding=embedding,
        reranker=reranker,
    )
    return packets


def oracle_query(
    workspace: Path | str,
    phase: str,
    project: str,
    *,
    domains: list[str] | None = None,
    query: str = "",
    oracle_cfg: dict | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Main aggregator entry point.

    Args:
        workspace: UACP workspace root path
        phase: current lifecycle phase (drives PHASE_TIERS mode selection)
        project: project identifier for source filtering
        domains: optional domain filter list
        query: optional search query string
        oracle_cfg: optional oracle config dict (defaults to loading from workspace config)
        limit: maximum number of packets to return

    Returns:
        dict with keys:
          - packets: list of ProviderPacket (or empty)
          - metadata: dict with phase, mode, sources_skipped, and optional note
    """
    workspace = Path(workspace)

    # Load oracle config if not provided
    if oracle_cfg is None:
        try:
            from config import get_config
            oracle_cfg = get_config(workspace).model_extra.get("oracle", {"enabled": False})
        except Exception:
            oracle_cfg = {"enabled": False}

    # Check if oracle is enabled
    if not oracle_cfg.get("enabled", False):
        return {
            "packets": [],
            "metadata": {
                "phase": phase,
                "mode": OracleMode.NONE.value,
                "sources_skipped": ["all"],
                "note": "oracle disabled (oracle.enabled=false)",
            },
        }

    mode = mode_for_phase(phase)

    # NONE and WRITEBACK phases have no external retrieval
    if mode in (OracleMode.NONE, OracleMode.WRITEBACK):
        return {
            "packets": [],
            "metadata": {
                "phase": phase,
                "mode": mode.value,
                "sources_skipped": [],
                "note": f"phase {phase} has no external retrieval",
            },
        }

    # FULL and ADVISORY: collect from all enabled sources
    packets: list[ProviderPacket] = []
    sources_skipped: list[str] = []

    # Source 1: run-state (deterministic, always available)
    try:
        from engines.oracle.sources.runstate import query_runstate
        rs_packets = query_runstate(workspace, project=project, phase=None, limit=limit)
        packets.extend(rs_packets)
    except Exception:
        sources_skipped.append("runstate")

    # Source 2: honcho memory (advisory, optional)
    try:
        honcho_cfg = oracle_cfg.get("honcho", {})
        if isinstance(honcho_cfg, dict) and honcho_cfg.get("enabled", False):
            honcho_url = honcho_cfg.get("url", "")
            from engines.oracle.sources.honcho import packets_from_honcho
            h_packets = packets_from_honcho(
                url=honcho_url,
                project=project,
                phase=phase,
                query=query,
            )
            packets.extend(h_packets)
    except Exception:
        sources_skipped.append("honcho")

    # Source 3: semantic — runs the pipeline when the store is available;
    # records "semantic" in sources_skipped when the store is unavailable
    # (lancedb absent, index not built, or oracle.enabled=false).
    try:
        sem_packets = _semantic_packets(
            workspace, phase, project,
            domains=domains, query=query, oracle_cfg=oracle_cfg,
        )
        packets.extend(sem_packets)
    except Exception:
        sources_skipped.append("semantic")

    # Trim to limit
    packets = packets[:limit]

    return {
        "packets": packets,
        "metadata": {
            "phase": phase,
            "mode": mode.value,
            "sources_skipped": sources_skipped,
        },
    }

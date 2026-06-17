"""Oracle aggregator: compose per-phase retrieval sources and apply PHASE_TIERS gating.

The aggregator is the main entry point for oracle_query(). It:
1. Looks up the OracleMode for the requested phase via PHASE_TIERS
2. For NONE/WRITEBACK modes, returns empty packets with metadata note
3. For FULL/ADVISORY modes, collects packets from all enabled sources
4. _semantic_packets is a stub that raises NotImplementedError (C-semantic tasks
   are deferred) — the aggregator wraps it in try/except and adds to sources_skipped
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


def _semantic_packets(
    workspace: Path,
    phase: str,
    project: str,
    domains: list[str] | None = None,
    query: str = "",
    oracle_cfg: dict | None = None,
) -> list[ProviderPacket]:
    """Stub for C-semantic sources (Tasks 4/6/7/8 deferred).

    Raises NotImplementedError always — the aggregator catches this and adds
    "semantic" to sources_skipped. When C-semantic tasks are implemented,
    this function will import and call the semantic pipeline.
    """
    raise NotImplementedError("C-semantic tasks not yet implemented")


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

    # Source 3: semantic (C-semantic deferred — always skipped at C-floor)
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

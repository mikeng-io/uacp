"""Honcho memory source for the Oracle engine.

Queries Honcho's REST API to retrieve memory packets relevant to a project/phase.
This source is advisory and non-fatal: failures are caught and reported but do
not block the aggregator.

Heavy dependency (httpx) is lazily imported so the floor (no ML deps) works
without httpx installed.
"""
from __future__ import annotations

from typing import Any


def _httpx_client(*a: Any, **k: Any) -> Any:
    """Create an httpx client. Lazy import — returns None if httpx is not installed."""
    try:
        import httpx
        return httpx.Client(*a, **k)
    except ImportError:
        return None


def query_honcho(
    *,
    url: str,
    project: str,
    phase: str,
    query: str = "",
    timeout: float = 5.0,
) -> list[dict]:
    """Query Honcho memory API for relevant context.

    Args:
        url: Honcho API base URL (e.g. "http://honcho:4000")
        project: project identifier to scope the query
        phase: current lifecycle phase
        query: optional search query string
        timeout: HTTP request timeout in seconds

    Returns:
        List of memory record dicts from Honcho, or [] on any failure.
    """
    if not url:
        return []

    client = _httpx_client(timeout=timeout)
    if client is None:
        return []

    try:
        with client:
            resp = client.get(
                f"{url.rstrip('/')}/memory",
                params={"project": project, "phase": phase, "q": query},
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "results" in data:
                return data["results"]
            return []
    except Exception:
        return []


def packets_from_honcho(
    *,
    url: str,
    project: str,
    phase: str,
    query: str = "",
    timeout: float = 5.0,
) -> list:
    """Wrap query_honcho results into ProviderPacket list.

    Import is inline to avoid circular imports.
    """
    from engines.oracle.packets import ProviderPacket, TrustClass

    records = query_honcho(url=url, project=project, phase=phase, query=query, timeout=timeout)
    packets = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        content = rec.get("content", str(rec))
        packets.append(
            ProviderPacket(
                source="honcho",
                trust_class=TrustClass.advisory,
                payload=content,
                score=float(rec.get("score", 0.0)),
                evidence_required=True,
                metadata={"honcho_id": rec.get("id", ""), "phase": phase},
            )
        )
    return packets

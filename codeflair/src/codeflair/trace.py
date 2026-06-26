"""Codeflair P4 — output honesty: the JSON contract + the replayable, watermarked trace.

A Codeflair run returns a ranked heatmap. The orchestrator must be able to TRUST it, which
means three things, all here (04-outputs, the "re-derivability reconciliation"):

  1. a single canonical, machine-parseable contract — ``{nodes[], gaps[], trace{}}`` — that
     is BYTE-STABLE: same result -> byte-identical JSON (sorted keys, preserved rank order,
     no wall-clock, no set-iteration nondeterminism). The string heatmap is a rendering of
     this; the JSON is the source of truth.
  2. a ``trace`` that records enough to RE-DERIVE the ranking: the seed/query, the
     watermark (repo_commit + built_at), the per-probe hop log (every candidate + score),
     and the kept/pruned beam. ``replay(trace)`` reconstructs the ranked nodes/scores/order
     from the log alone — not the node SET, the full ranking (CF-D11: same store + seed ->
     same trace, so a deterministic engine clears the "replayable" bar trivially).
  3. STALENESS: the trace carries the content-hash basis it was computed against. When the
     working tree moves on (a file's recorded hash diverges), ``mark_stale`` flags it, so a
     replayed/old trace is never silently treated as current.

Determinism discipline (10-freshness): zero wall-clock here. ``built_at`` is whatever the
store's watermark was set to (injected by the caller); the serializer only echoes it. All
unordered collections are sorted; ranked sequences (nodes, the beam) preserve their order
because the order IS the ranking and must round-trip.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from codeflair.policy import default_policy

if TYPE_CHECKING:  # pragma: no cover - typing only, no runtime import cycle
    from codeflair.expand import ExpandResult
    from codeflair.store import Store

# Bumped when the trace JSON shape changes incompatibly; replay/consumers can refuse a
# foreign version rather than mis-read an old log.
TRACE_SCHEMA = "codeflair.trace/1"


@dataclass(frozen=True)
class TraceCandidate:
    """One candidate a probe yielded during expansion, with the score it carried. ``admitted``
    is False when the merge dropped it (the seed itself, or a symbol an earlier probe already
    claimed under first-claim-wins) — recorded so the pruning is auditable, not invisible."""

    symbol: str
    score: float
    hop: int
    via: str
    source: str
    admitted: bool


@dataclass(frozen=True)
class HopRecord:
    """One probe's contribution: its name/kind and every candidate it expanded, in yield
    order. The ordered candidate list is what ``replay`` re-ranks to re-derive the result."""

    probe: str
    kind: str
    candidates: tuple[TraceCandidate, ...]


@dataclass(frozen=True)
class SearchTrace:
    """The watermarked, replayable hop log. ``basis_hash`` is the content-hash basis the
    trace was computed against; ``stale`` is set by :func:`mark_stale` when that basis no
    longer matches the working tree."""

    seed: str
    query: dict[str, Any]
    repo_commit: str
    built_at: str
    basis_hash: str
    hops: tuple[HopRecord, ...]
    result_order: tuple[str, ...]  # the kept beam, in final rank order
    pruned: tuple[TraceCandidate, ...]  # admitted but cut below top-k
    stale: bool = False


@dataclass(frozen=True)
class ReplayNode:
    """A node reconstructed purely from the trace's hop log — the re-derivation output."""

    symbol: str
    score: float
    hop: int
    via: str
    source: str


# --------------------------------------------------------------------------- #
# Content-hash basis + staleness
# --------------------------------------------------------------------------- #


def compute_basis_hash(store: Store) -> str:
    """A deterministic hash over the content-hash BASIS a trace is keyed to: the store
    watermark's ``repo_commit`` plus every recorded file hash (sorted). Re-recording any
    file hash (the working tree moving on) changes this; nothing else does. No wall-clock —
    ``built_at`` is deliberately excluded (it is build TIME, not content)."""
    rows = sorted(store.con.execute("SELECT path, content_hash FROM files").fetchall())
    wm = store.watermark() or ("", "")
    payload = json.dumps(
        {"repo_commit": wm[0], "files": {p: h for p, h in rows}},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def mark_stale(trace: SearchTrace, current_basis_hash: str) -> SearchTrace:
    """Return ``trace`` with ``stale`` set iff its basis no longer matches the current
    working-tree basis. A matching basis is fresh; a divergent one is stale — a replayed/old
    trace is never silently treated as current."""
    return replace(trace, stale=trace.basis_hash != current_basis_hash)


# --------------------------------------------------------------------------- #
# Replay — re-derive the ranking from the hop log alone
# --------------------------------------------------------------------------- #


def replay(trace: SearchTrace) -> list[ReplayNode]:
    """Reconstruct the ranked heatmap from the trace's hop log, WITHOUT the store.

    Re-applies exactly the merge expand performed: probes in order, first claim on a symbol
    wins (so the recorded ``admitted`` flags fall out the same way); adds the P6 multi-probe
    corroboration bonus (the only score component NOT already baked into each logged
    candidate, since it depends on the cross-probe count the log itself records); then sorts
    by ``(-score, symbol)`` and truncates to ``k``. This re-derives the same ranked
    nodes/scores/order on the store-authoritative path — the re-derivability reconciliation.
    Corrupt a logged score and the reconstruction diverges.

    Scope: replay reconstructs the PRE-reconcile ranking (the bare hop log). When a query
    ran with a live overlay, the reconcile's freshness re-tagging — and its strip of the
    corroboration bonus from an ``unreconciled`` node — are overlay state, recorded under
    ``trace.signals``, not replayable from the hop log alone; replay assumes the default
    policy's non-conflicting bonus."""
    k = int(trace.query.get("k", len(trace.result_order)))
    seed = trace.seed
    merged: dict[str, TraceCandidate] = {}
    found_by: dict[str, set[str]] = {}
    for hop in trace.hops:
        for cand in hop.candidates:
            found_by.setdefault(cand.symbol, set()).add(hop.probe)
            if cand.symbol == seed or cand.symbol in merged:
                continue  # first claim wins — mirrors expand's merge precedence
            merged[cand.symbol] = cand
    policy = default_policy()
    scored: list[tuple[TraceCandidate, float]] = []
    for cand in merged.values():
        bonus = policy.agreement_bonus(len(found_by.get(cand.symbol, ())), False)
        scored.append((cand, round(cand.score + bonus, 6) if bonus else cand.score))
    ranked = sorted(scored, key=lambda t: (-t[1], t[0].symbol))[:k]
    return [
        ReplayNode(symbol=c.symbol, score=s, hop=c.hop, via=c.via, source=c.source)
        for c, s in ranked
    ]


# --------------------------------------------------------------------------- #
# Serialization — the canonical {nodes[], gaps[], trace{}} contract
# --------------------------------------------------------------------------- #


def _candidate_json(c: TraceCandidate, *, with_admitted: bool) -> dict[str, Any]:
    out: dict[str, Any] = {
        "symbol": c.symbol,
        "score": c.score,
        "hop": c.hop,
        "via": c.via,
        "source": c.source,
    }
    if with_admitted:
        out["admitted"] = c.admitted
    return out


def _trace_json(trace: SearchTrace, signals: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": TRACE_SCHEMA,
        "query": dict(trace.query),
        "watermark": {"repo_commit": trace.repo_commit, "built_at": trace.built_at},
        "basis_hash": trace.basis_hash,
        "stale": trace.stale,
        "signals": signals,
        "hops": [
            {
                "probe": h.probe,
                "kind": h.kind,
                "candidates": [_candidate_json(c, with_admitted=True) for c in h.candidates],
            }
            for h in trace.hops
        ],
        "result_order": list(trace.result_order),
        "pruned": [_candidate_json(c, with_admitted=False) for c in trace.pruned],
    }


def _signals_json(result: ExpandResult) -> dict[str, Any]:
    """The P2 reconcile signals, surfaced (not dropped). Unordered collections are sorted;
    ``warnings`` is already built in a deterministic order so it is preserved as emitted."""
    return {
        "lsp_degraded": result.lsp_degraded,
        "warnings": list(result.warnings),
        "overlay_only": sorted(result.overlay_only),
        "conflicts": [
            {
                "file": c.file,
                "scip_symbols": list(c.scip_symbols),
                "overlay_symbols": list(c.overlay_symbols),
            }
            for c in sorted(result.conflicts, key=lambda c: c.file)
        ],
    }


def _degenerate_trace(
    result: ExpandResult,
    watermark: tuple[str, str] | None,
    query: dict[str, Any] | None,
) -> SearchTrace:
    """Build a minimal (non-replayable) trace for a result expanded WITHOUT ``capture_trace``.
    The contract is still byte-stable; it just has no hop log to replay from."""
    repo_commit, built_at = watermark or ("", "")
    return SearchTrace(
        seed=(query or {}).get("seed", ""),
        query=dict(query or {}),
        repo_commit=repo_commit,
        built_at=built_at,
        basis_hash="",
        hops=(),
        result_order=tuple(e.symbol for e in result.heatmap),
        pruned=(),
    )


def to_json(
    result: ExpandResult,
    *,
    watermark: tuple[str, str] | None = None,
    query: dict[str, Any] | None = None,
    indent: int | None = None,
) -> str:
    """Serialize an :class:`ExpandResult` to the canonical ``{nodes[], gaps[], trace{}}``
    document — deterministic and byte-stable.

    ``nodes[]`` preserves the heatmap's RANK order (the order is the ranking); each node
    carries ``symbol/score/hop/via/source/freshness``. ``gaps[]`` is the gap output.
    ``trace{}`` is the watermarked, replayable hop log (the P2 reconcile signals ride under
    ``trace.signals``). When ``result.trace`` was captured it is authoritative; otherwise a
    degenerate (non-replayable) trace is synthesized from ``watermark``/``query``.

    Determinism: ``sort_keys`` orders every object's keys; ranked sequences keep their order;
    nothing reads the wall clock (``built_at`` is echoed from the injected watermark)."""
    trace = getattr(result, "trace", None)
    if trace is None:
        trace = _degenerate_trace(result, watermark, query)

    doc = {
        "nodes": [
            {
                "symbol": e.symbol,
                "score": e.score,
                "hop": e.hop,
                "via": e.via,
                "source": e.source,
                "freshness": e.freshness,
            }
            for e in result.heatmap
        ],
        "gaps": [{"symbol": g.symbol, "file": g.file, "reason": g.reason} for g in result.gaps],
        "trace": _trace_json(trace, _signals_json(result)),
    }
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), indent=indent)

"""Codeflair expansion loop + gaps (CF-D3 / CF-D6) — the relation-finder.

Fuses the two signal classes into one ranked heatmap:
- **precise** edge-walk (SCIP/LSP/tree-sitter) via the recursive-CTE blast radius, and
- **inferred** file-level couplings (co-change / shared-string) projected to symbols,
  expanded only from the top-``beam`` precise nodes so cost stays bounded on huge graphs.

Precise always outranks inferred at equal distance (the CF-D14 ladder). Deterministic:
no LLM, stable ordering. Gaps (untested impacted symbols) are a first-class, best-effort
output scored separately from the heatmap (CF-D6).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from codeflair.overlay import FileConflict, LspOverlay, reconcile_overlay
from codeflair.policy import ScorePolicy, default_policy
from codeflair.probes import ProbeContext, ProbeParams, ProbeRegistry, default_registry
from codeflair.query import HeatmapEntry
from codeflair.store import Store
from codeflair.trace import (
    HopRecord,
    SearchTrace,
    TraceCandidate,
    compute_basis_hash,
)

_TEST_FILE_RE = re.compile(
    r"(_test\.go$|_test\.py$|test_.*\.py$|\.test\.[jt]sx?$|\.spec\.[jt]sx?$|(^|/)tests?/)"
)


@dataclass(frozen=True)
class Gap:
    symbol: str
    file: str
    reason: str  # e.g. "no test references this impacted symbol"


@dataclass(frozen=True)
class ExpandResult:
    heatmap: list[HeatmapEntry]
    gaps: list[Gap]
    n_precise: int  # symbols reached by precise edge-walk
    n_inferred: int  # symbols added only by coupling projection
    # P2 (additive) — the live-overlay reconcile outcome. Defaults describe the
    # store-authoritative path (no reconcile requested): nothing degraded, no conflict.
    lsp_degraded: bool = False  # a dirty file needed the live LSP overlay but it was absent/failed
    warnings: list[str] = field(default_factory=list)  # agent-readable (lsp_degraded, unreconciled)
    conflicts: list[FileConflict] = field(default_factory=list)  # SCIP↔LSP disagreements, surfaced
    overlay_only: list[str] = field(default_factory=list)  # F4: live symbols the store lacks
    # P4 (additive) — the replayable, watermarked search trace. ``None`` unless ``expand`` was
    # called with ``capture_trace=True``; the result is otherwise byte-identical to before.
    trace: SearchTrace | None = None


def is_test_file(path: str) -> bool:
    return bool(_TEST_FILE_RE.search(path))


def expand(
    store: Store,
    seed: str,
    *,
    k: int = 20,
    max_hops: int = 3,
    beam: int = 50,
    direction: str = "callers",
    include_coupling: bool = True,
    registry: ProbeRegistry | None = None,
    working_files: dict[str, bytes] | None = None,
    overlay: LspOverlay | None = None,
    capture_trace: bool = False,
    policy: ScorePolicy | None = None,
    now: int | None = None,
) -> ExpandResult:
    """Grow the relation subgraph from ``seed`` and rank it into a top-``k`` heatmap + gaps.

    The probe sequence is NOT hardcoded: the loop consults ``registry`` (defaulting to the
    core probe set — precise edge-walk then coupling projection). Probes run in registration
    order; the FIRST probe to claim a symbol wins, so precise evidence outranks inferred
    couplings (and any later-registered probe). New sources (LSP, contracts, the UACP
    cross-plane join) plug in by registering a probe — no change to this function.

    When ``working_files`` (a ``{path: current_bytes}`` snapshot of the dirty tree) is given,
    the query becomes reconcile-aware (P2, OD-1): every dirty node is reconciled against the
    live LSP ``overlay`` and tagged ``trusted``/``live``/``unreconciled``/``stale``. The
    overlay is always attempted and fail-soft — absent or failing, the query still returns
    and sets ``lsp_degraded``. With ``working_files=None`` the reconcile is skipped entirely
    and behaviour is byte-identical to the store-authoritative path (every node ``trusted``).
    """
    if registry is None:
        registry = default_registry(include_coupling=include_coupling)
    if policy is None:
        policy = default_policy()
    params = ProbeParams(k=k, max_hops=max_hops, beam=beam, direction=direction)
    ctx = ProbeContext(store=store, seed=seed, params=params, policy=policy, now=now)

    counts = {"precise": 0, "inferred": 0}
    hops: list[HopRecord] = []
    # P6: which distinct probes corroborated each symbol (admitted-or-not — a second probe
    # finding a node IS corroboration even when first-claim-wins drops its duplicate).
    found_by: dict[str, set[str]] = {}
    for probe in registry.probes:
        candidates: list[TraceCandidate] = []
        for entry in probe.expand(ctx):
            found_by.setdefault(entry.symbol, set()).add(probe.name)
            admitted = not (entry.symbol == seed or entry.symbol in ctx.entries)
            if capture_trace:
                candidates.append(
                    TraceCandidate(
                        symbol=entry.symbol,
                        score=entry.score,
                        hop=entry.hop,
                        via=entry.via,
                        source=entry.source,
                        admitted=admitted,
                    )
                )
            if not admitted:
                continue  # first claim wins — precise evidence (earlier probe) is never displaced
            ctx.entries[entry.symbol] = entry
            counts[probe.kind] = counts.get(probe.kind, 0) + 1
        if capture_trace:
            hops.append(HopRecord(probe=probe.name, kind=probe.kind, candidates=tuple(candidates)))

    # P6 multi-probe corroboration: add the policy's agreement bonus to each node BEFORE the
    # top-k cut (so corroboration can affect selection). Applied with conflicting=False here;
    # the reconcile below strips it from any node it later tags 'unreconciled'. ``core_scores``
    # keeps the pre-bonus score so that strip is exact.
    core_scores: dict[str, float] = {sym: e.score for sym, e in ctx.entries.items()}
    for sym, e in list(ctx.entries.items()):
        bonus = policy.agreement_bonus(len(found_by.get(sym, ())), False)
        if bonus:
            ctx.entries[sym] = replace(e, score=round(e.score + bonus, 6))

    ordered = sorted(ctx.entries.values(), key=lambda e: (-e.score, e.symbol))
    ranked = ordered[:k]

    lsp_degraded = False
    warnings: list[str] = []
    conflicts: list[FileConflict] = []
    overlay_only: list[str] = []
    if working_files is not None:
        rec = reconcile_overlay(store, ranked, working_files, overlay)
        ranked = rec.entries
        lsp_degraded = rec.lsp_degraded
        warnings = rec.warnings
        conflicts = rec.conflicts
        overlay_only = rec.overlay_only
        # Never boost an unreconciled node: strip the corroboration bonus from any node the
        # reconcile flagged 'unreconciled' (a SCIP↔overlay conflict is surfaced, not blended).
        stripped: list[HeatmapEntry] = []
        changed = False
        for e in ranked:
            if e.freshness == "unreconciled" and len(found_by.get(e.symbol, ())) > 1:
                stripped.append(replace(e, score=core_scores.get(e.symbol, e.score)))
                changed = True
            else:
                stripped.append(e)
        ranked = sorted(stripped, key=lambda e: (-e.score, e.symbol)) if changed else stripped

    gaps = find_test_gaps(store, ranked)

    trace: SearchTrace | None = None
    if capture_trace:
        repo_commit, built_at = store.watermark() or ("", "")
        trace = SearchTrace(
            seed=seed,
            query={
                "seed": seed,
                "k": k,
                "max_hops": max_hops,
                "beam": beam,
                "direction": direction,
                "include_coupling": include_coupling,
            },
            repo_commit=repo_commit,
            built_at=built_at,
            basis_hash=compute_basis_hash(store),
            hops=tuple(hops),
            # ``ranked`` is reconcile-tagged but order/scores are preserved, so the kept beam
            # is exactly the final heatmap order; the pruned beam is what the top-k cut dropped.
            result_order=tuple(e.symbol for e in ranked),
            pruned=tuple(
                TraceCandidate(
                    symbol=e.symbol,
                    score=e.score,
                    hop=e.hop,
                    via=e.via,
                    source=e.source,
                    admitted=True,
                )
                for e in ordered[k:]
            ),
        )

    return ExpandResult(
        heatmap=ranked,
        gaps=gaps,
        n_precise=counts.get("precise", 0),
        n_inferred=counts.get("inferred", 0),
        lsp_degraded=lsp_degraded,
        warnings=warnings,
        conflicts=conflicts,
        overlay_only=overlay_only,
        trace=trace,
    )


def find_test_gaps(store: Store, entries: list[HeatmapEntry]) -> list[Gap]:
    """Impacted symbols (in non-test files) that NO test file references — the actionable
    'changing this is unguarded' signal. Best-effort, deterministic, ordered by entry rank."""
    gaps: list[Gap] = []
    for e in entries:
        row = store.symbol(e.symbol)
        if row is None or not row.file or is_test_file(row.file):
            continue
        # any caller (edge dst=sym) whose source symbol lives in a test file?
        callers = store.con.execute("SELECT src FROM edges WHERE dst=?", (e.symbol,)).fetchall()
        tested = False
        for (src,) in callers:
            src_row = store.symbol(src)
            if src_row is not None and is_test_file(src_row.file):
                tested = True
                break
        if not tested:
            gaps.append(
                Gap(
                    symbol=e.symbol, file=row.file, reason="no test references this impacted symbol"
                )
            )
    return gaps

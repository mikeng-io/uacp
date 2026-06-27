"""Codeflair P6 — the swappable ``score()`` policy + the full Policy-D heat formula.

CF-D11 keeps the core loop deterministic (no LLM); P6 completes the *shape* of the
deterministic heat formula (03-expansion-loop) and exposes it behind one named, swappable
seam (OD-3). Policy-D is the default implementation; a future policy can replace it without
touching the probes, the loop, the outputs, or the trace — the benchmark (P5 recall@K)
measures any swap, so no A/B/C comparison machinery is built here.

The full Policy-D formula (03-expansion-loop), per node::

    heat(node) =  base_weight(source, rel)         # precision ladder (rel · provenance trust)
                × distance_decay ^ hop             # closer to the seed = hotter
                × recency_factor(last_change)      # recently-changed = hotter
                ÷ (1 + w_fanin · log(fan_in))      # down-weight ubiquitous utils
                + w_cc · co_change_PMI(seed, node) # temporal coupling (additive)
                + agreement · (probes_found − 1)   # multi-probe corroboration (additive)

The first three lines + the fan-in penalty + the PMI term are the per-node ``core``; the
corroboration term is the cross-probe ``agreement_bonus`` the expansion loop adds once it
knows how many probes found a node. CRITICAL (resolves the P2↔formula tension): the
corroboration bonus applies ONLY to non-conflicting nodes — it NEVER boosts a node the
reconcile tagged ``unreconciled`` (a SCIP↔overlay conflict). An unreconciled node is
surfaced, not up-weighted.

Determinism discipline (10-freshness): no wall-clock. ``recency_factor`` takes an INJECTED
reference point (``now``); it never reads the clock. Constants are benchmark-tuned starting
points (the *shape* is the spec); all arithmetic is pure + deterministic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ScoreSignals:
    """The per-node inputs a scoring policy reduces to one ``heat`` value.

    ``rel_weight`` × ``provenance_trust`` is the precision-ladder base weight of the
    strongest edge that reached the node; the rest are node-level signals. Defaults are the
    *neutral* element of each term (recency 1.0, fan-in 1, PMI 0, a single probe, no
    conflict) so a signal that is unavailable leaves the score unchanged — additive terms
    contribute 0, multiplicative terms contribute ×1.
    """

    rel_weight: float
    provenance_trust: float
    hop: int
    recency_factor: float = 1.0  # (0, 1]; 1.0 = most recent / unknown (neutral)
    fan_in: int = 1  # incoming-edge count; clamped to >= 1 (log(1) = 0 = neutral)
    co_change_pmi: float = 0.0  # PMI(seed_file, node_file); 0 = no temporal coupling
    probes_found: int = 1  # how many distinct probes corroborated the node
    conflicting: bool = False  # node is 'unreconciled' (SCIP↔overlay conflict) -> never boost


@runtime_checkable
class ScorePolicy(Protocol):
    """The swappable scoring seam (OD-3). ``score`` is the full per-node formula;
    ``agreement_bonus`` is the additive corroboration term the loop applies post-merge once
    the cross-probe count is known (kept separate so the loop can add it without re-deriving
    the multiplicative base)."""

    @property
    def name(self) -> str:
        """The policy's name. A READ-ONLY property in the Protocol (not a writable attribute):
        a writable protocol member is invariant, which would reject an implementer (PolicyD)
        that exposes ``name`` as a plain dataclass field. Read-only relaxes it to covariant
        read — any class with a readable ``name`` satisfies the seam (pyright-clean)."""
        ...

    def score(self, sig: ScoreSignals) -> float: ...

    def agreement_bonus(self, probes_found: int, conflicting: bool) -> float: ...


def recency_factor(changed_at: int, now: int | None, *, half_life: float = 30.0) -> float:
    """Recency weight in ``(0, 1]`` from an INJECTED reference point — more-recently-changed
    nodes score higher. ``changed_at``/``now`` are caller-supplied ordinals (commit index,
    epoch day, …); the store never reads the wall clock (determinism belongs to the gate).

    Half-life decay: ``0.5 ** (age / half_life)`` where ``age = max(now - changed_at, 0)``.
    age 0 (just changed) -> 1.0; age == ``half_life`` -> 0.5; older -> smaller. Neutral
    (1.0) when ``now`` is unknown or ``changed_at`` is unrecorded (<= 0), so an index without
    recency metadata is unaffected."""
    if now is None or changed_at <= 0 or half_life <= 0:
        return 1.0
    age = now - changed_at
    if age <= 0:
        return 1.0
    return 0.5 ** (age / half_life)


@dataclass(frozen=True)
class PolicyD:
    """The default deterministic policy (CF-D11). The four constants are benchmark-tuned
    starting points; the *shape* (each term, how combined) is the spec."""

    name: str = "policy-d"
    hop_decay: float = 0.5  # each hop from the seed halves contribution
    # Strength of the ÷(1 + w·log(fan_in)) ubiquity penalty. Tuned to 0.15 (benchmark): the
    # penalty must bite only for GENUINELY ubiquitous utils (fan-in in the tens/hundreds), not
    # flip a direct caller (fan-in 2) below a weaker same-hop edge. At 0.15: fan-in 2 ≈ −7%,
    # fan-in 50 ≈ −37%, fan-in 200 ≈ −44%. (0.5 demoted a fan-in-2 direct caller — regressed
    # the real-SCIP "closest caller ranks first" property.)
    w_fanin: float = 0.15
    w_cc: float = 0.15  # weight of the additive co-change-PMI temporal term
    agreement: float = 0.1  # per-extra-probe corroboration bonus (≈ 0.1, 03-expansion-loop)

    def score(self, sig: ScoreSignals) -> float:
        """The full Policy-D heat for one node (see module docstring for the formula)."""
        base = sig.rel_weight * sig.provenance_trust
        multiplicative = base * (self.hop_decay**sig.hop) * sig.recency_factor
        fan_in = sig.fan_in if sig.fan_in >= 1 else 1
        penalised = multiplicative / (1.0 + self.w_fanin * math.log(fan_in))
        core = penalised + self.w_cc * sig.co_change_pmi
        return core + self.agreement_bonus(sig.probes_found, sig.conflicting)

    def agreement_bonus(self, probes_found: int, conflicting: bool) -> float:
        """Additive multi-probe corroboration: ``agreement · (probes_found − 1)``. Zero for a
        single-probe node and ALWAYS zero for a conflicting (``unreconciled``) node — the
        corroboration term must never re-blend a SCIP↔overlay conflict."""
        if conflicting:
            return 0.0
        return self.agreement * max(probes_found - 1, 0)


# The package default. ``default_policy()`` returns it so callers (query.heatmap,
# expand, trace.replay) share one instance; pass an explicit policy to swap (OD-3).
_DEFAULT_POLICY = PolicyD()


def default_policy() -> ScorePolicy:
    """The default scoring policy (Policy-D). Callers that do not pass an explicit
    ``policy`` use this; a swap is a single argument, no other code changes (OD-3)."""
    return _DEFAULT_POLICY

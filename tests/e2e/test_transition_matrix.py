"""E2E: full transition matrix — every ordered (from, to) phase pair.

This is a deliberate bug-shaking matrix: 30 cells (6 phases x 6, minus the
diagonal). It pins the kernel's `Heartgate.validate_transition` against the legal
transition graph declared in `config/phase-transitions.yaml`
(triage -> propose -> plan -> execute -> verify -> resolved).

TWO LAYERS, KEPT SEPARATE
-------------------------
`validate_transition` runs BOTH the transition-GRAPH check and the always-on
adaptive evidence gates in one pass. A bare call (only from/to/run_id/
artifact_path, no seeded evidence) therefore mixes two distinct rejection
reasons, and this matrix must not conflate them:

  * GRAPH rejection  — the pair is not in the legal graph. core.py emits the
    blocker ``f"transition not allowed: {from_phase} -> {to_phase}"`` (see
    `Heartgate.validate_transition` / `_transition_allowed`). This is the layer
    this matrix tests.
  * EVIDENCE rejection — the pair IS legal, but an adaptive gate
    (e.g. `adaptive_proposal_package_gate` on propose->plan,
    `adaptive_plan_package_gate` on plan->execute) demands a package-selection
    artifact that this bare call does not seed. Those blockers are prefixed
    ``adaptive_..._gate:`` and never contain "transition not allowed". A legal
    pair blocked ONLY for this reason is NOT a graph bug, so this matrix must
    not fail it.

We discriminate purely on the substring ``"transition not allowed"``:

  * ALLOWED pair  -> assert NO graph blocker is present (it may still be blocked
                     by a missing-evidence gate — that is fine and expected for
                     propose->plan and plan->execute, which are exercised end to
                     end by test_full_lifecycle.py with real seeded evidence).
  * DISALLOWED pair -> assert decision == "block" AND a graph blocker IS present
                       AND .blockers is non-empty (a human-readable reason).

In all 30 cells the call must NEVER raise.

FAILURE POLICY: this task builds and records. It does not fix the kernel. A cell
that reveals a genuine kernel bug is marked xfail with a precise reason rather
than having its assertion weakened. As of authoring, the kernel passes all 30
cells cleanly (probed), so there are no xfails.
"""
from __future__ import annotations

import pytest

from core import Heartgate

PHASES = ["triage", "propose", "plan", "execute", "verify", "resolved"]

# The legal transition graph, mirroring config/phase-transitions.yaml's
# stages.<phase>.exits_to. This is the ground truth the matrix asserts against.
ALLOWED = {
    ("triage", "propose"),
    ("propose", "plan"),
    ("plan", "execute"),
    ("execute", "verify"),
    ("verify", "resolved"),
}

# The exact blocker substring core.py emits for an illegal-graph transition.
# Keying on this is what separates GRAPH rejection from EVIDENCE rejection.
GRAPH_BLOCKER = "transition not allowed"

PAIRS = [(f, t) for f in PHASES for t in PHASES if f != t]


def _graph_blocked(decision) -> bool:
    """True iff the decision was blocked for transition-GRAPH reasons."""
    return any(GRAPH_BLOCKER in b for b in decision.blockers)


@pytest.mark.parametrize("frm,to", PAIRS, ids=[f"{f}->{t}" for f, t in PAIRS])
def test_transition_cell(temp_uacp_root, valid_run_id, frm, to):
    hg = Heartgate.load(str(temp_uacp_root))

    # Must never raise — a raised exception is itself a kernel bug.
    decision = hg.validate_transition(
        {
            "from_phase": frm,
            "to_phase": to,
            "run_id": valid_run_id,
            "artifact_path": "plans/test.yaml",
        }
    )

    if (frm, to) in ALLOWED:
        # A legal pair must NEVER be rejected for graph reasons. It MAY still be
        # blocked by a missing-evidence adaptive gate (propose->plan,
        # plan->execute) — that is not a graph bug, so we only assert the
        # absence of a graph blocker here, not decision == "pass".
        assert not _graph_blocked(decision), (
            f"{frm}->{to} is a LEGAL transition but was graph-blocked: "
            f"{decision.blockers}"
        )
    else:
        # Every illegal pair must block, with a non-empty human-readable reason,
        # and that reason must include the graph rejection (not merely an
        # evidence gate that happened to fire).
        assert decision.decision == "block", (
            f"{frm}->{to} is ILLEGAL but decision was "
            f"{decision.decision!r}: {decision.blockers}"
        )
        assert decision.blockers, f"{frm}->{to} blocked without a reason"
        assert _graph_blocked(decision), (
            f"{frm}->{to} is ILLEGAL but was not rejected for graph reasons; "
            f"blockers were: {decision.blockers}"
        )

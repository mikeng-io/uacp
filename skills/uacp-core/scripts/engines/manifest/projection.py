"""Manifest-graph structural-integrity validator for UACP runs (codes ``GP_``).

Projects a run's manifest artifacts into an in-memory node/edge graph and asserts
its STRUCTURAL integrity — the serialization invariant behind the "no phantom /
no dropped intent" guarantee. This is the read-only ("Phase A") graduation of the
design spike (``design/graph-engine/spike/projector.py``); see decision ledger
D20/D29/D32 and ``23-final-review.md``.

Grounding (what the nodes/edges are):

* **scope_item** — each ``proposal.scope.in_scope`` item. New canonical form is a
  keyed mapping ``{id, statement}`` (its ``id`` is the node id); a legacy bare
  string is tolerated (a synthetic id is derived, which then reads as *uncovered* —
  correctly flagging a pre-keys run, never silently passing it).
* **work_unit** — each ``plan``/``execution`` ``work_units[]`` item (its ``id``).
  Its ``derives_from: [scope_item_id, ...]`` is the PROPOSE->PLAN edge.
* **evidence_obligation / checkpoint / assessment** — PIV obligations, EXECUTE
  checkpoints, and VERIFY assessments, linked by ``work_unit_id`` / ``obligation_id``
  / ``evidence_refs``.

What this engine checks — STRUCTURAL integrity only (always a defect, any phase):

* ``GP_UNCOVERED_INTENT``   — a ``scope_item`` with no inbound ``derives_from``
  (a declared intent no task serves: dropped intent).
* ``GP_ORPHAN_WORK_UNIT``   — a ``work_unit`` with no ``derives_from`` (a task with
  no parent intent: phantom work).
* ``GP_PHANTOM_EDGE``       — an edge whose target resolves to no node (a forged or
  dangling reference, e.g. ``derives_from`` a non-existent scope_item).
* ``GP_CONTRADICTED``       — a ``pass`` assessment whose evidence checkpoint rolled
  up to ``block`` (a "done" claim contradicted by its own failed evidence; ``warn``/
  ``deferred`` are legitimate close-with-deferred, not contradictions).

What this engine deliberately does NOT check (honest limits):

* **``unverified`` (progress/completeness).** A ``work_unit`` with no *passing*
  assessment is EXPECTED mid-run; it is only a defect at the VERIFY phase exit.
  That is a *phase-gated* check (Heartgate's concern at the relevant transition),
  not a structural always-block, so it is NOT emitted here (final-review T2).
* **Semantic correctness.** Closure proves coverage *topology*, not that a
  ``derives_from`` points at the *right* intent — an invented edge to a real-but-
  unrelated scope_item passes. That is a council concern (PROPOSE->PLAN gate), not
  computable here.

Architecture: read-only; all disk reads go through :mod:`engines.io`; never raises
(every failure becomes a Violation). Empty result == structurally sound.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from engines.base import ENGINES, Violation
from engines.io import load_artifact, load_manifest


def _v(code: str, message: str, severity: str = "block", **detail: Any) -> Violation:
    return Violation(code=code, severity=severity, message=message, detail=detail)


def _aslist(v: Any) -> list:
    return v if isinstance(v, list) else []


def _synth_id(prefix: str, text: str, run: str) -> str:
    return f"{prefix}-{hashlib.sha1(f'{run}:{text}'.encode()).hexdigest()[:8]}"


def _rollup_result(results: list) -> str | None:
    """Roll a checkpoint's evidence[].result values up to one outcome — worst wins (block > warn >
    deferred); 'pass' only if EVERY evidence result is 'pass'. Returns None when there is no
    evidence OR a result is missing/unknown — None is "indeterminate" (never a contradiction), so a
    legacy result is conservatively ignored, not mistaken for block."""
    for severity in ("block", "warn", "deferred"):
        if severity in results:
            return severity
    if results and all(r == "pass" for r in results):
        return "pass"
    return None


def _project(doc: dict, nodes: dict, edges: list, run: str) -> None:
    """Extract nodes + typed edges from one artifact doc into the shared graph."""

    def add_node(nid: str, kind: str, **extra: Any) -> None:
        nodes.setdefault(nid, {"id": nid, "kind": kind, **extra})

    def add_edge(src: str, dst: str, rel: str) -> None:
        edges.append({"src": src, "dst": dst, "rel": rel})

    scope = doc.get("scope")
    scope = scope if isinstance(scope, dict) else {}
    for item in _aslist(scope.get("in_scope")):
        if isinstance(item, dict) and item.get("id"):  # new canonical form
            add_node(item["id"], "scope_item", statement=item.get("statement", ""))
        elif isinstance(item, str):  # legacy bare string
            add_node(_synth_id("si", item, run), "scope_item", statement=item)

    for wu in _aslist(doc.get("work_units")):
        if isinstance(wu, dict) and wu.get("id"):
            add_node(wu["id"], "work_unit", intent=wu.get("intent", ""))
            # derives_from = the PROPOSE->PLAN coverage edge. NOTE (D42 producer gap): the real PIV
            # validator does NOT require it on work_units (only id/intent/expected_outputs), so the
            # coverage checks (GP_UNCOVERED/GP_ORPHAN) only bind once the PIV producer emits it —
            # the producer-side coverage emission is the documented follow-on; the projection reads
            # it when present.
            for dst in _aslist(wu.get("derives_from")):
                add_edge(wu["id"], dst, "derives_from")

    for ob in _aslist(doc.get("evidence_obligations")):
        if isinstance(ob, dict) and ob.get("id"):
            add_node(ob["id"], "evidence_obligation")
            if ob.get("work_unit_id"):
                add_edge(ob["id"], ob["work_unit_id"], "obligation_for")

    # execution_checkpoint (D42): the REAL shape is ONE doc per checkpoint (top-level checkpoint_id
    # + work_unit_id + evidence[]), NOT a doc carrying a `checkpoints[]` list (the spike). Map each
    # such doc to one checkpoint node, rolling its outcome up from evidence[].result.
    cp_id = doc.get("checkpoint_id")
    if cp_id:
        ev_items = [ev for ev in _aslist(doc.get("evidence")) if isinstance(ev, dict)]
        add_node(cp_id, "checkpoint", result=_rollup_result([ev.get("result") for ev in ev_items]))
        if doc.get("work_unit_id"):
            add_edge(cp_id, doc["work_unit_id"], "checkpoint_of")
        # Per-obligation evidence outcome as an `evidence` node: the REAL assessment<->checkpoint
        # join is the shared obligation_id (both validated vs the PIV), so recording each evidence
        # result against its obligation is what lets GP_CONTRADICTED bind on real producer output
        # (the free-text evidence_refs join does not). Carry whether this is a REMEDIATION
        # checkpoint: only a remediation pass clears an earlier block (a normal pass must not, else
        # a pass-then-block regression would be wrongly cleared).
        is_remediation = doc.get("checkpoint_type") == "remediation"
        for ev in ev_items:
            ev_oid = ev.get("obligation_id")
            if ev_oid:
                add_node(
                    f"ev::{cp_id}::{ev_oid}",
                    "evidence",
                    obligation_id=ev_oid,
                    result=ev.get("result"),
                    remediation=is_remediation,
                )

    for a in _aslist(doc.get("assessments")):
        if not isinstance(a, dict):
            continue
        oid = a.get("obligation_id")
        aid = a.get("id") or _synth_id("as", str(oid), run)
        add_node(aid, "assessment", result=a.get("state") or a.get("result"), obligation_id=oid)
        if oid:
            add_edge(aid, oid, "obligation_id")
        if a.get("work_unit_id"):
            add_edge(aid, a["work_unit_id"], "work_unit_id")
        for ref in _aslist(a.get("evidence_refs")):
            if isinstance(ref, str):
                add_edge(aid, ref, "evidence_refs")


# --- individual checks (each operates on the projected (nodes, edges)) --------
#
# STRUCTURAL (always a defect, any phase): uncovered / orphan / phantom /
# contradicted. PHASE-GATED coverage (a defect only once that layer's artifacts
# exist — enforced at the transition where the inputs first complete, D35):
# obligation-coverage / checkpoint-coverage / unverified. Each check self-gates
# by iterating only the nodes whose layer is present, so an empty/earlier-phase
# graph yields no false positives.


# Scope-coverage adoption gate (D43): the intent->task coverage checks (uncovered/orphan) bind on
# `derives_from` edges, which require keyed scope_items the PROPOSE producer does not yet emit
# (proposal scope is markdown today — the unresolved D43 scope-serialization decision). Until a run
# ADOPTS the coverage layer (emits >=1 derives_from edge), these two checks SKIP — else activating
# the gate would false-flood every real run as all-orphan/all-uncovered. Once adopted, they bind
# fully (a dropped intent / unanchored task among covered siblings is a real defect). The OTHER
# checks (phantom/contradicted) and the execute/verify coverage checks do NOT depend on scope_items
# and stay unconditional.
def _coverage_adopted(edges: list) -> bool:
    return any(e["rel"] == "derives_from" for e in edges)


def _check_uncovered(nodes: dict, edges: list) -> list[Violation]:
    if not _coverage_adopted(edges):
        return []
    df_dst = {e["dst"] for e in edges if e["rel"] == "derives_from"}
    return [
        _v(
            "GP_UNCOVERED_INTENT",
            f"scope_item '{n['id']}' has no work_unit deriving from it "
            f"(dropped intent): «{(n.get('statement') or '')[:60]}»",
            scope_item=n["id"],
        )
        for n in nodes.values()
        if n["kind"] == "scope_item" and n["id"] not in df_dst
    ]


def _check_orphan(nodes: dict, edges: list) -> list[Violation]:
    if not _coverage_adopted(edges):
        return []
    df_src = {e["src"] for e in edges if e["rel"] == "derives_from"}
    return [
        _v(
            "GP_ORPHAN_WORK_UNIT",
            f"work_unit '{n['id']}' has no derives_from to any scope_item (unanchored task)",
            work_unit=n["id"],
        )
        for n in nodes.values()
        if n["kind"] == "work_unit" and n["id"] not in df_src
    ]


def _check_phantom(nodes: dict, edges: list) -> list[Violation]:
    return [
        _v(
            "GP_PHANTOM_EDGE",
            f"edge {e['src']} --{e['rel']}--> {e['dst']} targets a node that "
            f"does not exist (forged/dangling reference)",
            src=e["src"],
            dst=e["dst"],
            rel=e["rel"],
        )
        for e in edges
        if e["dst"] not in nodes
    ]


def _check_contradicted(nodes: dict, edges: list) -> list[Violation]:
    # A pass assessment whose evidence FAILED (rolled up to BLOCK) is the contradiction. `block` is
    # the sole "failed" outcome (the validator allows ready_with_deferred_items), so a `warn`/
    # `deferred` checkpoint under a pass assessment is a LEGITIMATE close-with-deferred, not a
    # contradiction. Two joins: (A) the REAL, producer-present join — a pass assessment for an
    # obligation that has a block `evidence` item; (B) the explicit evidence_refs -> checkpoint_id
    # ref, for producers that emit it. Deduped per assessment.
    cp_result = {n["id"]: n.get("result") for n in nodes.values() if n["kind"] == "checkpoint"}
    # An obligation is "blocked" if it has block evidence that no REMEDIATION pass cleared. A plain
    # (non-remediation) pass must NOT clear it — order-blind set logic would otherwise let an
    # earlier pass cancel a LATER block (a regression). Only a checkpoint_type=remediation pass
    # clears (Codex P2): the doc carries checkpoint_type but not seq, so remediation is the
    # order-free disambiguator (residual third-order edge — block -> remediation-pass -> block-again
    # — needs real seq ordering, a producer follow-on).
    has_block: set[str] = set()
    cleared: set[str] = set()
    for n in nodes.values():
        if n["kind"] != "evidence" or not n.get("obligation_id"):
            continue
        oid = n["obligation_id"]
        if n.get("result") == "block":
            has_block.add(oid)
        elif n.get("result") == "pass" and n.get("remediation"):
            cleared.add(oid)
    blocked_obls = has_block - cleared
    flagged: dict[str, Violation] = {}
    # path A — shared obligation_id (binds on real producer output)
    for n in nodes.values():
        if (
            n["kind"] == "assessment"
            and n.get("result") == "pass"
            and n.get("obligation_id") in blocked_obls
        ):
            flagged[n["id"]] = _v(
                "GP_CONTRADICTED",
                f"assessment '{n['id']}' claims pass but its obligation "
                f"'{n['obligation_id']}' has block evidence",
                assessment=n["id"],
                obligation_id=n.get("obligation_id"),
            )
    # path B — explicit evidence_refs -> checkpoint_id (when the producer emits checkpoint refs)
    for e in edges:
        if e["rel"] != "evidence_refs":
            continue
        asmt = nodes.get(e["src"], {})
        if (
            asmt.get("result") == "pass"
            and cp_result.get(e["dst"]) == "block"
            and e["src"] not in flagged
        ):
            flagged[e["src"]] = _v(
                "GP_CONTRADICTED",
                f"assessment '{e['src']}' claims pass but its evidence "
                f"checkpoint '{e['dst']}' is 'block'",
                assessment=e["src"],
                checkpoint=e["dst"],
            )
    return list(flagged.values())


def _check_obligation_coverage(nodes: dict, edges: list) -> list[Violation]:
    covered = {e["dst"] for e in edges if e["rel"] == "obligation_for"}
    return [
        _v(
            "GP_WORK_UNIT_NO_OBLIGATION",
            f"work_unit '{n['id']}' has no evidence_obligation "
            f"(nothing will be required of it at EXECUTE)",
            work_unit=n["id"],
        )
        for n in nodes.values()
        if n["kind"] == "work_unit" and n["id"] not in covered
    ]


def _check_checkpoint_coverage(nodes: dict, edges: list) -> list[Violation]:
    covered = {e["dst"] for e in edges if e["rel"] == "checkpoint_of"}
    return [
        _v(
            "GP_WORK_UNIT_NO_CHECKPOINT",
            f"work_unit '{n['id']}' has no EXECUTE checkpoint (no evidence it was performed)",
            work_unit=n["id"],
        )
        for n in nodes.values()
        if n["kind"] == "work_unit" and n["id"] not in covered
    ]


def _check_unverified(nodes: dict, edges: list) -> list[Violation]:
    # A work_unit is verified iff a passing assessment links to it — directly (work_unit_id edge) OR
    # transitively via its obligation (assessment.obligation_id -> obligation --obligation_for-->
    # work_unit). Real PIV assessments carry obligation_id, NOT the optional work_unit_id, so the
    # transitive path is the one that binds on producer output.
    obl_to_wu = {e["src"]: e["dst"] for e in edges if e["rel"] == "obligation_for"}
    passing: set[str] = set()
    for n in nodes.values():
        if n["kind"] == "assessment" and n.get("result") == "pass":
            wu = obl_to_wu.get(n.get("obligation_id"))
            if wu:
                passing.add(wu)
    for e in edges:
        if e["rel"] == "work_unit_id" and nodes.get(e["src"], {}).get("result") == "pass":
            passing.add(e["dst"])
    return [
        _v(
            "GP_UNVERIFIED",
            f"work_unit '{n['id']}' has no passing assessment "
            f"(claimed done without verified evidence)",
            work_unit=n["id"],
        )
        for n in nodes.values()
        if n["kind"] == "work_unit" and n["id"] not in passing
    ]


# Terminal (closure) check set — STRUCTURAL only; the phase-gated coverage
# checks are NOT run here (they have a transition-of-enforcement, final-review T2).
_TERMINAL_CHECKS = (_check_uncovered, _check_orphan, _check_phantom, _check_contradicted)

# Phase-keyed gates (D35): the subset enforced at each transition, keyed by the
# `from_phase`-exit gate where each check's inputs first complete.
_SCOPE_CHECKS = {
    "plan_exit": (_check_uncovered, _check_orphan, _check_phantom, _check_obligation_coverage),
    "execute_exit": (_check_checkpoint_coverage,),
    "verify_exit": (_check_unverified, _check_contradicted),
}


def _load_and_project(workspace: str | Path, run_id: str) -> tuple[dict, list] | None:
    """Load a run's manifest, project every artifact into one (nodes, edges)
    graph. Returns None when there is no usable manifest (nothing to project)."""
    root = Path(str(workspace)).resolve()
    loaded = load_manifest(root, run_id)
    if loaded.error is not None or loaded.value is None:
        return None
    artifacts = loaded.value.raw.get("artifacts")
    if not isinstance(artifacts, dict):
        return None
    # Goal-chained runs REUSE parent prior-phase outputs via inherited_artifacts
    # (triage/proposal/plan refs copied at init), not their own `artifacts`. Project
    # those too — otherwise a child run's coverage graph is missing the inherited
    # scope_items/work_units and a dropped intent silently passes. Own artifacts are
    # projected FIRST so a child's re-authored doc wins over an inherited one
    # (add_node uses setdefault).
    inherited = loaded.value.raw.get("inherited_artifacts")
    rels = list(artifacts.values())
    if isinstance(inherited, dict):
        rels += list(inherited.values())
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    for rel in rels:
        if not isinstance(rel, str) or not rel:
            continue
        doc = load_artifact(root, rel)
        if doc.error is None and isinstance(doc.value, dict):
            _project(doc.value, nodes, edges, run_id)
    return nodes, edges


def _validate_inputs(workspace: str | Path, run_id: str) -> list[Violation] | None:
    """Shared input guard for the public entry points (None == inputs OK)."""
    try:
        Path(str(workspace)).resolve()
    except Exception as exc:
        return [_v("GP0_WORKSPACE_INVALID", f"workspace path invalid: {type(exc).__name__}: {exc}")]
    if not run_id or not isinstance(run_id, str):
        return [_v("GP0_RUN_ID_INVALID", f"run_id invalid: {run_id!r}")]
    return None


def validate_graph_projection(workspace: str | Path, run_id: str) -> list[Violation]:
    """Project the run's manifest artifacts into a graph and assert structural
    integrity (terminal / closure set). Returns a list of Violation (empty ==
    sound). Never raises. The phase-gated coverage checks are NOT run here — they
    are enforced at their transition via :func:`validate_graph_invariants`."""
    if (bad := _validate_inputs(workspace, run_id)) is not None:
        return bad
    graph = _load_and_project(workspace, run_id)
    if graph is None:
        # No manifest -> nothing to project (other engines own "manifest missing").
        return []
    nodes, edges = graph
    out: list[Violation] = []
    for check in _TERMINAL_CHECKS:
        out.extend(check(nodes, edges))
    return out


def validate_graph_invariants(workspace: str | Path, run_id: str, scope: str) -> list[Violation]:
    """Run the phase-scoped subset of structural checks for one transition gate
    (D35). ``scope`` is the ``<from_phase>_exit`` key (``plan_exit`` /
    ``execute_exit`` / ``verify_exit``); each check self-gates so a graph that
    has not yet reached that layer yields no false positives. Returns a list of
    Violation (empty == sound for this gate). Never raises."""
    if (bad := _validate_inputs(workspace, run_id)) is not None:
        return bad
    checks = _SCOPE_CHECKS.get(scope)
    if checks is None:
        return [
            _v(
                "GP0_UNKNOWN_SCOPE",
                f"unknown phase-gate scope: {scope!r} (expected one of {sorted(_SCOPE_CHECKS)})",
                scope=scope,
            )
        ]
    graph = _load_and_project(workspace, run_id)
    if graph is None:
        return []
    nodes, edges = graph
    out: list[Violation] = []
    for check in checks:
        out.extend(check(nodes, edges))
    return out


# Register this engine (guard against double-registration under alias imports).
if not any(name == "graph_projection" for name, _ in ENGINES):
    ENGINES.append(("graph_projection", validate_graph_projection))

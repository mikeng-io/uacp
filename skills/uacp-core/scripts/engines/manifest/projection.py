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
import re
from pathlib import Path
from typing import Any

from config import base_dir
from engines.base import ENGINES, Violation
from engines.domain.artifact_hashes import content_hash, load_hash_index
from engines.domain.layout import CATALOG_VERSION
from engines.domain.verification_floor import CLASSES, candidate_class, class_rank, load_floor
from engines.io import load_artifact, load_manifest, resolve_in_workspace


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

    # uacp.check.* — a generated, FROZEN verification check (capsule #3, slice 0). Project it as a
    # `check` node carrying its replay payload (catalog kind + bind + expect + severity) and a
    # `measured_by` edge to the target it proves, so the check-coverage gate can require every
    # target carry a check and the replay engine (validate_check_replay) can re-run it. NET-NEW
    # arm: a check doc matches none of the structural extractors below, so without this arm it
    # projects ZERO nodes (the built-vs-new correction in design node 30 — not "for free").
    doc_kind = doc.get("kind")
    if isinstance(doc_kind, str) and doc_kind.startswith("uacp.check.") and doc.get("id"):
        frm = doc.get("from")
        frm = frm if isinstance(frm, dict) else {}
        bind = doc.get("bind")
        add_node(
            doc["id"],
            "check",
            check_kind=doc_kind,
            bind=bind if isinstance(bind, dict) else {},
            expect=doc.get("expect"),
            severity=str(doc.get("severity") or "block"),
            # `from.class` = the generator's recorded comprehension of the target's class (capsule
            # #3 slice 2 / design node 34 L2); `from.basis` = the text it derived from. The floor
            # engine reads `class` to require a class-appropriate check kind per target.
            target_class=frm.get("class"),
            basis=frm.get("basis"),
            catalog_version=doc.get("catalog_version"),
        )
        target = frm.get("target")
        if target:
            add_edge(doc["id"], str(target), "measured_by")

    # uacp.investigation_entry — one move in the verify loop (capsule #3 node 13). Project it as an
    # `investigation_entry` node carrying its move/verdict and a `supersedes` edge to the entry it
    # revises, so the open-investigation closure check + the dry-predicate read the latest trail.
    if doc_kind == "uacp.investigation_entry" and doc.get("entry_id"):
        add_node(
            doc["entry_id"],
            "investigation_entry",
            move=doc.get("move"),
            verdict=doc.get("verdict"),
            check_ref=doc.get("check_ref"),
            inv_target=doc.get("target"),
        )
        sup = doc.get("supersedes")
        if sup:
            add_edge(doc["entry_id"], str(sup), "supersedes")

    scope = doc.get("scope")
    scope = scope if isinstance(scope, dict) else {}
    for item in _aslist(scope.get("in_scope")):
        if isinstance(item, dict) and item.get("id"):  # new canonical form
            anchor = item.get("anchor")
            add_node(
                item["id"],
                "scope_item",
                statement=item.get("statement", ""),
                # PROTOTYPE (grounding retarget): `entailed_class` is the class attributed to this
                # target by an INDEPENDENT oracle (code-plane entailment from the real symbol, or an
                # independent judge reading the MD) — NOT the agent's self-declared check class and
                # NOT prose the gate greps. It is the B1-era grounding the underclaim gate measures.
                entailed_class=item.get("entailed_class"),
                # SLICE 1 (anchor primitive): YAML node → MD section pointer. Carried so the
                # resolution validator can check it; recorded as an `anchored_to` edge below.
                anchor=anchor,
            )
            # One-directional: YAML names the anchor, MD holds the content. An anchor-at-nothing is
            # caught by validate_anchor_resolution (a FAIL, not a silent pass).
            if anchor:
                add_edge(item["id"], str(anchor), "anchored_to")
        elif isinstance(item, str):  # legacy bare string
            add_node(_synth_id("si", item, run), "scope_item", statement=item)

    for wu in _aslist(doc.get("work_units")):
        if isinstance(wu, dict) and wu.get("id"):
            # `expected_outputs` is carried too: node 34 L2b derives the candidate class from the
            # work_unit's intent AND expected_outputs, so strong content can't be hidden there.
            add_node(
                wu["id"],
                "work_unit",
                intent=wu.get("intent", ""),
                expected_outputs=wu.get("expected_outputs"),
                # PROTOTYPE (grounding retarget): independent-oracle class — see scope_item above.
                entailed_class=wu.get("entailed_class"),
            )
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


# Scope-coverage adoption gate (D43): used now ONLY by the ORPHAN check. A work_unit
# with no `derives_from` should not be flooded as an orphan in a run that has adopted NO
# coverage edges at all (the pre-keys / unprojected-coverage shape). UNCOVERED no longer
# uses this gate — an intent that nothing derives from is uncovered on scope PRESENCE (it
# self-gates on "are there any scope_item nodes?"), so a run that declares intents and
# covers NONE is caught rather than skipped. Phantom/contradicted and the execute/verify
# coverage checks do not depend on scope_items and stay unconditional.
def _coverage_adopted(edges: list) -> bool:
    return any(e["rel"] == "derives_from" for e in edges)


def _check_uncovered(nodes: dict, edges: list) -> list[Violation]:
    # Fire whenever scope_items are PRESENT: an uncovered intent is uncovered whether
    # or not ANY derives_from edge exists. Skipping only on no-edges (the old adoption
    # gate) over-skipped the worst case — a run that declares intents but covers NONE.
    # We skip ONLY when there are no scope_item nodes at all (nothing declared to
    # cover: a pre-keys / unprojected-scope run), which is the real false-flood guard.
    scope_items = [n for n in nodes.values() if n["kind"] == "scope_item"]
    if not scope_items:
        return []
    df_dst = {e["dst"] for e in edges if e["rel"] == "derives_from"}
    return [
        _v(
            "GP_UNCOVERED_INTENT",
            f"scope_item '{n['id']}' has no work_unit deriving from it "
            f"(dropped intent): «{(n.get('statement') or '')[:60]}»",
            scope_item=n["id"],
        )
        for n in scope_items
        if n["id"] not in df_dst
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
        # `anchored_to` (SLICE 1) is the ONE edge whose dst is intentionally NOT a graph node — it
        # is a YAML→MD section pointer (e.g. "proposals/x.md#si-1"). Its integrity is enforced by
        # validate_anchor_resolution (file/heading/non-empty), NOT by node membership, so it must be
        # excluded here or every anchored node would falsely trip GP_PHANTOM_EDGE.
        if e["dst"] not in nodes and e["rel"] != "anchored_to"
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


def _check_unchecked_target(nodes: dict, edges: list) -> list[Violation]:
    # Adequacy Layer 1 (design node 34): once a run has ADOPTED the generative gate,
    # every scope_item/work_unit must be `measured_by` >=1 frozen check — the
    # structural half of "prove each task" (replay proves the checks that exist pass;
    # this proves a check exists per target). Reuses the coverage pattern exactly:
    # projection emits a `measured_by` edge per check; a target with no inbound one is
    # GP_UNCHECKED_TARGET (block). Self-gates on ADOPTION (>=1 `check` node), mirroring
    # ORPHAN's derives_from adoption gate, so the existing suite — which authors no
    # checks — is never flooded.
    #
    # HONEST LIMIT (do not overclaim): this proves a check NAMES each target, not that the
    # check's assertion is RELEVANT to it. Coverage reads the agent-declared `from.target`
    # edge; the check's actual `bind` (what replay evaluates) is decoupled from that target —
    # so a check that names `wu-1` but binds a trivial field on an unrelated artifact still
    # satisfies coverage (and can still pass replay). Closing that — check-relevance / honest
    # class — is the required-kinds floor (node 34 L2), content-entailment (L2b), the council
    # (L3), and ultimately the code plane (class entailed from the real symbol), NOT this gate.
    # Adoption-gating likewise means this closes only RECURSIVE/PARTIAL omission (class D —
    # checks for some targets, a risky one dropped); it does NOT force a zero-check run to adopt
    # checks (L2). Structural coverage is necessary, not sufficient.
    if not any(n["kind"] == "check" for n in nodes.values()):
        return []
    measured = {e["dst"] for e in edges if e["rel"] == "measured_by"}
    return [
        _v(
            "GP_UNCHECKED_TARGET",
            f"{n['kind']} '{n['id']}' is measured_by no check "
            f"(claimed work with no frozen verification)",
            target=n["id"],
            target_kind=n["kind"],
        )
        for n in nodes.values()
        if n["kind"] in ("scope_item", "work_unit") and n["id"] not in measured
    ]


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


def _open_investigation_ids(nodes: dict, edges: list) -> list[str]:
    """The OPEN investigation entries (node 13, fail-closed): a `fail`/`error` move that no acyclic
    chain of newer revisions RESOLVES with a `pass`. Only a passing remediation clears a failure — a
    later non-pass revision (another fail, or a non-measuring move) does NOT, and a supersede CYCLE
    reaches no pass, so cycled/self-superseding failures stay open. (Council: the naive "superseded
    = any inbound supersedes edge" let a 2+ cycle, a non-resolving supersede, and a self-supersede
    erase a recorded failure.)"""
    entries = {n["id"]: n for n in nodes.values() if n["kind"] == "investigation_entry"}
    newer: dict[str, set[str]] = {}  # newer[A] = entries that supersede A (its revisions)
    for e in edges:
        if (
            e["rel"] == "supersedes"
            and e["src"] != e["dst"]
            and e["src"] in entries
            and e["dst"] in entries
        ):
            newer.setdefault(e["dst"], set()).add(e["src"])

    def resolved_by_pass(start: str) -> bool:
        # Acyclic forward walk over revisions: is `start` (or any revision of it) a `pass`?
        seen, stack = {start}, [start]
        while stack:
            cur = stack.pop()
            if entries[cur].get("verdict") == "pass":
                return True
            for nxt in newer.get(cur, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return False

    return [
        eid
        for eid, n in entries.items()
        if n.get("verdict") in ("fail", "error") and not resolved_by_pass(eid)
    ]


def _check_open_investigation(nodes: dict, edges: list) -> list[Violation]:
    """An OPEN investigation blocks (node 13 — the ledger's teeth + the no-self-attesting-closure
    invariant): a `fail`/`error` investigation_entry that no `pass` remediation resolved is an open
    move. ERROR is fail-closed (never a pass)."""
    by_id = {n["id"]: n for n in nodes.values()}
    return [
        _v(
            "GP_OPEN_INVESTIGATION",
            f"investigation_entry '{eid}' is {by_id[eid].get('verdict')!r} and unresolved "
            f"(no passing remediation supersedes it — done cannot close over it)",
            entry=eid,
            verdict=by_id[eid].get("verdict"),
        )
        for eid in _open_investigation_ids(nodes, edges)
    ]


# Terminal (closure) check set — STRUCTURAL only; the phase-gated coverage checks
# (obligation/checkpoint/unverified) are NOT run here (they have a transition-of-enforcement and
# legitimate close-with-deferred reasons to be absent at terminal — final-review T2). EXCEPTION:
# _check_unchecked_target IS a terminal backstop (council/opencode) — unlike those, it is
# adoption-gated and a HARD invariant (a run that adopted checks must cover every target), and the
# closure sweep (run_all_engines) is the one gate that runs on EVERY closure regardless of path, so
# coverage is enforced at BOTH the verify_exit transition and closure — robust to any bypass path.
_TERMINAL_CHECKS = (
    _check_uncovered,
    _check_orphan,
    _check_phantom,
    _check_contradicted,
    _check_unchecked_target,
    _check_open_investigation,
)

# Phase-keyed gates (D35): the subset enforced at each transition, keyed by the
# `from_phase`-exit gate where each check's inputs first complete.
_SCOPE_CHECKS = {
    "plan_exit": (_check_uncovered, _check_orphan, _check_phantom, _check_obligation_coverage),
    "execute_exit": (_check_checkpoint_coverage,),
    # verify_exit also re-runs _check_phantom so a check whose `from.target` is a ghost node is
    # caught HERE (the gate it was authored into), not only at terminal closure (reviewer finding).
    "verify_exit": (
        _check_unverified,
        _check_contradicted,
        _check_unchecked_target,
        _check_phantom,
        _check_open_investigation,
    ),
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
    # SLICE 1 wiring: a declared anchor that does not resolve FAILs at closure (inert without
    # anchors). The closure sweep runs on EVERY close, so the "never a silent pass" guarantee holds.
    out.extend(_anchor_violations(nodes, Path(str(workspace)).resolve()))
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
    # SLICE 1 wiring: a declared anchor that does not resolve FAILs at the phase exit too (inert
    # without anchors) — so the guarantee is enforced at the transition, not only at closure.
    out.extend(_anchor_violations(nodes, Path(str(workspace)).resolve()))
    # The REPLAY half of "prove each task" on the FORCED path: coverage (above) proves a check
    # EXISTS per target; replay proves the checks that exist PASS. Enforcing coverage at
    # verify_exit but replay only at closure would let a run exit VERIFY with FAILING checks
    # (reviewer finding) — so a failing/erroring frozen check blocks the VERIFY exit here too.
    if scope == "verify_exit":
        out.extend(validate_check_replay(workspace, run_id))
        out.extend(validate_check_floor(workspace, run_id))
        out.extend(validate_class_underclaim(workspace, run_id))
    return out


def investigation_status(workspace: str | Path, run_id: str) -> dict:
    """The investigation convergence read (node 13 dry-predicate). Returns a dict with ``dry``
    (bool), ``open`` (entry ids), ``contradictions``, and ``entries`` (the total entry count).

    DRY == the verify loop has no OPEN move left to resolve: no ``fail``/``error`` move left
    unresolved by a passing remediation, AND no open ``GP_CONTRADICTED`` (the ``reconcile`` signal,
    node 13). The harness reads this to decide keep-generating-vs-stop; the open set ALSO blocks
    closure via ``GP_OPEN_INVESTIGATION``. Fail-closed: an ``error`` keeps it not-dry; a load/input
    failure -> ``dry=False`` rather than a false convergence. NB ``dry=True`` + ``entries==0`` means
    "no investigation recorded yet" (not-started), distinct from converged-after-work — the harness
    should check ``entries`` to tell them apart. Never raises."""
    if _validate_inputs(workspace, run_id) is not None:
        return {"dry": False, "open": [], "contradictions": [], "entries": 0, "error": "bad input"}
    graph = _load_and_project(workspace, run_id)
    if graph is None:
        return {"dry": True, "open": [], "contradictions": [], "entries": 0}
    nodes, edges = graph
    open_ids = _open_investigation_ids(nodes, edges)
    contradictions = [v.detail for v in _check_contradicted(nodes, edges)]
    total = sum(1 for n in nodes.values() if n["kind"] == "investigation_entry")
    return {
        "dry": not open_ids and not contradictions,
        "open": open_ids,
        "contradictions": contradictions,
        "entries": total,
    }


# N: how many failing moves on ONE target before the harness stops patching and emits the
# architecture verdict (node 11 ESCALATE; loop-engineering "3 failed fixes -> question the design").
# A default; per-phase/risk tuning (via the goal-driven budget) is a documented follow-on.
_ESCALATE_THRESHOLD = 3


def escalation_candidates(
    workspace: str | Path, run_id: str, threshold: int = _ESCALATE_THRESHOLD
) -> list[dict]:
    """Architecture-verdict candidates (node 11 ESCALATE): a target on which >= ``threshold``
    failing investigation moves accumulated AND which is STILL OPEN (no passing remediation resolved
    it) — the deterministic rule for "the design, not the code, is wrong; stop patching symptoms."
    A READ only: the harness fires ``uacp_escalation_event`` for each candidate (the writer exists).
    The target is already blocked by ``GP_OPEN_INVESTIGATION``; this is the escalate SIGNAL atop it.
    Never raises."""
    if _validate_inputs(workspace, run_id) is not None:
        return []
    graph = _load_and_project(workspace, run_id)
    if graph is None:
        return []
    nodes, edges = graph
    open_targets = {
        nodes[eid].get("inv_target")
        for eid in _open_investigation_ids(nodes, edges)
        if eid in nodes
    }
    fails: dict[str, int] = {}
    for n in nodes.values():
        tgt = n.get("inv_target")
        if n["kind"] == "investigation_entry" and n.get("verdict") in ("fail", "error") and tgt:
            fails[tgt] = fails.get(tgt, 0) + 1
    return [
        {"target": t, "failed_moves": c}
        for t, c in sorted(fails.items())
        if c >= threshold and t in open_targets
    ]


def convergence_status(
    workspace: str | Path, run_id: str, escalate_threshold: int = _ESCALATE_THRESHOLD
) -> dict:
    """The harness LOOP+ESCALATE read (node 11) in one call: the node-13 dry-predicate
    (:func:`investigation_status`) PLUS the escalation verdict — which targets crossed the
    failed-fix threshold and are still open. Returns the ``investigation_status`` dict + an
    ``escalate`` list. The harness loops while not ``dry`` and escalates those targets."""
    status = investigation_status(workspace, run_id)
    status["escalate"] = escalation_candidates(workspace, run_id, escalate_threshold)
    return status


# --- the replay engine (capsule #3, slice 0) -----------------------------------
#
# The deterministic re-execution of the FROZEN typed checks projected above as
# `check` nodes (design nodes 30/31/32). NO agent code runs here — each kind has a
# fixed evaluator that compares the check's `expect` (data) against the bound
# reality (data). Fail-closed: a bind that cannot resolve or an unknown kind is an
# ERROR, and ERROR is always a BLOCK, never a silent pass (#503 class A). Slice 0
# binds the RELATION (`graph`) + `artifact` planes only; `code`/`behavior` planes
# ERROR-block until wired (fail-closed-until-wired — node 32).

_MISSING = object()


def _read_path(doc: dict, path: str) -> Any:
    """Read a dotted json-path out of an artifact mapping; _MISSING if any segment
    is absent. Lists are addressable by integer index segment."""
    cur: Any = doc
    for seg in str(path).split(".") if path else []:
        if isinstance(cur, dict) and seg in cur:
            cur = cur[seg]
        elif (
            isinstance(cur, list) and seg.lstrip("-").isdigit() and -len(cur) <= int(seg) < len(cur)
        ):  # noqa: E501
            cur = cur[int(seg)]
        else:
            return _MISSING
    return cur


def _obligation_satisfied(oid: str, nodes: dict) -> tuple[str, str]:
    """Graph-plane: is evidence_obligation ``oid`` satisfied in the projected manifest? PASS iff a
    passing assessment binds to it AND it has no UNCLEARED block evidence — the same node semantics
    `_check_unverified`/`_check_contradicted` use, so the frozen check and the structural gates
    agree. ERROR (fail-closed, #503 class A) when ``oid`` resolves to no obligation node — an
    unresolvable bind is never a silent pass."""
    if not oid or not any(
        n.get("kind") == "evidence_obligation" and n["id"] == oid for n in nodes.values()
    ):
        return ("ERROR", f"obligation {oid!r} not found in manifest graph (unresolvable bind)")
    passing = any(
        n.get("kind") == "assessment"
        and n.get("obligation_id") == oid
        and n.get("result") == "pass"
        for n in nodes.values()
    )
    ev = [
        n for n in nodes.values() if n.get("kind") == "evidence" and n.get("obligation_id") == oid
    ]
    has_block = any(n.get("result") == "block" for n in ev)
    cleared = any(n.get("result") == "pass" and n.get("remediation") for n in ev)
    if passing and not (has_block and not cleared):
        return ("PASS", "")
    return (
        "FAIL",
        f"obligation {oid} not satisfied (passing_assessment={passing}, "
        f"uncleared_block={has_block and not cleared})",
    )


def _evaluate_check(
    root: Path, kind: str, bind: dict, expect: Any, edge_set: set, nodes: dict, hash_index: dict
) -> tuple[str, str]:
    """Return (PASS|FAIL|ERROR, detail) for one frozen check. Pure: data vs data (the code plane
    resolves against the run's Codeflair index)."""
    # symbol_resolves is the ONE wired code-plane kind (slice 3): resolve the bound symbol against
    # the run's SCIP index via the code_plane adapter (fail-closed when no index / no codeflair),
    # handled BEFORE the unwired-plane guard which still ERRORs every OTHER code/behavior kind.
    if kind == "uacp.check.symbol_resolves":
        from engines.code_plane import resolve_symbol

        ref = bind.get("ref")
        ref = ref if isinstance(ref, dict) else {}
        return resolve_symbol(root, str(ref.get("symbol") or ""))
    # behavioral is the ONE wired behavior-plane kind (node 32 slice 0): run the declared argv
    # command in an isolated subprocess and bind to its result, handled BEFORE the unwired-plane
    # guard (which still ERRORs every OTHER behavior/code kind).
    if kind == "uacp.check.behavioral":
        from engines.behavior_plane import resolve_behavior

        return resolve_behavior(root, bind, expect)
    # Fail-closed-until-wired guard (council/mimo #2): ANY OTHER kind declaring the code/behavior
    # plane ERRORs (block) until those planes are built, so an implemented kind can't be mislabeled
    # onto an unwired plane (e.g. a field_equals authored with `plane: code`).
    if bind.get("plane") in ("code", "behavior"):
        return ("ERROR", f"{kind}: the {bind.get('plane')} plane is not wired yet (fail-closed)")

    if kind == "uacp.check.edge_exists":
        triple = (str(bind.get("src")), str(bind.get("rel")), str(bind.get("dst")))
        return ("PASS", "") if triple in edge_set else ("FAIL", f"edge {triple} absent")

    if kind == "uacp.check.obligation_satisfied":
        return _obligation_satisfied(str(bind.get("obligation_id") or ""), nodes)

    if kind in (
        "uacp.check.field_equals",
        "uacp.check.field_present",
        "uacp.check.artifact_integrity",
    ):
        ref = bind.get("ref")
        ref = ref if isinstance(ref, dict) else {}
        # SLICE 2 — anchor binding mode (opt-in): when bind.ref.anchor is set, resolve the anchored
        # MD section and assert ONLY its presence (section resolves + non-empty). No artifact key is
        # required. Content adequacy is NEVER judged here — that stays council's. Anchor mode is
        # PRESENCE-ONLY, so it is valid ONLY for field_present; a field_equals carries an
        # `expect.value` that a presence read cannot honor (it would silently degrade to presence),
        # so field_equals+anchor is a fail-closed ERROR. artifact_integrity verifies a watermark,
        # not a section, so it has no anchor semantic either (falls through to the artifact path).
        # Detect a DECLARED anchor by key presence, not truthiness (codex bot P2 on #70): a
        # present-but-empty `anchor: ""` is a broken anchor and must FAIL, never silently fall back
        # to the legacy artifact/path binding. Anchor mode is presence-only → valid ONLY for
        # field_present; any other kind (field_equals, artifact_integrity) with a declared anchor is
        # a fail-closed ERROR.
        if "anchor" in ref:
            anchor = ref.get("anchor")
            if not isinstance(anchor, str) or not anchor.strip():
                return ("ERROR", "bind.ref.anchor is declared but empty/invalid")
            if kind == "uacp.check.field_present":
                return _resolve_anchor_section(root, anchor)
            return (
                "ERROR",
                f"{kind} does not support anchor binding (anchor mode is presence-only); "
                "use field_present for an anchored section",
            )
        art = ref.get("artifact")
        if not art:
            return ("ERROR", "bind.ref.artifact missing")
        loaded = load_artifact(root, str(art))
        if loaded.error is not None or not isinstance(loaded.value, dict):
            return ("ERROR", f"cannot bind artifact {art!r}: {loaded.error or 'not a mapping'}")
        if kind == "uacp.check.artifact_integrity":
            # REAL integrity (council/kimi: was a no-op PASS — a usable gaming vector). Verify the
            # artifact's CURRENT content against its recorded watermark (state/hashes). No watermark
            # -> ERROR (integrity unverifiable, fail-closed — #503 class A), NOT a silent pass; a
            # hash mismatch -> FAIL (out-of-band tamper since the governed write). Reuses the same
            # watermark the AI_ artifact-integrity engine uses, so the check and that engine agree.
            recorded = hash_index.get(str(art))
            if not recorded:
                return ("ERROR", f"no watermark recorded for {art!r} — integrity unverifiable")
            try:
                raw = (base_dir(root) / str(art)).read_text(encoding="utf-8")
            except OSError as exc:
                return ("ERROR", f"cannot read {art!r} for integrity: {exc}")
            if content_hash(raw) == recorded:
                return ("PASS", "")
            return ("FAIL", f"{art} content diverged from its watermark (out-of-band tamper)")
        val = _read_path(loaded.value, str(ref.get("path") or ""))
        if kind == "uacp.check.field_present":
            empty = val is _MISSING or val in (None, "", [], {})
            return ("FAIL", f"{ref.get('path')!r} missing/empty") if empty else ("PASS", "")
        exp = expect.get("value") if isinstance(expect, dict) else _MISSING
        if val is not _MISSING and val == exp:
            return ("PASS", "")
        return ("FAIL", f"{ref.get('path')!r} = {val!r} != expected {exp!r}")

    return ("ERROR", f"unknown check kind {kind!r}")


def validate_check_replay(workspace: str | Path, run_id: str) -> list[Violation]:
    """Re-run every FROZEN ``uacp.check.*`` projected for the run against its bound
    reality; emit a ``CHK_*`` Violation on FAIL/ERROR (ERROR always block — class A).
    One ``Engine`` in the shared ``run_all_engines`` sweep. Never raises."""
    if (bad := _validate_inputs(workspace, run_id)) is not None:
        return bad
    graph = _load_and_project(workspace, run_id)
    if graph is None:
        return []
    nodes, edges = graph
    root = Path(str(workspace)).resolve()
    edge_set = {(e["src"], e["rel"], e["dst"]) for e in edges}
    hash_index = load_hash_index(workspace, run_id)  # artifact_integrity watermark lookup (once)
    out: list[Violation] = []
    for n in nodes.values():
        if n.get("kind") != "check":
            continue
        kind = str(n.get("check_kind") or "")
        # CATALOG VERSION guard (node 30): a check whose recorded catalog_version is present but is
        # NOT the current one was authored under a DIFFERENT catalog whose kind semantics we cannot
        # vouch for — refuse it (ERROR, block) rather than re-run it under today's evaluators. A
        # missing version is tolerated (legacy/raw checks); the writer injects the current version.
        # NB the coverage/floor/entailment gates count a check's EXISTENCE (not its replay outcome),
        # so a foreign-version check still satisfies them at projection — but it blocks HERE, and
        # removing it re-triggers GP_UNCHECKED_TARGET; either path is fail-closed (council).
        cv = n.get("catalog_version")
        if cv is not None and str(cv) != CATALOG_VERSION:
            out.append(
                _v(
                    "CHK_CATALOG_VERSION",
                    f"check '{n['id']}' was authored under catalog_version {cv!r} != current "
                    f"{CATALOG_VERSION!r} — its kind semantics are not vouched for (re-author it)",
                    severity="block",
                    check=n["id"],
                    status="ERROR",
                )
            )
            continue
        bind = n.get("bind") if isinstance(n.get("bind"), dict) else {}
        try:
            status, detail = _evaluate_check(
                root, kind, bind, n.get("expect"), edge_set, nodes, hash_index
            )
        except Exception as exc:  # any evaluator raise is an ERROR (block), never a pass
            status, detail = "ERROR", f"{type(exc).__name__}: {exc}"
        if status in ("FAIL", "ERROR"):
            code = "CHK_" + (kind.removeprefix("uacp.check.") or "UNKNOWN").upper()
            # FAIL and ERROR both BLOCK — the check's own declared `severity` is NOT trusted to
            # downgrade a failing gate check (reviewer finding: a gated agent could author its
            # check as `severity: warn` and ship failing work non-blocked). A slice-0 check GATES;
            # policy-graded (advisory) severities are an L2 concern and, when added, must not count
            # toward coverage.
            sev = "block"
            out.append(
                _v(
                    code,
                    f"check '{n['id']}' ({kind}) {status}: {detail}",
                    severity=sev,
                    check=n["id"],
                    status=status,
                )
            )
    return out


def validate_check_floor(workspace: str | Path, run_id: str) -> list[Violation]:
    """Required-kinds FLOOR (design node 34 Layer 2): a target whose checks declare class X must
    carry >=1 check of a floor[X]-required kind, else ``CHK_FLOOR_UNMET`` (block). This closes the
    weakness coverage cannot — a present-but-weak check (e.g. ``field_present`` on a "wire up X"
    target). Self-limits to DECLARED classes: a target whose checks declare no class places no floor
    requirement here (that omission is Layer 2b's content cross-check, a follow-on). The floor table
    is loaded fail-closed (config YAML or the shipped code default). Never raises.

    Honest residual (do NOT overclaim): the class is the AGENT-declared ``from.class`` — the floor
    forces a class-appropriate KIND given an honest class, not an honest class. Layer 2b (content
    entailment) shrinks the mis-classification surface; only the code plane closes it."""
    if (bad := _validate_inputs(workspace, run_id)) is not None:
        return bad
    graph = _load_and_project(workspace, run_id)
    if graph is None:
        return []
    nodes, edges = graph
    floor = load_floor(workspace)
    check_nodes = {n["id"]: n for n in nodes.values() if n.get("kind") == "check"}
    inbound: dict[str, list[str]] = {}
    for e in edges:
        if e["rel"] == "measured_by":
            inbound.setdefault(e["dst"], []).append(e["src"])
    out: list[Violation] = []
    for tnode in nodes.values():
        if tnode["kind"] not in ("scope_item", "work_unit"):
            continue
        cids = [cid for cid in inbound.get(tnode["id"], []) if cid in check_nodes]
        present_kinds = {str(check_nodes[cid].get("check_kind") or "") for cid in cids}
        declared = {check_nodes[cid].get("target_class") for cid in cids}
        for cls in sorted(c for c in declared if c in floor):
            required = set(floor[cls])
            if not (present_kinds & required):
                out.append(
                    _v(
                        "CHK_FLOOR_UNMET",
                        f"target '{tnode['id']}' is class '{cls}' but carries no check of a "
                        f"required kind {sorted(required)} (has {sorted(present_kinds)})",
                        target=tnode["id"],
                        target_class=cls,
                        required=sorted(required),
                        present=sorted(present_kinds),
                    )
                )
    return out


def validate_class_underclaim(workspace: str | Path, run_id: str) -> list[Violation]:
    """Layer 2b — class ENTAILMENT (design node 34): derive a CANDIDATE class from a target's own
    intent/statement text; if the strongest class its checks DECLARE is weaker than the content
    implies, the agent under-classified to satisfy the floor with a weak kind -> a block violation
    (block). Catches the omitted-class dodge too (undeclared = rank 0). Heuristic + PARTIAL: it
    raises the cost of mis-classification (the intent text must also be corrupted), it does not
    make class honesty deterministic — only the code plane does; Layer 3 owns the residual. Never
    raises."""
    if (bad := _validate_inputs(workspace, run_id)) is not None:
        return bad
    graph = _load_and_project(workspace, run_id)
    if graph is None:
        return []
    nodes, edges = graph
    check_nodes = {n["id"]: n for n in nodes.values() if n.get("kind") == "check"}
    inbound: dict[str, list[str]] = {}
    for e in edges:
        if e["rel"] == "measured_by":
            inbound.setdefault(e["dst"], []).append(e["src"])
    out: list[Violation] = []
    for tnode in nodes.values():
        if tnode["kind"] not in ("scope_item", "work_unit"):
            continue
        cids = [cid for cid in inbound.get(tnode["id"], []) if cid in check_nodes]
        if not cids:
            continue
        declared_rank = max(
            (class_rank(check_nodes[cid].get("target_class")) for cid in cids), default=0
        )
        # The ORACLE: an independent derivation of the target's true class, to cross-check the
        # agent's (weaker) declared class. This gate is fundamentally an INDEPENDENCE check, not a
        # prose check — the prose keyword-match was only a cheap independent oracle that happened
        # to live in the YAML the gate could read. Two sources, strongest wins (ADDITIVE ratchet):
        #   1. `entailed_class` (PROTOTYPE / B1): the class an INDEPENDENT source attributes to the
        #      target — code-plane entailment from the real symbol (deterministic, the docstring's
        #      "only the code plane" owner) or an independent judge reading the MD. Survives B1
        #      because it does NOT depend on prose being in the YAML.
        #   2. `candidate_class(prose)` (LEGACY): the intent/expected_outputs/statement keyword
        #      match. Kept so pre-B1 runs (prose in YAML) stay caught; dark once prose moves to MD.
        eo = tnode.get("expected_outputs")
        eo_text = " ".join(map(str, eo)) if isinstance(eo, list) else str(eo or "")
        text = " ".join(s for s in (tnode.get("intent"), eo_text, tnode.get("statement")) if s)
        cand, kw = candidate_class(text)
        entailed = tnode.get("entailed_class")
        # FAIL-CLOSED on a malformed oracle (codex P2 #70): `entailed_class` is the INDEPENDENT
        # grounding signal, so a present-but-unknown value (e.g. a typo `wire_symbol`) must NOT
        # silently degrade to "no oracle" (class_rank → 0) and let a weak declared class pass — it
        # blocks instead. A truly absent (None) oracle is fine (prose / no-witness path).
        if entailed is not None and entailed not in CLASSES:
            out.append(
                _v(
                    "CHK_ENTAILED_CLASS_INVALID",
                    f"target '{tnode['id']}' declares unknown entailed_class {entailed!r} "
                    f"(not one of {sorted(CLASSES)}) — the grounding oracle must fail closed",
                    target=tnode["id"],
                    entailed_class=str(entailed),
                )
            )
            continue
        # Pick the strongest oracle that fires, preferring the grounded `entailed_class`.
        if class_rank(entailed) >= class_rank(cand) and class_rank(entailed) > 0:
            oracle_cls, oracle_src, oracle_basis = entailed, "entailed_class", "independent oracle"
        else:
            oracle_cls, oracle_src, oracle_basis = cand, "prose", f"matched «{kw}»"
        if oracle_cls and class_rank(oracle_cls) > declared_rank:
            out.append(
                _v(
                    "CHK_CLASS_UNDERCLAIM",
                    f"target '{tnode['id']}' implies class '{oracle_cls}' ({oracle_basis}, via "
                    f"{oracle_src}) but its checks declare a weaker class — mis-classification "
                    f"under the floor",
                    target=tnode["id"],
                    candidate=oracle_cls,
                    keyword=kw,
                    oracle_source=oracle_src,
                    declared_rank=declared_rank,
                )
            )
    return out


_ANCHOR_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_ANCHOR_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")


def _resolve_anchor_section(root: Path, anchor: str) -> tuple[str, str]:
    """Deterministic read for a YAML→MD anchor ``"relpath#section"`` (SLICE 1). PASS iff:
    the file resolves UNDER the governed root (containment via ``resolve_in_workspace`` — parity
    with the artifact loaders, so an anchor cannot read outside ``.uacp/``); a heading whose text
    EXACTLY equals ``section`` exists; and that section's body — everything down to the next heading
    of the SAME-OR-SHALLOWER level (deeper sub-headings' content is INCLUDED), with fenced code
    blocks treated as opaque body and their ``#`` lines NOT counted as headings — has
    non-whitespace. Duplicate headings: PASS if ANY matching section is non-empty. Asserts ONLY
    presence; adequacy stays council's. Returns ``(PASS|FAIL|ERROR, message)``; never raises.

    CONTRACT (deliberate scope): this is a pragmatic PRESENCE FLOOR with simple structural
    fence/heading handling, NOT a CommonMark parser — full CommonMark conformance is a NON-GOAL.
    Adversarial fence/heading micro-edges (mismatched-length nested fences, info strings, indented
    fences, setext headings, …) are ACCEPTED, not chased: the check makes no adequacy claim (council
    owns that), the MD is an author-controlled governed artifact (this is a drift/anti-fabrication
    floor, not a boundary against the author), and the checks are opt-in/inert — so fooling the
    section boundary gains nothing. If a real CommonMark guarantee is ever needed, swap this scan
    for a parser library wholesale rather than accreting per-edge fixes."""
    relpath, sep, frag = str(anchor).partition("#")
    if not relpath or not sep or not frag:
        return ("FAIL", f"anchor {anchor!r} is not 'relpath#section'")
    resolved = resolve_in_workspace(root, relpath)
    if resolved is None:  # escapes the governed root (../, absolute, …) — never read outside .uacp
        return ("FAIL", f"anchor path escapes the governed root: {relpath}")
    if not resolved.is_file():
        return ("FAIL", f"anchor target file missing: {relpath}")
    try:
        raw = resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:  # unreadable/undecodable is ERROR, never a raise
        return ("ERROR", f"anchor target unreadable: {relpath}: {exc}")

    fence_char = ""  # "" when not in a fence; "`" or "~" = the OPENING fence's marker char
    in_section = False
    section_level = 0
    found_match = False
    body: list[str] = []
    for line in raw.splitlines():
        fm = _ANCHOR_FENCE_RE.match(line)
        if fm is not None:
            marker = fm.group(1)[0]
            if not fence_char:
                fence_char = marker  # open a fence
            elif marker == fence_char:
                fence_char = ""  # CommonMark: a fence closes only with its OWN marker char
            # a non-matching fence marker inside an open fence is literal code content
            if in_section:
                body.append(line)
            continue
        m = None if fence_char else _ANCHOR_HEADING_RE.match(line)
        if m is not None:
            this_level = len(m.group(1))
            if in_section and this_level <= section_level:
                if any(s.strip() for s in body):
                    return ("PASS", "")  # a matching section had content — done
                in_section = False  # this match was empty; keep scanning for a later duplicate
                body = []
            if not in_section and m.group(2) == frag:
                in_section, found_match, section_level = True, True, this_level
            continue
        if in_section:
            body.append(line)
    if in_section and any(s.strip() for s in body):
        return ("PASS", "")
    if found_match:
        return ("FAIL", f"anchor section #{frag} in {relpath} is empty")
    return ("FAIL", f"anchor section #{frag} not found in {relpath}")


def _anchor_violations(nodes: dict, root: Path) -> list[Violation]:
    """SLICE 1 core: a ``GP_ANCHOR_UNRESOLVED`` for every node whose declared ``anchor`` does not
    resolve. Pure over already-projected nodes so the wired gates can call it without re-projecting.
    INERT: nodes without an ``anchor`` contribute nothing, so existing (anchor-free) runs are
    unaffected. Currently only ``scope_item`` nodes carry an ``anchor`` (the schema field added in
    Slice 1); other node kinds simply never match."""
    out: list[Violation] = []
    for n in nodes.values():
        anchor = n.get("anchor")
        # ABSENT (key not declared) is inert; PRESENT-but-empty ("" / whitespace) is a DECLARED but
        # broken anchor and must FAIL (codex re-review) — `_resolve_anchor_section("")` already
        # returns FAIL, so we only skip the truly-absent case here.
        if anchor is None:
            continue
        status, msg = _resolve_anchor_section(root, str(anchor))
        if status != "PASS":
            out.append(
                _v(
                    "GP_ANCHOR_UNRESOLVED",
                    f"node {n['id']}: {msg}",
                    target=n["id"],
                    anchor=str(anchor),
                )
            )
    return out


def validate_anchor_resolution(workspace: str | Path, run_id: str) -> list[Violation]:
    """SLICE 1 — anchor primitive (public entry: projects then checks). An anchor pointing at
    nothing is a FAIL, not a silent pass — this stops the model re-introducing a NEW drift. Wired
    into ``validate_graph_projection`` (closure) and ``validate_graph_invariants`` (phase exits) so
    the guarantee holds in real runs, not only when called directly. Never raises."""
    if (bad := _validate_inputs(workspace, run_id)) is not None:
        return bad
    graph = _load_and_project(workspace, run_id)
    if graph is None:
        return []
    return _anchor_violations(graph[0], Path(str(workspace)).resolve())


# Register this engine (guard against double-registration under alias imports).
if not any(name == "graph_projection" for name, _ in ENGINES):
    ENGINES.append(("graph_projection", validate_graph_projection))
if not any(name == "check_replay" for name, _ in ENGINES):
    ENGINES.append(("check_replay", validate_check_replay))
if not any(name == "check_floor" for name, _ in ENGINES):
    ENGINES.append(("check_floor", validate_check_floor))
if not any(name == "check_class_underclaim" for name, _ in ENGINES):
    ENGINES.append(("check_class_underclaim", validate_class_underclaim))

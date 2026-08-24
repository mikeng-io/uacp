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
import json
import re
from pathlib import Path
from typing import Any

from config import get_config
from engines.base import ENGINES, Violation
from engines.domain.artifact_hashes import content_hash, load_hash_index
from engines.domain.layout import CATALOG_VERSION
from engines.domain.verification_floor import (
    CLASSES,
    candidate_class,
    class_rank,
    load_floor,
    witness_class,
)
from engines.io import (
    DiffContentResult,
    changed_files,
    derive_witness,
    diff_content,
    glob_in_workspace,
    load_artifact,
    load_manifest,
    load_yaml_under_root,
    resolve_in_workspace,
)

# M2's evidence-reference resolver (engines/rework_completeness.py): an artifact named AS PROOF is
# proven by RESOLUTION (run-bound + exists + loads), never its bare presence as a string. The
# correctness findings gate reuses it for `discharged` dispositions — importing, not duplicating,
# the rule (design/grounded-governance/03 §"Findings reuse the disposition grounding"). No cycle:
# rework_completeness imports only config / engines.base / engines.io, never this projection.
from engines.rework_completeness import _artifact_resolves


def _v(code: str, message: str, severity: str = "block", **detail: Any) -> Violation:
    return Violation(code=code, severity=severity, message=message, detail=detail)


def _aslist(v: Any) -> list:
    return v if isinstance(v, list) else []


def _carry_code_refs(raw: Any) -> list[dict[str, str]] | None:
    """Carry a target's declared ``code_refs`` onto its projected node (class witness, node 03).

    Returns a list of ``{file, name}`` string dicts, or ``None`` when the field is absent,
    empty, or MALFORMED (not a list, or any entry not a ``{file, name}`` pair of non-empty
    strings). Defensive by design: the write-time schema for the package docs is OPEN-world, so
    the projection reads possibly hand-authored/tampered state — a malformed shape carries as
    ``None`` (no witness feed for that target — byte-identical to no claim), never a partial/
    silently-dropped list. An empty list is a no-claim, so it also carries as ``None``."""
    if not isinstance(raw, list):
        return None
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            return None
        f = item.get("file")
        n = item.get("name")
        if not (isinstance(f, str) and f and isinstance(n, str) and n):
            return None
        out.append({"file": f, "name": n})
    return out or None


def _synth_id(prefix: str, text: str, run: str) -> str:
    return f"{prefix}-{hashlib.sha1(f'{run}:{text}'.encode()).hexdigest()[:8]}"


def _seq_of_key(key: Any) -> int | None:
    """Extract the authoring ``seq`` from a multi-instance artifact registration key.

    The entity-writer registers placeholder-bearing kinds under a composite key
    ``<type>:k=v-…`` (e.g. ``check.field_equals:seq=3``); ``seq`` is that instance's monotonic
    authoring counter — the ONE load-order-independent ordering signal available at projection.
    Single-instance kinds (plain ``proposal``/``plan``) and hand-registered/legacy artifacts carry
    no ``seq`` -> None (dedup then keeps first-wins, the historical behavior)."""
    m = re.search(r"(?:^|[-:])seq=(\d+)(?:$|-)", str(key))
    return int(m.group(1)) if m else None


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


def _project(
    doc: dict,
    nodes: dict,
    edges: list,
    run: str,
    seq: int | None = None,
    node_seq: dict[str, int | None] | None = None,
    check_edges: dict[str, str | None] | None = None,
) -> None:
    """Extract nodes + typed edges from one artifact doc into the shared graph.

    ``seq`` is THIS doc's authoring sequence (parsed from its multi-instance registration key,
    ``…:seq=N``); ``node_seq`` and ``check_edges`` are shared ledgers (id->seq, id->measured_by
    target) used to keep ``check``-node dedup CONSISTENT across nodes AND their edges — see
    ``add_node`` and _load_and_project's deferred check-edge emission."""
    ns = node_seq if node_seq is not None else {}
    ce = check_edges if check_edges is not None else {}

    def add_node(nid: str, kind: str, measured_by: str | None = None, **extra: Any) -> None:
        existing = nodes.get(nid)
        if existing is None:
            nodes[nid] = {"id": nid, "kind": kind, **extra}
            if kind == "check":
                ns[nid] = seq if isinstance(seq, int) else None
                ce[nid] = measured_by  # emitted at the end (deferred), only for the winning copy
            return
        # DEDUP TIE-BREAK (#131), DEFENCE-IN-DEPTH ONLY — NOT the security boundary. The real teeth
        # live at AUTHORING: create_entity rejects a second uacp.check.* that reuses a frozen `id`
        # at a new path, so a governed run can never register two same-id checks. This branch only
        # disambiguates duplicates that BYPASS governed authoring (a hand-`register`ed / legacy /
        # externally-crafted manifest). It is deliberately NOT adversary-proof: `seq` is
        # caller-supplied, so a hostile author who could also register directly could pick `seq=0`
        # — closing that is the authoring-time uniqueness guard's job, not this one. Here we only
        # need a DETERMINISTIC (load-order-independent) pick, and lowest-seq gives one; the node's
        # measured_by edge is carried with it so the graph never mixes the winner's node payload
        # with a loser's edge (Codex P1). NON-check kinds keep first-wins — a deliberate ordering
        # guarantee (own-over-inherited, see _load_and_project), not a bug.
        if kind != "check" or existing.get("kind") != "check":
            return
        old_seq = ns.get(nid)
        if isinstance(seq, int) and isinstance(old_seq, int) and seq < old_seq:
            nodes[nid] = {"id": nid, "kind": kind, **extra}
            ns[nid] = seq
            ce[nid] = measured_by  # winner's edge replaces the displaced copy's

    def add_edge(src: str, dst: str, rel: str) -> None:
        edges.append({"src": src, "dst": dst, "rel": rel})

    # uacp.check.* — a generated, FROZEN verification check (capsule #3, slice 0). Project it as a
    # `check` node carrying its replay payload (catalog kind + bind + expect + severity) and a
    # `measured_by` edge to the target it proves, so the check-coverage gate can require every
    # target carry a check and the replay engine (validate_check_replay) can re-run it. NET-NEW
    # arm: a check doc matches none of the structural extractors below, so without this arm it
    # projects ZERO nodes (the built-vs-new correction in design node 30 — not "for free"). The
    # measured_by edge is passed THROUGH add_node (not add_edge) and emitted at the end for the
    # winning copy only, so node+edge dedup stay consistent under a same-id collision (Codex P1).
    doc_kind = doc.get("kind")
    if isinstance(doc_kind, str) and doc_kind.startswith("uacp.check.") and doc.get("id"):
        frm = doc.get("from")
        frm = frm if isinstance(frm, dict) else {}
        bind = doc.get("bind")
        target = frm.get("target")
        add_node(
            doc["id"],
            "check",
            # measured_by target travels WITH the node through dedup so a losing same-id copy's
            # edge is never emitted (Codex P1); _load_and_project materialises it at the end.
            measured_by=str(target) if target else None,
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
                # CLASS WITNESS (node 03): the target's declared code symbol(s). Carried so
                # validate_class_underclaim can feed the codeflair connectivity witness. Malformed
                # -> None (defensive; the package docs are open-world at write time).
                code_refs=_carry_code_refs(item.get("code_refs")),
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
                # CLASS WITNESS (node 03): the work_unit's declared code symbol(s) — mirror of the
                # scope_item carry above. Malformed -> None (defensive).
                code_refs=_carry_code_refs(wu.get("code_refs")),
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
    # (add_node keeps first-wins for every non-check kind).
    inherited = loaded.value.raw.get("inherited_artifacts")
    # (key, rel): the KEY carries a multi-instance artifact's authoring `seq` (…:seq=N),
    # the only load-order-independent signal for deterministic check-node dedup (#131).
    pairs = list(artifacts.items())
    if isinstance(inherited, dict):
        pairs += list(inherited.items())
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    node_seq: dict[str, int | None] = {}
    # check id -> its winning copy's measured_by target (deferred so a losing same-id copy's edge
    # is never emitted — node/edge dedup consistency, Codex P1).
    check_edges: dict[str, str | None] = {}
    for key, rel in pairs:
        if not isinstance(rel, str) or not rel:
            continue
        doc = load_artifact(root, rel)
        if doc.error is None and isinstance(doc.value, dict):
            _project(doc.value, nodes, edges, run_id, _seq_of_key(key), node_seq, check_edges)
    for cid, dst in check_edges.items():
        if dst is not None:
            edges.append({"src": cid, "dst": dst, "rel": "measured_by"})
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
    # PREVENTION-at-PLAN forecast (design node 04): a NEW phase-bound check joins the
    # plan_exit forced-gate invocation point (its first subprocess prober). It reads the
    # run's SCOPE (code_refs + write_paths) — a concern the scope-conformance engine owns —
    # so it is imported locally to keep the projection<->scope_conformance dependency one-
    # directional. Advisory (warn) + it writes its own forecast of record; it never blocks.
    if scope == "plan_exit":
        from engines.scope_conformance import validate_cascade_forecast

        out.extend(validate_cascade_forecast(workspace, run_id))
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
        if kind == "uacp.check.artifact_integrity":
            # REAL integrity (was a no-op PASS — a gaming vector). Verify the artifact's CURRENT
            # content against its recorded watermark (state/hashes). It reads RAW bytes and must
            # NOT YAML-parse the artifact, so plain-text (.txt) evidence (e.g. pytest output) binds
            # fine (#116; the load_artifact YAML-parse below previously rejected it with a
            # ScannerError before this check ran). No watermark -> ERROR (unverifiable, fail-closed,
            # #503 class A), not a silent pass; hash mismatch -> FAIL (out-of-band tamper).
            recorded = hash_index.get(str(art))
            if not recorded:
                return ("ERROR", f"no watermark recorded for {art!r} — integrity unverifiable")
            # Containment: resolve UNDER the governed root before reading, so an escaping path
            # (../, absolute, symlink) fails closed even with a matching watermark — parity with
            # the load_artifact guard this branch now precedes (#116 codex P2). Never read outside.
            resolved = resolve_in_workspace(root, str(art))
            if resolved is None:
                return ("ERROR", f"integrity artifact path escapes the governed root: {art}")
            try:
                raw = resolved.read_text(encoding="utf-8")
            except OSError as exc:
                return ("ERROR", f"cannot read {art!r} for integrity: {exc}")
            if content_hash(raw) == recorded:
                return ("PASS", "")
            return ("FAIL", f"{art} content diverged from its watermark (out-of-band tamper)")
        # field_equals / field_present read a field from a parsed mapping — these DO require YAML:
        loaded = load_artifact(root, str(art))
        if loaded.error is not None or not isinstance(loaded.value, dict):
            return ("ERROR", f"cannot bind artifact {art!r}: {loaded.error or 'not a mapping'}")
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


# Source-code file suffixes the GIT WITNESS reads as "code changed" (design/verify-substrate/02,
# M3). A witnessed change set touching any of these obliges the run to carry a behavioral check;
# a docs/config/design-only change set carries no such obligation.
_CODE_SUFFIXES = (
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".go",
    ".rs",
    ".rb",
    ".java",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".sh",
)

# Safe migration default for CHK_BEHAVIORAL_FLOOR_UNMET — "warn", never "block": a
# block-by-accident (bad config, unread key) would break every live code-changing run.
_BEHAVIORAL_FLOOR_DEFAULT_SEVERITY = "warn"


def _behavioral_floor_severity(root: Path) -> str:
    """Config-gated severity for ``CHK_BEHAVIORAL_FLOOR_UNMET``, read from
    ``[verification] behavioral_floor`` (default ``warn``, flips to ``block`` in a later
    named release — the SC_DIFF migration precedent, design/verify-substrate/02). Only the
    literals ``warn``/``block`` are honored; an absent/invalid value -> ``warn`` (the safe
    migration default — block-by-accident breaks runs). Never raises."""
    try:
        cfg = get_config(root).model_dump()
        raw = (cfg.get("verification") or {}).get("behavioral_floor")
        if raw in ("warn", "block"):
            return raw
        return _BEHAVIORAL_FLOOR_DEFAULT_SEVERITY
    except Exception:
        return _BEHAVIORAL_FLOOR_DEFAULT_SEVERITY


def validate_behavioral_floor(workspace: str | Path, run_id: str) -> list[Violation]:
    """Behavioral FLOOR (design/verify-substrate/02, M3): when the GIT WITNESS shows the run
    changed CODE, the run must carry >=1 behavioral check — which replay then RUNS, turning
    behaviour into grounded substrate — else ``CHK_BEHAVIORAL_FLOOR_UNMET``.

    This closes the loophole :func:`validate_check_floor` leaves: that floor self-limits to the
    AGENT-DECLARED ``from.class``, so a doer routes around the behavioral obligation by simply
    never declaring ``changes_behavior``, and a zero-check run passes entirely. This engine keys
    off the FACT the diff touched code (the git witness), NOT off an agent-declared class and NOT
    off keyword classification (``witness_class`` is rejected, design 01 §anti-pattern).

    Fail-open where it cannot witness, fail-closed where it can:
    * not a git repo -> ``[]`` (no witness available — synthetic/non-git fixtures; nothing to
      ground; mirrors :mod:`scope_conformance`'s noop).
    * repo present but unobservable (``result.error``) -> one ``CHK_BEHAVIORAL_FLOOR_UNWITNESSED``
      at ``warn`` (an expected witness that cannot testify — never a silent pass, not the
      agent's fault).
    * no code in the change set -> ``[]`` (docs/config/design-only runs are exempt).
    * code changed and no ``uacp.check.behavioral`` node present -> one
      ``CHK_BEHAVIORAL_FLOOR_UNMET`` at the config-gated severity (default ``warn``).

    Never raises."""
    if (bad := _validate_inputs(workspace, run_id)) is not None:
        return bad
    root = Path(str(workspace)).resolve()
    result = changed_files(root)
    if not result.is_repo:
        # No git witness available — nothing to ground here (other engines own "no repo").
        return []
    if result.error is not None:
        return [
            _v(
                "CHK_BEHAVIORAL_FLOOR_UNWITNESSED",
                f"git witness present but unobservable ({result.error}); the behavioral "
                f"floor for run '{run_id}' cannot be verified",
                severity="warn",
                error=result.error,
            )
        ]
    code_changed = [f for f in result.files if str(f).endswith(_CODE_SUFFIXES)]
    if not code_changed:
        # No code touched -> no behavioral obligation (docs/config/design-only change set).
        return []
    graph = _load_and_project(workspace, run_id)
    has_behavioral = False
    if graph is not None:
        nodes, _edges = graph
        has_behavioral = any(
            n.get("kind") == "check" and n.get("check_kind") == "uacp.check.behavioral"
            for n in nodes.values()
        )
    if has_behavioral:
        return []
    examples = sorted(code_changed)[:5]
    return [
        _v(
            "CHK_BEHAVIORAL_FLOOR_UNMET",
            f"the git witness shows {len(code_changed)} code file(s) changed "
            f"(e.g. {examples}) but the run carries no behavioral check "
            f"(uacp.check.behavioral) to ground it; a code-changing run must author >=1 "
            f"behavioral check that replay runs into substrate",
            severity=_behavioral_floor_severity(root),
            code_changed=len(code_changed),
            examples=examples,
        )
    ]


# ---------------------------------------------------------------------------------------------
# Correctness-screening FLOOR (design/grounded-governance/03, Layer 2 slice 2): the mandatory,
# grounded gate that makes a correctness screening EXIST, be GROUNDED in the kernel-produced
# substrate (gitio.diff_content, slice 1), and RE-RUN after a fix moves HEAD (the fixpoint).
# ---------------------------------------------------------------------------------------------

# The governed kind a correctness-screening artifact declares at top level. Slice 3 adds its
# schema + governed writer; this gate loads LENIENTLY (yaml.safe_load, no schema registration),
# keying only on this kind + a ``substrate_hash`` field.
_CORRECTNESS_SCREENING_KIND = "uacp.correctness_screening"

# Safe migration default for CHK_CORRECTNESS_SCREENING_{MISSING,STALE} — "warn", never "block":
# block-by-accident would break every live code-changing run before screenings exist. Mirrors
# _BEHAVIORAL_FLOOR_DEFAULT_SEVERITY / the SC_DIFF migration precedent.
_CORRECTNESS_SCREENING_DEFAULT_SEVERITY = "warn"


def _correctness_screening_severity(root: Path) -> str:
    """Config-gated severity for ``CHK_CORRECTNESS_SCREENING_{MISSING,STALE}``, read from
    ``[verification] correctness_screening`` (default ``warn``, flips to ``block`` in a later
    named release — the behavioral_floor / SC_DIFF migration precedent). Only the literals
    ``warn``/``block`` are honored; absent/invalid -> ``warn`` (the safe migration default —
    block-by-accident breaks runs). SUBSTRATE_UNAVAILABLE is NOT gated here (always ``warn``).
    Never raises."""
    try:
        cfg = get_config(root).model_dump()
        raw = (cfg.get("verification") or {}).get("correctness_screening")
        if raw in ("warn", "block"):
            return raw
        return _CORRECTNESS_SCREENING_DEFAULT_SEVERITY
    except Exception:
        return _CORRECTNESS_SCREENING_DEFAULT_SEVERITY


def _substrate_hash(dc: DiffContentResult) -> str:
    """The substrate IDENTITY: sha256 over ``base_commit`` + HEAD + the full diff text
    (design/grounded-governance/03). Because it folds in HEAD and the diff CONTENT, any fix that
    moves HEAD changes the hash — so a screening built for an old HEAD no longer covers the current
    substrate. That is the fixpoint enforcement: a stale screening cannot clear the gate."""
    payload = f"{dc.base_commit or ''}\n{dc.head_commit or ''}\n{dc.text}"
    return hashlib.sha256(payload.encode()).hexdigest()


def _correctness_screening_docs(
    workspace: str | Path, run_id: str, root: Path
) -> list[dict[str, Any]]:
    """Every RESOLVING correctness-screening artifact DICT for THIS run (``kind:
    uacp.correctness_screening``).

    Located two ways (the M2 rework-resolver precedent + the run's own evidence dir): the run's
    REGISTERED manifest artifacts AND a scan of ``verification/{run_id}/*.y{a,}ml`` under the
    governed base. An artifact contributes only if it EXISTS + LOADS (M2's resolution bar) and
    declares ``kind: uacp.correctness_screening``. Loaded leniently (the governed writer + schema
    are slice 3a; this READ side keys on the kind, never on schema validity). Never raises.

    This is the shared locator; :func:`_correctness_screening_hashes` (slice 2, the MISSING/STALE
    floor) and :func:`validate_correctness_findings` (slice 4, the disposition gate) both read from
    it — the substrate-hash logic lives in one place."""
    docs: list[dict[str, Any]] = []
    seen: set[str] = set()

    # 1. Registered artifacts on the run manifest (the M2 way — a governed screening lands here).
    loaded = load_manifest(root, run_id)
    if loaded.error is None and loaded.value is not None:
        arts = loaded.value.raw.get("artifacts")
        if isinstance(arts, dict):
            for rel in arts.values():
                if not isinstance(rel, str) or not rel.strip() or rel in seen:
                    continue
                seen.add(rel)
                d = load_artifact(root, rel)
                if d.error is None and isinstance(d.value, dict):
                    docs.append(d.value)

    # 2. Scan the run's verification dir (covers a screening placed there without registration).
    for pattern in (f"verification/{run_id}/*.yaml", f"verification/{run_id}/*.yml"):
        for path in glob_in_workspace(root, pattern):
            rel = str(path)
            if rel in seen:
                continue
            seen.add(rel)
            d = load_yaml_under_root(root, rel)
            if d.error is None and isinstance(d.value, dict):
                docs.append(dict(d.value))

    return [doc for doc in docs if doc.get("kind") == _CORRECTNESS_SCREENING_KIND]


def _correctness_screening_hashes(workspace: str | Path, run_id: str, root: Path) -> list[str]:
    """Every non-empty ``substrate_hash`` carried by a RESOLVING correctness-screening artifact for
    THIS run — the covering-hash set the slice-2 floor matches the current substrate identity
    against. Reads the shared :func:`_correctness_screening_docs` locator. Never raises."""
    hashes: list[str] = []
    for doc in _correctness_screening_docs(workspace, run_id, root):
        sh = doc.get("substrate_hash")
        if isinstance(sh, str) and sh:
            hashes.append(sh)
    return hashes


def validate_correctness_screening(workspace: str | Path, run_id: str) -> list[Violation]:
    """Correctness-screening FLOOR (design/grounded-governance/03, Layer 2 slice 2): a
    code-changing run may not clear VERIFY unless a correctness-screening artifact EXISTS,
    RESOLVES, and COVERS the kernel-produced substrate for the run's true ``merge-base..HEAD``
    range.

    This is the enforcement half a fail-open prose instruction ("please review the diff") lacks:
    the gate keys on a resolving, substrate-covering artifact, not on the agent's word. It reuses
    the same grounding shape as the behavioral floor — the claim ("I screened the work") validates
    on the artifact's RESOLUTION against the kernel's substrate identity, never on its presence.

    Fail-open where it cannot witness, fail-closed where it can:
    * not a git repo -> ``[]`` (no substrate — synthetic/non-git fixtures; other engines own "no
      repo"). A repo whose change set is unobservable yields an empty witness, so no code is seen
      changed and the gate no-ops (behavioral_floor owns the UNWITNESSED signal).
    * no CODE in the change set -> ``[]`` (docs/config-only runs need no correctness screening).
    * code changed but the substrate cannot be produced (no merge-base) -> one
      ``CHK_CORRECTNESS_SUBSTRATE_UNAVAILABLE`` at ``warn`` (an expected substrate that cannot be
      produced — an environment fact, surfaced, never a silent pass or an agent fault).
    * code changed and a resolving screening artifact COVERS the current substrate -> ``[]``.
    * code changed and NO screening artifact found -> one ``CHK_CORRECTNESS_SCREENING_MISSING`` at
      the config-gated severity (default ``warn``).
    * code changed and screening artifact(s) found but ALL cover a DIFFERENT substrate (HEAD moved
      since screening) -> one ``CHK_CORRECTNESS_SCREENING_STALE`` at the config-gated severity — the
      fixpoint: re-screen the moved diff.

    Never raises."""
    if (bad := _validate_inputs(workspace, run_id)) is not None:
        return bad
    root = Path(str(workspace)).resolve()
    result = changed_files(root)
    if not result.is_repo:
        # No substrate available — nothing to ground here (synthetic/non-git fixtures).
        return []
    code_changed = [f for f in result.files if str(f).endswith(_CODE_SUFFIXES)]
    if not code_changed:
        # No code touched (or the change set was unobservable) -> no correctness obligation.
        return []
    dc = diff_content(root)
    if dc.error is not None:
        return [
            _v(
                "CHK_CORRECTNESS_SUBSTRATE_UNAVAILABLE",
                f"the review substrate for run '{run_id}' cannot be produced ({dc.error}); the "
                f"correctness screening for {len(code_changed)} changed code file(s) cannot be "
                f"grounded — surfaced, not silently passed",
                severity="warn",
                error=dc.error,
                code_changed=len(code_changed),
            )
        ]
    current_hash = _substrate_hash(dc)
    hashes = _correctness_screening_hashes(workspace, run_id, root)
    if current_hash in hashes:
        # A screening covers the current substrate — screened.
        return []
    severity = _correctness_screening_severity(root)
    examples = sorted(code_changed)[:5]
    if not hashes:
        return [
            _v(
                "CHK_CORRECTNESS_SCREENING_MISSING",
                f"the git witness shows {len(code_changed)} code file(s) changed "
                f"(e.g. {examples}) but run '{run_id}' carries no correctness-screening artifact "
                f"({_CORRECTNESS_SCREENING_KIND}) covering the kernel-produced substrate; a "
                f"code-changing run must be screened for correctness over its real diff",
                severity=severity,
                code_changed=len(code_changed),
                examples=examples,
                substrate_hash=current_hash,
            )
        ]
    return [
        _v(
            "CHK_CORRECTNESS_SCREENING_STALE",
            f"run '{run_id}' carries correctness-screening artifact(s) but none cover the CURRENT "
            f"substrate (HEAD moved since screening); the {len(hashes)} screening(s) cover a "
            f"different diff — re-screen the moved delta (the fixpoint)",
            severity=severity,
            code_changed=len(code_changed),
            substrate_hash=current_hash,
            found_hashes=hashes,
        )
    ]


# ---------------------------------------------------------------------------------------------
# Correctness-FINDINGS disposition gate (design/grounded-governance/03, Layer 2 slice 4): once a
# screening COVERS the current substrate, every finding it carried must be DISPOSITIONED — the
# verdict must resolve. Findings reuse the SAME disposition grounding the rework floor uses
# (M2/M3d): `discharged` -> a fix pointer that RESOLVES; `adjudicated` -> decision + rationale +
# cost-if-wrong.
# ---------------------------------------------------------------------------------------------


def _s(v: Any) -> str:
    """A field's non-empty stripped string value, or "" (matches the rework floor's ``_str_field``
    truthiness — a whitespace-only / non-string value is absent)."""
    return v.strip() if isinstance(v, str) else ""


def _finding_dispositioned(
    finding: dict[str, Any],
    root: Path,
    run_id: str,
    allowed_prefixes: tuple[str, ...] | None = None,
) -> bool:
    """True iff the finding carries a COMPLETE disposition, resolved — not merely named (the M2/M3d
    rule, applied to a correctness finding unchanged):

    * ``discharged`` -> ``handling_artifact_path`` must RESOLVE (run-bound to THIS run + exists +
      loads) via M2's :func:`_artifact_resolves`. A path that is empty, foreign-run, or nonexistent
      is a *label*, not a fix.
    * ``adjudicated`` -> ``decision``, ``rationale``, and ``cost_if_wrong`` must ALL be present +
      non-empty (M3d's ``_adjudication_complete``, read from this schema's nested field names). A
      partial adjudication is not a decision made with eyes open.

    Any other disposition kind, a missing/non-object ``disposition``, or an incomplete one -> not
    dispositioned (blocks)."""
    disp = finding.get("disposition")
    if not isinstance(disp, dict):
        return False
    kind = disp.get("kind")
    if kind == "discharged":
        return _artifact_resolves(
            root, run_id, _s(disp.get("handling_artifact_path")), allowed_prefixes
        )
    if kind == "adjudicated":
        return all(_s(disp.get(f)) for f in ("decision", "rationale", "cost_if_wrong"))
    return False


def validate_correctness_findings(workspace: str | Path, run_id: str) -> list[Violation]:
    """Correctness-FINDINGS disposition gate (design/grounded-governance/03, Layer 2 slice 4).

    For the RESOLVING correctness-screening artifact(s) that COVER the current kernel-produced
    substrate (the same ``_substrate_hash`` identity the slice-2 floor matches), the screening's
    VERDICT must resolve into grounded state:

    * ``clean`` -> ``[]`` (nothing found).
    * ``findings`` -> EACH carried finding must be DISPOSITIONED (:func:`_finding_dispositioned`):
      ``discharged`` with a RESOLVING fix pointer (M2), or ``adjudicated`` with decision + rationale
      + cost-if-wrong (M3d). Each undispositioned/incomplete finding emits one
      ``CHK_CORRECTNESS_FINDING_UNDISPOSITIONED`` at the config-gated severity (same
      ``[verification] correctness_screening`` key as the floor; default ``warn``, migration).
    * ``cannot_verify`` -> one ``CHK_CORRECTNESS_SCREENING_INCONCLUSIVE`` at ``warn`` — the
      screening ABSTAINED; surfaced, never a silent pass (it must not read as clean).

    Scope discipline — this gate owns ONLY the disposition/verdict of a COVERING screening:
    * not a git repo / no code changed / substrate unavailable -> ``[]`` (nothing to disposition
      here; the slice-2 floor owns the SUBSTRATE_UNAVAILABLE surfacing — don't double-report).
    * NO covering screening (missing or stale) -> ``[]`` — that is
      :func:`validate_correctness_screening`'s MISSING/STALE signal; double-reporting it here would
      duplicate the block.

    Never raises."""
    if (bad := _validate_inputs(workspace, run_id)) is not None:
        return bad
    root = Path(str(workspace)).resolve()
    result = changed_files(root)
    if not result.is_repo:
        return []
    code_changed = [f for f in result.files if str(f).endswith(_CODE_SUFFIXES)]
    if not code_changed:
        return []
    dc = diff_content(root)
    if dc.error is not None:
        # Substrate can't be produced — the slice-2 floor surfaces that (SUBSTRATE_UNAVAILABLE);
        # there is no covering screening to disposition here.
        return []
    current_hash = _substrate_hash(dc)
    covering = [
        doc
        for doc in _correctness_screening_docs(workspace, run_id, root)
        if doc.get("substrate_hash") == current_hash
    ]
    if not covering:
        # No screening covers the current substrate — validate_correctness_screening owns the
        # MISSING/STALE signal; don't double-report.
        return []
    severity = _correctness_screening_severity(root)
    violations: list[Violation] = []
    for doc in covering:
        verdict = doc.get("verdict")
        if verdict == "cannot_verify":
            violations.append(
                _v(
                    "CHK_CORRECTNESS_SCREENING_INCONCLUSIVE",
                    f"the correctness screening for run '{run_id}' abstained "
                    f"(verdict=cannot_verify) over the current substrate; an inconclusive "
                    f"screening is surfaced, never read as a pass — resolve it (re-screen, or "
                    f"adjudicate the inability to verify) before closing VERIFY",
                    severity="warn",
                    substrate_hash=current_hash,
                )
            )
            continue
        if verdict != "findings":
            # clean (or a verdict this gate imposes no obligation on) — nothing to disposition.
            continue
        findings = doc.get("findings")
        if not isinstance(findings, list):
            continue
        for finding in findings:
            if not isinstance(finding, dict) or not _finding_dispositioned(finding, root, run_id):
                fid = _s(finding.get("id")) if isinstance(finding, dict) else ""
                violations.append(
                    _v(
                        "CHK_CORRECTNESS_FINDING_UNDISPOSITIONED",
                        f"correctness finding {fid or '(unidentified)'!r} in run '{run_id}' "
                        f"(verdict=findings) carries no COMPLETE disposition; every open finding "
                        f"must be discharged (a fix pointer that RESOLVES) or adjudicated "
                        f"(decision + rationale + cost-if-wrong) — a named-but-unresolved handling "
                        f"is a label, not a disposition",
                        severity=severity,
                        finding_id=fid,
                        substrate_hash=current_hash,
                    )
                )
    return violations


# ---------------------------------------------------------------------------------------------
# TRIAGE grounding (design/grounded-governance/04 + 05): the HEAD of the cascade. This is the SAME
# machine as the VERIFY correctness screening above — a mandatory, grounded, fixpoint-enforced gate
# — instantiated at triage exit. The ONLY difference is the SUBSTRATE PRODUCER: the reality here is
# not a git diff but the REAL state of the scope's declared TARGETS (existence + kind + size in the
# project tree), keyed off the run's declared scope. Everything else is reused: the resolves-not-
# asserts floor (M2), the disposition loop (M3d, via `_finding_dispositioned`), the substrate-hash
# fixpoint, and the config-gated warn->block migration.
# ---------------------------------------------------------------------------------------------

# The governed kind a triage-screening artifact declares at top level (schema + writer: layout.py /
# schema.py). This gate loads LENIENTLY, keying on this kind + a `substrate_hash` field.
_TRIAGE_SCREENING_KIND = "uacp.triage_screening"
# The declaration kinds a run's declared scope is read from: the triage verdict itself (open-world,
# so a producer may carry `scope_targets`) and — once authored — the scope artifact (`write_paths`).
_TRIAGE_DECL_KINDS = ("uacp.triage", "uacp.scope")
# Safe migration default — "warn", never "block": a triage gate that blocked by accident would
# break EVERY live run at its first governed crossing. Mirrors the correctness floor's default.
_TRIAGE_GROUNDING_DEFAULT_SEVERITY = "warn"


def _triage_grounding_severity(root: Path) -> str:
    """Config-gated severity for the triage grounding codes, read from ``[triage] scope_grounding``
    (default ``warn``, flips to ``block`` in a later named release — the behavioral_floor /
    SC_DIFF /
    correctness_screening migration precedent). Only the literals ``warn``/``block`` are honored;
    absent/invalid -> ``warn`` (the safe migration default — block-by-accident breaks runs).
    TRIAGE_SCREENING_INCONCLUSIVE is NOT gated here (always ``warn``). Never raises."""
    try:
        cfg = get_config(root).model_dump()
        raw = (cfg.get("triage") or {}).get("scope_grounding")
        if raw in ("warn", "block"):
            return raw
        return _TRIAGE_GROUNDING_DEFAULT_SEVERITY
    except Exception:
        return _TRIAGE_GROUNDING_DEFAULT_SEVERITY


def _run_kind_docs(
    root: Path, run_id: str, kinds: tuple[str, ...], patterns: tuple[str, ...]
) -> list[dict[str, Any]]:
    """Every RESOLVING artifact DICT for THIS run whose ``kind`` is in ``kinds``, located the two
    ways the correctness locator uses: the run's REGISTERED manifest artifacts AND a scan of the
    given base-relative glob ``patterns``. An artifact contributes only if it EXISTS + LOADS (the
    M2 resolution bar). Loaded leniently (keys on ``kind``, never on schema validity). Never raises.
    Shared by the triage scope-target reader and the triage-screening locator."""
    docs: list[dict[str, Any]] = []
    seen: set[str] = set()

    loaded = load_manifest(root, run_id)
    if loaded.error is None and loaded.value is not None:
        arts = loaded.value.raw.get("artifacts")
        if isinstance(arts, dict):
            for rel in arts.values():
                if not isinstance(rel, str) or not rel.strip() or rel in seen:
                    continue
                seen.add(rel)
                d = load_artifact(root, rel)
                if d.error is None and isinstance(d.value, dict):
                    docs.append(d.value)

    for pattern in patterns:
        for path in glob_in_workspace(root, pattern):
            rel = str(path)
            if rel in seen:
                continue
            seen.add(rel)
            d = load_yaml_under_root(root, rel)
            if d.error is None and isinstance(d.value, dict):
                docs.append(dict(d.value))

    return [doc for doc in docs if doc.get("kind") in kinds]


def _triage_declared_targets(root: Path, run_id: str) -> list[str]:
    """The run's declared scope TARGETS at triage: the ``write_paths`` and/or ``scope_targets`` a
    ``uacp.triage`` (open-world) or ``uacp.scope`` artifact carries — path/glob strings naming the
    real tree the run intends to touch. Read from the serialized declaration (the
    ``_run_forced_plan_exit_gate`` precedent reads the run's serialized scope), never asserted.
    Deduped, order-independent (the substrate sorts). Empty when the run declares no scope — the
    gate then no-ops, mirroring the correctness floor's 'no code changed'. Never raises."""
    docs = _run_kind_docs(
        root,
        run_id,
        _TRIAGE_DECL_KINDS,
        (f"proposals/{run_id}-triage.yaml", f"plans/{run_id}-scope.yaml"),
    )
    targets: list[str] = []
    for doc in docs:
        for key in ("write_paths", "scope_targets"):
            v = doc.get(key)
            if isinstance(v, list):
                targets.extend(x.strip() for x in v if isinstance(x, str) and x.strip())
    return targets


def _target_state(root: Path, target: str) -> tuple[bool, str, int]:
    """Resolve one declared scope target against the REAL project tree under ``root``
    (NOT ``.uacp``).
    Returns ``(exists, kind, size)`` — ``kind`` in {file, dir, glob, ''}; ``size`` is the file byte
    count, a glob's match count, or 0. A target that escapes ``root`` (traversal)
    resolves as absent. A glob target (containing ``* ? [``) resolves iff >=1 path
    matches under the tree. Never raises."""
    try:
        base = root.resolve()
        if any(ch in target for ch in "*?["):
            matches = []
            for m in base.glob(target):
                try:
                    m.resolve().relative_to(base)
                except Exception:
                    continue
                matches.append(m)
            return (bool(matches), "glob", len(matches))
        resolved = (base / target).resolve()
        if resolved != base and base not in resolved.parents:
            return (False, "", 0)  # escapes the project root -> treated as unresolved
        if resolved.is_dir():
            return (True, "dir", 0)
        if resolved.is_file():
            return (True, "file", resolved.stat().st_size)
        return (False, "", 0)
    except Exception:
        return (False, "", 0)


def _triage_substrate(root: Path, targets: list[str]) -> list[tuple[str, bool, str, int]]:
    """The triage substrate: for each DISTINCT declared target (sorted), its real state
    ``(target, exists, kind, size)`` in the project tree. Deterministic — the sorted, deduped
    target set makes the produced reality (and its hash) independent of declaration order."""
    rows: list[tuple[str, bool, str, int]] = []
    for t in sorted(set(targets)):
        exists, kind, size = _target_state(root, t)
        rows.append((t, exists, kind, size))
    return rows


def _triage_substrate_hash(substrate: list[tuple[str, bool, str, int]]) -> str:
    """The substrate IDENTITY: sha256 over the sorted ``(target, exists, kind, size)`` tuples
    (design/grounded-governance/05), mirroring ``_substrate_hash``. Because it folds in each
    target's real existence/kind/size, ANY change to the declared scope OR to the tree the scope
    names moves the hash — so a screening built for an old scope no longer covers. That is the
    fixpoint: a stale screening cannot clear the gate."""
    payload = "\n".join(
        f"{t}\t{int(exists)}\t{kind}\t{size}" for (t, exists, kind, size) in substrate
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _triage_screening_docs(root: Path, run_id: str) -> list[dict[str, Any]]:
    """Every RESOLVING triage-screening artifact DICT for THIS run (``kind:
    uacp.triage_screening``), located via the shared locator (registered artifacts + the per-run
    subdir scan ``proposals/{run_id}/*.y{a,}ml`` — the governed writer's home). Never raises."""
    return _run_kind_docs(
        root,
        run_id,
        (_TRIAGE_SCREENING_KIND,),
        (f"proposals/{run_id}/*.yaml", f"proposals/{run_id}/*.yml"),
    )


def _triage_screening_hashes(root: Path, run_id: str) -> list[str]:
    """Every non-empty ``substrate_hash`` carried by a RESOLVING triage-screening artifact for THIS
    run — the covering-hash set the floor matches the current substrate identity against."""
    hashes: list[str] = []
    for doc in _triage_screening_docs(root, run_id):
        sh = doc.get("substrate_hash")
        if isinstance(sh, str) and sh:
            hashes.append(sh)
    return hashes


def validate_triage_screening(workspace: str | Path, run_id: str) -> list[Violation]:
    """TRIAGE grounding FLOOR + screening-coverage gate (design/grounded-governance/04 + 05).

    When the run DECLARES a scope at triage, TRIAGE-exit may not pass clean unless (a) every
    declared target RESOLVES in the real tree and (b) a triage-screening artifact EXISTS, RESOLVES,
    and COVERS the kernel-produced substrate (the scope-target reality). This is the head-of-cascade
    instance of the same machine the VERIFY correctness floor is:

    * no declared scope targets -> ``[]`` (no substrate; nothing to ground — mirrors the correctness
      floor's 'no code changed'). This keeps the gate INERT for runs whose triage declares no scope,
      preserving existing triage->propose behavior.
    * a declared target that does NOT resolve in the real tree -> one
      ``TRIAGE_SCOPE_TARGET_UNRESOLVED`` at the config-gated severity, per phantom target (the M2
      resolves-not-asserts floor for scope targets — a scope naming a fiction, no agent needed).
    * targets declared and NO covering screening found -> one ``TRIAGE_SCREENING_MISSING`` at the
      config-gated severity.
    * screening(s) found but ALL cover a DIFFERENT substrate (the scope changed since screening) ->
      one ``TRIAGE_SCREENING_STALE`` — the fixpoint: re-screen the moved scope.

    The unresolved-target floor is INDEPENDENT of screening coverage (a phantom target is a hard
    floor regardless), so it can co-fire with MISSING/STALE. Never raises."""
    if (bad := _validate_inputs(workspace, run_id)) is not None:
        return bad
    root = Path(str(workspace)).resolve()
    targets = _triage_declared_targets(root, run_id)
    if not targets:
        # No declared scope -> no substrate -> no triage-grounding obligation.
        return []
    substrate = _triage_substrate(root, targets)
    severity = _triage_grounding_severity(root)
    out: list[Violation] = []

    # DETERMINISTIC FLOOR: every declared target must resolve in the real tree.
    for target, exists, _kind, _size in substrate:
        if not exists:
            out.append(
                _v(
                    "TRIAGE_SCOPE_TARGET_UNRESOLVED",
                    f"run '{run_id}' declares scope target {target!r} but it does not resolve in "
                    f"the real project tree; a scope naming a nonexistent target mis-scopes the "
                    f"whole run at its head — resolve the target or correct the scope",
                    severity=severity,
                    target=target,
                )
            )

    # SCREENING COVERAGE: a triage screening must cover the current substrate identity.
    current_hash = _triage_substrate_hash(substrate)
    hashes = _triage_screening_hashes(root, run_id)
    if current_hash in hashes:
        return out
    examples = [t for (t, _e, _k, _s) in substrate][:5]
    if not hashes:
        out.append(
            _v(
                "TRIAGE_SCREENING_MISSING",
                f"run '{run_id}' declares {len(targets)} scope target(s) (e.g. {examples}) but "
                f"carries no triage-screening artifact ({_TRIAGE_SCREENING_KIND}) covering the "
                f"kernel-produced project-root substrate; the declared scope must be screened "
                f"against reality before TRIAGE exits",
                severity=severity,
                declared_targets=len(targets),
                examples=examples,
                substrate_hash=current_hash,
            )
        )
    else:
        out.append(
            _v(
                "TRIAGE_SCREENING_STALE",
                f"run '{run_id}' carries triage-screening artifact(s) but none cover the CURRENT "
                f"scope substrate (the declared scope or the tree it names changed since "
                f"screening); the {len(hashes)} screening(s) cover a different substrate — "
                f"re-screen the moved scope (the fixpoint)",
                severity=severity,
                declared_targets=len(targets),
                substrate_hash=current_hash,
                found_hashes=hashes,
            )
        )
    return out


def validate_triage_findings(workspace: str | Path, run_id: str) -> list[Violation]:
    """TRIAGE-FINDINGS disposition gate (design/grounded-governance/04 + 05) — the triage
    instance of
    ``validate_correctness_findings``, reusing the SAME disposition grounding (M2/M3d via
    :func:`_finding_dispositioned`).

    For the RESOLVING triage-screening artifact(s) that COVER the current substrate:
    * ``clean`` -> ``[]``.
    * ``findings`` -> EACH carried finding must be DISPOSITIONED (``discharged`` with a
      RESOLVING fix
      pointer, or ``adjudicated`` with decision + rationale + cost-if-wrong). Each undispositioned
      finding -> one ``TRIAGE_FINDING_UNDISPOSITIONED`` at the config-gated severity.
    * ``cannot_verify`` -> one ``TRIAGE_SCREENING_INCONCLUSIVE`` at ``warn`` (abstained; surfaced,
      never read as a pass).

    Scope discipline (mirrors the correctness findings gate): no declared scope / NO covering
    screening -> ``[]`` (the MISSING/STALE signal is :func:`validate_triage_screening`'s; don't
    double-report). Never raises."""
    if (bad := _validate_inputs(workspace, run_id)) is not None:
        return bad
    root = Path(str(workspace)).resolve()
    targets = _triage_declared_targets(root, run_id)
    if not targets:
        return []
    substrate = _triage_substrate(root, targets)
    current_hash = _triage_substrate_hash(substrate)
    covering = [
        doc
        for doc in _triage_screening_docs(root, run_id)
        if doc.get("substrate_hash") == current_hash
    ]
    if not covering:
        # No covering screening — validate_triage_screening owns MISSING/STALE; don't double-report.
        return []
    severity = _triage_grounding_severity(root)
    violations: list[Violation] = []
    for doc in covering:
        verdict = doc.get("verdict")
        if verdict == "cannot_verify":
            violations.append(
                _v(
                    "TRIAGE_SCREENING_INCONCLUSIVE",
                    f"the triage screening for run '{run_id}' abstained (verdict=cannot_verify) "
                    f"over the current scope substrate; an inconclusive screening is surfaced, "
                    f"never read as a pass — resolve it before closing TRIAGE",
                    severity="warn",
                    substrate_hash=current_hash,
                )
            )
            continue
        if verdict != "findings":
            continue
        findings = doc.get("findings")
        if not isinstance(findings, list):
            continue
        for finding in findings:
            # A triage finding discharges to TRIAGE-phase evidence under ``proposals/{run}`` (the
            # governed-writer root where uacp.triage / the re-scoped artifact live — there is no
            # ``triage/`` root), not the late-phase verification/executions dirs the correctness
            # gate uses. The evidence-reference type is phase-appropriate.
            if not isinstance(finding, dict) or not _finding_dispositioned(
                finding, root, run_id, allowed_prefixes=("proposals/",)
            ):
                fid = _s(finding.get("id")) if isinstance(finding, dict) else ""
                violations.append(
                    _v(
                        "TRIAGE_FINDING_UNDISPOSITIONED",
                        f"triage finding {fid or '(unidentified)'!r} in run '{run_id}' "
                        f"(verdict=findings) carries no COMPLETE disposition; every open finding "
                        f"must be discharged (a fix pointer that RESOLVES) or adjudicated "
                        f"(decision + rationale + cost-if-wrong)",
                        severity=severity,
                        finding_id=fid,
                        substrate_hash=current_hash,
                    )
                )
    return violations


# ---------------------------------------------------------------------------------------------
# PROPOSE grounding (design/grounded-governance/06): the PROPOSE instance of the same
# grounding-screening machine the TRIAGE gate above is — a config-gated, fixpoint-enforced
# screening-coverage gate — instantiated at PROPOSE exit. The ONLY difference from TRIAGE is the
# SUBSTRATE PRODUCER: the reality here is not the scope's declared TARGETS but the proposal's
# declared PREMISE (its intent + constraint fields), hashed. Everything else is reused: the
# screening-coverage floor (MISSING/STALE via the substrate-hash fixpoint), the disposition loop
# (via `_finding_dispositioned`), and the config-gated warn->block migration.
#
# HONEST LIMIT (design/grounded-governance/06): the substrate hashes the PREMISE — a DECLARATION —
# to drive the fixpoint (re-premising moves the hash -> stale screening -> re-screen). The
# grounding-via-reproduction ("reproduce, don't read") the premise demands is carried by the CHARGE
# (skills/uacp-propose/references/grounding-screening.md), NOT yet by kernel-witnessed reproduction
# evidence. A witnessed behavior_plane reproduction record per finding (M5-style) is a documented
# follow-on tightening; this first cut mirrors TRIAGE structurally and ships config-gated `warn`.
#
# Unlike TRIAGE, PROPOSE has NO deterministic "targets resolve" floor — a premise is prose, not a
# path that can be resolved against the tree — so there is no `*_UNRESOLVED`-style deterministic
# block here; propose grounding is ONLY the screening-coverage gate + the findings-disposition gate.
# ---------------------------------------------------------------------------------------------

# The governed kind a propose-screening artifact declares at top level (schema + writer: layout.py /
# schema.py). This gate loads LENIENTLY, keying on this kind + a `substrate_hash` field.
_PROPOSE_SCREENING_KIND = "uacp.propose_screening"
# The declaration kinds the run's PREMISE is read from: the registered proposal (open-world) and —
# tolerated — the doc-form `uacp.propose` the proposal-schema doc describes.
_PROPOSE_DECL_KINDS = ("uacp.proposal", "uacp.propose")
# The premise-bearing fields of a proposal: its declared INTENT (`title`/`objective`/`purpose`) plus
# the CONSTRAINTS it commits to (`scope` prose statements, `declared_side_effects`, `authority`,
# `human_involvement`). Read robustly across the registered schema (`objective`) and the doc form
# (`purpose`). NOT the scope-target PATHS (those are TRIAGE's substrate) — these are the prose
# declaration of what the run intends and under what constraints. Changing ANY moves the hash.
_PROPOSE_PREMISE_FIELDS = (
    "title",
    "objective",
    "purpose",
    "scope",
    "declared_side_effects",
    "authority",
    "human_involvement",
)
# Safe migration default — "warn", never "block": a propose gate that blocked by accident would
# break EVERY live run at its PROPOSE crossing. Mirrors the triage / correctness floor default.
_PROPOSE_GROUNDING_DEFAULT_SEVERITY = "warn"


def _propose_grounding_severity(root: Path) -> str:
    """Config-gated severity for the propose grounding codes, read from
    ``[verification] propose_screening`` (default ``warn``, flips to ``block`` in a later named
    release — the behavioral_floor / SC_DIFF / correctness_screening / triage migration precedent).
    Only the literals ``warn``/``block`` are honored; absent/invalid -> ``warn`` (the safe migration
    default — block-by-accident breaks runs). PROPOSE_SCREENING_INCONCLUSIVE is NOT gated here
    (always ``warn``). Never raises."""
    try:
        cfg = get_config(root).model_dump()
        raw = (cfg.get("verification") or {}).get("propose_screening")
        if raw in ("warn", "block"):
            return raw
        return _PROPOSE_GROUNDING_DEFAULT_SEVERITY
    except Exception:
        return _PROPOSE_GROUNDING_DEFAULT_SEVERITY


def _propose_premise(root: Path, run_id: str) -> dict[str, Any]:
    """The run's declared PREMISE at propose: the intent + constraint fields a ``uacp.proposal``
    (open-world) carries — ``title``/``objective``(/``purpose``)/``scope``/
    ``declared_side_effects``/``authority``/``human_involvement``. Read from the serialized
    declaration (mirroring the triage scope reader), never asserted. First-writer-wins across
    multiple declaration docs, so the produced premise (and its hash) is order-independent. Empty
    when the run declares no premise-bearing fields — the gate then no-ops, mirroring the
    correctness floor's 'no code changed'. Never raises."""
    docs = _run_kind_docs(
        root,
        run_id,
        _PROPOSE_DECL_KINDS,
        (f"proposals/{run_id}-proposal.yaml",),
    )
    premise: dict[str, Any] = {}
    for doc in docs:
        for key in _PROPOSE_PREMISE_FIELDS:
            if key in premise:
                continue
            value = doc.get(key)
            if value is not None:
                premise[key] = value
    return premise


def _propose_substrate_hash(premise: dict[str, Any]) -> str:
    """The premise substrate IDENTITY: sha256 over the canonical JSON of the premise fields
    (sorted keys, so nested-mapping order cannot perturb the identity), mirroring
    ``_triage_substrate_hash``. Because it folds in every premise-bearing field, ANY change to the
    declared intent OR its constraints (re-premising) moves the hash — so a screening built for an
    old premise no longer covers. That is the fixpoint: a stale screening cannot clear the gate."""
    payload = json.dumps(premise, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _propose_screening_docs(root: Path, run_id: str) -> list[dict[str, Any]]:
    """Every RESOLVING propose-screening artifact DICT for THIS run (``kind:
    uacp.propose_screening``), located via the shared locator (registered artifacts + the per-run
    subdir scan ``proposals/{run_id}/*.y{a,}ml`` — the governed writer's home, shared with the
    triage screening but kind-filtered apart). Never raises."""
    return _run_kind_docs(
        root,
        run_id,
        (_PROPOSE_SCREENING_KIND,),
        (f"proposals/{run_id}/*.yaml", f"proposals/{run_id}/*.yml"),
    )


def _propose_screening_hashes(root: Path, run_id: str) -> list[str]:
    """Every non-empty ``substrate_hash`` carried by a RESOLVING propose-screening artifact for THIS
    run — the covering-hash set the gate matches the current premise-substrate identity against."""
    hashes: list[str] = []
    for doc in _propose_screening_docs(root, run_id):
        sh = doc.get("substrate_hash")
        if isinstance(sh, str) and sh:
            hashes.append(sh)
    return hashes


def validate_propose_screening(workspace: str | Path, run_id: str) -> list[Violation]:
    """PROPOSE grounding screening-coverage gate (design/grounded-governance/06).

    When the run DECLARES a premise at propose, PROPOSE-exit may not pass clean unless a
    propose-screening artifact EXISTS, RESOLVES, and COVERS the kernel-produced substrate (the
    proposal's premise reality). This is the PROPOSE instance of the same machine the TRIAGE gate
    is, minus the deterministic resolve-floor (a premise is prose, not a resolvable path):

    * no declared premise -> ``[]`` (no substrate; nothing to ground — mirrors the triage floor's
      'no scope declared'). Keeps the gate INERT for runs whose proposal carries no premise fields,
      preserving existing propose->plan behavior.
    * a premise declared and NO covering screening found -> one ``PROPOSE_SCREENING_MISSING`` at
      the config-gated severity.
    * screening(s) found but ALL cover a DIFFERENT substrate (the premise changed since screening)
      -> one ``PROPOSE_SCREENING_STALE`` — the fixpoint: re-screen the re-premised run.

    Never raises."""
    if (bad := _validate_inputs(workspace, run_id)) is not None:
        return bad
    root = Path(str(workspace)).resolve()
    premise = _propose_premise(root, run_id)
    if not premise:
        # No declared premise -> no substrate -> no propose-grounding obligation.
        return []
    current_hash = _propose_substrate_hash(premise)
    hashes = _propose_screening_hashes(root, run_id)
    if current_hash in hashes:
        return []
    severity = _propose_grounding_severity(root)
    fields = sorted(premise)
    if not hashes:
        return [
            _v(
                "PROPOSE_SCREENING_MISSING",
                f"run '{run_id}' declares a proposal premise ({len(fields)} field(s): {fields}) "
                f"but carries no propose-screening artifact ({_PROPOSE_SCREENING_KIND}) covering "
                f"the kernel-produced premise substrate; the declared premise must be screened "
                f"(reproduced, not merely read) before PROPOSE exits",
                severity=severity,
                premise_fields=fields,
                substrate_hash=current_hash,
            )
        ]
    return [
        _v(
            "PROPOSE_SCREENING_STALE",
            f"run '{run_id}' carries propose-screening artifact(s) but none cover the CURRENT "
            f"premise substrate (the declared intent or its constraints changed since screening); "
            f"the {len(hashes)} screening(s) cover a different premise — re-screen the re-premised "
            f"run (the fixpoint)",
            severity=severity,
            premise_fields=fields,
            substrate_hash=current_hash,
            found_hashes=hashes,
        )
    ]


def validate_propose_findings(workspace: str | Path, run_id: str) -> list[Violation]:
    """PROPOSE-FINDINGS disposition gate (design/grounded-governance/06) — the propose instance of
    ``validate_triage_findings``, reusing the SAME disposition grounding (M2/M3d via
    :func:`_finding_dispositioned`).

    For the RESOLVING propose-screening artifact(s) that COVER the current premise substrate:
    * ``clean`` -> ``[]``.
    * ``findings`` -> EACH carried finding must be DISPOSITIONED (``discharged`` with a RESOLVING
      fix pointer, or ``adjudicated`` with decision + rationale + cost-if-wrong). Each
      undispositioned finding -> one ``PROPOSE_FINDING_UNDISPOSITIONED`` at the config-gated
      severity.
    * ``cannot_verify`` -> one ``PROPOSE_SCREENING_INCONCLUSIVE`` at ``warn`` (abstained;
      surfaced, never read as a pass).

    Scope discipline (mirrors the triage findings gate): no declared premise / NO covering screening
    -> ``[]`` (the MISSING/STALE signal is :func:`validate_propose_screening`'s; don't
    double-report). Never raises."""
    if (bad := _validate_inputs(workspace, run_id)) is not None:
        return bad
    root = Path(str(workspace)).resolve()
    premise = _propose_premise(root, run_id)
    if not premise:
        return []
    current_hash = _propose_substrate_hash(premise)
    covering = [
        doc
        for doc in _propose_screening_docs(root, run_id)
        if doc.get("substrate_hash") == current_hash
    ]
    if not covering:
        # No covering screening — validate_propose_screening owns MISSING/STALE; no double-report.
        return []
    severity = _propose_grounding_severity(root)
    violations: list[Violation] = []
    for doc in covering:
        verdict = doc.get("verdict")
        if verdict == "cannot_verify":
            violations.append(
                _v(
                    "PROPOSE_SCREENING_INCONCLUSIVE",
                    f"the propose screening for run '{run_id}' abstained (verdict=cannot_verify) "
                    f"over the current premise substrate; an inconclusive screening is surfaced, "
                    f"never read as a pass — resolve it before closing PROPOSE",
                    severity="warn",
                    substrate_hash=current_hash,
                )
            )
            continue
        if verdict != "findings":
            continue
        findings = doc.get("findings")
        if not isinstance(findings, list):
            continue
        for finding in findings:
            # A propose finding discharges to PROPOSE-phase evidence under ``proposals/{run}`` (the
            # governed-writer root where uacp.proposal / the re-premised artifact live — there is no
            # ``propose/`` root), not the late-phase verification/executions dirs the correctness
            # gate uses. Phase-appropriate, mirroring the triage gate's ``proposals/`` prefix.
            if not isinstance(finding, dict) or not _finding_dispositioned(
                finding, root, run_id, allowed_prefixes=("proposals/",)
            ):
                fid = _s(finding.get("id")) if isinstance(finding, dict) else ""
                violations.append(
                    _v(
                        "PROPOSE_FINDING_UNDISPOSITIONED",
                        f"propose finding {fid or '(unidentified)'!r} in run '{run_id}' "
                        f"(verdict=findings) carries no COMPLETE disposition; every open finding "
                        f"must be discharged (a fix pointer that RESOLVES) or adjudicated "
                        f"(decision + rationale + cost-if-wrong)",
                        severity=severity,
                        finding_id=fid,
                        substrate_hash=current_hash,
                    )
                )
    return violations


# The inbound-edge relations the CLASS WITNESS counts (design node 03): calls/references only.
# `defines` (container -> member) is EXCLUDED — it lands inbound on every method and would mark
# every member "wired-in", destroying the sets_value/wires_symbol distinction. This mirrors the
# codeflair witness's inbound_counts semantics (kept here for the defensive fallback path).
_WITNESS_COUNT_REASONS = frozenset({"calls", "references"})


def _canonical_touched(
    ref: tuple[str, str], touched_set: set[tuple[str, str]]
) -> tuple[str, str] | None:
    """Resolve an AUTHORED target ref against the CANONICAL touched set.

    Exact ``(file, name)`` membership wins. Otherwise an unqualified authored name
    matches a touched symbol in the same file whose canonical name ends with
    ``.<name>`` (component boundary, mirroring codeflair's resolution) — but only
    when the match is UNIQUE: an ambiguous shorthand resolves to ``None`` (an
    ambiguous claim must never count as coverage). Returns the canonical touched
    ref used for inbound-count lookup, or ``None``. Never raises."""
    if ref in touched_set:
        return ref
    file, name = ref
    if "." in name:
        return None  # qualified names match exactly or not at all
    suffix = "." + name
    candidates = [t for t in touched_set if t[0] == file and t[1].endswith(suffix)]
    return candidates[0] if len(candidates) == 1 else None


def _target_code_refs(tnode: dict) -> list[tuple[str, str]]:
    """The carried, validated ``code_refs`` on a target node as ``(file, name)`` tuples (empty when
    absent/malformed — ``_carry_code_refs`` already reduced a bad shape to ``None``)."""
    crefs = tnode.get("code_refs")
    if not isinstance(crefs, list):
        return []
    return [
        (r["file"], r["name"]) for r in crefs if isinstance(r, dict) and "file" in r and "name" in r
    ]


def _inbound_count(facts: Any, ref: tuple[str, str]) -> int:
    """Inbound fan-in for a touched symbol (class witness, node 03).

    Prefer the witness's authoritative ``inbound_counts`` (which now carries EVERY touched symbol,
    zero included). Fall back — defensively, should never fire — to counting DISTINCT (src, rel)
    ``calls``/``references`` neighborhood edges whose ``dst`` is ``ref``; ``defines`` is NEVER
    counted (see :func:`witness_class`). Never raises.

    NOTE (council review): this fallback is LOSSY BY CONSTRUCTION — it dedups on
    (src.file, src.name, rel) over the possibly-CAPPED neighborhood list, so it can
    undercount vs the authoritative inbound_counts. A version-skewed witness (no
    inbound_counts key) routes EVERY ref through it; undercount degrades to a weaker
    class, which raise-only turns into less catch, never a false block.
    """
    key = f"{ref[0]}:{ref[1]}"
    ic = getattr(facts, "inbound_counts", None)
    if isinstance(ic, dict):
        val = ic.get(key)
        if isinstance(val, int) and not isinstance(val, bool):
            return val
    seen: set[tuple[Any, Any, Any]] = set()
    for edge in getattr(facts, "neighborhood", ()):  # type: ignore[union-attr]
        if not isinstance(edge, dict) or edge.get("reason") not in _WITNESS_COUNT_REASONS:
            continue
        dst, src = edge.get("dst"), edge.get("src")
        if not isinstance(dst, dict) or not isinstance(src, dict):
            continue
        if (dst.get("file"), dst.get("name")) == ref:
            seen.add((src.get("file"), src.get("name"), edge.get("reason")))
    return len(seen)


def validate_class_underclaim(workspace: str | Path, run_id: str) -> list[Violation]:
    """Layer 2b — class ENTAILMENT (design node 34) + the CLASS WITNESS (design node 03): the gate
    grades the strongest class a target's checks DECLARE against an independent ORACLE. The oracle
    is a RAISE-ONLY, max-rank pick over three sources (node 03 review B1):

      1. ``code_witness`` — the codeflair CONNECTIVITY witness (node 03): for each target that
         declares ``code_refs``, the gate derives the code account ONCE (``derive_witness``), honors
         only refs the diff actually TOUCHED (falsified against ``symbols_touched`` — an untouched
         claim derives nothing and fires ``CHK_CLASS_REF_UNTOUCHED``), and maps each honored ref's
         inbound fan-in to a class (:func:`witness_class`). The per-target witness class is the MAX
         over honored refs. It can only RAISE the oracle, never lower it.
      2. ``entailed_class`` — an independent oracle field (code-plane entailment or a judge).
      3. ``prose`` — the legacy intent/expected_outputs/statement keyword match.

    If the strongest oracle out-ranks the declared class -> ``CHK_CLASS_UNDERCLAIM`` (block, as
    before — only the oracle's provenance/floor upgraded). When the witness and ``entailed_class``
    both testify and DISAGREE, ``CHK_ENTAILED_CLASS_SUPERSEDED`` (warn) records which governs
    (max-rank) regardless of which side wins. When a target declares ``code_refs`` but the witness
    cannot testify (CLI unavailable / weak provenance floor), ``CHK_CLASS_WITNESS_UNAVAILABLE``
    (warn, once) fires and the gate falls back VISIBLY to the two-source oracle — never a silent
    revert. A run with NO ``code_refs`` anywhere is byte-identical to the pre-witness gate: the CLI
    is never invoked. All new codes are advisory ``warn``. Never raises."""
    if (bad := _validate_inputs(workspace, run_id)) is not None:
        return bad
    root = Path(str(workspace)).resolve()
    graph = _load_and_project(workspace, run_id)
    if graph is None:
        return []
    nodes, edges = graph
    check_nodes = {n["id"]: n for n in nodes.values() if n.get("kind") == "check"}
    inbound: dict[str, list[str]] = {}
    for e in edges:
        if e["rel"] == "measured_by":
            inbound.setdefault(e["dst"], []).append(e["src"])

    targets = [n for n in nodes.values() if n.get("kind") in ("scope_item", "work_unit")]

    # --- CLASS WITNESS: derive ONCE over the UNION of every target's declared code_refs (node 03).
    # The claim is opt-in: with no code_refs anywhere, derive_witness is NOT called (byte-identical
    # to the pre-witness gate). derive_witness memoizes, but we still gather + call once here.
    union_refs: list[dict[str, str]] = []
    seen_refs: set[tuple[str, str]] = set()
    for tnode in targets:
        for ref in _target_code_refs(tnode):
            if ref not in seen_refs:
                seen_refs.add(ref)
                union_refs.append({"file": ref[0], "name": ref[1]})

    out: list[Violation] = []
    witness_facts: Any | None = None
    touched_set: set[tuple[str, str]] = set()
    if union_refs:
        result = derive_witness(root, union_refs)
        facts = result.facts
        if result.available and facts is not None and facts.ingestion == "scip":
            witness_facts = facts
            for entry in facts.symbols_touched:
                if isinstance(entry, dict):
                    f, n = entry.get("file"), entry.get("name")
                    if isinstance(f, str) and f and isinstance(n, str) and n:
                        touched_set.add((f, n))
        else:
            # Fail-closed visibility, ONCE: the witness was expected (code_refs declared) but could
            # not testify. Fall back to the two-source oracle below — never a silent revert.
            if not result.available:
                reason = result.error or "witness unavailable"
            else:
                reason = (
                    f"weak provenance floor (ingestion="
                    f"{facts.ingestion if facts else None!r}, expected 'scip')"
                )
            out.append(
                _v(
                    "CHK_CLASS_WITNESS_UNAVAILABLE",
                    f"targets declare code_refs but the class witness could not testify "
                    f"({reason}); falling back to the entailed_class/prose oracle",
                    severity="warn",
                    error=reason,
                    command=list(result.command),
                )
            )

    for tnode in targets:
        # FAIL-CLOSED on a malformed oracle BEFORE the no-checks early-exit (codex P2 #70):
        # `entailed_class` is the INDEPENDENT grounding signal, so a present-but-unknown value
        # (e.g. a typo `wire_symbol`) must block even on a zero-check / pre-adoption target — never
        # silently degrade to "no oracle". A truly absent (None) oracle is fine.
        entailed = tnode.get("entailed_class")
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

        # --- CLASS WITNESS per-target: diff-grounding + heuristic mapping (independent of checks,
        # so CHK_CLASS_REF_UNTOUCHED / CHK_ENTAILED_CLASS_SUPERSEDED fire even on a zero-check
        # target). `witness_cls` becomes the third, raise-only oracle source below.
        witness_cls: str | None = None
        refs = _target_code_refs(tnode)
        if witness_facts is not None and refs:
            # Canonicalize AUTHORED refs against the CANONICAL touched set (codex review
            # MATERIAL): symbols_touched carries derived class-qualified names, so an
            # authored shorthand ("validate_closure" for "Heartgate.validate_closure")
            # would falsely read as untouched under exact matching. Mirror codeflair's
            # documented resolution: exact (file, name) match first; else a UNIQUE
            # component-boundary match (canonical name ends with ".<authored>"); an
            # AMBIGUOUS shorthand (two touched candidates) resolves to nothing — an
            # ambiguous claim must never manufacture coverage (node 03 / C2 doctrine).
            honored: list[tuple[str, str]] = []
            untouched: list[tuple[str, str]] = []
            for ref in refs:
                match = _canonical_touched(ref, touched_set)
                (honored if match is not None else untouched).append(
                    match if match is not None else ref
                )
            if untouched:
                shown = sorted(untouched)
                out.append(
                    _v(
                        "CHK_CLASS_REF_UNTOUCHED",
                        f"target '{tnode['id']}' declares {len(untouched)} code_ref(s) the diff "
                        f"did not touch: {[f'{f}:{n}' for f, n in shown]} — they DERIVE NO CLASS "
                        f"(diff-grounded: an untouched claim cannot manufacture a weak oracle)",
                        severity="warn",
                        target=tnode["id"],
                        refs=[f"{f}:{n}" for f, n in shown],
                    )
                )
            if honored:
                # Per-target witness class = MAX over honored refs (a multi-symbol target cannot
                # cherry-pick its weakest symbol — node 03 review M3).
                witness_cls = max(
                    (witness_class(_inbound_count(witness_facts, r)) for r in honored),
                    key=class_rank,
                )
            # Disagreement surfacing: fire regardless of which side wins (max-rank governs).
            if witness_cls is not None and entailed is not None and witness_cls != entailed:
                governs = (
                    witness_cls if class_rank(witness_cls) >= class_rank(entailed) else entailed
                )
                out.append(
                    _v(
                        "CHK_ENTAILED_CLASS_SUPERSEDED",
                        f"target '{tnode['id']}' witness class '{witness_cls}' disagrees with the "
                        f"declared entailed_class '{entailed}' — '{governs}' governs (max-rank)",
                        severity="warn",
                        target=tnode["id"],
                        witness_class=witness_cls,
                        entailed_class=entailed,
                        governs=governs,
                    )
                )

        cids = [cid for cid in inbound.get(tnode["id"], []) if cid in check_nodes]
        if not cids:
            continue
        declared_rank = max(
            (class_rank(check_nodes[cid].get("target_class")) for cid in cids), default=0
        )
        # The ORACLE: an independent derivation of the target's true class, to cross-check the
        # agent's (weaker) declared class. Fundamentally an INDEPENDENCE check. RAISE-ONLY, max-rank
        # over THREE sources (node 03 B1 — strongest wins; ties prefer the more grounded source):
        #   3. `code_witness` — codeflair connectivity (node 03), the most grounded; can only raise.
        #   2. `entailed_class` — independent oracle field (code-plane entailment / a judge).
        #   1. `candidate_class(prose)` — legacy intent/expected_outputs/statement keyword match.
        eo = tnode.get("expected_outputs")
        eo_text = " ".join(map(str, eo)) if isinstance(eo, list) else str(eo or "")
        text = " ".join(s for s in (tnode.get("intent"), eo_text, tnode.get("statement")) if s)
        cand, kw = candidate_class(text)
        # (rank, priority, class, source, basis) — max by (rank, priority) is the raise-only pick;
        # priority breaks a rank tie toward the more grounded source, preserving the legacy
        # entailed-over-prose preference exactly (witness > entailed > prose).
        oracle_candidates: list[tuple[int, int, str, str, str]] = []
        if witness_cls is not None:
            oracle_candidates.append(
                (class_rank(witness_cls), 3, witness_cls, "code_witness", "codeflair connectivity")
            )
        if entailed is not None:
            oracle_candidates.append(
                (class_rank(entailed), 2, entailed, "entailed_class", "independent oracle")
            )
        if cand is not None:
            oracle_candidates.append((class_rank(cand), 1, cand, "prose", f"matched «{kw}»"))
        if oracle_candidates:
            _, _, oracle_cls, oracle_src, oracle_basis = max(
                oracle_candidates, key=lambda c: (c[0], c[1])
            )
        else:
            oracle_cls = oracle_src = oracle_basis = None
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
if not any(name == "behavioral_floor" for name, _ in ENGINES):
    ENGINES.append(("behavioral_floor", validate_behavioral_floor))
if not any(name == "correctness_screening" for name, _ in ENGINES):
    ENGINES.append(("correctness_screening", validate_correctness_screening))
if not any(name == "correctness_findings" for name, _ in ENGINES):
    ENGINES.append(("correctness_findings", validate_correctness_findings))
if not any(name == "check_class_underclaim" for name, _ in ENGINES):
    ENGINES.append(("check_class_underclaim", validate_class_underclaim))

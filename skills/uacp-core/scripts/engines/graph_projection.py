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
* ``GP_CONTRADICTED``       — a ``pass`` assessment whose evidence checkpoint is
  itself ``fail`` (a "done" claim contradicted by its own evidence).

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


def _project(doc: dict, nodes: dict, edges: list, run: str) -> None:
    """Extract nodes + typed edges from one artifact doc into the shared graph."""
    def add_node(nid: str, kind: str, **extra: Any) -> None:
        nodes.setdefault(nid, {"id": nid, "kind": kind, **extra})

    def add_edge(src: str, dst: str, rel: str) -> None:
        edges.append({"src": src, "dst": dst, "rel": rel})

    scope = doc.get("scope") if isinstance(doc.get("scope"), dict) else {}
    for item in _aslist(scope.get("in_scope")):
        if isinstance(item, dict) and item.get("id"):                 # new canonical form
            add_node(item["id"], "scope_item", statement=item.get("statement", ""))
        elif isinstance(item, str):                                   # legacy bare string
            add_node(_synth_id("si", item, run), "scope_item", statement=item)

    for wu in _aslist(doc.get("work_units")):
        if isinstance(wu, dict) and wu.get("id"):
            add_node(wu["id"], "work_unit", title=wu.get("title", ""))
            for dst in _aslist(wu.get("derives_from")):
                add_edge(wu["id"], dst, "derives_from")

    for ob in _aslist(doc.get("evidence_obligations")):
        if isinstance(ob, dict) and ob.get("id"):
            add_node(ob["id"], "evidence_obligation")
            if ob.get("work_unit_id"):
                add_edge(ob["id"], ob["work_unit_id"], "obligation_for")

    for cp in _aslist(doc.get("checkpoints")):
        if isinstance(cp, dict) and cp.get("id"):
            add_node(cp["id"], "checkpoint", result=cp.get("result"))
            if cp.get("work_unit_id"):
                add_edge(cp["id"], cp["work_unit_id"], "checkpoint_of")

    for a in _aslist(doc.get("assessments")):
        if not isinstance(a, dict):
            continue
        oid = a.get("obligation_id")
        aid = a.get("id") or _synth_id("as", str(oid), run)
        add_node(aid, "assessment", result=a.get("state") or a.get("result"))
        if oid:
            add_edge(aid, oid, "obligation_id")
        if a.get("work_unit_id"):
            add_edge(aid, a["work_unit_id"], "work_unit_id")
        for ref in _aslist(a.get("evidence_refs")):
            if isinstance(ref, str):
                add_edge(aid, ref, "evidence_refs")


def _structural_violations(nodes: dict, edges: list) -> list[Violation]:
    out: list[Violation] = []
    df_dst = {e["dst"] for e in edges if e["rel"] == "derives_from"}
    df_src = {e["src"] for e in edges if e["rel"] == "derives_from"}

    for n in nodes.values():
        if n["kind"] == "scope_item" and n["id"] not in df_dst:
            out.append(_v("GP_UNCOVERED_INTENT",
                          f"scope_item '{n['id']}' has no work_unit deriving from it "
                          f"(dropped intent): «{(n.get('statement') or '')[:60]}»",
                          scope_item=n["id"]))
        if n["kind"] == "work_unit" and n["id"] not in df_src:
            out.append(_v("GP_ORPHAN_WORK_UNIT",
                          f"work_unit '{n['id']}' has no derives_from to any scope_item "
                          f"(unanchored task)", work_unit=n["id"]))

    for e in edges:
        if e["dst"] not in nodes:
            out.append(_v("GP_PHANTOM_EDGE",
                          f"edge {e['src']} --{e['rel']}--> {e['dst']} targets a node that "
                          f"does not exist (forged/dangling reference)",
                          src=e["src"], dst=e["dst"], rel=e["rel"]))

    cp_result = {n["id"]: n.get("result") for n in nodes.values() if n["kind"] == "checkpoint"}
    for e in edges:
        if e["rel"] != "evidence_refs":
            continue
        asmt = nodes.get(e["src"], {})
        if asmt.get("result") == "pass" and cp_result.get(e["dst"]) not in (None, "pass"):
            out.append(_v("GP_CONTRADICTED",
                          f"assessment '{e['src']}' claims pass but its evidence "
                          f"checkpoint '{e['dst']}' is '{cp_result.get(e['dst'])}'",
                          assessment=e["src"], checkpoint=e["dst"]))
    return out


def validate_graph_projection(workspace: str | Path, run_id: str) -> list[Violation]:
    """Project the run's manifest artifacts into a graph and assert structural
    integrity. Returns a list of Violation (empty == sound). Never raises."""
    try:
        root = Path(str(workspace)).resolve()
    except Exception as exc:
        return [_v("GP0_WORKSPACE_INVALID", f"workspace path invalid: {type(exc).__name__}: {exc}")]
    if not run_id or not isinstance(run_id, str):
        return [_v("GP0_RUN_ID_INVALID", f"run_id invalid: {run_id!r}")]

    loaded = load_manifest(root, run_id)
    if loaded.error is not None or loaded.value is None:
        # No manifest -> nothing to project (other engines own "manifest missing").
        return []
    artifacts = loaded.value.raw.get("artifacts")
    if not isinstance(artifacts, dict):
        return []

    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    for rel in artifacts.values():
        if not isinstance(rel, str) or not rel:
            continue
        doc = load_artifact(root, rel)
        if doc.error is None and isinstance(doc.value, dict):
            _project(doc.value, nodes, edges, run_id)

    return _structural_violations(nodes, edges)


# Register this engine (guard against double-registration under alias imports).
if not any(name == "graph_projection" for name, _ in ENGINES):
    ENGINES.append(("graph_projection", validate_graph_projection))

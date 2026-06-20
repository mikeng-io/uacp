#!/usr/bin/env python3
"""Spike: in-memory manifest graph projector + closure checks (READ-ONLY).

Proves the PROPOSE->PLAN seam. Parses today's manifest YAML for one run into an
in-memory node/edge graph and runs the closure checks. Because today's manifests
lack scope_item ids and work_unit.derives_from, every scope_item is `uncovered`
and every work_unit is an `orphan` -- self-demonstrating the broken seam.

Throwaway scratch under docs/design/graph-engine/spike/. No writes. stdlib + PyYAML.

Usage:  python3 projector.py <run_id>
"""
from __future__ import annotations
import sys, hashlib
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[3]  # spike -> graph-engine -> design -> docs -> repo


def synth_id(prefix: str, text: str, run: str) -> str:
    h = hashlib.sha1(f"{run}:{text}".encode()).hexdigest()[:8]
    return f"{prefix}-{h}"


class Graph:
    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.edges: list[dict] = []

    def add_node(self, nid, kind, run, path, **extra):
        self.nodes.setdefault(nid, {"id": nid, "kind": kind, "run": run, "path": path, **extra})

    def add_edge(self, src, dst, rel, prov):
        self.edges.append({"src": src, "dst": dst, "rel": rel, "prov": prov})


def _aslist(v):
    return v if isinstance(v, list) else []


def project(g: Graph, doc: dict, path: str, run: str) -> None:
    # scope_items <- scope.in_scope (proposal + plan). Compat shim: synth id from text.
    scope = doc.get("scope")
    scope = scope if isinstance(scope, dict) else {}
    for item in _aslist(scope.get("in_scope")):
        if isinstance(item, str):                            # legacy: bare string -> synth id
            g.add_node(synth_id("si", item, run), "scope_item", run, path, statement=item)
        elif isinstance(item, dict) and item.get("id"):      # NEW canonical form: {id, statement}
            g.add_node(item["id"], "scope_item", run, path, statement=item.get("statement", ""))
    # work_units <- plan or execution work_units[].
    for wu in _aslist(doc.get("work_units")):
        if not isinstance(wu, dict) or not wu.get("id"):
            continue
        g.add_node(wu["id"], "work_unit", run, path, title=wu.get("title", ""))
        for dst in (wu.get("derives_from") or []):     # the missing key -> none today
            g.add_edge(wu["id"], dst, "derives_from", "asserted")
    # evidence_obligations (PIV) -> work_unit
    for ob in (doc.get("evidence_obligations") or []):
        if isinstance(ob, dict) and ob.get("id"):
            g.add_node(ob["id"], "evidence_obligation", run, path)
            if ob.get("work_unit_id"):
                g.add_edge(ob["id"], ob["work_unit_id"], "obligation_for", "derived")
    # assessments (piv_assessment) -> obligation / work_unit
    for a in (doc.get("assessments") or []):
        if not isinstance(a, dict):
            continue
        oid = a.get("obligation_id")
        aid = a.get("id") or synth_id("as", oid or path, run)
        g.add_node(aid, "assessment", run, path, result=a.get("state") or a.get("result"))
        if oid:
            g.add_edge(aid, oid, "obligation_id", "derived")
        if a.get("work_unit_id"):
            g.add_edge(aid, a["work_unit_id"], "work_unit_id", "derived")
        for ref in _aslist(a.get("evidence_refs")):
            if isinstance(ref, str):
                g.add_edge(aid, ref, "evidence_refs", "derived")
    # checkpoints (EXECUTE) -> work_unit
    for cp in _aslist(doc.get("checkpoints")):
        if isinstance(cp, dict) and cp.get("id"):
            g.add_node(cp["id"], "checkpoint", run, path, result=cp.get("result"))
            if cp.get("work_unit_id"):
                g.add_edge(cp["id"], cp["work_unit_id"], "checkpoint_of", "derived")


def load_run(run_id: str) -> Graph:
    g = Graph()
    patterns = [f"proposals/{run_id}*.yaml", f"plans/{run_id}*.yaml",
                f"executions/{run_id}*.yaml", f"verification/{run_id}*.yaml",
                f"outputs/{run_id}*.yaml", f"state/runs/{run_id}*.yaml"]
    for pat in patterns:
        for fp in sorted(ROOT.glob(pat)):
            try:
                doc = yaml.safe_load(fp.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"  ! parse error {fp.name}: {e}")
                continue
            if isinstance(doc, dict):
                project(g, doc, str(fp.relative_to(ROOT)), run_id)
    return g


def closure(g: Graph) -> dict:
    df_dst = {e["dst"] for e in g.edges if e["rel"] == "derives_from"}
    df_src = {e["src"] for e in g.edges if e["rel"] == "derives_from"}
    # T5 fix: a work_unit is verified ONLY by an assessment whose result == pass (not just any assessment)
    passed_wu = {e["dst"] for e in g.edges if e["rel"] == "work_unit_id"
                 and g.nodes.get(e["src"], {}).get("result") == "pass"}
    cp_result = {n["id"]: n.get("result") for n in g.nodes.values() if n["kind"] == "checkpoint"}
    # contradicted: a `pass` assessment whose evidence checkpoint is itself NOT pass (a lie)
    contradicted = [f"{e['src']}(pass) ← evidence {e['dst']}={cp_result.get(e['dst'])}"
                    for e in g.edges if e["rel"] == "evidence_refs"
                    and g.nodes.get(e["src"], {}).get("result") == "pass"
                    and cp_result.get(e["dst"]) not in (None, "pass")]
    sids = [n["id"] for n in g.nodes.values() if n["kind"] == "scope_item"]
    wids = [n["id"] for n in g.nodes.values() if n["kind"] == "work_unit"]
    return {
        "uncovered": [s for s in sids if s not in df_dst],     # scope_item, no inbound derives_from
        "orphan": [w for w in wids if w not in df_src],        # work_unit, no outbound derives_from
        "phantom": [e for e in g.edges if e["dst"] not in g.nodes],  # edge to a missing node
        "contradicted": contradicted,                          # pass assessment over fail/absent evidence
        "unverified": [w for w in wids if w not in passed_wu], # work_unit with no PASSING assessment
    }


def trace(g: Graph, start: str) -> None:
    """Walk the full connected chain from `start` (both directions) and report end-to-end coverage."""
    adj: dict[str, list] = {}
    for e in g.edges:
        adj.setdefault(e["src"], []).append(e["dst"])
        adj.setdefault(e["dst"], []).append(e["src"])
    seen, stack = {start}, [start]
    while stack:
        for m in adj.get(stack.pop(), []):
            if m not in seen:
                seen.add(m); stack.append(m)
    kinds = sorted({g.nodes[n]["kind"] for n in seen if n in g.nodes})
    print(f"\n-- TRACE from {start} (full connected chain, both directions) --")
    print(f"reached {len(seen)} nodes · kinds: {kinds}")
    for e in g.edges:
        if e["src"] in seen and e["dst"] in seen:
            print(f"   {e['src']:5} --{e['rel']:14}--> {e['dst']}")
    phases = {"scope_item", "work_unit", "evidence_obligation", "checkpoint", "assessment"}
    missing = sorted(phases - set(kinds))
    print(f">> END-TO-END chain {'COMPLETE' if not missing else 'INCOMPLETE'} "
          f"(PROPOSE→PLAN→EXECUTE→VERIFY): "
          f"{'all 5 node kinds connected (intent→task→obligation→checkpoint→assessment)' if not missing else 'missing '+str(missing)}")


def load_dir(d: str, run: str) -> Graph:
    g = Graph()
    for fp in sorted(Path(d).glob("*.yaml")):
        try:
            doc = yaml.safe_load(fp.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  ! parse error {fp.name}: {e}")
            continue
        if isinstance(doc, dict):
            project(g, doc, fp.name, run)
    return g


def main():
    args = sys.argv[1:]
    if args and args[0] == "--dir":
        run = Path(args[1]).name
        g = load_dir(args[1], run)
    else:
        run = args[0] if args else "uacp-governed-lifecycle-dry-run"
        g = load_run(run)
    c = closure(g)
    kinds = {}
    for n in g.nodes.values():
        kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
    print(f"== manifest graph projection: run={run} (repo={ROOT.name}) ==")
    print(f"nodes: {len(g.nodes)}  {dict(sorted(kinds.items()))}")
    print(f"edges: {len(g.edges)}  by-rel={ {r: sum(1 for e in g.edges if e['rel']==r) for r in sorted({e['rel'] for e in g.edges})} }")
    # T2: structural checks ALWAYS block; progress checks are phase-gated (only block at the relevant exit)
    STRUCTURAL = {"uncovered", "orphan", "phantom", "contradicted"}
    print("\n-- CLOSURE CHECKS --  (STRUCT = always-block · PROG = phase-gated)")
    for chk in ("uncovered", "orphan", "phantom", "contradicted", "unverified"):
        items = c[chk]
        cat = "STRUCT" if chk in STRUCTURAL else "PROG"
        flag = ("BLOCK" if chk in STRUCTURAL else "note") if items else "ok"
        print(f"[{flag:5}] {cat:6} {chk:12} {len(items)}")
        for it in items[:8]:
            label = it if isinstance(it, str) else f"{it['src']}->{it['dst']} ({it['rel']})"
            extra = ""
            if isinstance(it, str) and it in g.nodes and g.nodes[it].get("statement"):
                extra = f"  «{g.nodes[it]['statement'][:48]}»"
            print(f"            - {label}{extra}")
    df = sum(1 for e in g.edges if e["rel"] == "derives_from")
    seam = bool(c["uncovered"]) and bool(c["orphan"])
    verdict = "DEMONSTRATED — broken as designed" if seam else (
        "CLOSED — intents covered" if df else "empty (no nodes)")
    print(f"\n>> PROPOSE->PLAN seam {verdict}: "
          f"{len(c['uncovered'])} uncovered intents, {len(c['orphan'])} orphan work_units, "
          f"{df} derives_from edges.")
    if "--trace" in args:
        trace(g, args[args.index("--trace") + 1])


if __name__ == "__main__":
    main()

"""Codeflair SCIP ingest — a real SCIP index -> the fused store.

Split in two, like the core: a PURE transform over already-parsed SCIP JSON
(``ingest_scip_json``) that is hermetically testable on a tiny fixture, and a thin
wrapper (``index_go_repo``) that shells out to ``scip-go`` + ``scip print --json`` for
real use. The pure layer is where the logic — and the tests — live.

Edge model (spike-proven on Trustless): SCIP occurrences carry symbol + role, not an
explicit call graph, so a reference edge is attributed to its **enclosing definition**
(the nearest preceding ``Definition`` occurrence in the same document). That yields
caller -> callee: ``src`` = the enclosing symbol, ``dst`` = the referenced symbol.
"""
from __future__ import annotations

import bisect
import json
import subprocess
from dataclasses import dataclass

from codeflair.store import Edge, Store, Symbol

_ROLE_DEFINITION = 0x1  # SCIP symbol_roles bit


@dataclass(frozen=True)
class IngestStats:
    documents: int
    symbols: int
    edges: int


def _scheme_lang(symbol: str) -> str:
    """SCIP symbol scheme is the first whitespace token: ``scip-go`` / ``scip-typescript``."""
    head = symbol.split(" ", 1)[0]
    return {"scip-go": "go", "scip-typescript": "ts", "scip-python": "py"}.get(head, head or "?")


def _display_name(symbol: str) -> str:
    """Last descriptor of a SCIP symbol, for human display (not identity)."""
    return symbol.split(" ")[-1].split("/")[-1] or symbol


def _is_repo_path(path: str) -> bool:
    """True for a file that actually lives in the indexed repo. scip-go also emits
    documents for the stdlib and the go-build cache (``../../Library/Caches/...``); those
    escape the repo root or are absolute and must not pollute the graph."""
    if not path or path.startswith("../") or path.startswith("/"):
        return False
    if "go-build" in path or "/Caches/" in path:
        return False
    # drop hidden-dir + worktree-copy paths (.git/.trustless/worktrees/…)
    return not any(p.startswith(".") or p == "worktrees" for p in path.split("/"))


def ingest_scip_json(
    store: Store,
    data: dict,
    *,
    provenance: str = "parsed",
) -> IngestStats:
    """Ingest a parsed SCIP index (the JSON shape of ``scip print --json``) into ``store``.

    Adds a :class:`Symbol` per distinct non-local symbol (keyed by its SCIP descriptor)
    and a ``calls`` :class:`Edge` (source=``scip``) from each reference's enclosing
    definition to the referenced symbol. Returns counts.
    """
    documents = data.get("documents", [])
    # Per document: collect (symbol, line, is_def); remember a representative location
    # for each symbol's definition so the store node has a file/line.
    defs_by_doc: dict[str, list[tuple[int, str]]] = {}
    refs_by_doc: dict[str, list[tuple[int, str]]] = {}
    sym_def_loc: dict[str, tuple[str, int]] = {}
    all_syms: set[str] = set()

    n_repo_docs = 0
    for d in documents:
        path = d.get("relative_path", "")
        if not _is_repo_path(path):
            continue                         # skip stdlib / dep / go-build-cache documents
        n_repo_docs += 1
        for o in d.get("occurrences", []):
            rng = o.get("range") or []
            if not rng:
                continue
            sym = o.get("symbol", "")
            if not sym or sym.startswith("local "):
                continue
            line = rng[0]
            all_syms.add(sym)
            if o.get("symbol_roles", 0) & _ROLE_DEFINITION:
                defs_by_doc.setdefault(path, []).append((line, sym))
                sym_def_loc.setdefault(sym, (path, line))
            else:
                refs_by_doc.setdefault(path, []).append((line, sym))

    for arr in defs_by_doc.values():
        arr.sort()

    # symbols
    for sym in all_syms:
        path, line = sym_def_loc.get(sym, ("", 0))
        store.add_symbol(
            Symbol(symbol=sym, lang=_scheme_lang(sym), file=path, name=_display_name(sym), line=line)
        )

    # edges: each reference -> its enclosing (nearest preceding) definition in the same doc
    n_edges = 0
    seen: set[tuple[str, str]] = set()
    for path, refs in refs_by_doc.items():
        defs = defs_by_doc.get(path)
        if not defs:
            continue
        for line, ref_sym in refs:
            i = bisect.bisect_right(defs, (line, "￿")) - 1
            if i < 0:
                continue
            caller = defs[i][1]
            if caller == ref_sym:
                continue
            key = (caller, ref_sym)
            if key in seen:
                continue
            seen.add(key)
            store.add_edge(Edge(src=caller, dst=ref_sym, rel="calls", source="scip", provenance=provenance))
            n_edges += 1

    store.commit()
    return IngestStats(documents=n_repo_docs, symbols=len(all_syms), edges=n_edges)


# -- real-tool wrapper (integration; not exercised by the hermetic unit suite) --------

def index_go_repo(store: Store, repo_path: str, *, scip_go: str = "scip-go", scip: str = "scip") -> IngestStats:
    """Index a Go repo with ``scip-go`` and ingest it. Indexes IN ``repo_path`` and reads
    the result read-only — never mutates the target's source. Requires ``scip-go`` and the
    ``scip`` CLI on PATH."""
    out = subprocess.run(
        [scip_go, "--output", "/dev/stdout"], cwd=repo_path, capture_output=True
    )
    # scip-go writes protobuf; convert to JSON via `scip print --json -`.
    printed = subprocess.run(
        [scip, "print", "--json", "-"], input=out.stdout, capture_output=True
    )
    data = json.loads(printed.stdout)
    return ingest_scip_json(store, data)

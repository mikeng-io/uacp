"""Codeflair SCIP ingest — a real SCIP index -> the fused store.

Split in two, like the core: a PURE transform over already-parsed SCIP JSON
(``ingest_scip_json``) that is hermetically testable on a tiny fixture, and a thin
wrapper (``index_repo``) that shells out to the per-language SCIP indexer (scip-go /
scip-python / scip-typescript) + ``scip print --json``. The pure layer holds the logic
and the tests; ``ingest_scip_json`` is indexer-agnostic — SCIP is one format.

Edge model (spike-proven on Trustless): SCIP occurrences carry symbol + role, not an
explicit call graph, so a reference edge is attributed to its **enclosing definition**
(the nearest preceding ``Definition`` occurrence in the same document). That yields
caller -> callee: ``src`` = the enclosing symbol, ``dst`` = the referenced symbol.
"""

from __future__ import annotations

import bisect
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from codeflair.store import Edge, Store, Symbol

# Repo-local indexer binaries (Python/TypeScript) live under the package's vendor/
# node_modules/.bin — installed by scripts/bootstrap.py, never on the global PATH.
_VENDOR_BIN = Path(__file__).resolve().parents[2] / "vendor" / "node_modules" / ".bin"

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
            continue  # skip stdlib / dep / go-build-cache documents
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
            Symbol(
                symbol=sym, lang=_scheme_lang(sym), file=path, name=_display_name(sym), line=line
            )
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
            store.add_edge(
                Edge(src=caller, dst=ref_sym, rel="calls", source="scip", provenance=provenance)
            )
            n_edges += 1

    store.commit()
    return IngestStats(documents=n_repo_docs, symbols=len(all_syms), edges=n_edges)


# -- real-tool wrapper (integration; not exercised by the hermetic unit suite) --------

# SCIP indexer per stage-1 language. Python/TypeScript resolve from the repo-local
# vendor bin (npm); Go uses scip-go (a Go tool, installed via `go install` / PATH).
SCIP_LANGS = ("go", "python", "typescript")


def _resolve_bin(tool: str) -> str:
    """Prefer the repo-local vendored binary; fall back to PATH."""
    local = _VENDOR_BIN / tool
    return str(local) if local.exists() else tool


def _indexer_cmd(lang: str, out: str, repo_path: str) -> list[str]:
    name = os.path.basename(os.path.abspath(repo_path)) or "project"
    if lang == "go":
        return [_resolve_bin("scip-go"), "--output", out]
    if lang == "python":
        # --project-version is required: scip-python's git-revision default crashes on a
        # repo without a resolvable revision (ScipSymbol normalizeNameOrVersion).
        return [
            _resolve_bin("scip-python"),
            "index",
            "--output",
            out,
            "--project-name",
            name,
            "--project-version",
            "0.0.0",
        ]
    if lang == "typescript":
        return [_resolve_bin("scip-typescript"), "index", "--output", out, "--infer-tsconfig"]
    raise ValueError(f"unsupported SCIP language {lang!r}; expected one of {SCIP_LANGS}")


def index_repo(store: Store, repo_path: str, lang: str, *, scip: str = "scip") -> IngestStats:
    """Index ``repo_path`` with the SCIP indexer for ``lang`` (go|python|typescript), convert
    to JSON, and ingest. Reads the repo READ-ONLY; the index is written to a temp dir OUTSIDE
    the target, so the target's source is never mutated. Indexers resolve repo-local first."""
    tmp = tempfile.mkdtemp(prefix="cf-scip-")
    out = os.path.join(tmp, "index.scip")
    try:
        subprocess.run(
            _indexer_cmd(lang, out, repo_path), cwd=repo_path, check=True, capture_output=True
        )
        printed = subprocess.run(
            [_resolve_bin(scip), "print", "--json", out], check=True, capture_output=True
        )
        return ingest_scip_json(store, json.loads(printed.stdout))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

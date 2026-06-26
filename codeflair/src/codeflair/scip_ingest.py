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
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from codeflair.freshness import content_hash
from codeflair.store import Edge, Store, Symbol

# Per-source freshness stamp for SCIP-ingested files (11-substrate `tool_version`).
SCIP_TOOL_VERSION = "codeflair-scip-ingest/1"

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


def _descriptor(symbol: str) -> str:
    """The trailing descriptor token of a SCIP symbol (the last whitespace-separated field).
    SCIP descriptor suffixes encode the kind: ``).`` method, ``.`` term, ``#`` type,
    ``/`` namespace. Mirrors ``_display_name``'s convention (descriptor = last space token)."""
    return symbol.split(" ")[-1]


def _is_callable(symbol: str) -> bool:
    """True for a SCIP **method** descriptor (ends ``).``) — a call TARGET. A reference to a
    callable is a ``calls`` edge; a reference to a non-callable (term/type) is ``references``."""
    return _descriptor(symbol).endswith(").")


def _is_container(symbol: str) -> bool:
    """True for a SCIP **type** (``#``) or **namespace** (``/``) descriptor — a scope that can
    DEFINE members. ``defines`` edges run container -> member; siblings never define siblings."""
    desc = _descriptor(symbol)
    return desc.endswith("#") or desc.endswith("/")


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
    file_contents: Mapping[str, bytes] | None = None,
    commit_sha: str = "",
) -> IngestStats:
    """Ingest a parsed SCIP index (the JSON shape of ``scip print --json``) into ``store``.

    Adds a :class:`Symbol` per distinct non-local symbol (keyed by its SCIP descriptor) and
    THREE distinct SCIP-sourced :class:`Edge` relations (source=``scip``) per 01b-store (D2):

    - ``defines`` — a container definition (type/namespace) -> each member it defines (the
      nearest enclosing **container** def, so sibling methods never "define" one another);
    - ``calls`` — a reference whose target is a **callable** (a SCIP method descriptor, ``).``)
      attributed to its enclosing definition (caller -> callee);
    - ``references`` — a reference whose target is **not** callable (a term/type use)
      attributed to its enclosing definition.

    SCIP occurrences carry only symbol + role (no explicit call graph), so call/reference
    edges are attributed to the nearest preceding ``Definition`` in the same document, and
    the call/reference split is decided by the *callee*'s descriptor kind. Returns counts
    (``edges`` totals all three relations).

    When ``file_contents`` (``{relative_path: source_bytes}``) is supplied, a per-file
    content hash + a per-source ``freshness`` row (source=``scip``) are recorded for each
    **actually-ingested** repo document — the freshness substrate (10-freshness). Only
    files SCIP actually ingested get rows (a path present in ``file_contents`` but skipped
    as stdlib/dep is *not* recorded); absent bytes mean no row for that file.
    """
    documents = data.get("documents", [])
    # Per document: collect (symbol, line, is_def); remember a representative location
    # for each symbol's definition so the store node has a file/line.
    defs_by_doc: dict[str, list[tuple[int, str]]] = {}
    refs_by_doc: dict[str, list[tuple[int, str]]] = {}
    sym_def_loc: dict[str, tuple[str, int]] = {}
    all_syms: set[str] = set()
    repo_paths: list[str] = []

    n_repo_docs = 0
    for d in documents:
        path = d.get("relative_path", "")
        if not _is_repo_path(path):
            continue  # skip stdlib / dep / go-build-cache documents
        n_repo_docs += 1
        repo_paths.append(path)
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

    # edges (D2): three distinct relations, deduped by (src, dst, rel).
    n_edges = 0
    seen: set[tuple[str, str, str]] = set()

    def _emit(src: str, dst: str, rel: str) -> None:
        nonlocal n_edges
        if src == dst:
            return
        key = (src, dst, rel)
        if key in seen:
            return
        seen.add(key)
        store.add_edge(Edge(src=src, dst=dst, rel=rel, source="scip", provenance=provenance))
        n_edges += 1

    # `defines`: each member definition -> its nearest enclosing CONTAINER definition
    # (type/namespace). Container -> member, never sibling -> sibling (a sibling method is
    # not a container, so it is never picked as an enclosing scope).
    for defs in defs_by_doc.values():
        containers = [(ln, sym) for ln, sym in defs if _is_container(sym)]
        if not containers:
            continue
        for ln, sym in defs:
            enclosing: str | None = None
            for cln, csym in containers:  # ascending; keep the last container at/above `ln`
                if cln > ln:
                    break
                if csym != sym:
                    enclosing = csym
            if enclosing is not None:
                _emit(enclosing, sym, "defines")

    # `calls` / `references`: each reference -> its nearest preceding definition in the same
    # doc; the relation is `calls` iff the referenced symbol is callable, else `references`.
    for path, refs in refs_by_doc.items():
        defs = defs_by_doc.get(path)
        if not defs:
            continue
        for line, ref_sym in refs:
            i = bisect.bisect_right(defs, (line, "￿")) - 1
            if i < 0:
                continue
            caller = defs[i][1]
            _emit(caller, ref_sym, "calls" if _is_callable(ref_sym) else "references")

    # freshness substrate: hash each actually-ingested repo file (10-freshness). Only
    # files SCIP ingested AND for which bytes were supplied get a row.
    if file_contents is not None:
        for path in repo_paths:
            data_bytes = file_contents.get(path)
            if data_bytes is None:
                continue
            h = content_hash(data_bytes)
            store.record_file(path, h, lang=_scheme_lang_for_file(path), commit_sha=commit_sha)
            store.record_freshness(
                "scip", path, h, commit_sha=commit_sha, tool_version=SCIP_TOOL_VERSION
            )

    store.commit()
    return IngestStats(documents=n_repo_docs, symbols=len(all_syms), edges=n_edges)


def _scheme_lang_for_file(path: str) -> str:
    """Best-effort file language from suffix (the file table's ``lang`` is advisory)."""
    return {".go": "go", ".py": "py", ".ts": "ts", ".tsx": "ts"}.get(os.path.splitext(path)[1], "")


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


def index_repo(
    store: Store,
    repo_path: str,
    lang: str,
    *,
    scip: str = "scip",
    commit_sha: str = "",
    built_at: str | None = None,
) -> IngestStats:
    """Index ``repo_path`` with the SCIP indexer for ``lang`` (go|python|typescript), convert
    to JSON, and ingest. Reads the repo READ-ONLY; the index is written to a temp dir OUTSIDE
    the target, so the target's source is never mutated. Indexers resolve repo-local first.

    File bytes are read from the repo to populate the freshness substrate (per-file hash +
    per-source ``freshness`` row). When ``built_at`` is given the store watermark is set —
    ``built_at`` is injected (the store never reads the wall clock)."""
    tmp = tempfile.mkdtemp(prefix="cf-scip-")
    out = os.path.join(tmp, "index.scip")
    try:
        # Capture the instant indexing begins. A repo file modified at/after this instant was
        # edited DURING (or after) the index run, so the SCIP edges may reflect older content
        # than the bytes we are about to read (the ingest-time TOCTOU, F5). Such files have
        # their freshness WITHHELD below — the index still gets their symbols/edges, but no
        # "this is fresh" stamp, so a later query treats them 'unverified', never trusted.
        index_started = time.time()
        subprocess.run(
            _indexer_cmd(lang, out, repo_path), cwd=repo_path, check=True, capture_output=True
        )
        printed = subprocess.run(
            [_resolve_bin(scip), "print", "--json", out], check=True, capture_output=True
        )
        index = json.loads(printed.stdout)
        file_contents = _read_repo_bytes(repo_path, index, index_started=index_started)
        stats = ingest_scip_json(store, index, file_contents=file_contents, commit_sha=commit_sha)
        if built_at is not None:
            store.set_watermark(commit_sha, built_at)
        return stats
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _modified_during_index(mtimes: dict[str, float], index_started: float) -> set[str]:
    """Files whose mtime is at/after ``index_started`` — edited during (or after) the index
    run, so their SCIP edges and the bytes we read may disagree (F5). Pure + deterministic
    (mtimes + threshold injected) so it is unit-testable without a real indexer."""
    return {p for p, mt in mtimes.items() if mt >= index_started}


def _read_repo_bytes(
    repo_path: str, index: dict, *, index_started: float | None = None
) -> dict[str, bytes]:
    """Read the on-disk bytes of each SCIP document that lives in the repo, for hashing.

    When ``index_started`` is given, files modified at/after that instant are EXCLUDED from
    the returned bytes (F5): their freshness is withheld so a later query cannot mistake their
    possibly-stale SCIP edges for fresh. The residual — a sub-second edit the filesystem mtime
    cannot resolve, or an edit AFTER this read — is not closeable without an atomic
    snapshot-with-indexer; the coarse guard for it is the watermark ``repo_commit`` (a query
    against a different commit reads the whole store as stale). Documented, not silently
    swallowed.
    """
    out: dict[str, bytes] = {}
    mtimes: dict[str, float] = {}
    for d in index.get("documents", []):
        path = d.get("relative_path", "")
        if not _is_repo_path(path):
            continue
        full = os.path.join(repo_path, path)
        try:
            with open(full, "rb") as fh:
                out[path] = fh.read()
            mtimes[path] = os.stat(full).st_mtime
        except OSError:
            out.pop(path, None)
            continue
    if index_started is not None:
        for suspect in _modified_during_index(mtimes, index_started):
            out.pop(suspect, None)  # withhold freshness for TOCTOU-suspect files
    return out

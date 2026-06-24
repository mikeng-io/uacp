"""Codeflair tree-sitter ingest — the syntactic breadth floor (CF-D14).

Gives every language a baseline symbol+edge layer with NO external SCIP indexer:
parse with tree-sitter, capture definitions and calls, attribute each call to its
enclosing definition. Symbols are ``tree_sitter`` / ``syntactic`` and identified by a
SYNTHESIZED path-based id (NOT a stable SCIP descriptor) — the fuzzy floor that SCIP
precision overlays and outranks when present (the fuse prefers parsed > syntactic).

Optional dependency (``pip install 'codeflair[treesitter]'``): tree-sitter +
tree-sitter-languages. Import is lazy so the core stays dependency-free.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# This module REQUIRES the optional tree-sitter dep (codeflair[treesitter]); importing it
# without the dep fails fast. Callers that must degrade (scripts) guard the module import.
from tree_sitter_languages import get_language, get_parser

from codeflair.store import Edge, Store, Symbol


@dataclass(frozen=True)
class _LangSpec:
    # node-type -> field name holding the definition's identifier
    def_types: dict[str, str]
    # tree-sitter query capturing call-target identifiers as @ref
    call_query: str


_SPECS: dict[str, _LangSpec] = {
    "python": _LangSpec(
        def_types={"function_definition": "name", "class_definition": "name"},
        call_query="(call function: (identifier) @ref)"
        " (call function: (attribute attribute: (identifier) @ref))",
    ),
    "go": _LangSpec(
        def_types={
            "function_declaration": "name",
            "method_declaration": "name",
            "type_spec": "name",
        },
        call_query="(call_expression function: (identifier) @ref)"
        " (call_expression function: (selector_expression field: (field_identifier) @ref))",
    ),
    "typescript": _LangSpec(
        def_types={
            "function_declaration": "name",
            "method_definition": "name",
            "class_declaration": "name",
        },
        call_query="(call_expression function: (identifier) @ref)"
        " (call_expression function: (member_expression property: (property_identifier) @ref))",
    ),
}

# file suffix -> tree-sitter language name
SUFFIX_LANG = {
    ".py": "python",
    ".go": "go",
    ".ts": "typescript",
    ".tsx": "typescript",
}


@dataclass(frozen=True)
class IngestStats:
    files: int
    symbols: int
    edges: int


def synth_symbol(lang: str, relpath: str, name: str, line: int) -> str:
    """A synthesized, path-based identity for a syntactic symbol. Deliberately NOT a SCIP
    descriptor — it is location-dependent (the floor); SCIP supplies stable identity."""
    return f"tree-sitter {lang} {relpath}:{name}#{line}"


def ingest_tree_sitter(store: Store, files: dict[str, tuple[str, bytes]]) -> IngestStats:
    """Ingest ``{relpath: (lang, source_bytes)}`` via tree-sitter. Adds a symbol per
    definition and a ``calls`` edge (source=tree_sitter, provenance=syntactic) from each
    call's enclosing definition to every same-named definition in the corpus (the
    syntactic over-approximation — SCIP refines it)."""
    name_index: dict[str, list[str]] = {}  # ref name -> candidate callee symbols
    # per file: (defnode_id -> symbol), and the parsed call refs to resolve in pass 2
    pending: list[tuple[str, str, object, dict[int, str], list[tuple[str, object]]]] = []
    n_symbols = 0

    for relpath, (lang, source) in files.items():
        spec = _SPECS.get(lang)
        if spec is None:
            continue
        parser = get_parser(lang)
        root = parser.parse(source).root_node

        # defs: walk the tree, record every definition node + its name
        defnode_to_sym: dict[int, str] = {}
        stack = [root]
        while stack:
            node = stack.pop()
            field = spec.def_types.get(node.type)
            if field is not None:
                nm = node.child_by_field_name(field)
                if nm is not None:
                    name = nm.text.decode("utf-8", "ignore")
                    sym = synth_symbol(lang, relpath, name, nm.start_point[0])
                    store.add_symbol(
                        Symbol(
                            symbol=sym,
                            lang=lang,
                            file=relpath,
                            name=name,
                            kind=node.type,
                            line=nm.start_point[0],
                        )
                    )
                    n_symbols += 1
                    defnode_to_sym[node.id] = sym
                    name_index.setdefault(name, []).append(sym)
            stack.extend(node.children)

        # refs: capture call targets for resolution in pass 2 (after all names are known)
        refs = [
            (node.text.decode("utf-8", "ignore"), node)
            for node, cap in get_language(lang).query(spec.call_query).captures(root)
            if cap == "ref"
        ]
        pending.append((relpath, lang, root, defnode_to_sym, refs))

    # pass 2: attribute each ref to its enclosing definition, link to same-named defs
    n_edges = 0
    seen: set[tuple[str, str]] = set()
    for _relpath, _lang, _root, defnode_to_sym, refs in pending:
        for ref_name, ref_node in refs:
            caller = _enclosing_def_symbol(ref_node, defnode_to_sym)
            if caller is None:
                continue
            for callee in name_index.get(ref_name, ()):
                if callee == caller:
                    continue
                key = (caller, callee)
                if key in seen:
                    continue
                seen.add(key)
                store.add_edge(
                    Edge(
                        src=caller,
                        dst=callee,
                        rel="calls",
                        source="tree_sitter",
                        provenance="syntactic",
                    )
                )
                n_edges += 1

    store.commit()
    return IngestStats(files=len(pending), symbols=n_symbols, edges=n_edges)


def _enclosing_def_symbol(node: object, defnode_to_sym: dict[int, str]) -> str | None:
    """Walk parents from a reference up to the nearest definition node we recorded."""
    cur = getattr(node, "parent", None)
    while cur is not None:
        sym = defnode_to_sym.get(cur.id)
        if sym is not None:
            return sym
        cur = cur.parent
    return None


def index_repo_tree_sitter(
    store: Store,
    repo_path: str,
    *,
    suffix_lang: dict[str, str] | None = None,
    max_bytes: int = 1_000_000,
) -> IngestStats:
    """Walk ``repo_path`` (read-only), parse supported source files, ingest the floor."""
    suffix_lang = suffix_lang or SUFFIX_LANG
    skip = {"node_modules", "vendor", "worktrees", "dist", "build"}
    files: dict[str, tuple[str, bytes]] = {}
    for base, dirs, names in os.walk(repo_path):
        # skip hidden dirs (.git/.venv/.trustless/…) + known build/copy dirs
        dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]
        for name in names:
            _, ext = os.path.splitext(name)
            lang = suffix_lang.get(ext)
            if lang is None:
                continue
            full = os.path.join(base, name)
            try:
                if os.path.getsize(full) > max_bytes:
                    continue
                with open(full, "rb") as fh:
                    files[os.path.relpath(full, repo_path)] = (lang, fh.read())
            except OSError:
                continue
    return ingest_tree_sitter(store, files)

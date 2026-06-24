#!/usr/bin/env python3
"""Codeflair smoke test — run the deterministic stack on a real repo, end to end.

    python3 scripts/smoke.py <repo_path> [seed_substring] [--lang go|python|typescript]

Ingests the probes that apply (SCIP for the language if its indexer is available, else the
tree-sitter floor; always co-change + grep), prints store stats + timing, then runs the
expansion loop on a real seed. Reads the target READ-ONLY; the SCIP index goes to a temp
dir OUTSIDE the target.
"""

from __future__ import annotations

import sys
import time

from codeflair import Store, expand
from codeflair.cochange import index_repo_cochange
from codeflair.grep_probe import index_repo_strings
from codeflair.scip_ingest import index_repo

_SUFFIX = {"go": (".go",), "python": (".py",), "typescript": (".ts", ".tsx")}
_LANG_NORM = {
    "go": "go",
    "py": "python",
    "python": "python",
    "ts": "typescript",
    "typescript": "typescript",
}


def _timed(label, fn):
    t0 = time.time()
    out = fn()
    dt = (time.time() - t0) * 1000
    print(f"  {label:<28} {dt:8.1f} ms")
    return out


def _ingest_symbols(store: Store, repo: str, lang: str) -> None:
    """SCIP for the language if its indexer works, else the tree-sitter floor."""
    try:
        _timed("scip (precise)", lambda: index_repo(store, repo, lang))
    except Exception as exc:
        print(f"  SCIP failed ({type(exc).__name__}); falling back to tree-sitter floor")
    if store.count_symbols() == 0:
        from codeflair.treesitter_ingest import index_repo_tree_sitter  # optional dep

        ext = {"go": ".go", "python": ".py", "typescript": ".ts"}[lang]
        _timed(
            "tree-sitter (floor)",
            lambda: index_repo_tree_sitter(store, repo, suffix_lang={ext: lang}),
        )


def main() -> None:
    argv = sys.argv[1:]
    lang = "go"
    if "--lang" in argv:
        i = argv.index("--lang")
        lang = argv[i + 1]
        del argv[i : i + 2]
    lang = _LANG_NORM.get(lang, lang)
    args = [a for a in argv if not a.startswith("--")]
    repo = args[0]
    seed_sub = args[1] if len(args) > 1 else None

    print(f"\n=== Codeflair smoke: {repo} (lang={lang}) ===")
    store = Store()
    print("INGEST")
    _ingest_symbols(store, repo, lang)
    _timed("co-change (git)", lambda: index_repo_cochange(store, repo, path_suffixes=_SUFFIX[lang]))
    _timed("grep (shared strings)", lambda: index_repo_strings(store, repo))

    print("\nSTORE")
    print(f"  symbols              {store.count_symbols():,}")
    for src in ("scip", "lsp", "tree_sitter", "grep", "co_change"):
        c = store.count_edges(source=src)
        if c:
            print(f"  edges[{src}]          {c:,}")
    for kind, c in store.con.execute(
        "SELECT kind, COUNT(*) FROM coupling GROUP BY kind"
    ).fetchall():
        print(f"  coupling[{kind}]   {c:,}")

    if seed_sub:
        row = store.con.execute(
            "SELECT symbol FROM symbols WHERE symbol LIKE ? LIMIT 1", (f"%{seed_sub}%",)
        ).fetchone()
    else:
        row = store.con.execute(
            "SELECT e.dst, COUNT(*) c FROM edges e JOIN symbols s ON s.symbol = e.dst "
            "WHERE s.file != '' AND s.file NOT LIKE '../%' "
            "GROUP BY e.dst ORDER BY c DESC LIMIT 1"
        ).fetchone()
    if not row:
        print("\n(no symbol to seed a query — precise layer empty)")
        return

    seed = row[0]
    print(f"\nQUERY  seed = {seed}")
    res = _timed("expand()", lambda: expand(store, seed, k=12))
    print(f"  precise={res.n_precise}  inferred={res.n_inferred}  gaps={len(res.gaps)}")
    print("  top heatmap:")
    for e in res.heatmap[:8]:
        name = e.symbol.split(" ")[-1].split("/")[-1] or e.symbol
        print(f"    {e.score:6.3f}  hop{e.hop}  {name:<32} via {e.via}")
    if res.gaps:
        print("  gaps (untested impacted symbols):")
        for g in res.gaps[:5]:
            print(f"    {g.symbol.split('/')[-1]:<32} {g.file}")


if __name__ == "__main__":
    main()

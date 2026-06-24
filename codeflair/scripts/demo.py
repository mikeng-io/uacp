#!/usr/bin/env python3
"""Codeflair impact report — the design's user journey, on a real repo.

    python3 scripts/demo.py <repo> --lang go|python|typescript [seed_substring]

Answers the question the design opens with: "I'm about to change symbol X — what's the
blast radius, what historically changes with it, what cross-language code is coupled, and
where are the test gaps?" Prints a formatted report. Read-only; SCIP index -> temp dir.

Requires `codeflair` importable (editable-installed in the dev venv) and, for the SCIP
layer, the repo-local indexers (scripts/bootstrap.py). Without SCIP it falls back to the
tree-sitter floor.
"""

from __future__ import annotations

import os
import sys

from codeflair import Store, expand
from codeflair.cochange import index_repo_cochange
from codeflair.grep_probe import index_repo_strings
from codeflair.scip_ingest import index_repo

W = 78
_SUFFIX = {"go": (".go",), "python": (".py",), "typescript": (".ts", ".tsx")}
_LANG_NORM = {
    "go": "go",
    "py": "python",
    "python": "python",
    "ts": "typescript",
    "typescript": "typescript",
}


def rule(ch: str = "─") -> str:
    return ch * W


def short(sym: str) -> str:
    """Human-readable tail of a symbol id (SCIP descriptor or synthesized ts id)."""
    tail = sym.split(" ")[-1]
    tail = tail.split("`")[-1].lstrip("/")
    return tail or sym


def build(repo: str, lang: str) -> Store:
    store = Store()
    try:
        index_repo(store, repo, lang)
    except Exception as exc:  # SCIP indexer missing/failed -> degrade to the floor
        print(f"  SCIP indexing failed ({type(exc).__name__}); using tree-sitter floor")
    if store.count_symbols() == 0:
        from codeflair.treesitter_ingest import index_repo_tree_sitter  # optional dep

        ext = {"go": ".go", "python": ".py", "typescript": ".ts"}[lang]
        index_repo_tree_sitter(store, repo, suffix_lang={ext: lang})
    index_repo_cochange(store, repo, path_suffixes=_SUFFIX[lang])
    index_repo_strings(store, repo)
    return store


def pick_seed(store: Store, sub: str | None) -> str | None:
    if sub:
        row = store.con.execute(
            "SELECT symbol FROM symbols WHERE symbol LIKE ? AND file!='' "
            "ORDER BY length(symbol) LIMIT 1",
            (f"%{sub}%",),
        ).fetchone()
        return row[0] if row else None
    # auto: the function/method with the most distinct callers, defined in a real
    # non-test file (a meaningful, recognizable change target)
    row = store.con.execute(
        "SELECT e.dst, COUNT(DISTINCT e.src) c FROM edges e "
        "JOIN symbols s ON s.symbol=e.dst "
        "WHERE s.file!='' AND s.file NOT LIKE '%test%' "
        "AND (s.name LIKE '%(%' OR s.kind LIKE '%func%' "
        "  OR s.kind LIKE '%method%' OR s.kind='function_definition') "
        "GROUP BY e.dst ORDER BY c DESC LIMIT 1"
    ).fetchone()
    return row[0] if row else None


def report(repo: str, lang: str, sub: str | None) -> None:
    store = build(repo, lang)
    seed = pick_seed(store, sub)
    if not seed:
        print("no seed symbol found")
        return
    srow = store.symbol(seed)
    res = expand(store, seed, k=10, max_hops=3)

    print("\n" + rule("═"))
    print("  CODEFLAIR · impact report")
    print(f"  repo   {os.path.basename(repo.rstrip('/'))}  ({lang})")
    print(f"  change {short(seed)}")
    print(f"         {srow.file}:{srow.line}")
    print(rule("═"))

    print(
        f"\n▌ BLAST RADIUS — who is affected if this changes  "
        f"({res.n_precise} precise + {res.n_inferred} inferred)"
    )
    print(f"  {'#':>2}  {'score':>5}  {'hop':>3}  {'evidence':<20}  symbol")
    for i, e in enumerate(res.heatmap, 1):
        print(f"  {i:>2}  {e.score:>5.2f}  {e.hop:>3}  {e.via:<20}  {short(e.symbol)}")

    print(f"\n▌ TEST GAPS — impacted symbols no test references  ({len(res.gaps)})")
    for g in res.gaps[:6]:
        print(f"  ⚠  {short(g.symbol):<34}  {g.file}")
    if not res.gaps:
        print("  (none — impacted symbols are test-referenced)")

    cc = store.coupled_files(srow.file, kind="co_change", min_weight=2)
    print(f"\n▌ CO-CHANGES WITH — files that historically move together  ({len(cc)})")
    for other, _kind, w in cc[:6]:
        print(f"  ×{w:<3} {other}")
    if not cc:
        print("  (no strong temporal coupling)")

    ss = store.coupled_files(srow.file, kind="shared_string")
    print(f"\n▌ CROSS-LANGUAGE COUPLING — shared route/event strings  ({len(ss)})")
    for other, _kind, w in ss[:6]:
        print(f"  ↔{w:<3} {other}")
    if not ss:
        print("  (no shared distinctive strings)")
    print(rule("═"))


def main() -> None:
    argv = sys.argv[1:]
    lang = "go"
    if "--lang" in argv:
        i = argv.index("--lang")
        lang = argv[i + 1]
        del argv[i : i + 2]  # consume the flag AND its value
    args = [a for a in argv if not a.startswith("--")]
    repo = args[0]
    sub = args[1] if len(args) > 1 else None
    report(repo, _LANG_NORM.get(lang, lang), sub)


if __name__ == "__main__":
    main()

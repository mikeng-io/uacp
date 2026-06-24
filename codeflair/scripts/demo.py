#!/usr/bin/env python3
"""Codeflair impact report — the design's user journey, on a real repo.

    python3 scripts/demo.py <repo> --lang go|py [seed_substring]

Answers the question the design opens with: "I'm about to change symbol X — what's the
blast radius, what historically changes with it, what cross-language code is coupled, and
where are the test gaps?" Prints a formatted report. Read-only; SCIP index -> temp dir.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codeflair import Store, expand                       # noqa: E402
from codeflair.cochange import index_repo_cochange        # noqa: E402
from codeflair.grep_probe import index_repo_strings       # noqa: E402

W = 78


def rule(ch="─"):
    return ch * W


def short(sym: str) -> str:
    """Human-readable tail of a symbol id (SCIP descriptor or synthesized ts id)."""
    tail = sym.split(" ")[-1]
    tail = tail.split("`")[-1].lstrip("/")
    return tail or sym


def build(repo: str, lang: str) -> Store:
    store = Store()
    if lang == "go":
        import json
        import shutil
        import subprocess
        import tempfile

        from codeflair.scip_ingest import ingest_scip_json
        tmp = tempfile.mkdtemp(prefix="cf-demo-")
        try:
            idx = os.path.join(tmp, "i.scip")
            subprocess.run(["scip-go", "--output", idx], cwd=repo, check=True, capture_output=True)
            data = json.loads(subprocess.run(["scip", "print", "--json", idx],
                                             check=True, capture_output=True).stdout)
            ingest_scip_json(store, data)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    else:
        from codeflair.treesitter_ingest import index_repo_tree_sitter
        index_repo_tree_sitter(store, repo, suffix_lang={".py": "python"})
    index_repo_cochange(store, repo, path_suffixes=((".go",) if lang == "go" else (".py",)))
    index_repo_strings(store, repo)
    return store


def pick_seed(store: Store, sub: str | None) -> str | None:
    if sub:
        row = store.con.execute(
            "SELECT symbol FROM symbols WHERE symbol LIKE ? AND file!='' ORDER BY length(symbol) LIMIT 1",
            (f"%{sub}%",)).fetchone()
        return row[0] if row else None
    # auto: the function/method with the most distinct callers, defined in a real
    # non-test file (a meaningful, recognizable change target)
    row = store.con.execute(
        "SELECT e.dst, COUNT(DISTINCT e.src) c FROM edges e JOIN symbols s ON s.symbol=e.dst "
        "WHERE s.file!='' AND s.file NOT LIKE '%test%' AND (s.name LIKE '%(%' OR s.kind LIKE '%func%' "
        "  OR s.kind LIKE '%method%' OR s.kind='function_definition') "
        "GROUP BY e.dst ORDER BY c DESC LIMIT 1").fetchone()
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

    print(f"\n▌ BLAST RADIUS — who is affected if this changes  "
          f"({res.n_precise} precise + {res.n_inferred} inferred)")
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
    for other, _k, w in cc[:6]:
        print(f"  ×{w:<3} {other}")
    if not cc:
        print("  (no strong temporal coupling)")

    ss = store.coupled_files(srow.file, kind="shared_string")
    print(f"\n▌ CROSS-LANGUAGE COUPLING — shared route/event strings  ({len(ss)})")
    for other, _k, w in ss[:6]:
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
        del argv[i:i + 2]                      # consume the flag AND its value
    args = [a for a in argv if not a.startswith("--")]
    repo = args[0]
    sub = args[1] if len(args) > 1 else None
    report(repo, "go" if lang in ("go",) else "py", sub)


if __name__ == "__main__":
    main()

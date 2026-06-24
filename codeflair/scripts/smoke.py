#!/usr/bin/env python3
"""Codeflair smoke test — run the deterministic stack on a real repo, end to end.

    python3 scripts/smoke.py <repo_path> [seed_substring] [--lang go]

Ingests whatever probes apply (SCIP if scip-go+scip present and lang=go; always
co-change + grep), prints store stats + timing, then runs the expansion loop on a real
seed and prints the heatmap + gaps. Reads the target repo READ-ONLY; the SCIP index is
written to a temp dir OUTSIDE the target (never mutates it).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codeflair import Store, expand  # noqa: E402
from codeflair.cochange import index_repo_cochange  # noqa: E402
from codeflair.grep_probe import index_repo_strings  # noqa: E402
from codeflair.scip_ingest import ingest_scip_json  # noqa: E402


def _timed(label, fn):
    t0 = time.time()
    out = fn()
    dt = (time.time() - t0) * 1000
    print(f"  {label:<28} {dt:8.1f} ms")
    return out


def _ts_floor(store: Store, repo: str, lang: str) -> None:
    """Add the tree-sitter syntactic floor for the target language, if the optional dep
    is installed. This is what gives a non-Go repo (e.g. Python UACP) a symbol layer."""
    norm = {
        "py": "python",
        "python": "python",
        "go": "go",
        "ts": "typescript",
        "typescript": "typescript",
    }.get(lang)
    ext = {"python": ".py", "go": ".go", "typescript": ".ts"}.get(norm or "")
    if not ext:
        return
    try:
        from codeflair.treesitter_ingest import index_repo_tree_sitter
    except ImportError:
        print("  (tree-sitter not installed — skipping the syntactic floor)")
        return
    _timed(
        "tree-sitter (floor)", lambda: index_repo_tree_sitter(store, repo, suffix_lang={ext: norm})
    )


def ingest_scip_go(store: Store, repo: str) -> int:
    if not (shutil.which("scip-go") and shutil.which("scip")):
        print("  (scip-go/scip not on PATH — skipping precise SCIP layer)")
        return 0
    tmp = tempfile.mkdtemp(prefix="cf-smoke-")
    idx = os.path.join(tmp, "index.scip")  # OUTSIDE the target repo
    try:
        subprocess.run(["scip-go", "--output", idx], cwd=repo, check=True, capture_output=True)
        printed = subprocess.run(["scip", "print", "--json", idx], check=True, capture_output=True)
        data = json.loads(printed.stdout)
        return ingest_scip_json(store, data).edges
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    repo = args[0]
    seed_sub = args[1] if len(args) > 1 else None
    lang = "go" if "--lang" not in sys.argv else sys.argv[sys.argv.index("--lang") + 1]
    suffix = {".go": (".go",)}.get("." + lang, None)

    print(f"\n=== Codeflair smoke: {repo} (lang={lang}) ===")
    store = Store()
    print("INGEST")
    if lang == "go":
        _timed("scip (precise)", lambda: ingest_scip_go(store, repo))
    _ts_floor(store, repo, lang)
    _timed("co-change (git)", lambda: index_repo_cochange(store, repo, path_suffixes=suffix))
    _timed("grep (shared strings)", lambda: index_repo_strings(store, repo))

    n_sym = store.count_symbols()
    print("\nSTORE")
    print(f"  symbols              {n_sym:,}")
    for src in ("scip", "lsp", "tree_sitter", "grep", "co_change"):
        c = store.count_edges(source=src)
        if c:
            print(f"  edges[{src}]          {c:,}")
    cpl = store.con.execute("SELECT kind, COUNT(*) FROM coupling GROUP BY kind").fetchall()
    for kind, c in cpl:
        print(f"  coupling[{kind}]   {c:,}")

    # pick a seed: the most-referenced symbol (highest in-degree), or one matching the arg
    if seed_sub:
        row = store.con.execute(
            "SELECT symbol FROM symbols WHERE symbol LIKE ? LIMIT 1", (f"%{seed_sub}%",)
        ).fetchone()
    else:
        # most-referenced symbol that is actually DEFINED in this repo (has a real file) —
        # not a stdlib/dep symbol that merely appears as an edge target.
        row = store.con.execute(
            "SELECT e.dst, COUNT(*) c FROM edges e "
            "JOIN symbols s ON s.symbol = e.dst "
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

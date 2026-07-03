"""Codeflair CLI — the command-line delivery face (P7, 12-delivery: "one core, four faces").

Thin wrappers over the existing engine — no reimplementation:

  - ``codeflair index <repo>``  builds the per-worktree index (SCIP precise edges -> the
    tree-sitter breadth floor -> co-change + shared-string couplings), sets the watermark,
    and prints an index summary.
  - ``codeflair query <seed>``  opens the index **read-only**, runs the expansion loop, and
    emits the canonical ``{nodes, gaps, trace}`` JSON contract (04-outputs).
  - ``codeflair witness --repo <root> [--code-ref file:name ...]``  reindexes the working
    tree and emits scope-conformance **facts** for the kernel gate to grade (see witness.py).
  - ``codeflair mcp``  boots the MCP server (face #3); gated on the optional ``mcp`` dep.

Determinism (CF-D11 / 10-freshness): ``query`` is read-only and byte-stable (``to_json``);
nothing reads the wall clock — the watermark's ``built_at`` is the injected repo commit.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from codeflair.cochange import index_repo_cochange
from codeflair.expand import expand
from codeflair.grep_probe import index_repo_strings
from codeflair.scip_ingest import index_repo
from codeflair.store import Store, default_store_path
from codeflair.trace import to_json
from codeflair.witness import build_baseline_witness, build_witness, parse_code_ref

try:  # the tree-sitter floor is optional (codeflair[treesitter]); degrade if absent
    from codeflair.treesitter_ingest import index_repo_tree_sitter
except ImportError:  # pragma: no cover - dep-presence branch
    index_repo_tree_sitter = None

# Per-language file suffixes (mirrors scripts/demo.py) for the co-change path-filter + the
# tree-sitter floor extension.
_SUFFIX: dict[str, tuple[str, ...]] = {
    "go": (".go",),
    "python": (".py",),
    "typescript": (".ts", ".tsx"),
}
_TS_EXT = {"go": ".go", "python": ".py", "typescript": ".ts"}


def _git_head(repo: str) -> str:
    """The repo's ``HEAD`` commit (read-only), or ``""`` if ``repo`` is not a git checkout.
    The watermark keys on commit, not a wall-clock timestamp (determinism discipline)."""
    try:
        out = subprocess.run(
            ["git", "-C", repo, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def build_index(
    repo: str, *, lang: str = "python", built_at: str | None = None
) -> dict[str, object]:
    """Build (or rebuild) the per-worktree index under ``repo`` and return a summary.

    The same ingest ladder the demo uses: SCIP (precise, degrades if the indexer is absent)
    -> the tree-sitter breadth floor (if SCIP found nothing and the optional dep is present)
    -> co-change (git) + shared-string (pure text) couplings.

    F4 — the watermark is the store's "I authoritatively index HEAD" claim, so it is advanced
    ONLY when the run actually produced index content. A SCIP step that RAISES is rolled back
    (no half-ingested rows persist) and surfaced under ``errors``; if NOTHING was indexed by
    any source the watermark is NOT advanced and ``indexed`` is False (the CLI exits nonzero),
    so a later delta never mistakes a failed/empty build for a current snapshot of HEAD."""
    path = default_store_path(repo, create=True)
    errors: list[str] = []
    with Store(path) as store:
        try:
            index_repo(store, repo, lang)
        except Exception as exc:  # noqa: BLE001 - SCIP indexer missing/failed
            # Discard any partial, uncommitted SCIP writes so no half-index persists (F4).
            store.con.rollback()
            errors.append(f"scip: {type(exc).__name__}: {exc}")
        if store.count_symbols() == 0 and index_repo_tree_sitter is not None:
            ext = _TS_EXT.get(lang, ".py")
            index_repo_tree_sitter(store, repo, suffix_lang={ext: lang})
        try:
            index_repo_cochange(store, repo, path_suffixes=_SUFFIX.get(lang))
        except Exception as exc:  # noqa: BLE001 - not a git repo / git absent -> no co-change
            errors.append(f"cochange: {type(exc).__name__}: {exc}")
        try:
            index_repo_strings(store, repo)
        except Exception as exc:  # noqa: BLE001 - unreadable tree -> no shared-string signal
            errors.append(f"strings: {type(exc).__name__}: {exc}")
        n_couplings = store.con.execute("SELECT COUNT(*) FROM coupling").fetchone()[0]
        produced = store.count_symbols() + store.count_edges() + n_couplings
        indexed = produced > 0
        repo_commit = _git_head(repo)
        if indexed:
            # advance the watermark ONLY for a non-empty build (F4)
            store.set_watermark(repo_commit, repo_commit if built_at is None else built_at)
        store.commit()
        summary: dict[str, object] = {
            "indexed": indexed,
            "store": path,
            "repo_commit": repo_commit if indexed else "",
            "symbols": store.count_symbols(),
            "edges": store.count_edges(),
        }
        if errors:
            summary["errors"] = errors
        return summary


def _resolve_seed(store: Store, seed: str) -> str | None:
    """Map a CLI seed to a stored symbol: exact id first, else the shortest symbol whose id
    contains ``seed`` (a human substring), preferring real (non-external) files."""
    if store.symbol(seed) is not None:
        return seed
    row = store.con.execute(
        "SELECT symbol FROM symbols WHERE symbol LIKE ? AND file != '' "
        "ORDER BY length(symbol), symbol LIMIT 1",
        (f"%{seed}%",),
    ).fetchone()
    return row[0] if row else None


def query_to_json(
    repo: str,
    seed: str,
    *,
    k: int = 20,
    max_hops: int = 3,
    direction: str = "callers",
    indent: int | None = None,
) -> str:
    """Open the index under ``repo`` **read-only**, run the expansion loop from ``seed``, and
    return the canonical ``{nodes, gaps, trace}`` document. Read-only (CF-D9): a UACP consumer
    can call this against an index it must not mutate. Byte-stable for a fixed store+seed."""
    path = default_store_path(repo)
    store = Store(path, read_only=True)
    try:
        resolved = _resolve_seed(store, seed)
        if resolved is None:
            return json.dumps(
                {"error": "seed not found", "seed": seed}, sort_keys=True, indent=indent
            )
        result = expand(
            store, resolved, k=k, max_hops=max_hops, direction=direction, capture_trace=True
        )
        return to_json(
            result,
            watermark=store.watermark(),
            query={"seed": resolved, "k": k, "max_hops": max_hops, "direction": direction},
            indent=indent,
        )
    finally:
        store.close()


def _cmd_index(args: argparse.Namespace) -> int:
    summary = build_index(args.repo, lang=args.lang, built_at=args.built_at)
    print(json.dumps(summary, sort_keys=True, indent=args.indent))
    # F4: surface a failed/empty build (no watermark advanced) as a nonzero exit.
    return 0 if summary["indexed"] else 1


def _cmd_query(args: argparse.Namespace) -> int:
    print(
        query_to_json(
            args.repo,
            args.seed,
            k=args.k,
            max_hops=args.max_hops,
            direction=args.direction,
            indent=args.indent,
        )
    )
    return 0


def _cmd_witness(args: argparse.Namespace) -> int:
    # The witness derives FACTS ONLY — no coverage/undeclared/over-declared verdicts (the gate
    # compares). Two modes: the default reindexes the CURRENT working tree (diff-grounded, 02);
    # --baseline-refs derives the hop-1 forecast on the committed baseline HEAD (diff-independent,
    # #86). build_index is injected as the reindex in both.
    refs = [parse_code_ref(r) for r in (args.code_ref or [])]
    if args.baseline_refs:
        result = build_baseline_witness(args.repo, build_index, code_refs=refs, lang=args.lang)
    else:
        result = build_witness(args.repo, build_index, code_refs=refs, lang=args.lang)
    print(json.dumps(result, sort_keys=True, indent=args.indent))
    # exit nonzero with {"error": ...} on failure (not a git repo / no HEAD / index empty)
    return 0 if "error" not in result else 1


def _cmd_mcp(args: argparse.Namespace) -> int:
    # Lazy (cli <-> mcp_server import cycle break + the mcp dep is optional): deliberate
    # exception to the imports-at-top rule for this optional-dependency face.
    from codeflair.mcp_server import build_server  # noqa: PLC0415

    try:
        build_server().run()
    except RuntimeError as exc:  # mcp not installed
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codeflair", description="Codeflair code-intelligence CLI."
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=None,
        help="pretty-print JSON with this indent (default: compact)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="build the per-worktree index for a repo")
    p_index.add_argument("repo", help="repo root to index")
    p_index.add_argument(
        "--lang", default="python", choices=sorted(_TS_EXT), help="primary language"
    )
    p_index.add_argument("--built-at", default=None, help="injected build id (default: repo HEAD)")
    p_index.set_defaults(func=_cmd_index)

    p_query = sub.add_parser("query", help="query the index for a seed's blast-radius heatmap")
    p_query.add_argument("seed", help="seed symbol id or human substring")
    p_query.add_argument("--repo", default=".", help="repo root whose index to query (default: .)")
    p_query.add_argument("--k", type=int, default=20, help="top-k heatmap size")
    p_query.add_argument("--max-hops", type=int, default=3, help="max graph distance from the seed")
    p_query.add_argument(
        "--direction", default="callers", choices=("callers", "callees"), help="walk direction"
    )
    p_query.set_defaults(func=_cmd_query)

    p_witness = sub.add_parser(
        "witness", help="reindex the working tree and report scope-conformance FACTS as JSON"
    )
    p_witness.add_argument("--repo", default=".", help="repo root to witness (default: .)")
    p_witness.add_argument(
        "--lang", default="python", choices=sorted(_TS_EXT), help="primary language"
    )
    p_witness.add_argument(
        "--code-ref",
        action="append",
        metavar="FILE:NAME",
        help="a declared code ref (repeatable); NAME may contain dots (split on first colon)",
    )
    p_witness.add_argument(
        "--baseline-refs",
        action="store_true",
        help="diff-independent forecast mode (#86): derive the hop-1 neighborhood of the "
        "--code-refs on the committed baseline (HEAD), not the dirty working tree",
    )
    p_witness.set_defaults(func=_cmd_witness)

    p_mcp = sub.add_parser("mcp", help="run the codeflair MCP server (stdio)")
    p_mcp.set_defaults(func=_cmd_mcp)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint (console_scripts ``codeflair`` and ``python -m codeflair``)."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

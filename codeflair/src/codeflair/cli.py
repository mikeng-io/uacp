"""Codeflair CLI — the command-line delivery face (P7, 12-delivery: "one core, four faces").

Thin wrappers over the existing engine — no reimplementation:

  - ``codeflair index <repo>``  builds the per-worktree index (SCIP precise edges -> the
    tree-sitter breadth floor -> co-change + shared-string couplings), sets the watermark,
    and prints an index summary.
  - ``codeflair query <seed>``  opens the index **read-only**, runs the expansion loop, and
    emits the canonical ``{nodes, gaps, trace}`` JSON contract (04-outputs).
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
    -> co-change (git) + shared-string (pure text) couplings. The watermark is set from the
    repo HEAD; ``built_at`` defaults to that same commit so the trace is deterministic."""
    path = default_store_path(repo, create=True)
    with Store(path) as store:
        try:
            index_repo(store, repo, lang)
        except Exception:  # noqa: BLE001 - SCIP indexer missing/failed -> degrade to the floor
            pass
        if store.count_symbols() == 0 and index_repo_tree_sitter is not None:
            ext = _TS_EXT.get(lang, ".py")
            index_repo_tree_sitter(store, repo, suffix_lang={ext: lang})
        try:
            index_repo_cochange(store, repo, path_suffixes=_SUFFIX.get(lang))
        except Exception:  # noqa: BLE001 - not a git repo / git absent -> no co-change signal
            pass
        try:
            index_repo_strings(store, repo)
        except Exception:  # noqa: BLE001 - unreadable tree -> no shared-string signal
            pass
        repo_commit = _git_head(repo)
        store.set_watermark(repo_commit, repo_commit if built_at is None else built_at)
        store.commit()
        return {
            "indexed": True,
            "store": path,
            "repo_commit": repo_commit,
            "symbols": store.count_symbols(),
            "edges": store.count_edges(),
        }


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
    return 0


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

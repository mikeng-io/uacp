# Codeflair — spike (proof artifacts)

Throwaway spike that proved the **deterministic** Codeflair thesis (CF-D11) on a real
codebase before any build. Moved into the UACP repo from a scratch `~/Workplace/codeflair/`
dir (2026-06-25) — Codeflair is built **in-UACP** as an abstracted package + adapter
(CF-D12), not a separate repo. Design lives at [`design/codeflair/`](../../design/codeflair/).

## What the scripts prove

| Script | Proves |
|---|---|
| `ingest.py` | SCIP index → SQLite (`occ`, `edges`); 1-hop refs + N-hop blast radius via a **recursive CTE**. The core query model — no graph DB, no LLM. |
| `fuse.py` | Multi-language SCIP indexes (Go + TS) **fuse into one SQLite**, namespaced by scheme — no collision; within-language edges precise; **zero cross-language symbol edges** (the grep/co-change boundary, CF-D13). |

## Measured result (Trustless, 543k LOC Go, 2026-06-24)

- `scip-go` index: **4.1s** · ingest → SQLite: **0.3s** · blast-radius query: **0.1–0.2 ms**, correct (`Pool#Conn`)
- ~200,000× under the retired QMD 42s/query bar — **zero LLM**.
- Symbol identity = the SCIP descriptor (e.g. `` scip-go gomod github.com/jackc/pgx/v5 v5.10.0 `…/pgxpool`/Pool#Conn(). ``):
  location-independent, version-pinned, move-stable — the stable anchor `code_anchor` needs.

## Adopt-eval addendum (C-spike, 2026-06-25)

Tested "adopt a fuller tool, build only the adapter" against `codebase-memory-mcp` → **rejected**:
it is tree-sitter + a C "Hybrid LSP" (no SCIP, fuzzy base), and its only durable symbol key
(`qualified_name`) **embeds the absolute checkout path** + globally renumbers its row `id` on
any reindex — nothing trustworthy for `code_anchor` to anchor onto. Confirms **build the
fuse + adapter over SCIP** (CF-D14 / Option B). (Tool fully uninstalled after the test.)

## Rebuilding the artifacts (not committed — derivable in seconds)

The `.db`, `.scip`, the `scip` binary and `scip.tar.gz` are **rebuildable** and git-ignored:

```sh
# 1. get the scip CLI (https://github.com/sourcegraph/scip) → ./scip
# 2. index a Go repo:   scip-go --output index.scip   (run inside the target repo)
# 3. ingest + query:    ./scip print --json index.scip | python3 ingest.py Pool
# 4. multi-lang fusion: python3 fuse.py index.scip index_ts.scip
```

Use a checkout READ-ONLY as the index target — never mutate the indexed repo.

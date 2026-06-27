@AGENTS.md

---

## Claude Code — Runtime-Specific

**Preferred dispatch: Task tool** — spawn parallel sub-agents (one per domain + Devil's Advocate + Integration Checker). Always available as fallback.

**Agent Teams** (complex multi-domain work — 3+ domains, thorough intensity):
Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in environment.
Guard: attempt `TeamCreate` first — fall back to Task tool immediately if it fails. Never retry.

**Workflows** (tier ≥3, research/audit, or `ultracode` keyword):
- `/deep-research` — deep multi-step research with recursive subagent dispatch
- `ultracode: <task>` — large-scale coding orchestration (up to 16 concurrent agents, 1,000 total)
- Custom JS: `.claude/workflows/`
Guard: always fall back to Agent Teams or Task tool if workflows are unavailable.

**Worktree isolation:** For parallel file mutations across agents, use `isolation: "worktree"` on the Agent tool. Each agent gets a clean working copy; unchanged worktrees are auto-removed.

**Non-interactive (`claude -p`) mode:** Add `--dangerously-skip-permissions` for file writes — no user is present to approve tool calls.

### Code intelligence — unified lookup/edit flow (grep · LSP · SCIP)

> **HARD RULE (a recurring miss): for a symbol (function / class / variable / method), LEAD WITH the `LSP` tool — never grep ALONE.** It is a **hybrid**, not a replacement: LSP is precise (resolves imports, no string/comment false-positives); grep is the complement that catches what LSP misses (strings, comments, dynamic/reflective refs, cross-language, stale-index gaps). Use BOTH for symbol work and **reconcile — the suite decides**. (Grep alone is fine for literal text / config keys / file discovery.)

Route by the **question**, not the language. The repo's LSP servers cover its languages; the flow is identical per language (and for SCIP later). Three tools, three jobs:

- **grep/Glob = TEXT.** String literals, config keys, patterns, "where does this appear", file discovery, cross-language sweeps. No index, never stale → the universal fallback.
- **LSP = LIVE SYMBOLS (this worktree).** Definition, references/callers, implementations, call hierarchy (in/out), types, rename-impact: `workspaceSymbol` / `documentSymbol` / `goToDefinition` / `findReferences` / `incomingCalls` / `goToImplementation`. Precise (resolves imports; never false-matches strings/comments); per-language server, **single-root**, **freshness-dependent**.
- **SCIP = PERSISTENT SYMBOLS (later).** A deterministic, dumpable per-commit index — immune to LSP's root/freshness limits; cross-checkout/offline; the substrate for UACP's code plane (prevention-at-PLAN).

**One procedure for LOOKUP and EDIT:**
1. **Locate** → a named symbol = LSP; literal text/config/pattern = grep.
2. **Understand** → callers / blast-radius / impls / call-hierarchy = LSP; "where is this string consumed" = grep.
3. **Edit** → BEFORE changing a shared symbol (signature/response/behavior), run LSP `findReferences` = **MANDATORY blast-radius audit** (never infer callers); then edit (TDD).
4. **Verify** → **tests are the final arbiter** — grep/LSP find *candidates*, tests *confirm*.

**Trust & freshness (language-agnostic):**
- LSP is **single-root** → keep the worktree UNDER the root (`$UACP_ROOT/.worktrees/`). After a **structural change** (worktree move, mass rename, many new files) **restart the LSP** before trusting `workspaceSymbol` / cross-file `findReferences`; file-scoped ops (`documentSymbol`, diagnostics, hover) tolerate staleness, workspace-wide ops don't.
- **LSP ⊕ grep disagree → reconcile, don't trust blindly:** LSP may be stale (e.g. thin/empty cross-file results after a structural change), grep may false-match in strings/comments. The test suite decides.
- No server for the language / `Executable not found` → grep, and say so. SCIP (later) removes the root/freshness anxiety entirely.

Full dispatch contract: `skills/uacp-bridge/references/claude.md`

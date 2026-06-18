---
type: plan
title: "Step 2 · Slice 2 — Bridge collapse (`bridge-*` → `uacp-bridge`)"
description: "Slice 2 plan to collapse six `bridge-*` skills into one `uacp-bridge` skill with per-runtime reference files"
tags: ["step2", "bridge", "collapse", "skills"]
timestamp: 2026-06-17
status: archived
---

# Step 2 · Slice 2 — Bridge collapse (`bridge-*` → `uacp-bridge`)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Collapse the six `bridge-*` skills into one `kind: reference` skill `uacp-bridge`: `SKILL.md` = the shared contract (today's `bridge-commons`, verbatim), `references/<runtime>.md` = each adapter's runtime-specific content (commons duplication stripped, `cli-reference.md` folded in), with every citer rewired so nothing breaks.

**Architecture:** Structure/relocation only — **no behavioral rewrites**. The shared contract body moves byte-for-byte (any summarization loses earned protocol). Each adapter file keeps only what is genuinely runtime-specific + load-bearing; everything it duplicated from commons is dropped (now inherited from `uacp-bridge/SKILL.md`). High blast radius: several read-pointers are runtime-breaking (hard-abort) — rewire them exactly.

**Tech Stack:** Markdown skills; `pytest` (`python3`), `ruff`, `claude plugin validate`. Baseline: 691 passed / 2 skipped.

**Spec source (authoritative):** `docs/plans/2026-06-16-step2-eval-maps.md` §A (bridge map) — the verbatim-migration plan, per-runtime keep-lists, the full **load-bearing master list**, and every rewiring action. This plan condenses it; consult the eval map (and the source files themselves) for the full preserve detail. Branch: `skills/step2-slice2-bridge-collapse`.

## Hard rules for this slice
- **`uacp-bridge/SKILL.md` body = `bridge-commons/SKILL.md` body byte-for-byte.** Only the frontmatter changes. Do NOT summarize or "tidy" the 785-line contract.
- **Path convention is `references/<runtime>.md`** (NOT `providers/`). The eval wiring strings sometimes say `providers/` — ignore that; ADR-0017 fixes `references/`.
- **Preserve per-bridge asymmetries** (deliberate, not bugs): Kimi HALTED-on-auth, OpenCode HALTED-on-no-provider, Codex HALT, vs Gemini SKIPPED; connection-preference orderings (OpenCode http-api@slot2, Codex mcp@slot2, Kimi acp@slot3); Claude's **extended** DA/IC prompts (do not reduce to commons generic); OpenCode tier-exception appears in BOTH the shared body and `opencode.md`.
- **Preserve 3 unresolved Kimi bugs as explicit open-question callouts** in `kimi.md` (do NOT silent-fix): `--output-format json` vs `stream-json`; `thinking` reasoning value with no CLI flag; `-C`/`-S` session vs commons-stateless treatment.
- **`references/<runtime>.md` are bundled reference docs, not skills** — strip the SKILL-style frontmatter (`name`/`location`/`context`/`dependencies`); put any "depends on debate-protocol" note in prose. They are not `SKILL.md`, so the readiness lint won't (and shouldn't) treat them as skills.
- After the collapse, `skills/bridge-*` dirs must be **gone**.

---

## Task 1: Scaffold `uacp-bridge` (shared contract + README)

**Files:** `skills/bridge-commons/SKILL.md` → `skills/uacp-bridge/SKILL.md`; `skills/bridge-commons/README.md` → `skills/uacp-bridge/README.md`

**Step 1:** `mkdir -p skills/uacp-bridge && git mv skills/bridge-commons/SKILL.md skills/uacp-bridge/SKILL.md`

**Step 2: Frontmatter only** — set the frontmatter to:
```yaml
---
name: uacp-bridge
description: Unified bridge dispatch contract — the shared pre-flight SOP, tier system, input/output schemas, timeout/verdict logic, and status semantics that all runtime adapters implement. Read via the Read tool; per-runtime specifics live in references/<runtime>.md.
kind: reference
location: managed
---
```
(name `bridge-commons`→`uacp-bridge`; rewrite the description; **add `kind: reference`**; **DROP `context: reference`** — reserved-key footgun per ADR-0017; keep `location: managed`.) **Leave the entire body unchanged.** Verify body is byte-identical: `git show HEAD:skills/bridge-commons/SKILL.md | tail -n +N` comparison, or `diff <(sed '1,/^---$/d; 1,/^---$/d' ...)` — simplest: confirm `git diff --stat` shows the move + only frontmatter lines changed.

**Step 3: README** — `git mv skills/bridge-commons/README.md skills/uacp-bridge/README.md`; update its ASCII hierarchy: `bridge-commons` → `uacp-bridge/SKILL.md (the contract)`; the per-adapter entries → `references/{claude,codex,gemini,kimi,opencode}.md`; add `kimi` if missing. (The 5 per-adapter READMEs are dropped in Task 2 — fold any unique line into the relevant `references/<runtime>.md` or this README.)

**Step 4:** `python3 -m pytest tests/unit/skills/ -q` → green (uacp-bridge/SKILL.md cites no ADR; it's in a named subdir; has a description). `grep -n "bridge-commons" skills/uacp-bridge/SKILL.md` — update any **self-referential** prose naming `bridge-commons` to `uacp-bridge` (the architectural-layer labels in the directory tree / Layer-2 descriptions describe runtimes, not paths — keep those; only fix path-shaped/self-name refs).

**Step 5: Commit**
```bash
git add -A skills/uacp-bridge/ skills/bridge-commons/
git commit -m "refactor(bridge): scaffold uacp-bridge from bridge-commons (verbatim body, conformant frontmatter)"
```

---

## Tasks 2-6: Create `references/<runtime>.md` (one task per runtime)

For EACH runtime, the pattern is: `git mv skills/bridge-<rt>/SKILL.md skills/uacp-bridge/references/<rt>.md`; **strip every section that merely duplicates the commons contract** (it's inherited from `uacp-bridge/SKILL.md`); **keep only runtime-specific + load-bearing content** (per the keep-list below + the eval map); **fold `skills/bridge-<rt>/cli-reference.md`** in as a "## CLI reference" appendix; **strip SKILL frontmatter** (replace with a 1-line title + a prose "Depends on: uacp-bridge[, …]" note); update prose refs `bridge-commons`→`uacp-bridge`; `git rm` the leftover `skills/bridge-<rt>/README.md` (fold any unique content first); confirm `skills/bridge-<rt>/` is empty and remove it. Run `python3 -m pytest tests/unit/skills/ -q` (green) and commit per runtime.

> The eval map's "Bridge collapse map → per_runtime_references" has the full keep-list per runtime; the "load_bearing_preserved" list is the master checklist. Honor them.

### Task 2 — `references/claude.md`
Keep (drop commons dupes): Bridge Identity (native-dispatch→cli→api→skip); `[bridges.claude]` config + the "not read from TOML" callout; the 3 pre-flight checks verbatim (Task-tool, `which claude`, `${ANTHROPIC_API_KEY:+found}`) + SKIPPED envelope; Dispatch Mode Selection table; Step 3A Workflows (workflows_enabled gate, /deep-research, ultracode, custom JS API, 16/1000 caps, depth-2 degrade guard); Step 3B Agent Teams full flow (TeamCreate-first fail-closed, TeamDelete-on-failure); **EXTENDED DA prompt (cross-domain synthesis + 3-part challenge standard) and EXTENDED IC prompt (5 focus areas) — do NOT reduce to commons generic**; effort mapping (`xhigh`→`--effort max`); CLI flags verbatim; read-only vs implementation `--allowedTools` split; API `/v1/models` discovery (never hardcode); bridge output fields; ID prefix C; recursion-depth caveats. **Fold `bridge-claude/cli-reference.md`** (`--resume`, piping, `.claude/agents/` format) as the CLI appendix. Prose note: "Depends on: uacp-bridge, domain-registry, debate-protocol (Claude-only Layer-2 supersession of the Post-Analysis Protocol)."

### Task 3 — `references/codex.md`
Keep: Bridge Identity (native→mcp→cli→**halt**); `[bridges.codex]` (timeout_multiplier 1.2); the **xhigh reasoning user-confirmation GATE verbatim** (mandatory prompt, warning text, fall-back-to-high-on-decline — silent xhigh is an anti-pattern); all 5 pre-flight checks A-E with exact bash; the 4-option interactive advisory incl. the **literal `.mcp.json` block** (`{mcpServers:{codex:{command:npx,args:[-y,codex,mcp-server]}}}` — keep as literal JSON, never paraphrase); coordinator-vs-commons template labeling; MCP dispatch (threadId) vs CLI dispatch (`codex exec`, full flag set, stateless full-context-embed); Codex-specific 4th CLI-error row (valid exit + invalid JSON → partial extraction); `multi_agent_enabled` always-emitted; ID prefix X; +50% timeout when multi_agent. Fold `cli-reference.md`. Prose note: "Depends on: uacp-bridge, domain-registry."

### Task 4 — `references/gemini.md`
Keep: Bridge Identity (native→cli→skip, no HALT); `[bridges.gemini]` (1.0, no surcharge); 3 pre-flight checks (dual-location `enableAgents` probe via the exact `python3 -c` JSON parse; `which gemini`; `gemini --version` auth/quota probe → SKIPPED not HALTED, keep the intent comment); exact CLI invocation; **`--approval-mode plan` vs `auto_edit` SAFETY INVARIANT** (with rationale); **`--output-format json` (NOT `-o json`) trap**; Subagent Mode (single-call fallback is valid not degraded); `--- ROUND 2 CONTEXT ---` literal header; provider key `google`; ID prefix G; SKIPPED-only (no HALT, deliberate). Fold `cli-reference.md`. Prose note: "Depends on: uacp-bridge, domain-registry."

### Task 5 — `references/kimi.md`
Keep: Bridge Identity (native→cli→acp-server→skip; ACP@tier3 unique); 3 TOML params incl. **Kimi-only `path`**; 5 pre-flight checks incl. **6-location binary resolution order** (TOML path > KIMI_CODE_CLI_PATH > `which kimi` > $HOME/.kimi-code/bin > $HOME/.local/bin > /usr/local/bin) and **Check E `kimi login status` → HALTED on auth failure (NOT SKIPPED — deliberate vs Gemini, do not homogenize)**; native dispatch; 3 CLI forms (`-p`, `-y`/--yolo, `--plan`); ACP server mode (`kimi acp` stdio); `-C`/`-S` session flags; full CLI subcommand table (Kimi-only `--skills-dir`); ID prefix K; single-model note. **Preserve as explicit open-question callouts (do NOT fix):** (1) `--output-format json` vs `stream-json`; (2) `thinking` reasoning value/no CLI flag; (3) `-C`/`-S` vs commons-stateless. Fold `cli-reference.md`. Prose note: "Depends on: uacp-bridge, domain-registry."

### Task 6 — `references/opencode.md`
Keep (write fresh per eval spec; do NOT duplicate the two-layer footnote or `[bridges.opencode]` block — those stay in `uacp-bridge/SKILL.md`): Bridge Identity (native→**http-api(slot2)**→cli→halt); pre-flight (OPENCODE_SESSION_ID+OPENCODE_CLIENT both; HTTP probe `curl … localhost:4096` + OPENCODE_PORT; `which opencode`; model discovery); **both advisory blocks verbatim** (`cli_not_found`; `no_provider_configured` → **HALTED, intentional, user-managed auth**); multi-model config read (note regex fragility); single-vs-multi dispatch; timeout `max(...)×1.5` (NOT sum); intra-bridge mini-synthesis (70% dedup, `intra_bridge_multi_model_confirmed`, **OpenCode-only-scoped**); HTTP API path (POST /session, agent `plan` vs `build`); CLI (`opencode run` — **TUI guard**, not bare); OpenCode tier-exception restated locally; ID scheme O/O-{slug}-NNN/O-merged-NNN; bridge output fields. Fold `cli-reference.md`. Prose note: "Depends on: uacp-bridge, domain-registry."

(After Tasks 2-6: `ls skills/ | grep bridge-` → only `uacp-bridge` should remain; the 6 `bridge-*` dirs gone.)

---

## Task 7: Rewire every citer (the wiring checklist — break nothing)

**Runtime-breaking (fix + verify first):**
- `CLAUDE.md:23` `skills/bridge-claude/SKILL.md` → `skills/uacp-bridge/references/claude.md`
- `AGENTS.md:120` `skills/bridge-codex/SKILL.md` → `skills/uacp-bridge/references/codex.md`
- `skills/uacp-council/references/phase-1-registration.md:12,27-31` — commons read-pointer → `uacp-bridge/SKILL.md`; the 5 provider read-pointers → `uacp-bridge/references/{rt}.md` (**hard-abort if 404 — highest severity**)
- `skills/uacp-council/references/phase-4-dispatch.md:75-79` (per-run Read directives) → `uacp-bridge/references/{rt}.md`; prose 11,14,34,38,70,106,111 `bridge-commons`→`uacp-bridge`; **line 33 `bridge-commons/tool-discovery.md`** → see Task 8
- `skills/uacp-context/SKILL.md:43` read-pointer → `uacp-bridge/SKILL.md` (+ frontmatter dep :15)

**Frontmatter dependency collapses (6→1 where listed):**
- `skills/uacp-council/SKILL.md:8-13` six bridge entries → single `- uacp-bridge` (keep uacp-council-taxonomy, domain-registry)
- `skills/uacp-parallel/SKILL.md:11`; `skills/uacp-context/SKILL.md:15`; `skills/uacp-debate/SKILL.md:8` (+ prose :90 "inherited from bridge-commons"→uacp-bridge); `skills/uacp-brainstorm/SKILL.md:15` — `bridge-commons`→`uacp-bridge`

**Council reference prose pointers:** `finding-driven-mode.md:27,140`; `phase-7-synthesis.md:3,7,11`; `phase-8-artifact.md:60,62`; `modes.md:22`; `phase-3-domain-planning.md:24` — `bridge-commons`→`uacp-bridge`.

**Definitional:** `skills/uacp-council-taxonomy/SKILL.md:24,27,63,243-244,292` — update the location-pattern definition (`skills/bridge-{name}/SKILL.md` → `skills/uacp-bridge/references/{name}.md`; `skills/bridge-commons/SKILL.md` → `skills/uacp-bridge/SKILL.md`) + extend the legacy-mapping table.

**Verify:** `grep -rn "bridge-commons\|bridge-claude\|bridge-codex\|bridge-gemini\|bridge-kimi\|bridge-opencode" --include=*.md --include=*.py . | grep -v docs/plans | grep -v "docs/architecture/0015\|docs/architecture/0017\|skills/uacp-bridge/references/trustless"` → only intentional/historical mentions remain (see Task 8 for docs). No live skill/code path points at a `bridge-*` dir. Run full suite.

**Commit:**
```bash
git commit -am "refactor(bridge): rewire all citers from bridge-* to uacp-bridge (incl. hard-abort council read-pointers, CLAUDE.md/AGENTS.md dispatch contracts)"
```

---

## Task 8: Dangling ref, docs annotations, cleanup

- **`tool-discovery.md`** (`phase-4-dispatch.md:33` cites `bridge-commons/tool-discovery.md`, which never existed). Inspect `uacp-bridge/SKILL.md` for native-dispatch tool-detection content: if present, repoint line 33 to that section anchor; if there is genuinely no such content, **remove the broken cite** (it was already dangling) and note it in the commit. Do NOT fabricate a file.
- `skills/uacp-bridge/references/trustless-acp-source-analysis.md`? No — `trustless-acp-source-analysis.md` is in `skills/references/` (handled by the references slice). For THIS slice, update its bridge-name table rows (lines ~88-92) to the `uacp-bridge` structure (it's a live mention of the collapsed names).
- `docs/decisions/decision-log.md`: resolve the `...outputs` three-dot item as "already removed from the contract; nothing to migrate"; add a dated entry recording the `bridge-* → uacp-bridge` path change.
- `docs/architecture/0015-*.md`: do NOT edit the ADR body; add a decision-log supersession note that `skills/bridge-commons/SKILL.md` is now `skills/uacp-bridge/SKILL.md`.
- `docs/architecture/0017-*.md`: line ~26 — add a past-tense annotation ("bridge-commons (now uacp-bridge/SKILL.md)"); the target description (line 59) already matches — no structural edit.
- Plan/design docs (`docs/plans/*`, `.outputs/plans/*`): historical — do NOT rewrite.

**Commit:**
```bash
git commit -am "docs(bridge): resolve dangling tool-discovery ref, decision-log path-change entry + ADR-0015 supersession note"
```

---

## Task 9: Full verification

**Step 1:** `python3 -m pytest -q` → 0 failures (≥ 691/2 baseline).
**Step 2:** `/Users/mike/.local/bin/ruff check tests/` clean (no test changes expected, but confirm).
**Step 3:** `claude plugin validate . 2>&1 | tail -2` → passes.
**Step 4:** Structural: `ls skills/ | grep bridge` → only `uacp-bridge`; `test ! -d skills/bridge-commons` (and the other 5); every `skills/uacp-bridge/references/{claude,codex,gemini,kimi,opencode}.md` exists; `grep -rn "skills/bridge-" --include=*.md --include=*.py . | grep -v docs/plans | grep -v "decision-log\|0015\|0017"` → no live pointers.
**Step 5:** Readiness/self-containment lints green; `uacp-bridge/SKILL.md` < 500 lines? (bridge-commons was 785 — it EXCEEDS 500. This is the one accepted exception: the shared contract is irreducible earned protocol. Note it; do NOT split or summarize. The convention's <500 is advisory "when approaching, add hierarchy" — the contract is a single authoritative reference; record the exception in the commit/council notes.)
**Step 6:** Do NOT merge — council gate.

---

## After this plan
1. **Council** (high-blast-radius): architecture/conformance lens + devil's-advocate lens. Focus: (a) is the shared body truly verbatim? (b) did every runtime-breaking read-pointer get rewired (hard-abort ones especially)? (c) were per-bridge asymmetries + extended DA/IC + the 3 Kimi open-bugs preserved? (d) any commons content lost during stripping, or any runtime-specific content wrongly dropped? (e) the >500-line shared body exception.
2. **Merge** `--no-ff` to `main`, delete branch.
3. Next: **Slice 3 — references relocation** (abolish `skills/references/`), then **Slice 4 — frontmatter slim + `kind` rollout**.

## Out of scope
- References relocation (Slice 3); frontmatter slim + kind rollout (Slice 4); the 2 remaining `context: reference` offenders (domain-registry, uacp-council-taxonomy — Slice 4).
- Any behavioral change to dispatch logic; Guardian/MCP wiring; distribution.

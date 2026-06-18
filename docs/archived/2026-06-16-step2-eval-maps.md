---
type: plan
title: "Step 2 Evaluation Maps — bridge collapse + references relocation"
description: "19-agent deep-evaluation output mapping what moves where in the bridge-collapse and references-relocation slices"
tags: ["step2", "bridge", "references", "evaluation"]
timestamp: 2026-06-16
status: archived
---

# Step 2 Evaluation Maps — bridge collapse + references relocation

> Read-only deep-evaluation output (19-agent workflow `step2-skill-eval`, 2026-06-16). This is the **design input** for the Step 2 implementation plan — the grounded map of what moves where, what merges, what context must survive, and the operator decisions still open. Nothing here has been executed.

Prime directive throughout: **preserve context, zero information loss.**

---

## A. Bridge collapse map (`bridge-*` → `uacp-bridge`)

**Unified `skills/uacp-bridge/SKILL.md` = today's `bridge-commons/SKILL.md` (785 lines), migrated VERBATIM** — frontmatter changes only (`name: bridge-commons`→`uacp-bridge`; rewrite `description` dropping "Not invocable standalone"; add `kind: reference`; keep `location: managed`, `context: reference`). It is already self-containment-clean (zero `docs/` citations) and has no runtime-specific mechanics, so nothing moves out of it. **Move byte-for-byte — any "cleanup" summarization loses the 32k-truncation rule, ID-before-dedup ordering, HALTED-conversion policy, etc.**

**Each `bridge-<runtime>/SKILL.md` → `skills/uacp-bridge/references/<runtime>.md`**, STRIPPED of commons-duplicated content, keeping only runtime-specific material:
- **claude.md** — Bridge Identity (native→cli→api→skip); `[bridges.claude]`; 3 pre-flight checks; Dispatch Mode Selection (Workflows/Agent Teams/Task); Step 3A Workflows + Step 3B Agent Teams full flow (TeamCreate-first fail-closed, TeamDelete-on-failure); **EXTENDED DA/IC prompts (must NOT be reduced to commons generic)**; effort mapping (`xhigh`→`--effort max`); CLI flags; API `/v1/models` discovery; recursion-depth caveats; **fold in `cli-reference.md` as appendix**; **keep `debate-protocol` dependency (Claude-only)**.
- **codex.md** — native→mcp→cli→**halt**; `xhigh` user-confirmation GATE (verbatim); all 5 pre-flight checks; literal `.mcp.json` auto-setup block; coordinator-vs-commons template labeling; MCP threadId vs CLI stateless; `codex exec` (not bare); ID prefix X; +50% timeout when multi_agent.
- **gemini.md** — native→cli→skip (no HALT); `--approval-mode plan` vs `auto_edit` SAFETY INVARIANT; `--output-format json` (not `-o json`) trap; dual-location `enableAgents` probe; `--- ROUND 2 CONTEXT ---` literal header; SKIPPED-only.
- **kimi.md** — native→cli→acp-server→skip; **HALTED-on-auth (deliberate asymmetry vs Gemini)**; `path` TOML knob; 6-location binary resolution order; `-C`/`-S` session flags; ACP tier-3. **Preserve 3 UNRESOLVED bugs as open-question callouts (do NOT silently fix):** (1) `--output-format json` vs `stream-json` discrepancy; (2) `thinking` reasoning value with no CLI flag; (3) `-C`/`-S` vs commons-stateless tension.
- **opencode.md** — native→**http-api(slot2)**→cli→halt; **HALTED-for-no-provider**; multi-model mini-synthesis (70% dedup, **opencode-only-scoped**); max-not-sum timeout; TUI guard (`opencode run`, not bare); `O`/`O-{slug}-NNN`/`O-merged-NNN` IDs; tier-exception restated locally.

**Load-bearing mechanics to preserve** (each in its proper home — see full list in workflow output): 7-step Pre-Flight SOP; HALTED→SKIPPED conversion + `auto_skipped_halted_bridges`/`partial_coverage`/"never drop silently"; tier derivation + 5-step resolution; OpenCode tier-exception **kept in shared body** as a visible carve-out; timeout formula + per-bridge multipliers; Agent Prompt Template JSON; verdict logic (audit compliance-calibrated); output schema + ID prefixes C/G/X/O/K; dedup ID-before-identify ordering; Post-Analysis round counts (distinct from `debate-protocol`); 32k context limit + tiered summarization; Context-Passing-Between-Rounds table; Two-Layer Debate Architecture (cross-references debate-protocol supersession); artifact paths `.uacp/bridges/...`; deprecated input aliases.

**Bridge risks:** (1) **PATH CONVENTION** — the wiring detail strings say `providers/<runtime>.md` but ADR-0017 line 59 is authoritative: use **`references/<runtime>.md`**. (2) **dangling `tool-discovery.md`** — `phase-4-dispatch.md:33` cites `bridge-commons/tool-discovery.md` which does NOT exist; must create or inline, not propagate. (3) verbatim-migration discipline. (4) DA/IC prompt dilution. (5) HALTED homogenization across bridges erases user-decision gates. (6) connection-preference flattening. (7) `...outputs` three-dot token (decision-log 60/68) is **already gone** from the current file — close as "nothing to migrate".

### Bridge rewiring actions (live links — break nothing)
**Runtime-breaking (highest priority):**
- `CLAUDE.md:23` `skills/bridge-claude/SKILL.md` → `skills/uacp-bridge/references/claude.md` (read at agent boot)
- `AGENTS.md:120` `skills/bridge-codex/SKILL.md` → `skills/uacp-bridge/references/codex.md`
- `skills/uacp-council/references/phase-1-registration.md:12,27-31` — commons + 5 provider read-pointers (**hard-abort if missing**) → `uacp-bridge/SKILL.md` + `uacp-bridge/references/{runtime}.md`
- `skills/uacp-council/references/phase-4-dispatch.md:75-79` (per-run Read directives) + prose 11,14,34,38,70,106,111 + line 33 `tool-discovery.md`
- `skills/uacp-context/SKILL.md:43` read-pointer → `uacp-bridge/SKILL.md`

**Frontmatter dependency collapses:** `uacp-council/SKILL.md:8-13` (six entries → one `uacp-bridge`); `uacp-parallel:11`; `uacp-context:15`; `uacp-debate:8` (+ prose :90); `uacp-brainstorm:15`. Each bridge file's own `dependencies:` `bridge-commons`→`uacp-bridge` (Claude also keeps `debate-protocol`).

**Council reference prose pointers:** `finding-driven-mode.md:27,140`; `phase-7-synthesis.md:3,7,11`; `phase-8-artifact.md:60,62`; `modes.md:22`; `phase-3-domain-planning.md:24`.

**Definitional:** `uacp-council-taxonomy/SKILL.md:24,27,63,243-244,292` — update the location-pattern definition + legacy-mapping table (future authors follow this).

**Docs/records (annotate, don't rewrite history):** `trustless-acp-source-analysis.md:88-92` (table); decision-log (resolve `...outputs`, add path-change entry); ADR-0015 (supersession note, don't edit body); ADR-0017:26 (past-tense annotation); plan/design docs = historical, leave.

**Wiring notes:** NO `.mcp.json`, NO `runtime-adapters/`, no `.py`/config/knowledge references to bridges exist. README disposition: `bridge-commons/README.md`→`uacp-bridge/README.md` (add kimi to diagram); `bridge-kimi/README.md:66` dep line.

### Bridge open questions (operator)
1. `tool-discovery.md`: create `uacp-bridge/references/tool-discovery.md` or inline a section in SKILL.md?
2. `cli-reference.md` fold into `references/claude.md` as appendix (recommended) vs separate file?
3. Kimi `--output-format` value (`json` vs `stream-json`) — audit against the binary; carry as flagged note meanwhile.
4. Do `references/<runtime>.md` files need any frontmatter, or are they pure loaded-on-demand resources?

---

## B. Reference relocation map (`skills/references/` → abolished)

Destination rule: cited by ONE lifecycle skill → that skill's `references/`; shared/kernel → `uacp-core/references/`; dated session-history/lessons/porting/external → `docs/knowledge/` (relocate, don't delete unless verbatim-dupe/superseded).

### → single skill's `references/`
| File | Destination | Action |
|---|---|---|
| adversarial-runtime-review.md | uacp-verify/references/ | move |
| codebase-verification-review-pattern.md | uacp-verify/references/ (already byte-identical) | **delete dump copy** |
| phase-end-council-hardening.md | uacp-verify/references/ (byte-identical) | **delete dump copy** |
| read-only-containment-validation.md | uacp-verify/references/ (byte-identical) | **delete dump copy** |
| retrieval-led-phase-verify.md | uacp-verify/references/ (byte-identical) | **delete dump copy** |
| proposal-council-concerns-pattern-20260515.md | uacp-propose/references/proposal-council-concerns-pattern.md (drop date) | move |
| state-mutation-protocol.md | uacp-state/references/ (REPLACE older landed copy — preserve its Artifact-routing table) | move |

### → `uacp-core/references/` (shared)
agent-council-followthrough.md · operator-phase-return-presentation.md · heartgate-council-artifact-management.md · kimi-codex-agent-council-audit-loop.md (drop date) · external-audit-runtime-gate-remediation.md · governed-canonical-writers.md · adaptive-package-backfill-pattern.md · adaptive-package-gate-commit-pattern.md (drop date) · **lifecycle-semantic-gates.md (MERGE — see below)**

### → `docs/knowledge/` (distill / merge; create the dir)
~20 target docs. Notable merges:
- **lifecycle-semantic-gates** (×3: -20260519 base + base + lifecycle-hardening-pattern) → actually lands in **uacp-core/references/** (still cited by live skills), not knowledge. Reconcile two 8-step sequences.
- agent-council-integration + phase6-operationalization → `agent-council-integration-and-operationalization-lessons.md`
- operator-phase-return-and-semantic-packages + semantic-package-council-patch-loop → `semantic-package-and-operator-return-lessons-20260519.md`
- 3 containment docs (anchor: contained-shell-execution-seam) → `filesystem-containment-phase-lessons.md`
- 3 runtime-porting docs → `hermes-adapter-porting-and-cleanup-lessons.md`
- phase4b + 2 phase5-kanban → `kanban-guard-and-closure-lessons.md`
- 2 full-lineage docs → `full-lineage-audit-and-remediation-lessons-20260520.md`
- singles distilled: phase-transition-finalization, guardian-branch-review, guardian-hook-audit, guardian-neutral-kernel-adapter, runtime-trust-boundary-correction, branch-porting-ground-truthing, round3→runtime-adapter-construction-guidelines, current-semi-auto-orchestration, adaptive-gate-selection, skills-validator-alignment, lexa-first-principles, trustless-acp-source-analysis, architecture-packet-uacp-compatibility, operational-dashboard-and-live-proof, lcp-integration (3-line extract only).

(Full per-doc "preserve" specs and the 7 merge-group preserve-lists are in the workflow output `/private/tmp/.../ws3z4d0ve.output` — the merge specs are detailed and must be honored verbatim during execution.)

### Delete candidates (with preconditions)
- 4 byte-identical uacp-verify dupes (confirmed via diff)
- governian-neutral-kernel-adapter.md (typo stub of guardian-…; fix 1 cross-ref)
- delegate-task-model-selection.md (empty placeholder, zero knowledge)
- lifecycle-skill-contract.md (superseded by lifecycle-reference.md 298-317 — **precondition: verify phase_local_granularity + human_involvement YAML templates exist in uacp-plan/uacp-execute first**)
- codex-handoff-for-uacp.md (superseded by bridge-codex — **precondition: confirm bridge-codex covers the vague-handoff pitfall**)

---

## C. Convention revision (ADR-0017 + uacp-skills) — REQUIRED
The shared home moves from `skills/references/` to **`uacp-core/references/`**; the top-level dump is abolished. Edits: ADR-0017 lines 57, 72 (`skills/references/`→`uacp-core/references/`); uacp-skills/SKILL.md lines 96, 107 (same); add the explicit destination-rule paragraph; the self-containment test must treat `uacp-core/references/` as the shared path AND **fail on any cite of the abolished `skills/references/`**; create `docs/knowledge/` (NOT skill-citable — it's human/agent reading, not instruction prose); repoint the root `skills/SKILL.md` (~12 cites) to new homes.

---

## D. Open questions for the operator (decide before planning execution)
1. **`docs/knowledge/` creation + registration** — confirm create; must `docs/INDEX.md` (authority priority 1) register it / each relocated doc?
2. **Root-router (`skills/SKILL.md`) vs self-containment** — it cites ~12 files; some go to `docs/knowledge/` → a skill citing `docs/` (rule violation). Is the root router an exempt **index** (points, doesn't instruct), or must every knowledge-bound file it still needs be mirrored to `uacp-core/references/` instead? Decides ~6 routings.
3. **"Cited only by the root index" classification** — architecture-packet, lexa, adaptive-package-* are cited only by the root router. Count as "shared" (→uacp-core) or "no skill cites it" (→docs/knowledge)? (Tied to Q2.)
4. **Date-suffix dropping** — drop `-2026MMDD` on move to uacp-core/references (session markers, not expiries) while knowledge-bound dated lessons KEEP the date as provenance — confirm.
5. **`tool-discovery.md`** (bridge) — create file vs inline.
6. Delete preconditions (verify templates landed; bridge-codex covers handoff).

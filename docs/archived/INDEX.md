---
type: index
tags: [index, archive, deprecated]
status: living-document
---

# Archived Documents — Index

These are **completed and shipped** initiatives kept for historical record. None are canonical; they document the design and implementation decisions behind features already merged to main.

## Archive Policy

A document is archived (not deleted) when:
1. A successor document supersedes it.
2. The content is no longer canonical but the historical context matters.
3. An ADR references the document as the prior state.

Archived documents must declare in their first paragraph: `**Status: archived. Superseded by [path]**`.

## Documents

| File | Title | Type | Date | Description |
|------|-------|------|------|-------------|
| [2026-06-09-claude-agents-md-design.md](2026-06-09-claude-agents-md-design.md) | Design: CLAUDE.md and AGENTS.md for UACP Root | design | 2026-06-09 | Design for adding runtime instruction files at the UACP root to orient Claude Code and Codex agents |
| [2026-06-09-claude-agents-md.md](2026-06-09-claude-agents-md.md) | CLAUDE.md and AGENTS.md Implementation Plan | plan | 2026-06-09 | Task-by-task plan to create AGENTS.md and the thin CLAUDE.md adapter at the UACP repo root |
| [2026-06-14-uacp-cc-hardening-design.md](2026-06-14-uacp-cc-hardening-design.md) | UACP — Claude-Code-First Hardening & Simplification (Design) | design | 2026-06-14 | Design for making UACP provably work end-to-end under Claude Code with a behavioral E2E test harness |
| [2026-06-14-uacp-cc-hardening.md](2026-06-14-uacp-cc-hardening.md) | UACP Claude-Code-First Hardening — Implementation Plan | plan | 2026-06-14 | Implementation plan for a no-LLM behavioral E2E harness driving a full UACP run through Guardian and Heartgate |
| [2026-06-15-computed-heartgate-engines-design.md](2026-06-15-computed-heartgate-engines-design.md) | Computed Heartgate Engines (Design) | design | 2026-06-15 | Design for replacing Heartgate's honor-system coherence lens with deterministic computed enforcement engines |
| [2026-06-15-uacp-namespace-and-config-collapse-design.md](2026-06-15-uacp-namespace-and-config-collapse-design.md) | `.uacp/` Namespace + Config Collapse (Design) | design | 2026-06-15 | Design for consolidating UACP's per-project footprint under `.uacp/` and collapsing 13 config YAMLs into one `uacp.toml` |
| [2026-06-15-uacp-namespace-and-config-collapse.md](2026-06-15-uacp-namespace-and-config-collapse.md) | `.uacp/` Namespace + Config Collapse — Implementation Plan | plan | 2026-06-15 | Master implementation plan for the `.uacp/` namespace relocation and config-collapse refactor across five slices |
| [2026-06-15-uacp-namespace-slice2.md](2026-06-15-uacp-namespace-slice2.md) | `.uacp/` Namespace — Slice 2 (Relocate runtime dirs) Implementation Plan | plan | 2026-06-15 | Slice 2 plan to relocate UACP runtime dirs (`state/`, `.outputs/`) under `.uacp/` via config-backed resolver |
| [2026-06-15-uacp-namespace-slice3.md](2026-06-15-uacp-namespace-slice3.md) | Config Collapse — Slice 3 (knob YAMLs → `uacp.toml`) Implementation Plan | plan | 2026-06-15 | Slice 3 plan to collapse 8 knob config YAMLs into `config/uacp.toml` sections wired through `config.py` |
| [2026-06-15-uacp-namespace-slice4a.md](2026-06-15-uacp-namespace-slice4a.md) | Config Collapse — Slice 4a (grammar schemas → code) Implementation Plan | plan | 2026-06-15 | Slice 4a plan to move validator-enforced schemas and enums from YAML into Pydantic models in `engines/domain` |
| [2026-06-15-uacp-namespace-slice4b.md](2026-06-15-uacp-namespace-slice4b.md) | Config Collapse — Slice 4b (phase-transitions.yaml → code) Implementation Plan | plan | 2026-06-15 | Slice 4b plan to move the phase graph and gate grammar into code, fixing three enforcement landmines including F-T3-01 fail-closed |
| [2026-06-16-step2-eval-maps.md](2026-06-16-step2-eval-maps.md) | Step 2 Evaluation Maps — bridge collapse + references relocation | plan | 2026-06-16 | 19-agent deep-evaluation output mapping what moves where in the bridge-collapse and references-relocation slices |
| [2026-06-16-uacp-goal-driven-track-design.md](2026-06-16-uacp-goal-driven-track-design.md) | UACP Goal-Driven Track — Design | design | 2026-06-16 | Design for a second lifecycle track enabling semantic/exploratory work under the same UACP phases without forward-only constraints |
| [2026-06-16-uacp-goal-driven-track-implementation.md](2026-06-16-uacp-goal-driven-track-implementation.md) | UACP Goal-Driven Track — Implementation Plan | plan | 2026-06-16 | 9-task implementation plan for the `goal-driven` lifecycle track with persistent goal, checkpoint manifest, and convergence budget |
| [2026-06-16-uacp-namespace-slice5.md](2026-06-16-uacp-namespace-slice5.md) | Config Collapse — Slice 5 (validator dedup + final codification + cleanup) Implementation Plan | plan | 2026-06-16 | Slice 5 plan to dedup validator copies, codify remaining phase-transitions grammar, and finalize the config-collapse refactor |
| [2026-06-16-uacp-skill-convention-design.md](2026-06-16-uacp-skill-convention-design.md) | UACP Skill Convention — Design | design | 2026-06-16 | Design for the `uacp-skills` meta-skill defining a single enforced convention for every skill in the UACP library |
| [2026-06-16-uacp-skills-convention-step1.md](2026-06-16-uacp-skills-convention-step1.md) | UACP Skills Convention — Step 1 Implementation Plan | plan | 2026-06-16 | Step 1 plan to author the `uacp-skills` convention meta-skill and enforce self-containment via a regression test |
| [2026-06-17-brainstorm-optional-phase-design.md](2026-06-17-brainstorm-optional-phase-design.md) | Brainstorm as an Optional Kernel Phase — Design | design | 2026-06-17 | Design for promoting `brainstorm` from an informal pre-TRIAGE skill to a formal, state-registered optional entry phase |
| [2026-06-17-brainstorm-optional-phase-plan.md](2026-06-17-brainstorm-optional-phase-plan.md) | Brainstorm Optional Kernel Phase — Implementation Plan | plan | 2026-06-17 | Implementation plan to add `brainstorm` as a formal entry phase in the lifecycle graph with governed-writer access |
| [2026-06-17-lesson-knowledge-corpus-design.md](2026-06-17-lesson-knowledge-corpus-design.md) | Lesson & Knowledge Corpus + Distillation Loop — Design | design | 2026-06-17 | Design for UACP's two prior-art corpora (lessons and knowledge) with BES scoring and the distillation loop |
| [2026-06-17-lesson-knowledge-corpus-plan.md](2026-06-17-lesson-knowledge-corpus-plan.md) | Lesson & Knowledge Corpus + Distillation — Implementation Plan | plan | 2026-06-17 | Implementation plan for the governed lessons/knowledge corpora in `.uacp/`, BES scorer, and RESOLVE-phase extraction |
| [2026-06-17-oracle-engine-design.md](2026-06-17-oracle-engine-design.md) | Oracle Retrieval Engine — Design | design | 2026-06-17 | Design for a config-gated Python retrieval aggregator composing run-state lookup, semantic search, and Honcho memory |
| [2026-06-17-oracle-engine-plan.md](2026-06-17-oracle-engine-plan.md) | Oracle Retrieval Engine — Implementation Plan | plan | 2026-06-17 | Implementation plan for `engines/oracle/` with QMD pipeline, LanceDB store, and the `uacp_oracle_query` governed tool |
| [2026-06-17-step2-slice1-cc-readiness.md](2026-06-17-step2-slice1-cc-readiness.md) | Step 2 · Slice 1 — Claude Code plugin readiness + convention re-grounding | plan | 2026-06-17 | Slice 1 plan to make the UACP skills library an installable Claude Code plugin with manifest and readiness lint |
| [2026-06-17-step2-slice2-bridge-collapse.md](2026-06-17-step2-slice2-bridge-collapse.md) | Step 2 · Slice 2 — Bridge collapse (`bridge-*` → `uacp-bridge`) | plan | 2026-06-17 | Slice 2 plan to collapse six `bridge-*` skills into one `uacp-bridge` skill with per-runtime reference files |
| [2026-06-17-step2-slice3-references-relocation.md](2026-06-17-step2-slice3-references-relocation.md) | Step 2 · Slice 3 — References relocation (abolish `skills/references/`) | plan | 2026-06-17 | Slice 3 plan to empty the top-level `skills/references/` dump by routing each doc to its correct canonical home |
| [2026-06-17-step2-slice4-frontmatter-kind.md](2026-06-17-step2-slice4-frontmatter-kind.md) | Step 2 · Slice 4 — Frontmatter slim + `kind` rollout | plan | 2026-06-17 | Slice 4 plan to drop vestigial authority mirrors from lifecycle skills and roll the `kind:` classifier to all 23 skills |
| [2026-06-17-step2-slice5-refdoc-policy-and-docs-cleanup.md](2026-06-17-step2-slice5-refdoc-policy-and-docs-cleanup.md) | Step 2 · Slice 5 — Reference-document policy + `docs/` back-pointer cleanup | plan | 2026-06-17 | Slice 5 plan to codify the anti-proliferation reference-doc policy and resolve remaining `docs/` back-pointers in lifecycle skills |
| [2026-06-17-step2-slice7-okf-alignment.md](2026-06-17-step2-slice7-okf-alignment.md) | Step 2 · Slice 7 — OKF frontmatter alignment + council-taxonomy → reference | plan | 2026-06-17 | Slice 7 plan to align the reference/knowledge layer to OKF frontmatter and fold `uacp-council-taxonomy` into the reference home |

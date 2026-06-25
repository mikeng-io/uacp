---
kind: handoff
workstream: docs-topology-cocoindex
title: UACP documentation topology + CocoIndex-generated derived layer (hybrid doc-maintenance strategy)
status: active
scope:
  in: [doc taxonomy/topology of docs/, the authoritative-vs-derived-vs-explanatory-vs-historical classification, the CocoIndex Layer-2 generation decision + its write-boundary]
  out: [the note-gardening essay for mikeng.io, UACP kernel/governance changes, hosting/rendering (MkDocs etc.), the graph-engine initiative]
attribution:
  generated_by: { agent: claude-code, model: claude-opus-4-8[1m], runtime: cc }
  updated_at: '2026-06-25'
edges:                                      # ANCHORS — reconstructable refs live ONLY here
  - {dst: 'branch:main', rel: anchored_to, provenance: parsed}
  - {dst: 'commit:048332d', rel: anchored_to, provenance: parsed}
---

# Handoff — docs-topology-cocoindex

## Intent
Make UACP's documentation reliably human-readable and *correct* without the recurring
failure where finishing a task and "updating the docs" spawns a new stray doc or
edits the wrong one. Directional goal: a **hybrid** doc system — hand-authored
authoritative doctrine stays human/agent-owned; a derived "implementation/reference"
layer is generated from the codebase and kept in sync incrementally — separated by a
hard, machine-enforceable boundary. This is documentation **FOR/ABOUT the UACP
plugin**, NOT a new UACP kernel feature, and it carries no governance authority.

## Decisions & rationale
- [locked] **Hybrid of two layers.** ① authoritative hand-authored doctrine (the doc
  IS truth; code implements it) + ② derived docs generated from code (code is truth).
  Why: no off-the-shelf tool reliably derives the right update for *conceptual* docs,
  but *code-reference* docs ARE derivable — so split the corpus by where truth lives.
- [locked] **Generation engine = CocoIndex.** Why over alternatives: actively
  maintained (10.4k★, commits daily), incremental/change-sized (matches user's "no
  full re-index"), BYO-LLM via LiteLLM (point at a LOCAL model → private kernel stays
  in-house), emits committed markdown with deterministic placement, and "you author
  the ~few-hundred-line pipeline" fits UACP's own-your-engines ethos.
- [2026-06-25 revisit] **CocoIndex SUPERSEDED as the ② indexer by Codeflair** (now
  built+merged): Codeflair already provides deterministic, incremental, repo-local,
  no-LLM, no-external-dep code indexing (SCIP Go/Py/TS + tree-sitter + co-change) —
  which was CocoIndex's *entire* technical justification. Revised ② = a thin generator
  over **Codeflair's index** + a render/prose step (template or local LLM) →
  `docs/generated/`. CocoIndex (alpha `1.0.0a6` Rust+LMDB external dep) is dropped — it
  would re-derive what Codeflair already holds, contradicting own-your-engines/fewer-deps.
  The ①/② split + write-boundary are unchanged; only the engine flips. Caveat: Codeflair
  indexes *code* (3 langs); docs derivable from config/skills/YAML aren't in its
  wheelhouse — but those fall in the hand-authored ① set anyway, so not a real gap.
- [locked] **NOT a UACP kernel feature.** It is a separate doc-generation concern that
  READS the repo; no Heartgate/Guardian authority, not part of the lifecycle. (User
  corrected this ~3×: "doc generator FOR UACP, not UACP generating docs.")
- [locked] **In-repo, not a hosted/served wiki.** The "fewer external dependencies"
  rule is about UACP's RUNTIME, not doc tooling — but docs must still live in-repo;
  user dislikes external wikis as inaccurate + needing re-index.
- [locked] **Taxonomy-first.** Classify the existing docs/ corpus BEFORE standing up
  CocoIndex; the classification defines the boundary the engine may operate in.
- [locked] **Classification axis = "where does the source of truth live?"** → 4
  classes: ① Authoritative (doc is truth; never AI), ② Derived (code is truth;
  CocoIndex owns), ③ Explanatory (curated narrative; human, AI-assist ok), ④
  Historical (archived; triage for removal).
- [locked] **The ONE boundary rule:** CocoIndex may READ everything but WRITE only to
  a designated ② tree (`docs/generated/`); never edits ①/③/`archived/`. Enforce as a
  lint write-allowlist.
- [locked] **Hard ① no-AI-touch set (user-explicit):** `architecture/` ADRs +
  `decisions/decision-log.md`; plus `policy/`, `lifecycle/` doctrine, `plans/`.
- [open] **Four sub-decisions proposed w/ recommendations, NOT yet user-confirmed:**
  (1) MIXED clusters `reference/`+`runtime/` → rec (b) never let CocoIndex edit
  existing docs; generate a *separate* `docs/generated/` tree and retire derivable
  hand-docs into it over time. (2) `archived/` → rec: migrate unique rationale into
  ADRs, then delete bulky realized-execution plans. (3) ② location/git → rec:
  `docs/generated/`, COMMITTED (not gitignored) + "GENERATED — DO NOT EDIT" banner,
  excluded from authority chain + authoritative lint. (4) class count → rec: keep ③
  Explanatory separate (don't collapse into ①).

## Rejected / not-this
- **Hosted DeepWiki (Cognition)** — external SaaS; ships a PRIVATE governance repo to
  a third party; and it's the "inaccurate + re-index" wiki the user objected to.
- **DeepDocs / Swimm / Promptless** — SaaS; DeepDocs *edits the repo* via PRs (breaks
  in-repo/no-external) and patches heuristically with no registry → reproduces the
  misfiling in CI rather than fixing it.
- **DeepWiki-Open (self-hosted)** — fixes the third-party concern but still FULL
  re-index (the disliked part) and is a served wiki app, not committed-in-repo.
- **RepoAgent** — best *mechanism* match (incremental git-diff per-object,
  deterministic placement, in-repo markdown, BYO-LLM) BUT dormant (last commit Dec
  2024), Python-only (blind to config/skills/docs), llama-index-coupled → would mean
  maintaining a fork. OK only as a throwaway spike, never as durable infra.
- **MkDocs / static-site generators** — that's hosting/rendering; user explicitly does
  NOT care about hosting, only content generation.
- **Building doc-derivation INTO UACP** as a governed lifecycle step or a "uacp-docs
  skill + lint" — user rejected twice; it's a separate concern, not a kernel feature.

## Open threads & watch-outs
- The four sub-decisions above are UNCONFIRMED — get the user's call before the audit.
- Next concrete step (deferred): a **per-doc audit** — fan out parallel agents over
  `archived/` (30 files), `reference/`, `runtime/` → final per-file topology +
  `archived/` migrate-vs-delete list + the CocoIndex write-boundary spec.
- watch-out: `reference/` and `runtime/` are MIXED *within* the folder —
  `proposal-schema`/`skill-enforcement-spec` = ① contracts; `lifecycle-trace-table` +
  runtime's "what the kernel does" description = ② derivable. The cut is per-doc.
- watch-out: CocoIndex v1 is **alpha** (`1.0.0a6`); the codebase-wiki is *sample
  code*, not a maintained API → pin versions, expect churn. Adds a Rust wheel + an
  LMDB state file (gitignore the state).
- watch-out (governance): the generator must run sandboxed (worktree/branch), OUTSIDE
  the run lifecycle, writing a clearly non-authoritative tree; never in the docs/
  authority chain, never fed back as evidence — else it collides with
  governed-writers-only / no-main-writes / no-self-attesting.
- context: user is concurrently writing a mikeng.io essay on note-gardening vs
  AI-native context; this doc-maintenance frustration is its real-world seed — but
  keep the essay OUT of this workstream.

## Now → next
- **Position:** see Anchors. NOTE: this was a pure decision/planning session — no code
  written; the last commit is unrelated repo position only.
- **Next intent:** get the user's call on the four open sub-decisions, then run the
  per-doc audit to produce the final docs topology + `archived/` triage + CocoIndex
  write-boundary spec. Only THEN stand up the CocoIndex pipeline.

## Anchors
- branch: main
- commit: 048332d — unrelated (repo position only; no work committed for this workstream)
- doc inventory is reconstructable: `find docs -name '*.md'` (84 files; `archived/`=30, `architecture/`=19)
- (no design node yet — `design/docs-topology/` not created)
- (no run_id — ungoverned planning session)

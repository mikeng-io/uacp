---
type: reference
title: UACP Directory & File Taxonomy (canonical, as-built)
description: The single authoritative map of what directories and files the UACP control plane has — the .uacp/ tree, every file's path template, its kind, and its format (YAML vs Markdown vs JSONL). Grounded in config/uacp.toml [paths] + the validator path templates. The reference schema.py / uacp-lint / uacp-fmt build against.
tags: [uacp, taxonomy, directory, files, layout, reference]
timestamp: 2026-06-22
edges:
  - {dst: 26-nomenclature, rel: relates_to, provenance: asserted}
  - {dst: 24-asbuilt-manifest-taxonomy, rel: depends_on, provenance: derived}
---

# UACP Directory & File Taxonomy (canonical, as-built)

> What files and directories the control plane actually has. Top-level dirs are from
> `config/uacp.toml [paths]` (the live resolver source); path templates are from the kernel
> validators (`scripts/validate_uacp_artifacts.py`) + [24-asbuilt-manifest-taxonomy](24-asbuilt-manifest-taxonomy.md).
> Kinds + formats: [26-nomenclature](26-nomenclature.md). `{run_id}` is the run; `*.md` = Markdown
> (prose, validated by required sections — NOT JSON-Schema); `*.yaml` = structured (JSON-Schema).

## The tree

```
.uacp/                                  ← governed namespace root ([paths].base)
├── state/                              ← state plane
│   ├── current.yaml                    uacp.current_state        (active-run pointer)
│   ├── run-registry.yaml               uacp.run_registry         (active runs)
│   ├── runs/{run_id}.yaml              RunManifest               (the run spine; artifacts map)
│   ├── runs/{run_id}-transition-*.yaml uacp.phase_transition     (Heartgate transition record)
│   ├── gate-ledger/{run_id}.jsonl      (ledger; incl. CHECKPOINT for goal-driven)   [JSONL]
│   └── hashes/{run_id}.json            (artifact watermark index)                   [JSON]
├── brainstorm/{run_id}/07-scope-package.yaml   (BRAINSTORM scope export → TRIAGE)
├── proposals/                          ← PROPOSE
│   ├── {run_id}-triage*.yaml           uacp.triage
│   ├── {run_id}-package-selection.yaml uacp.proposal_package_selection
│   ├── {run_id}-intent.md              uacp.intent               [Markdown: required sections]
│   └── {run_id}/                       proposal module artifacts (universal_core + modules)  [Markdown]
├── plans/                              ← PLAN (THREE documents)
│   ├── {run_id}-plan-selection.yaml    uacp.plan_package_selection
│   ├── {run_id}-scope.yaml             uacp.scope                (write-boundary)
│   ├── {run_id}-piv.yaml               uacp.phase_intent_verification_contract  (PIV contract)
│   └── {run_id}/                       plan module artifacts                                  [Markdown]
├── executions/                         ← EXECUTE
│   ├── {run_id}-checkpoint-NNN.yaml    uacp.execution_checkpoint (1 per work_unit)
│   └── {run_id}/                       execution semantic md (work-narrative, decision-log, …) [Markdown]
├── verification/                       ← VERIFY
│   ├── {run_id}-piv-assessment.yaml    uacp.piv_assessment
│   ├── {run_id}-verify-selection.yaml  uacp.verification_package
│   ├── {run_id}-resolve-readiness.yaml uacp.verify_resolve_readiness
│   ├── {run_id}-{cluster}-verified-facts.md / -assumptions.md   uacp.evidence_disposition  [Markdown paired]
│   ├── {run_id}-council.yaml           uacp.council_synthesis    (when council runs)
│   └── {run_id}/                       verify semantic md                                     [Markdown]
├── resolutions/                        ← RESOLVE
│   ├── {run_id}-resolve-selection.yaml uacp.resolve_package
│   ├── {run_id}-closure.yaml           uacp.resolve_closure
│   ├── {run_id}-lessons.yaml           uacp.lessons              (the RESOLVE lessons artifact)
│   └── {run_id}/                       resolve semantic md                                    [Markdown]
├── knowledge/                          ← knowledge plane (corpus)
│   ├── <id>.md                         knowledge_item (OKF)                                   [Markdown]
│   ├── index.md                        aggregate index
│   └── indexes/                        Oracle vector index (derived, .gitignored)
├── lessons/                            ← knowledge plane (corpus)
│   └── <id>.md                         lesson (OKF)                                           [Markdown]
├── bridges/                            ← runtime: bridge execution artifacts          [JSONL + md]
├── councils/                           ← runtime: council session artifacts
└── config.toml                         ← per-project config override (optional)

config/                                 ← REPO-level doctrine (NOT under .uacp/)
├── uacp.toml                           uacp.control_plane_config ([paths], knobs, registries)
├── state.yaml                          uacp.state_config
├── phase-transitions.yaml              uacp.phase_transition_config
├── gate-selection.yaml                 uacp.gate_selection_config
├── review-routing.yaml                 uacp.review_routing_config
└── evidence-clusters.yaml              uacp.evidence_cluster_registry
```

## By format (drives which validator handles it)

- **`*.yaml` structured** → JSON-Schema in `schema.py` + referential checks in `uacp-lint`. (Most lifecycle docs, state, config.)
- **`*.md` Markdown** → required-section / paired-file checks in `uacp-lint` (prose-aware); **NOT** JSON-Schema. (`uacp.intent`, `uacp.evidence_disposition`, the `{run_id}/` module artifacts, the knowledge/lessons corpus OKF.)
- **`*.jsonl` / `*.json`** → ledger + watermark index (append-only / derived); their own validators, not the schema registry.

## Aggregates (directory + members)

Per-phase `{run_id}/` directories (`proposals/{run_id}/`, `plans/{run_id}/`, `executions/{run_id}/`, `verification/{run_id}/`, `resolutions/{run_id}/`) hold the **Markdown module/semantic artifacts** referenced by that phase's YAML envelope. The envelope's `universal_core`/`semantic_package`/`evidence` keys point into this directory; `uacp-lint` checks the referenced artifacts exist + live under the dir (a referential check).

## Open item (the one unresolved part of the taxonomy)

The **knowledge plane sub-structure** is the only unsettled directory question. **As-built = flat**: two sibling dirs `.uacp/lessons/` (BES-scored per-run lessons) + `.uacp/knowledge/` (distilled, cross-project) — both Oracle-owned. The **D30 design proposes nested** `.uacp/knowledge/{facts,lessons,patterns,rules}/` + run-local `executions/{run_id}/observations/`, and `11-node-taxonomy` ↔ `22-context-loop` are unreconciled. **This taxonomy documents the as-built (flat); the nested form is a pending design decision, deliberately not imposed here.**

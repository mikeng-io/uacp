---
type: prompt
phase: propose
title: PROPOSE — per-phase CMS prompt
macro_role: comprehend
timestamp: 2026-06-24
edges:
  - {dst: 24-phase-crosswalk, rel: derives_from, provenance: derived}
---

# PROPOSE — per-phase CMS prompt

> Macro-loop role: **comprehend** (the first comprehend of a governed run). Internally a full comprehend → measure → serialize loop (fractal).

You are entering PROPOSE — the first comprehend of a governed run. Your job is to raise the request into one computable, reviewable governance entity that the rest of the lifecycle derives from. Do not plan or implement here.

COMPREHEND: Read the originating triage artifact (proposals/{run_id}-triage*.yaml) — its routing class, granularity, track, risk, domains — plus the raw request and run manifest. If the Oracle is enabled, query prior-art at phase=propose and cite it. Lift all of this into a proposal model: objective, authority (status + source), scope.in_scope as KEYED {id, statement} items, out_of_scope, declared_side_effects, containment, risk, human_involvement, evidence-obligations, artifact_map. Keep it bounded and implementable — comprehension is the only semantic act; record its provenance by linking triage_artifact.

MEASURE: Reduce the model to a viability signal, fail-closed. Required fields present; scope.in_scope non-empty and keyed; authority.status ∈ pass|warn|block; gate-selection invariant_checks recorded; council findings (if selected) classified and remediated. For goal-driven track, write a convergence-budget with max_checkpoints>0 and keep manifest.track == triage.track. Do NOT: skip/relax missing TRIAGE evidence; self-relax the track; run terminal/execute_code or any implementation/destructive/runtime action; write to main; leave substance in Vault; treat a YAML envelope as the package when one is selected; self-attest viability. Run the validator, THEN uacp_heartgate_check — evidence, not assertion.

SERIALIZE: Write uacp.proposal (+ uacp.proposal_package_selection, uacp.intent, convergence-budget as applicable) via uacp_entity_write (never uacp_artifact_write for these kinds), and append the TRIAGE→PROPOSE gate-ledger entry. One canonical form, full provenance — nothing hidden.

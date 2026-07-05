---
type: analysis
title: "Blast radius measurement and open questions"
description: "Quantifies the measured surface (engines, schema, lifecycle skills, tests) and lists must-resolve-early open questions before PLAN. Records the meta-finding of three lifecycle-executability breaks surfaced during the brainstorm."
tags: [blast-radius, open-questions, surface, analysis, measurement, pre-plan]
timestamp: 2026-06-30
edges:
  - {dst: 01-problem, rel: relates_to, provenance: asserted}
---
# 07 — Blast radius & open questions

## Measured surface (from the brainstorm)
| Surface | Count | Notes |
|---|---|---|
| Engine load-bearing | 2 | `projection.py` (`_project` + check replay/`_read_path`), `schema.py` |
| Engine peripheral refs | 3 | `heartgate.py`, `adaptive_gates.py`, `phase_transitions.py` |
| Schema/validator | 2 | `schema.py` + `validate_uacp_artifacts.py` (17 hits) |
| Lifecycle skills + refs | ~6 | propose, plan, verify, resolve, triage, brainstorm |
| Tests | 18 | e2e lifecycle, graph projection/invariant, schema, check authoring/replay, scope gate |
| Migration | N runs | NOT migrated (additive ratchet — see [05](05-migration.md)) |

Precedent: `uacp.intent`, `evidence_disposition` are already MARKDOWN kinds — paved path.

## Open questions — must resolve EARLY (before PLAN)
1. **Do `heartgate.py` / `adaptive_gates.py` read scope CONTENT or only STRUCTURE?**
   If structure-only, they are untouched and the radius shrinks. This gates the whole sizing.
   *(First task of any follow-on: grep + read those two against `in_scope`/`objective`.)*
   *(RESOLVED by Slice 0, node 11: only `validate_class_underclaim` / `candidate_class` in
   `manifest/projection.py` reads meaning; `_scope_concern_is_keyed` in
   `heartgate/validators/adaptive_gates.py` and `domain/schema.py` `statement`-required are
   presence-only. Slices 0–2 shipped — PR #70 / `c7bd737` / 2026-06-29.)*
2. **Anchor serialization** — inline-per-node vs sidecar map; `path#fragment` vs structured.
   Build decision; tests arbitrate. Contract is fixed in [03](03-anchor-primitive.md).
3. **Section-resolution semantics** — exact "non-empty / header present" definition for MD
   sections, and how it composes with `artifact_integrity` watermarking of MD files.
4. **Per-kind ratchet order** — which kind converts first (proposal scope vs evidence_disposition);
   [06](06-evidence-disposition-case.md) argues evidence_disposition is the cleanest first cut.

## Meta-finding (separate initiative — NOT this bundle)
Driving this brainstorm through the governed lifecycle surfaced 3 breaks where the documented
lifecycle is not executable through its own tools:
1. run init not exposed as a governed tool (skill says `uacp_state_write`; it refuses `state/runs/`),
2. evidence_disposition `verified-facts` unwriteable ([06](06-evidence-disposition-case.md)),
3. brainstorm→triage `uacp_heartgate_check` rejects `brainstorm/` paths (handler
   `allowed_transition_roots` omits it), contradicting the brainstorm skill's phase-8.

These are lifecycle-*executability* bugs, distinct from this content/relation redesign. They
deserve their own focused fix initiative — flagged here so they are not lost.

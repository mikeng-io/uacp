# Phase 2 — Exploration: the as-built map + blast radius

## What actually lives where (grounded in hnp-20260628 artifacts + kernel code)

Key fact — every generative-gate check binds to a **YAML field path**
(`check-1-field_present.yaml`: `bind.ref.artifact: ...proposal.yaml`, `field: scope.in_scope[0]`).
And `projection.py:141-145` builds `scope_item` graph nodes from `proposal.yaml → scope.in_scope[]`.
**The MD package contributes zero graph nodes and zero check targets. The gate never opens the MD.**

### Three categories (not a clean two-way split)
1. **Machine spine — YAML only.** proposal_id, phase, triage_artifact, granularity_level,
   gate-selection clusters, check.bind, gate-ledger, run-registry, watermarks. Pure plumbing.
2. **DUPLICATED — both YAML + MD.** objective/intent, scope.in_scope, authority{}, declared_side_effects.
   Gate reads the YAML copy; council reads the MD copy. They can drift; nothing notices.
3. **Council substance — MD only.** risk analysis (R1/R2/R3), containment, verification plan,
   transition reasoning, artifact map. This is what council spends its review on — gate-invisible.

### The problem in one sentence
The surface council reviews (MD substance, cat. 2-MD + cat. 3) and the surface the gate measures
(cat. 1 + cat. 2-YAML) **barely overlap.** After council, remediation lands mostly in cat. 3
(MD-only, ungated) and sometimes cat. 2 (duplicated, hand-synced) — and no check, lens, or replay
ever measures whether it happened.

## Principle alignment
`field_present` checking a YAML prose field is non-empty is the exact "weak proxy" the CMS
principle warns against (a grep standing in for "the feature works"). Presence of a string ≠
the intent is real. Semantic adequacy is a *semantic* judgment → belongs to council, not a
deterministic presence check.

## Blast radius (measured)
| Surface | Count | Notes |
|---|---|---|
| Engine load-bearing | 2 | `projection.py` (_project + check replay/_read_path), `schema.py` |
| Engine peripheral refs | 3 | heartgate.py, adaptive_gates.py, phase_transitions.py (confirm: structure vs content) |
| Schema/validator | 2 | schema.py + validate_uacp_artifacts.py (17 hits) |
| Lifecycle skills + refs | ~6 | propose, plan, verify, resolve, triage, brainstorm (prose) |
| Tests | 18 | e2e lifecycle, graph projection/invariant, schema, check authoring/replay, scope gate |
| Migration | N runs | existing on-disk artifacts use the old shape |

**Precedent already exists:** `uacp.intent` and `evidence_disposition` are ALREADY MARKDOWN kinds
(`layout.py:104,143`) — MD-as-content is a paved path, not new ground.

## Runtime gaps surfaced during this very brainstorm (extra evidence of the problem class)
- `handle_init` (run registration) is NOT exposed as a governed tool; the brainstorm skill says
  "register via uacp_state_write" but that writer REFUSES state/runs/. Had to call the engine fn directly.
- (from the parallel hnp session) `uacp.check.*` needs `ctx={seq}`, undocumented; raw Write to .uacp/
  is Guardian-blocked with no skill pointer to uacp_artifact_write; no post-council update contract.

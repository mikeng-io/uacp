# 08 — Council review findings (verdict: REWORK)

Reviewed by two independent Claude subagents (adversarial + as-built grounding) and
**codex (cross-provider)**. All three converged. Verdict: **rework before build.**

The factual groundings all CONFIRMED (evidence_disposition bug, the 3 executability
breaks, the YAML-only gate surface). The MODEL under-resolved its central fork.

## Blockers (unanimous)
1. **"Additive / peripheral / untouched" is false.** Moving `statement`/intent prose out of
   YAML breaks deterministic gates that read it today:
   - `schema.py:349-379` requires `scope.in_scope[].statement` (validate-on-write rejects {id, anchor});
   - `adaptive_gates.py:49-51` D43 `_scope_concern_is_keyed` requires `statement is not None`
     → else Heartgate rejects scope (`heartgate.py:276-290`);
   - `projection.py:945-980` `validate_class_underclaim` derives class from statement/intent
     text → silently stops firing if relocated (no test catches it — the regression is dark).
   Node 07's "open question #1" is already answered by the code: **the gates read content.**
2. **"Removes the weak proxy" is overstated.** "anchor resolves & non-empty" is the same
   proxy class, relocated. The existing evidence_disposition validator (`validators.py:388-498`)
   is STRONGER than the proposed anchor floor. Conflates "anchor resolves" with "contract met."
3. **Simpler alternative never weighed (B2).** Single-home-in-YAML (keep prose in YAML, drop
   the duplicate MD, council reads YAML or a generated rendering) dedupes with near-zero
   machinery and no broken gates. MD-as-home is asserted, not justified.

## Should-fix
- MD-section-by-id resolution is real new machinery (slug rules, dup-id, heading depth,
  frontmatter/fence exclusion, empty-body, watermark interaction) — not "build decides."
- Premise correction: "the gate never opens MD" is FALSE — the evidence_disposition validator
  already reads MD bodies (`validators.py:405-423`). (Cuts in the design's favor.)
- Content/relation boundary not crisp for risk / authority / declared_side_effects.
- Blast-radius counts loose (~26 tests not 18; "17 hits" doesn't reproduce); `bind.ref.field`
  vs real `bind.ref.path` drift.

## The decision this forces (PARKED for operator)
- **B1 — MD-home (this design):** gates must read through anchors into MD → contradicts
  "YAML = pure relations"; needs the full anchor/section-resolver stack. Bigger, riskier.
- **B2 — YAML-single-home:** prose stays in YAML (one home), drop duplicate MD, council reads
  YAML/rendering. Kills duplication with near-zero machinery, no broken gates.

## Status
PARKED. Not build-ready. B1/B2 is an operator architecture decision, deferred deliberately.
The lifecycle-executability fixes (node 07 meta-finding) are split out as a separate, higher
-priority initiative and proceed first.

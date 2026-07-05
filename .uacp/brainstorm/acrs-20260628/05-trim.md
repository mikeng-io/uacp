# Phase 5 — Trim to a bounded scope

## Selected scope (one paragraph)
Define the canonical UACP **artifact content/relation model**: Markdown carries the
semantic content (intent, scope statements, authority rationale, risk/containment/
verification analysis), YAML carries relations (ids, `derives_from`/`measured_by`
edges, deterministic scalars) plus an **anchor** linking each relation-node to its
MD content home. Retarget `field_present` to bind to anchored MD sections so the
gate measures the surface council actually reviews. Deliver as an **additive ratchet**
(anchors + new binding mode added; legacy YAML prose stays optional), NOT a cutover.

## This is a DESIGN-track scope
Output of the governed lifecycle here is a **design bundle** under
`design/artifact-content-relation/` (decomposed facet nodes + _index), per the UACP
design convention — NOT the implementation. Build follows in a later run.

## In scope
- The canonical content(MD) vs relations(YAML) split, stated as a rule per artifact kind
- The anchor primitive (YAML relation-node → MD section) — schema + projection
- `field_present` retarget: bind to an anchored MD section (presence + non-empty)
- The additive-ratchet migration strategy (legacy prose optional; no eager run migration)
- Resolve the open question: do heartgate/adaptive_gates read content vs structure
- The post-council artifact-update contract (Approach A folded in as the interim + the end-state)

## Out of scope
- The actual build/implementation (EXECUTE, a later run)
- Hard cutover; eager migration of in-flight on-disk runs
- Changing the council/gate AUTHORITY model (semantic=council, relational=gate stays)
- The separate runtime gaps surfaced (handle_init not a tool; these are noted, filed separately)

## enter_uacp: true
## routing_advisory: full_governance
Kernel (projection/checks) + schema + all lifecycle skills + council-required (Invariant #4),
cross-provider reviewer. High consequence, decomposed design bundle.

## rationale
Approach B is the principled fix (CMS at the artifact layer); the additive ratchet
keeps blast radius bounded (the 18 tests mostly survive). A is folded in as the interim
update contract; C is the check-retarget mechanism inside B.

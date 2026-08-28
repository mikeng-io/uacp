---
type: evidence
title: "UACP's own PRINCIPLE.md — derived from the implementation (the record)"
description: "The derivation record: UACP's own principal was produced by running CMS on the implementation (four implementation-first readers over kernel/gates, lifecycle/writers, config-as-wired, tests+trajectory — docs treated as claims to verify against the code), then engineer-agreed 2026-08-17. The canonical file ships at repo-root PRINCIPLE.md; this node is the proof-of-method + evidence base."
tags: [grounded-governance, principle, derivation, evidence, cms]
timestamp: 2026-08-17
edges: [{dst: 01-principle-md, rel: realizes, provenance: derived}]
---
# UACP's PRINCIPLE.md — the derivation record

The canonical principal ships at **repo-root `PRINCIPLE.md`** (status `agreed`). This node records
*how it was produced*, so the agreement is grounded, not asserted.

## Method — CMS at the project grain, implementation-first

Four implementation-first readers comprehended the running reality, **treating the prose docs as
claims to verify against the code, not as the answer**:

- **kernel & gates** — guardian.py, heartgate.py, coherence.py, scope_conformance.py, state_machine.py
- **lifecycle & governed writers** — state_machine.py, entity_writer.py, state.py
- **config as-wired** — uacp.toml, phase-transitions.yaml, verification-floor.yaml, gate-selection.yaml, evidence-clusters.yaml
- **tests & git trajectory** — tests/e2e/*, ~1062 commits 2026-05→07, #98 (telos), #155–158 (Proving Ground)

`comprehend` those → `measure` a grounded signal of purpose → `serialize` the statement.

## The finding that validated the method

All four readers, grounding independently on different parts of the code, converged on the same
product — **coherence** (a run whose claims are bound to evidence, re-derivable by a non-doer) — **and**
the same frontier: **the loop is closed over the record, not yet over the work** (evidence checked for
existence not truth; the git-grounded scope check advisory-only; the code/behaviour plane "BLOCKS until
wired" but unwired; witness/oracle/memory inert). The derivation **independently reproduced the
grounded-governance diagnosis** in `00` — validation from a fresh direction, not assertion.

## Agreement

The one thing derivation cannot supply is the *forward vector* — the intended direction where it
outruns the built reality. The engineer confirmed both the statement and the vector ("close the loop
over the work, not the paperwork") on 2026-08-17. The agreement is recorded as a governed
`uacp.principle_agreement` node (see `03`); the derivation method is the `uacp-bootstrap` skill.

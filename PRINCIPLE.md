---
name: uacp-principle
kind: principle
status: agreed                  # engineer-confirmed 2026-08-17 (the user-agreement gate); derived, not authored
derived_from: implementation-first
method: comprehend the running reality → measure a grounded signal of purpose → serialize (docs treated as claims to verify against the code, not as the answer)
evidence_base:
  - kernel & gates (guardian.py, heartgate.py, coherence.py, scope_conformance.py, state_machine.py)
  - lifecycle & governed writers (state_machine.py, entity_writer.py, state.py)
  - config as-wired (uacp.toml, phase-transitions.yaml, verification-floor.yaml, gate-selection.yaml, evidence-clusters.yaml)
  - tests & git trajectory (tests/e2e/*, ~1062 commits 2026-05→07, #98 telos, #155-158 Proving Ground)
derivation_record: skills/uacp-bootstrap/SKILL.md  # the derivation method; sources listed in evidence_base above
---

# PRINCIPLE — UACP

*What this project is trying to achieve — the toward-what, not the roadmap, product, policy, or standard.*

> **Make the output of non-deterministic (semantic) actors — AI agents and the humans directing them — trustworthy without trusting the actor, by manufacturing _coherence_: a run whose every claim is bound to external evidence and can be re-derived and checked by a party that did not do the work.**

## What holding this principle commits the project to (the invariants the code treats as sacred)

1. **No self-attestation.** Completion is externally *declared* (typed writers + a declared-intent envelope; Guardian default-denies anonymous governed writes) and externally *witnessed* at a boundary the actor cannot skip (exit gates forced into `handle_transition`). Closure is re-derived from emitted reality, never read from the run's self-report.
2. **Governance is a membrane, not a workflow.** The actor *requests* a transition; the writers and gates *authorize and effect* it. Authority over the record is structurally removed from the doer — every state-defining artifact is write-blocked to one narrow governed writer.
3. **Fail closed.** Absence, error, or ambiguity blocks. A green check that proves nothing is a defect — non-vacuity is its own tested category; degrade to a *finding*, never to a crash or a silent pass.
4. **Bind to reality, not assertion.** Verdicts are computed from independent witnesses — git's account of what changed, the append-only ledger, the manifest — reconciled against each other, not taken from the run's account of itself.
5. **Time-asymmetric friction.** Pay at the point of work so later work runs on rails: typed, provenanced, tamper-evident residue that another run — or another actor — can stand on without re-litigating.

The governed atom is **the phase transition**; the atom of value is **the gate-ledger record** (`{gate, run_id, ts, result}`, append-only, tamper-evident) — the irreducible proof that a specific gate was crossed, checkable after the fact.

## The frontier — where intended reality exceeds built reality (the "and when")

Today the conformance loop is **closed over the record**: structural / governance-state coherence — right phases in legal order, each with a recorded gate and an existing artifact, cross-checked manifest↔ledger↔registry↔scope — is enforced hard and fail-closed.

It is **not yet closed over the work**: that the evidence is *true*, that the code does what it claims, that a fix actually resolves its finding. The machinery says so itself — exit "evidence" is checked for *existence, not correctness*; the one reality-grounded scope check (git diff vs declared paths) is *advisory-only*; `verification-floor.yaml` demands a code/behavior verification plane *"not yet in the catalog — a target of those classes BLOCKS until that plane is wired"*; the witness, oracle, and memory planes ship *inert by default*; rework enforcement is *surfaced, not compelled*.

The direction is already visible in the build: the enforcement engine was built *first*, the telos written into the canon *last* (#98), and the newest, most active investment — the Proving Ground (#155–158) — exists to **empirically prove the engine constrains a real, untrusted agent over N replicates**.

> **The forward vector (engineer-confirmed): close the conformance loop over the _work_, not only the paperwork — bind the records to running reality.** Wire the behavior/code verification plane; promote scope-conformance and the witnesses from advisory to blocking where the evidence supports it; activate the memory substrate so serialized residue actually feeds later runs.

---

*Provenance: this principle was **derived, not authored** — CMS run on UACP's own implementation (docs treated as claims to verify against the code), then confirmed by the engineer on 2026-08-17. The derivation method is recorded in the `uacp-bootstrap` skill; its evidence base is the `evidence_base` frontmatter above; the agreement itself is recorded as a governed `uacp.principle_agreement` node.*

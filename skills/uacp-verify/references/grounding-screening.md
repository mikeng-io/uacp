# VERIFY Grounding Screening

How VERIFY reads the produced work for **undeclared** defects — the correctness screening that the
conformance floor cannot do. This is a **governance-plane** procedure: VERIFY produces the substrate,
dispatches a **neutral council `review`** over it, and consumes the findings into the governed
artifact its gate enforces. The council contributes only its neutral review posture; it never learns
about VERIFY. Rationale + the six-phase picture: `design/grounded-governance/`.

## Substrate (kernel-produced, never nominated by the run)

- the **diff** from the run's true `merge-base..HEAD` range (`gitio.diff_content`) — the real change
  set, in full;
- the **reality-run output** — what the changed code did when executed in the contained scratch
  (`behavior_plane`).

## Dispatch — a neutral review, charged not scripted

Dispatch a council `review` over the substrate. Hand it the material and **one** charge — *construct
the input that defeats this work* — under the Code Review Rules (`AGENTS.md`) as its charge, and
nothing that pre-judges it. No "check X"; the defect precipitates from reading the real diff. Give it a
writable scratch (`behavior_plane`) so it **runs** the component against inputs it constructs.

## Discipline (shared across all grounding screenings)

- **Substrate, not declaration** — read the kernel-produced diff/run, never the run's account.
- **Charge, not checklist** — one adversarial instruction under the Code Review Rules; dimensions
  (correctness/security/resource-safety) are what the read *surfaces*, not roles assigned up front.
- **Reproduce, don't read** — every finding binds to a hunk or a probe result; an unexecuted reading
  cannot block or clear.
- **Typed output incl. honest abstention** — verdict `clean | findings | cannot_verify`;
  `cannot_verify` is treated as unresolved, never a silent pass.
- **Disposition + fixpoint** — open findings are discharged (a fix pointer that resolves) or
  adjudicated (decision + rationale + cost-if-wrong); any fix moves the diff, so the substrate hash
  changes, the stale screening no longer covers, and VERIFY re-screens the delta to a clean round.

## Finding lenses — the reasoning that makes defects precipitate

The charge is "defeat the work"; these are the *ways* to defeat it — reasoning methods to run over the
substrate, **not** a checklist of expected findings (they say HOW to look, never WHAT to find). Sweep
each lens to saturation: once it surfaces one instance of a defect class, find EVERY instance before
moving on. (Derived from what a competent external reviewer actually does; a screening that skips these
is a screening in name only.)

1. **Adversarial input** — for each predicate/guard, construct the input that PASSES it but violates
   its intent (a shared-prefix run-id; a path that escapes the root; a boundary value).
2. **Missing / boundary value** — for a guard like `if a and b and mismatch`, ask what ABSENT or empty
   value makes it silently pass (a null session; an omitted field).
3. **Sibling consistency** — when two components describe the same reality (a change set, a commit
   range, a count), check they AGREE; a divergence is the defect (`changed_files` vs `diff_content`).
4. **End-to-end value tracing** — follow a value producer→consumer (a path, an id, a hash); do both
   ends agree on what/where it is? (double-prefixing a root; reporting a path the validator resolves
   elsewhere).
5. **Schema-vs-enforcement** — what does the data MODEL permit that the code never checks? (a `verdict`
   the schema allows but the gate treats as resolved).
6. **Promise-vs-delivery** — the code/response PROMISES something (a structured envelope, a populated
   field); is it kept on EVERY path, or empty on some? (a `findings[]` envelope left empty).
7. **Lifecycle preconditions** — does a check account for WHEN/where it runs? (a pre-execution phase
   requiring an artifact that only exists post-execution).
8. **Invariant cross-check** — does each write/action obey the project's stated invariants (governed
   writers, no main writes, plane separation)? (a shell script writing raw into `.uacp/`).
9. **Class-completeness** — having found one instance of a class, sweep for ALL siblings sharing the
   shape (every branch reusing a flawed helper; every hard-coded assumption).
10. **Principle / generality** — does the implementation honor the project's stated principles
   (runtime-neutrality, determinism-at-the-gate)? A Python-only assumption in a runtime-neutral system
   is a defect (`_CODE_SUFFIXES` missing C#/PHP/Kotlin/…).

## Output + gate

Write a governed `uacp.correctness_screening` artifact — `{substrate_hash, reviewed_range, verdict,
findings[], screener}` — keyed to the substrate hash. The VERIFY grounding gate (`uacp-core`) blocks
the crossing unless a screening **resolves and covers** the current substrate, and every finding of a
`findings` verdict is dispositioned. This procedure is the read that satisfies that gate.

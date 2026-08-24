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

## Output + gate

Write a governed `uacp.correctness_screening` artifact — `{substrate_hash, reviewed_range, verdict,
findings[], screener}` — keyed to the substrate hash. The VERIFY grounding gate (`uacp-core`) blocks
the crossing unless a screening **resolves and covers** the current substrate, and every finding of a
`findings` verdict is dispositioned. This procedure is the read that satisfies that gate.

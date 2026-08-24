# TRIAGE Grounding Screening

How TRIAGE keeps the run from being scoped against a fiction — the head of the cascade. A
**governance-plane** procedure: TRIAGE produces the substrate, dispatches a **neutral council
`review`** over it, and consumes the findings into the governed artifact its gate enforces. The
council never learns about TRIAGE; it only reviews. Rationale + the six-phase picture:
`design/grounded-governance/` (node 05).

## Substrate (kernel-produced)

The real state of the **scope's declared targets**: for each path/symbol the scope names, whether it
resolves in the real tree, its kind/size, and — via the code plane — the real local structure of the
symbols involved. Not the design doc that motivated the scope.

## Two layers

- **Deterministic floor (no agent).** Every declared scope target must *resolve* in the real tree
  (exist as its declared kind). A scope naming a phantom blocks with no review — the M2
  resolves-not-asserts rule for scope targets.
- **Neutral review (over the produced slice).** Dispatch a council `review` charged: *here is the real
  state of the targets this scope names — is the scope real, and is its granularity/routing consistent
  with what is actually there?* No checklist; the mis-scope (wrong granularity over entangled code; a
  false premise-referent) precipitates from reading the real slice against the declared scope.

## Discipline (shared across grounding screenings)

Substrate not declaration; charge not checklist; reproduce-don't-read (every finding binds to the
produced slice); typed output with a first-class `cannot_verify`; disposition (discharge by re-scoping,
or adjudicate with residual risk) + the substrate-hash fixpoint (re-scoping forces a re-screen).

## Output + gate

Write a governed `uacp.triage_screening` artifact — `{substrate_hash, reviewed_scope, verdict,
findings[], screener}`. The TRIAGE grounding gate (`uacp-core`) enforces the floor (targets resolve)
and the coverage (a screening resolves + covers the substrate; findings dispositioned). This procedure
is the read that satisfies it.

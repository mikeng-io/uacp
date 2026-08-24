# PROPOSE Grounding Screening

How PROPOSE stops a correctly-scoped run from being built on a false premise. A **governance-plane**
procedure: PROPOSE produces the substrate, dispatches a **neutral council `review`** over it, and
consumes the findings into the governed artifact its gate enforces. The council never learns about
PROPOSE; it only reviews. Rationale + the six-phase picture: `design/grounded-governance/` (node 06).

## Substrate (kernel-produced)

The **reproduced current behavior** of the premise's referent — what the code *does now*, not its
text. Via `behavior_plane`: run the referent against the input the premise implies and capture what
actually happens; for a presence/absence premise, a witnessed search of the real tree; for a
structural premise, the code plane's real count.

## Dispatch — a neutral review that must reproduce

Dispatch a council `review` charged: *here is the real, reproduced current behavior of what this
proposal claims about — is the premise true?* The review lifts each factual claim in the premise into
something runnable/searchable and reproduces it against the substrate. A premise claim that **does not
reproduce** (the code does not eager-load; the guard already exists) is a **P1** finding: the run is
mis-motivated. Reproduce, don't read — an unexecuted reading of the premise cannot clear it.

## Discipline (shared across grounding screenings)

Substrate not declaration; charge not checklist; reproduce-don't-read; typed output with a first-class
`cannot_verify` (a claim the sandbox cannot stand up — legitimately adjudicable as residual risk);
disposition (discharge by re-premising, or adjudicate) + the substrate-hash fixpoint (re-premising
forces a re-screen).

## Output + gate

Write a governed `uacp.propose_screening` artifact — `{substrate_hash, reviewed_premise, verdict,
findings[], screener}`. The PROPOSE grounding gate (`uacp-core`) blocks the crossing unless a screening
resolves + covers the current substrate and every finding is dispositioned. This procedure turns "the
proposal says X is broken" into "X was run and is in fact broken."

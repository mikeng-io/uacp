## Propose-Grounding-Screening Mode

A `propose-grounding-screening` council is the PROPOSE-phase read that stops a correctly-scoped run
from being built on a false premise (`design/grounded-governance/06`). It shares all the discipline of
`correctness-screening` (fuzzy intent, no checklist, reproduce-don't-read, typed findings incl. a
first-class `cannot_verify`, the fixpoint loop — see
`[skills-root]/uacp-council/references/correctness-screening.md`); what differs is the **substrate**
and the **question**.

### The substrate — the reproduced current behavior

A proposal's premise is an account of the *current* state that justifies the work ("`toll_fee`
eager-loads on every request"; "there is no idempotency guard"; "the retry double-counts"). The
reality is not the code's text — it is what the code **does now**. The kernel produces the **reproduced
current behavior** of the premise's referent via `behavior_plane` (the contained-execution primitive):
run the referent against the input the premise implies and capture what actually happens; for a
presence/absence premise, a witnessed search of the real tree; for a structural premise, the code
plane's real count.

### The question — is the premise true?

One thing precipitates: **does the premise reproduce?** The screener lifts each factual claim in the
premise into something runnable/searchable, reproduces it against the substrate, and reports:

- a premise claim that **does not reproduce** — the code does *not* eager-load, the guard *does* exist —
  is a **P1** finding: the run is mis-motivated, and everything downstream inherits the phantom.
- a claim that **cannot be reproduced** in the sandbox (needs an environment the scratch can't stand
  up) returns **`cannot_verify`** — a typed abstention, never a silent pass. It may be legitimately
  **adjudicated** ("could not reproduce X here; residual risk R"), the M3d grammar.

### The charge

*Here is the real, reproduced current behavior of what this proposal claims about — is the premise
true?* Reproduce, don't read: an unexecuted reading of the premise cannot clear it. No checklist; the
false premise precipitates from running the claim against reality.

### Output

A governed `uacp.propose_screening` artifact — `{substrate_hash, reviewed_premise, verdict:
clean|findings|cannot_verify, findings[], screener}` — keyed to the substrate hash the PROPOSE gate
matches. The loop and disposition are identical to `correctness-screening`: re-premising moves the
substrate hash and forces a re-screen; a non-reproducing premise is discharged (the proposal
re-premises) or adjudicated (accepted residual). Enforcement is `validate` in `uacp-core` (the PROPOSE
grounding gate); this mode is the read that satisfies it — turning "the proposal says X is broken"
into "X was run and is in fact broken."

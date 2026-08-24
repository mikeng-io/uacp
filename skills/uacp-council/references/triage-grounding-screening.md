## Triage-Grounding-Screening Mode

A `triage-grounding-screening` council is the TRIAGE-phase read that keeps the run from being scoped
against a fiction (`design/grounded-governance/05`). It shares all the discipline of
`correctness-screening` (fuzzy intent, no checklist, reproduce-don't-read, typed findings incl. a
first-class `cannot_verify`, the fixpoint loop — see `[skills-root]/uacp-council/references/correctness-screening.md`);
what differs is the **substrate** and the **question**.

### The substrate — the real project-root slice the scope names

Not a diff (no work exists yet). The kernel produces the **current state of the scope's declared
targets**: for each path/symbol the triage scope names, whether it resolves in the real tree, its kind
and size, and — via the code plane — the real local structure of the symbols involved. The screener
reads *that*, not the design doc that motivated the scope.

### The question — is this scope real, and is it right-sized?

Three things precipitate, over that slice:

- **Existence** (a deterministic floor the gate already enforces): does every named target actually
  exist as the declared kind? A scope naming a phantom is caught without the screener.
- **Granularity** (semantic): is the granularity score consistent with the *real* structure? A "small,
  P2, doc-hygiene" verdict over code that is actually entangled is the classic mis-score — the screener
  reads the real symbols and says so.
- **Premise referent** (semantic): if the scope is "fix X", does X — the real thing the scope points
  at — exist and look like what the scope claims? (Reproducing X's *behavior* is PROPOSE's job,
  `06`; triage confirms the referent is real.)

### The charge

Same as `correctness-screening`, pointed at scope: *here is the real state of the targets this scope
names — is the scope real, and is its size/routing consistent with what is actually there?* No list of
things to check; the mis-scope precipitates from reading the real slice against the declared scope.

### Output

A governed `uacp.triage_screening` artifact — `{substrate_hash, reviewed_scope, verdict:
clean|findings|cannot_verify, findings[], screener}` — keyed to the substrate hash the TRIAGE gate
matches. A finding is a mis-scope (phantom target already caught by the floor; wrong granularity;
false premise-referent). `cannot_verify` is the honest abstention when the scope's reality cannot be
settled from the produced slice. The loop and disposition are identical to `correctness-screening`:
re-scoping moves the substrate hash and forces a re-screen; open findings are discharged (re-scope) or
adjudicated (accepted with residual risk). Enforcement is `validate` in `uacp-core`
(the TRIAGE grounding gate); this mode is the read that satisfies it.

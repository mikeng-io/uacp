## Correctness-Screening Mode

A `correctness-screening` council is the VERIFY-phase read that the conformance floor cannot do: it
**reads the work for undeclared defects**. Its input is not the run's account of itself — it is the
kernel-produced **substrate** (`design/grounded-governance/01`): the real diff from the run's true
`merge-base..HEAD` range, what the changed code did when run, and the files as they are. The council
screens *that material* and lets whatever is wrong precipitate.

Use it whenever a run changed code. It is a `review`-family mode (produces findings + a verdict), but
distinguished by two things: the material is the witnessed substrate, and the charge forbids a
checklist.

### The charge — fuzzy intent, never a checklist

The dispatch packet hands the screener the substrate and **one instruction**: *here is the real diff
and what it did when run — construct the input that defeats this work.* It does **not** tell the
screener what to look for. The moment the packet says "check input validation" or "you are the
security reviewer," it has pre-digested the work outside the agent and reintroduced the disease the
whole layer exists to cure (`design/verify-substrate/02`). Dimensions — correctness, security,
resource-safety, encoding — are what the reading **surfaces**, not roles assigned up front.

The screener runs under the **Code Review Rules** (`AGENTS.md`) as its *charge*, not its checklist:
severity by consequence (P1 = data loss / corruption / security / silent wrong answer; P2 = real but
bounded); saturation (report a defect **class** once, not every instance); class-completeness (having
found one of a class, sweep for the rest); don't-review-a-fix-into-a-new-defect; and
behavioral-over-structural proof.

### Grounding — reproduce, don't read

Every finding binds to a **hunk in the substrate or a probe result** — never to the author's account.
An unexecuted reading cannot block or clear. The screener gets a **writable scratch** and
`behavior_plane` to *run* the changed component against inputs it constructs: "I think this `open()`
follows symlinks" becomes "I pointed one at it and it did." The probe's own execution is witnessed
(the containment evidence is grounded, not self-declared — the M5 independence mechanism), so the
screening cannot claim a run it did not do.

### Required inputs

```yaml
correctness_screening_input:
  mode: "correctness-screening"
  substrate:
    substrate_hash: ""          # the kernel's sha256 identity for this run's diff (the gate matches it)
    reviewed_range: {base_commit: "", head_commit: ""}
    diff_text: ""               # the kernel-produced unified diff (merge-base..HEAD) — the material
    reality_run: ""             # what the changed code did when executed (exit/stdout/observed)
  charge: "construct the input that defeats this work"   # NOT a list of things to check
  # + standard fields (scope, tier, intensity). NO expected findings, NO suspected cause, NO rubric.
```

### Output — the screening artifact, including honest abstention

The screening writes a governed `uacp.correctness_screening` artifact (schema in
`uacp-core`), keyed to the substrate it read:

```yaml
kind: uacp.correctness_screening
substrate_hash: ""              # MUST equal the kernel's identity for the range it reviewed
reviewed_range: {base_commit: "", head_commit: ""}
verdict: clean | findings | cannot_verify
findings:                       # [] when clean
  - {id, severity: P1|P2, defect_class, message, substrate_ref, repro, disposition?}
screener: {model, independence_evidence}
```

`cannot_verify` is a **first-class, typed** result for a claim the substrate cannot settle (a behavior
the scratch cannot stand up). It is not silence and it is not a pass — the gate treats an inconclusive
screening as unresolved, never as clean. Silence is the one failure mode the whole floor exists to
prevent.

### The loop — the fixpoint that terminates

Review is a fixpoint, not a step. On any fix in response to findings, HEAD moves, so the kernel
**re-produces the substrate** (a new `substrate_hash`) and the prior screening no longer covers it —
the gate rejects it as stale, forcing a **re-screen scoped to the changed delta** plus any finding it
interacts with (don't-review-a-fix-into-a-new-defect). The loop ends at a **clean round** — a pass
with no new P1 over the current diff — not at a fixed attempt count. Each finding that survives to
the rework cap must be discharged (a fix whose pointer resolves) or explicitly adjudicated
(decision + rationale + cost-if-wrong); convergence or adjudication, never a silent give-up. The
enforcement for all of this lives in `uacp-core` (`validate_correctness_screening` /
`validate_correctness_findings`); this mode is the semantic read that satisfies it.

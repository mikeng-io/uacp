# 04 — MEMEX + BES Architecture

## Core answer

Mike asked whether MEMEX+BES is the “glue” of UACP.

Answer:

```text
Yes — MEMEX + BES is the connective tissue of UACP.
MEMEX is the glue.
BES is the weighting/learning signal inside the glue.
```

More structurally:

```text
UACP lifecycle      = spine
Guardian/Heartgate = immune system / gates
Agent Council      = cognition
Kanban             = coordination memory
MEMEX              = associative memory / connective tissue
BES                = adaptive weighting / learning signal
```

## Why it is glue

Without MEMEX:

```text
TRIAGE sees current request
PROPOSE writes current intent
PLAN designs current work
EXECUTE does current tasks
VERIFY checks current output
RESOLVE writes current lessons
```

But every phase depends on the active session/model manually remembering:

- previous warnings,
- prior Heartgate failures,
- repeated council concerns,
- unresolved deferred items,
- previous runtime boundary decisions,
- verification patterns,
- lessons that were useful/noisy.

With MEMEX:

```text
TRIAGE asks MEMEX: what similar runs/failures/patterns exist?
PROPOSE asks MEMEX: what authority constraints and prior decisions apply?
PLAN asks MEMEX: what execution pitfalls and verification obligations recur?
EXECUTE asks MEMEX: what known runtime/worker failure modes apply?
VERIFY asks MEMEX: what prior invariants/warnings must be checked?
RESOLVE asks MEMEX: what patterns should be promoted, retired, or rescored?
```

## Boundary: glue, not governor

MEMEX must connect UACP, but must not govern UACP.

Correct:

```text
MEMEX suggests relevant governed memory.
BES ranks usefulness.
Council reasons over it.
Heartgate validates transition coherence.
Guardian enforces runtime boundaries.
```

Incorrect:

```text
MEMEX found this, therefore the phase may proceed.
```

Sharp boundary:

```text
Glue, not governor.
Memory, not authority.
Ranking, not approval.
Context, not command.
```

## What gets glued

### 1. Phase-to-phase memory

```text
RESOLVE lessons → future TRIAGE/PLAN/VERIFY packets
```

### 2. Council-to-runtime memory

```text
Council concern → execution guardrail → verification invariant
```

### 3. Warning-to-deferred-item continuity

```text
Accepted Heartgate warning → PLAN obligation → VERIFY check → RESOLVE closure
```

### 4. Artifact-to-context selection

```text
state/runs + verification + plans + skills → phase-aware Recall Packet
```

### 5. Pattern-to-effectiveness loop

```text
Pattern injected → outcome observed → BES updated → future retrieval changed
```

## Clean architecture sentence

```text
UACP MEMEX is the governed connective memory layer of UACP. It links lifecycle phases, council findings, verification outcomes, warnings, deferred items, and lessons into phase-aware recall packets. BES provides the adaptive scoring signal that determines which remembered patterns remain useful over time.
```

Shorter:

```text
MEMEX connects UACP’s memory. BES teaches it what mattered.
```

## UACP-adapted BES

Trustless baseline:

```text
BES = (successes + 1) / (eligible + 2) × recency_factor
```

UACP-adapted formula proposed by council:

```text
uacp_bes = (successes + 1) / (eligible + 2) × recency_factor × authority_factor
```

Why add authority?

UACP is not only measuring bug prevention. It is measuring governance usefulness. A council-reviewed resolved run and a draft note should not have equal weight.

Example authority factors:

```yaml
council_reviewed_resolved_run: 1.00
heartgate_transition_warning: 0.95
verification_artifact: 0.90
accepted_deferred_item: 0.85
skill_reference: 0.75
draft_plan_note: 0.60
pre_tracking_legacy_note: 0.50
```

## What BES means inside UACP

For Trustless:

```text
Did this lesson prevent code/spec bugs?
```

For UACP:

```text
Did this recalled pattern improve governance outcomes?
```

Possible success outcomes:

- prevented a phase transition error,
- prevented stale doctrine/config mismatch,
- avoided repeating a Guardian/Heartgate bug,
- caused a council to catch a blocker earlier,
- prevented Kanban/UACP state conflation,
- improved verification coverage,
- reduced rework or phase rollback,
- surfaced the right deferred item before execution.

Possible recurrence/failure outcomes:

- known warning repeated,
- Heartgate rejected something MEMEX should have caught,
- council found a blocker already present in prior lessons,
- stale artifact was injected,
- irrelevant packet polluted reasoning,
- authority boundary got confused,
- hidden doctrine drift appeared.

## Design line

```text
MEMEX retrieves.
BES ranks.
Council reasons.
Heartgate gates.
Guardian enforces.
UACP state records.
```

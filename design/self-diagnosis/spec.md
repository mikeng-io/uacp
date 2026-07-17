# Lifecycle conformance — the engine-prover (v1 target)

> Working name: **lifecycle conformance / engine-prover**. Drop "self-diagnosis"
> (introspection connotation; wrong subject). Project-scope skill (`.claude/skills/`),
> NOT a `skills/uacp-*` plugin skill — the observer cannot be part of the observed.

## Subject under test
The **UACP lifecycle ENGINE** — the machinery: phases, transitions, gates, governed
writers, handoffs. **NOT** the content/substance of any run. We prove the lifecycle
*itself*, not what it builds.

## Probe
A throwaway real task. v1: **build a local Astro blog, no external deps** (no Cloudflare).
Its only job is to make the engine run. Its content quality is irrelevant and is
explicitly **not** checked.

## Stimulus (the original intent)
A **breaking change injected into UACP**. The prover's job is to catch that the engine
broke. Without a stimulus it is a smoke test (does the engine drive end-to-end); with one
it is a regression test (does the break get caught — the PR#96 gate-deadlock class).

## Measure — content-independent mechanism properties
- **L1 transitions-through-apparatus** — every phase hop went through Heartgate with a
  real evaluation; not bypassed, forced, or skipped.
- **L2 gates-non-vacuous** — each gate actually evaluated and derived a verdict; not
  always-pass, short-circuited, or deadlocked. *(PR#96 class.)*
- **L3 terminal-reached** — the engine drove to RESOLVE via a legal path; no stall,
  deadlock, or mid-lifecycle error.
- **L4 plumbing** — governed writers persisted, the ledger appended, handoffs carried
  state forward.

## Gate — per property, fail-closed, CODE (never an LLM judge)
PASS = property held. FAIL = mechanism defect. ERROR = trace lacks the signal to decide
(itself a finding: *make the mechanism observable*). Run-level: engine-conformant iff
L1–L4 all PASS; else the FAIL set is the findings. Every finding cites its trace signal
(non-vacuity).

## The decoupling that makes it engine-level (the invariant that defines the target)
- garbage plan + working engine → **PASS** (content is not our concern)
- good plan + deadlocked gate → **FAIL**

A content-auditor gets these **backwards** (fails the good-engine/bad-plan run, passes the
broken-engine/nice-plan run). The engine-prover must get them right. This is the litmus
that we are testing the engine, not the payload.

## How we know the measure itself is correct (mandatory calibration)
Planted-fault method — a prover never run against a known-broken engine is unverified:
1. **Clean run** → L1–L4 all PASS (baseline).
2. **Inject a KNOWN engine break** (e.g., force a gate to always-pass) → the matching L
   **must FAIL**. If it doesn't, the prover is theater.

## Sessions (the "how")
**Two Claude contexts.** Session 1 = runner (drives the probe through the real lifecycle,
emits a handoff). Session 2 = independent observer (fresh context, reads the trail, runs
L1–L4, files findings). The on-disk handoff is the **only** channel between them. Optional
**non-LLM watchdog** (`timeout`/heartbeat) wrapping Session 1 to capture an L3 deadlock as
evidence rather than a silent hang. Never a sub-agent (shares the runner's blind spot).

## Signals collected
- **Engine self-record** (checked FOR mechanism function, never trusted as narrative):
  gate ledger (transition + gate-evaluation records), `state/runs/<id>/`.
- **Machine ground truth** (runner cannot author): session transcript JSONL
  (`~/.claude/projects/…`), work-tree git log, Guardian hook activity.

## Open precondition (blocks Session 1)
Whether a plain `claude` session can *drive* the lifecycle here — the `uacp_*` governed
writers were **not present** in this design session. Session 1 needs the UACP plugin/MCP
live, or must drive the phase-skill scripts directly. Resolve before the first run.

## NOT in scope (deferred — see prior-art.md)
Content conformance (coverage/containment), semantic fidelity / re-derivation, signed
receipts, LTL templates, live Tier-1 monitor.

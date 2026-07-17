# self-diagnosis — prior art (filed reference)

> Reference only. This is the sophisticated end of the design space, kept here so v1
> can stay simple. **v1 does not implement any of this** — see `v1.md` (to be written).
> Both sources below are 2026 pre-prints; **neither ships usable code**. We lift
> patterns and algorithms, not packages.

## What self-diagnosis is (one line)

Runtime verification of a governed agent run against its own claims + UACP invariants:
the runner leaves a machine trail; an **independent** party deterministically checks
whether the run's *claimed account* is corroborated by the trail. Conformance, not
correctness. `correctness ≠ conformance`.

The field's names for this: **runtime verification** (formal-methods lineage) /
**trajectory conformance evaluation** (agent-eval lineage). "self-diagnosis" is our
informal handle; the guarantee word is **conformance**.

## The one result that settles the oracle debate

AgentVerify benchmarked four verifiers on the same agent traces:

| verifier | accuracy |
|---|---|
| Monolithic **neural** verifier (LLM judging LLM output directly) | **13.33%** |
| Runtime monitor **without** temporal logic | 46.67% |
| Monolithic contract verification | 80.00% |
| **Formal verification of observable control flow** | **86.67%** |

→ Empirical proof of the rule: **the oracle must deterministically read the machine
record; an LLM-as-judge is useless here.** The agent (which may be wrong) never authors
the verdict. This is the single most important external validation.

---

## Source 1 — NabaOS, "Practical Hallucination Detection for AI Agents" (arXiv 2603.10060)

The *problem* match: "agent claimed X, the tool actually did Y."

### Receipt mechanism — the most liftable idea
Every tool execution emits a signed **receipt**:
`{tool, input_hash, output_hash, result_count, facts, timestamp, HMAC-signature}`.
Verifier corroborates a claim by receipt-ID lookup + signature check.
Key primitive: *"any claim referencing a non-existent receipt ID is immediately
detectable as a fabricated tool call."*
→ **UACP mapping:** governed writers + Guardian hooks + Heartgate already are the choke
points; have each emit a receipt. (Growth-path; v1 uses plain artifact/ledger existence,
no crypto.)

### 6-type taxonomy → UACP claim-failure categories
| NabaOS type | detection | UACP self-diagnosis check |
|---|---|---|
| Fabricated Tool Call | receipt-ID lookup | claims a gate/writer ran, no ledger/receipt |
| Count Mismatch | compare `result_count` | claims N artifacts, trail shows M |
| Fact Mismatch | compare `facts` | claims gate=PASS, ledger=FAIL |
| Inference-as-Fact | LLM self-tag (weak) | judgment presented as gate verdict |
| False Absence | verify `result_count=0` | claims "clean", signals disagree |
| Source Fabrication | URL re-fetch / receipt absent | cites artifact path that doesn't exist |

4 of 6 are **pure deterministic**; only Inference-as-Fact needs LLM self-tagging and they
flag it as the weak link ("depends on the LLM honestly reporting"). → Deterministic core
is trustworthy; anything relying on the agent's self-report is low-confidence, quarantine it.

### Measuring the diagnoser itself
NyayaVerifyBench = **1,200 injected-hallucination scenarios + 600 clean controls**;
reported 91% detection / 4% false-positive / +12ms / $0. → Template for our planted-fault
test set: inject known defects, measure recall; run clean controls, measure false-positive.

### Honesty (threat-model exclusions to inherit)
Receipts verify **grounding, not correctness**: compromised tools pass receipt checks;
"only verifies grounding, not logical validity." Self-diagnosis proves the run didn't
*lie*; it does not prove the run was *right*.

---

## Source 2 — AgentVerify, "Compositional Formal Verification … via LTL Model Checking" (preprints 202604.1029)

The *architecture* match.

### Two-tier hybrid = our live-supervisor + peer-viewer split, validated
- **Tier 1 — online runtime monitor:** O(1)-per-event FSM over safety-critical invariants;
  can intervene (pause / request human) on violation. = the dumb live supervisor catching
  deadlock/violation in-flight.
- **Tier 2 — offline post-hoc analyzer:** exhaustive Büchi-automaton audit of the complete
  trace. = the independent peer shell auditing the whole run after.
- **L4 caution:** bounded-horizon live monitors miss violations spanning > k steps → the
  post-hoc tier is load-bearing; the live monitor is only a safety net.

### Instrumentation = UACP hooks, confirmed
*"orchestration framework instrumented via lightweight hooks to emit a timestamped event
stream … no modification of the LLM … <0.5% overhead."* = Guardian PreToolUse/PostToolUse
tap. The event stream is the independent machine record.

### State abstraction α: Event→S
Deterministic function mapping raw events → discrete states = our "comprehend" step.
Their **L2 limitation**: α needs manual per-framework engineering. **UACP is easier** —
lifecycle states (TRIAGE→…→RESOLVE) and gate names are already defined, so most of α is given.

### Invariant-response template + monitor algorithm (liftable pseudocode)
Workhorse form `□(p → ◯q)` via obligation/fulfilment tokens: on `p`, create obligation
`⟨p, q, deadline⟩`; discharge when `q` holds; violation when deadline passes.
Their 23 parameterized LTL templates → **our invariant library = AGENTS.md's 5 Key
Invariants as templates**:
- `□(claim_done → ◊ evidence_receipt_exists)` — Invariant #5 (evidence must be produced)
- `□(¬ write_to_main)` — Invariant #2 (no main writes)
- `□(transition → gate_passed_before)` — Heartgate
- `□(governed_state_write → via_governed_writer)` — Invariant #3

---

## Convergent design (both agree — highest confidence)

1. Instrument the **orchestration boundary** (hooks); never modify the model.
2. Verify the **observable control flow deterministically**; never via LLM judge (13% vs 87%).
3. **Ground every claim in a receipt/event**; a claim with no backing event = fabrication, O(1).
4. **Two tiers**: cheap live monitor (can pause) + deep post-hoc audit (exhaustive).
5. Express checks as **parameterized invariant templates**.
6. **Measure the verifier** with a planted-fault benchmark (injected + clean controls).

## Lift vs build vs ours

- **Lift:** receipt structure, 6-type taxonomy, invariant-response monitor algorithm,
  two-tier split, planted-fault benchmark, the LLM-judge-fails evidence.
- **Build (UACP-specific):** α from hook+transcript events → lifecycle states; invariant
  library = 5 Key Invariants as `□(p→◯q)`; receipt emission in governed writers / Heartgate
  / Guardian; the **handoff manifest as the claim source**.
- **Ours (neither paper does it):** both check *fixed* safety properties. We check against
  **invariants + the run's own claimed account** (the handoff manifest as the spec-to-refute).
  That is what makes it *self*-diagnosis rather than generic runtime verification.

## Sources
- NabaOS — arXiv 2603.10060 (`arxiv.org/html/2603.10060v1`)
- AgentVerify — preprints.org 202604.1029

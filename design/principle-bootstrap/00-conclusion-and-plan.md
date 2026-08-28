---
type: analysis
title: "UACP grounding gap — conclusion & fix plan"
description: "The consolidated diagnosis — UACP kept governance's structure from Trustless but severed the grounding, so every phase measures the declaration, not reality or purpose — and the ordered fix plan anchored by a bootstrap-born PRINCIPLE.md."
tags: [grounded-governance, diagnosis, trustless, telos, plan, analysis]
timestamp: 2026-08-17
edges: []
---
# UACP grounding gap — conclusion & fix plan

From the Trustless-ACP vs UACP investigation (4 parallel gate investigators, 2026-08). Trustless ACP is UACP's parent. This is the consolidated issue + plan.

---

## The issue, in one sentence

**UACP inherited the *structure* of governance from Trustless but severed the *grounding*: every phase measures the declaration, never reality or purpose — and in case after case the reality tool is already present, just not wired to a mandatory gate.**

## The evidence, one layer at a time

Two layers exist for any check: **advisory** (an expert persona a reviewer may run) and **deterministic/mandatory** (a gate wired into the pipeline that fails closed).

- On the **advisory** layer UACP is *equal or richer* than Trustless (broader personas: security, compliance-with-residency, resilience, concurrency).
- On the **mandatory** layer UACP's fail-closed gates are **all structural** — did you write the artifact, is the transition coherent, is a check present. **None is keyed to reality or to any quality dimension.** The selector that would route the personas is literally `implementation_status: not_runtime_active`.

The same signature repeats at every phase — and three times the tool exists and only the mandate is missing:

| Phase | Trustless grounds against reality by… | UACP has the tool… | Gap |
|---|---|---|---|
| Triage | inspecting **live code (LSP) + the running cluster** before scoring | **Serena/LSP is bundled AND conduct-enforced** (CLAUDE.md "lead with LSP") | not a **gate** — triage grounds against the request package |
| Propose | a *mandatory* Code-Feasibility reviewer that opens the real files | — | no mandate to inspect the real code |
| Verify (run it) | Gate 0: boot real infra, run migrations as prod user; **INCONCLUSIVE blocks** | `behavior_plane.py` — a real subprocess runner, **built** | not mandatory; selector off; paper-pass explicitly sanctioned |
| Verify (external) | Gate 2: **mandatory, coordinator-excluded, pull-grounded** reviewer | a design (`council-reviewer-independence`) naming "self-attestation by proxy", **written** | teeth deferred; external review collapsed to a conditional council seat |
| Dimensions | mandatory gates keyed to security / deploy / a11y | rich personas | behind the `not_runtime_active` off-switch; zero dimension-keyed fail-closed gate |

**Fair note (not all worse):** UACP moved the *structural* gate grammar into code with a fail-closed loader + a replay engine that re-runs checks — genuinely *stronger* than Trustless's prose invariants. It also has better external-reviewer containment rails. The machinery to enforce is there; it's aimed only at structure.

## The ceiling — the piece above the root

There is no **PRINCIPLE.md**: a per-project statement of *what the project is trying to achieve* (distinct from roadmap/product/policy/standard — pure "toward-what"). Without it the conformance loop has **no top**: "does realized reality match declared intent?" bottoms out at each *task's* local intent, with nothing above to say whether a coherent run is even aimed right. (This is the drift we hit repeatedly — locally coherent, globally pointless, nothing to catch it.)

**PRINCIPLE.md is born at bootstrap**, from two dimensions reconciled:
1. **What the repo *is*** — evidence read from the project (dirs, manifests, code, history).
2. **What the engineer *intends*** — their stated purpose.

`comprehend` both → `measure` = reconcile them (a mismatch is itself the first finding) → `serialize` as a **user-agreed** PRINCIPLE.md. It then becomes the *source that derives obligations* — not a poster on the wall (or it rots like every other unwired doc).

## Blind spots in BOTH systems (new capability, not restoration)

Neither Trustless nor UACP checks: **supply-chain / SBOM / dependency-CVE**, **dormant-alert wiring** (will a new failure path's alert actually fire — the #530 class), **license compatibility**, **performance-regression gate**, **cost/token budget gate**, **mechanical secret-scanning**.

## A cross-cutting issue — presentation

Phase returns (and the agent's output generally) are anchored to the *producer's* context, not the *recipient's* frame: they reference reasoning/findings the user can't see and often hand no followable action. Same inner-vs-outer disease, one layer up. UACP has a presentation contract but it's advisory prose, weak on two rules: **(1) ground in the recipient's frame — no context only the producer holds; (2) always hand a followable handle (decision/question/action).**

---

## The plan

The unifying fix: **restore grounding as mandatory gates — mostly by WIRING tooling UACP already has — anchored at the top by a bootstrap-born PRINCIPLE.md.** Ordered by dependency:

1. **PRINCIPLE.md at bootstrap (the anchor — first).** Bootstrap comprehends the repo + collects engineer intent → proposes → user agrees. Becomes the root that later phases ground against and derive obligations from. *This is also the fix to the weeks-old bootstrap gap: init's most important output is the agreed PRINCIPLE.md, not just `.uacp/` dirs.*
2. **Reality-grounding gates by wiring existing tools:**
   - **Triage/Propose:** a mandatory **LSP/Serena-grounded scope** check — the tool is already present and conduct-enforced; make it a *gate* (scope must be verified against live code, not asserted from the request).
   - **Verify:** a mandatory **reality gate** — derive the requirement from declared side-effects (not agent self-classification), wire `behavior_plane.py`, add an **INCONCLUSIVE-blocks-resolve** verdict, and **forbid the sanctioned paper-pass** for a reality-required target.
   - **Verify:** promote the external reviewer to **mandatory + coordinator-excluded + pull-grounded** (build the shelved `council-reviewer-independence` design).
3. **Dimensional gates:** flip `not_runtime_active` so personas route as **mandatory gates keyed to declared risk**, with the risk derived from PRINCIPLE.md + declared side-effects (a "handle money" principle auto-mandates the security/deploy seats).
4. **New blind-spot scans:** supply-chain, secrets, dormant-alerts (new capability — likely a separate track).
5. **Presentation contract:** encode the two rules above and enforce them, not as prose.

**How the already-filed issues fold in:** #163 (fixpoint loop / re-review-after-fix) and the system-gap-review finding are *facets* of step 2 — they are "measure against reality including the fix." #164 (scope work-product surface) and #165 (kernel gaps) are enabling fixes underneath. The frame above subsumes them; they don't need to be separate efforts.

## The one decision this plan needs from the operator

Sequencing. Three defensible first moves:
- **PRINCIPLE.md first** (it's the anchor everything grounds against; also unblocks bootstrap on real projects like trustless/cortex).
- **The reality gate first** (biggest single drop; the runner already exists; most immediate teeth).
- **The whole thing as one "grounded governance" design bundle**, then build in the above order.

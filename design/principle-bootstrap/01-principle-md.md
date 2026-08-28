---
type: design
title: "PRINCIPLE.md — the project telos: born at bootstrap, injected, derived-from by the gates"
description: "What PRINCIPLE.md is (the per-project toward-what, distinct from roadmap/product/policy/persona), how it is born at bootstrap via CMS-on-implementation, its one-neutral-mechanism injection (two axes = two workspace roots), and how it gets teeth."
tags: [grounded-governance, principle, telos, bootstrap, injection, design]
timestamp: 2026-08-17
edges: [{dst: 00-conclusion-and-plan, rel: depends_on, provenance: derived}]
---
# PRINCIPLE.md — the project telos: born at bootstrap, injected at two axes, derived-from by the gates

Node 01 of `grounded-governance`. Leads the build sequence (operator chose PRINCIPLE.md first). Depends on `00-conclusion-and-plan.md` for the diagnosis. Design altitude — build detail is deliberately deferred to the open questions, not pre-resolved.

## 1. What it is (and what it is not)

`PRINCIPLE.md` is the per-project statement of **what the project is trying to achieve** — pure *toward-what*. It is the **top of the conformance loop**: the outermost declared intent that every lower intent (task, proposal, plan) grounds against. Today the loop has no top — *"does realized reality match declared intent?"* bottoms out at each task's local intent, so a locally-coherent run can be globally pointless and nothing catches it.

It is distinct from every neighbouring artifact — this distinction is the whole point:

| Artifact | Answers | This is |
|---|---|---|
| **KERNEL.md / persona** | how the *agent entity* exists/behaves | per-agent, portable conduct |
| project.md / product.md / roadmap | *what* is being built | plan / foresight |
| standard / policy / contribution | *how* / by what rules | constraints |
| **PRINCIPLE.md** | *what this project is for* | **the principal — none of the above** |

Form: markdown + frontmatter, read at runtime, hot-reloadable — consistent with the external-data-file convention (personas/config live as runtime-read markdown, never hardcoded). It is **not** a policy, a standard, or a restriction.

## 2. How it is born — at bootstrap (a phase UACP does not yet have)

Verified this session: UACP has **no init/bootstrap skill** and **no project-principle artifact** at all. So bootstrap is new, and its **most important output is the agreed PRINCIPLE.md** — not the `.uacp/` directories.

Birth is comprehend → measure → serialize at the *project* grain:

1. **Comprehend — two dimensions:**
   - **What the repo *is*** — evidence read from the project: structure, manifests, code (via the bundled LSP/Serena), history, existing docs.
   - **What the engineer *intends*** — their stated purpose, elicited.
2. **Measure — reconcile the two.** They may disagree. A mismatch (evidence reads *payments system*, engineer says *throwaway prototype*) is **itself the first governed finding**, surfaced at bootstrap rather than discovered later as drift.
3. **Serialize — a user-agreed PRINCIPLE.md with provenance** (which evidence, which stated intent it derived from). **User-agreement is the gate on dimension 2** — the human anchor. UACP *proposes* from the evidence; the engineer *corrects/confirms*. It is not authored by fiat on either side.

## 3. Injection — one neutral mechanism (detail in node 03)

**The injection surface is the runtime-neutral `UACP.md` payload, not `CLAUDE.md`** — `CLAUDE.md` is Claude-Code-specific, and hanging a UACP feature off it platform-locks it (Kimi/opencode use their own native files). One source of truth per project — its `PRINCIPLE.md` — appended as a labelled section to the injected `UACP.md` cognition payload by the platform's session-start hook.

The **two axes are two values of the workspace root** the hook already resolves, not two mechanisms:
- **Axis 1 — developing a repo directly** (UACP itself, here): `ws_root == plugin_root`, so the hook appends the repo's *own* PRINCIPLE.md.
- **Axis 2 — installed UACP governing a foreign project** (`UACP_HOME` governs a `UACP_ROOT`): `ws_root != plugin_root`, so the hook appends *that project's* PRINCIPLE.md.

Same code, correct principal *by construction* — the axes cannot cross-contaminate. Maps onto the two-roots split (HOME vs ROOT). The trade (injection now depends on the hook being active; each non-Claude runtime needs its own session-start hook) is in node 03.

## 4. How it gets teeth (or it rots like every other unwired doc)

The whole `00` diagnosis is "knowledge without wiring rots." PRINCIPLE.md avoids that by being enforced **two ways — the same dual UACP already uses for CMS** (architectural + cognition):

- **In cognition** — injected (§3), so the agent *carries* the purpose and can self-check direction, not just conduct.
- **In architecture** — the **source the gates derive obligations from**:
  - **Triage** grounds the *delta* against it — *does this work serve the stated purpose?* Zero-alignment is a refusal, not a low score.
  - The **external/alignment reviewer** aligns each realized change to it (mirrors Trustless's Constitution → mandatory compliance gate).
  - **Dimensional mandates are derived from it** — a *"handle money safely"* principle auto-mandates the security/deploy reviewer seats. This is what flips the dimensional selector from `not_runtime_active`/self-classified to **principle-derived and mandatory**.

## 5. Scope of this node

- **In:** the artifact, its bootstrap birth, the two-axis injection, and the derive-obligations *contract*.
- **Deferred to later nodes / the plan sequence:** the actual gate wiring (reality gate, external-reviewer independence, dimensional selector flip) — those *consume* PRINCIPLE.md but are separate builds. This node makes the anchor exist; the others hang teeth on it.

## 6. Open questions for red-pen (not pre-resolved on purpose)

> **Resolved 2026-08-17 by live derivation** (proof: `02-uacp-principle-draft.md` → agreed `PRINCIPLE.md`). Running CMS on a real project (UACP itself) settled the two hardest questions below:
> - **Q1 (elicitation):** the method is **infer-first** — comprehend the *implementation* (it is the answer); the engineer *confirms/corrects* and supplies only the **forward vector** (intent where it outruns built reality). Not an interview from scratch.
> - **Q5 (measurability):** no new framework — the measurement **is** CMS's measure step, grounded on the code. The human act reduces to confirming direction, not inventing metrics.
> Q2 (staleness/versioning), Q3 (granularity), Q4 (agreement authority) remain open.

1. **Elicitation balance** — how much does bootstrap *infer* vs *ask*? Propose-then-confirm keeps human cost low but risks anchoring the engineer to our guess. What's the minimum viable interview? *(Resolved above: infer-first, human supplies the forward vector.)*
2. **Re-derivation / staleness** — the project evolves; a stale principle is a *wrong* north-star. Does bootstrap re-run on drift? Is PRINCIPLE.md versioned, and does a change to it require re-agreement?
3. **Granularity** — one PRINCIPLE.md per repo, or per package in a monorepo? Does a sub-system inherit or override the root principal?
4. **Agreement authority** — in a team, whose sign-off constitutes "user-agreed"? Is the agreement itself a governed, provenanced record?
5. **Measurability floor** — a principle is abstract. Is "does this serve the purpose?" reviewer-judgment only (semantic), or do we require the principal to *name* concrete invariants so the derivation in §4 is mechanical, not a second act of interpretation?

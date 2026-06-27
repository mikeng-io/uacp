---
type: design
title: The Council Method — the generative gate run as a panel
description: >-
  The council is the generative gate run as a panel. ENUMERATE / ASSIGN-one-verifier /
  DIVERSE-LENS already exist as uacp-council's finding-driven mode + tiers + cross-provider
  panel — so this node narrows to the genuine delta: the adversarial DEFAULT-TO-REFUTE +
  MAJORITY-CLEAR decision rule, and serializing the panel's verdicts into the investigation
  ledger.
tags: [verification, council, adversarial, default-to-refute, generative-gate]
timestamp: 2026-06-24
edges:
  - {dst: 10-generative-gate, rel: depends_on, provenance: derived}
  - {dst: 13-investigation-ledger, rel: depends_on, provenance: derived}
---

# The Council Method

## The frame

The council **is the [generative gate](10-generative-gate.md) run as a panel**, not a separate mechanism. Its job is the gate's job — comprehend the artifact, measure it against checks generated from the content, serialize the verdicts — done by several verifiers instead of one. So "designing a council method" is not designing council infrastructure: most of that already exists. It is naming the **one discipline the panel form adds** on top of the gate, and wiring the panel's output into the [investigation ledger](13-investigation-ledger.md).

## Already built — reference, do not re-describe

The panel mechanics this node used to specify are now the as-built `uacp-council` (the unified, tier-parameterized skill — `task_type` selects the authority profile; it replaced the historical separate agent/runtime/deep councils):

- **ENUMERATE targets → ASSIGN one verifier per target** is `uacp-council`'s **finding-driven mode** (`skills/uacp-council/references/finding-driven-mode.md`): each finding becomes one verification target, run through up to four structural checks — resolution / regression / design-drift / fix-interaction. Structural coverage (closes the #503 class-D miss) is already its contract.
- **DIVERSE LENS** is the **cross-provider panel** (`skills/uacp-council/references/phase-4-dispatch.md`): Tier 2/3 dispatch distinct runtimes (codex / gemini / kimi) and surface cross-runtime-confirmed findings. This is the diverse lens *and* the external-reviewer requirement — already satisfied, not net-new.
- **Severity tiers** are `skills/code-review`'s `[blocking]` / `[important]` / `[nit]` (note: it lives at `skills/code-review/`, it is not vendored). The council references it (one-directional, ADR-0017); it does not copy it.

## The delta — what the panel form actually adds

Two things, neither present in `uacp-council` today (confirmed: no `refute` / `adversarial` / `majority` anywhere in the skill).

1. **DEFAULT-TO-REFUTE + MAJORITY-CLEAR.** A panel that "re-reads and opines" is the human-judgment form of #503's weak proxy — N reviewers nodding is not stronger than one. So invert the default: each verifier's task is to **refute** the claim under test, and a target **clears only on a majority that fails to refute it**. Agreement has to be *earned against attack*, not assumed from a quiet read. This is the only decision rule the panel form contributes — the gate's per-check measure stays the same; what changes is how multiple measures of the *same* target compose into a verdict.

2. **SERIALIZE verdicts into the investigation ledger.** The panel emits findings (planes separation: council is a verification *body*, never a state database — it never writes phase state). Its verdicts — target, lens, refuted/cleared, the majority that decided — serialize into the [investigation ledger](13-investigation-ledger.md) with provenance, so the panel run is replayable and auditable rather than a one-off prose opinion.

## Reasonable UPDATE (optional)

Map `code-review`'s severity tiers onto the gate's outcomes: `[blocking]` → gate **BLOCK**, `[important]` → **warn**, `[nit]` → **note**. This is a small alignment of two existing vocabularies, not new machinery — keep it an UPDATE to the gate's verdict mapping, decided in BUILD.

## To expand

- Panel sizing (verifiers per target by risk/phase), tied to the harness's adaptive depth — `finding-driven-mode.md` already hoists the Integration Checker by tier; the refute-panel size rides the same dial.
- Quorum edge cases for MAJORITY-CLEAR (ties, single-verifier targets, abstentions on out-of-domain lenses).

---

**Summary of changes**
1. Narrowed the node to its real net-new delta — DEFAULT-TO-REFUTE + MAJORITY-CLEAR and serialize-verdicts-into-the-investigation-ledger (node 13, now an edge); cut the re-described ENUMERATE / ASSIGN / DIVERSE-LENS scaffolding and converted it to references against the as-built finding-driven mode + cross-provider panel.
2. Fixed inaccuracies — dropped "vendored" for `skills/code-review` (it is not vendored), dropped the stale two-target framing of `uacp-council`/`uacp-debate` (now one unified tier-parameterized skill), and reframed the node as "the council is the generative gate run as a panel."
3. Reframed the `code-review` severity tiers as an optional gate-mapping UPDATE rather than an adoption, and updated frontmatter (timestamp 2026-06-24, new description/tags, serializes_into edge to node 13).

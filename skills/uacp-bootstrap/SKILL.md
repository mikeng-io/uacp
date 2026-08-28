---
name: uacp-bootstrap
description: >
  Derive and agree a project's PRINCIPLE.md — its telos, what the project is trying to achieve — by
  running comprehend→measure→serialize on the IMPLEMENTATION. Use when onboarding UACP onto an
  existing project that has no PRINCIPLE.md (the session-start hook auto-surfaces the prompt), or when
  re-deriving after the project has drifted from its agreed principle. Produces a user-agreed
  PRINCIPLE.md at the project root plus a governed uacp.principle_agreement provenance node. NOT a
  lifecycle phase and NOT a roadmap/product/policy/standard — the principal only.
kind: orchestration
authority_source: "runtime-adapters/claude/inject_uacp_md.py (the neutral injection surface that carries PRINCIPLE.md); engines/domain/layout.py + engines/domain/schema.py (the uacp.principle_agreement governed kind + its content-hash binding)"
---
# UACP Bootstrap — derive & agree the project's PRINCIPLE.md

Bootstrap gives a governed project its **top**: `PRINCIPLE.md`, the outermost declared intent every
later phase grounds against. UACP's conformance loop asks *"does realized reality match declared
intent?"* — without a stated project telos that loop has no ceiling, so a locally-coherent run can be
globally pointless and nothing catches it. This skill produces that ceiling.

`PRINCIPLE.md` is the project's **toward-what** — pure purpose. It is **not** a roadmap or product
description (*what* is built), **not** a policy/standard/contribution guide (*how* / rules), and
**not** a KERNEL/persona file (how the *agent* behaves). None of those substitute for it.

## When to use

- **Onboarding:** a governed project (`.uacp/` present) has no `PRINCIPLE.md`. The session-start hook
  (`inject_uacp_md.py`) surfaces an advisory nudge; run this skill to answer it.
- **Re-derivation:** the implementation has drifted from the agreed principal; re-run to propose a new
  version (which requires fresh agreement).

## The method — comprehend → measure → serialize, on the implementation

**The existing implementation IS the answer.** Do not interview the engineer from scratch; infer the
principle from what the code actually does, then have the engineer confirm and supply the one thing
code cannot give — the forward vector.

### 0. Open the run FIRST — before reading anything

Open the governed run at the **start**, not at the serialize step:

```
uacp_run_init(initial_phase="brainstorm", reason="derive PRINCIPLE.md for <project>",
              authority_artifact="<the onboarding request>")
```

**Why before the sweep, not after it.** A whole-project comprehension sweep, a derived principle, and
an engineer agreement are not trivial work; opening the run only to carry the final provenance write
would put all of it outside governance, where it produces no proposal, no plan, and no verification
evidence — and the one artifact that governs everything afterwards would be the least evidenced thing
in the repo. Invariant #1 is TRIAGE-first for exactly this reason, and BRAINSTORM is the documented
phase for exploration that *precedes* TRIAGE (`brainstorm->triage` is a canonical transition; it does
not skip TRIAGE, it feeds it). Bootstrap is that shape: steps 1–3 are exploration, and step 4 is the
governed deliverable. So the derivation runs **inside** `brainstorm`, and the serialize step happens
after a real `brainstorm->triage` transition.

This corrects an earlier reading of "bootstrap is pre-governance" that treated the run as a mere
vehicle for one write. Bootstrap precedes the *project's* governed work; it is not exempt from
governance itself.

### 1. Comprehend — read the running reality (implementation-first)

Run a fan-out of read-only comprehension over the project, **grounding on the implementation, not the
prose docs** (treat `README`/design docs as *claims to verify against the code*). Cover, in parallel:

- **entrypoints / kernel** — what the core actually does and enforces;
- **config as-wired** — what is mandatory/enforced vs inert/deferred (a rule in a file that nothing
  loads is aspirational, not achieved reality — say so);
- **tests** — what behavior is actually pinned (the guaranteed reality);
- **git trajectory** — what the project actually invested in and rebuilt.

**Scale rule:** size the sweep to the project — a handful of readers for a large codebase, a single
comprehension pass for a small one. `log()` what you did not cover; never let a bounded sweep read as
"covered everything."

### 2. Measure — reduce to a proposed principle, grounded in mechanisms

Reconcile the readers into ONE proposed principle. Every claim must bind to a mechanism you read
(cite it). Produce three parts:

- **the statement** — one sentence: what the project manufactures / is for;
- **the sacred invariants** — what the code treats as non-negotiable (each grounded in a mechanism);
- **the frontier** — where the *built* reality falls short of the *intended* one (the honest gap).

If the engineer's stated intent and the implementation **disagree**, that mismatch is **the first
finding** — surface it, do not paper over it.

### 3. Propose & agree — the human supplies the forward vector

Present the proposed principal to the engineer. They **confirm or correct** the statement and
invariants, and **supply the forward vector** — the intended direction where it outruns the built
reality (the "and when"). **Agreement is the gate.** Do not serialize an un-agreed principal.

### 4. Serialize — the file + the governed agreement

- Write **`PRINCIPLE.md` at the project root** (a normal work-product file — the project's own, like
  its `AGENTS.md`). Use the template below; set `status: agreed`.
- Close out BRAINSTORM the way the phase actually exits — the gate is structural, not a formality:
  1. `uacp_entity_write(kind="uacp.brainstorm_scope_package", ...)`, which the brainstorm-exit
     invariant globs at `brainstorm/{run_id}/07-scope-package.yaml`. For a bootstrap the scope
     package is already in hand: `in_scope` = what the sweep actually covered (and, per the scale
     rule, what it did not), `routing_advisory` = `standard`.
  2. `uacp_run_transition("brainstorm" -> "triage")`. Without step 1 this transition is **refused**;
     the exploration is done, and the deliverable below is not exploration.
- Record a **governed provenance node** so the agreement is auditable, not a vibe:
  `uacp_entity_write(kind="uacp.principle_agreement", fields={...})` — inside the run opened at step
  0, which is what satisfies the writer's run-context requirement (the K2/#164 gap). Close with
  **`uacp_run_abort` passing `disposition: direct`** (a deliberate close — NOT the default
  `abandoned`, which would misrecord the completed agreement's run as abandoned work). Do NOT
  `uacp_run_finalize` (finalize is allowlisted only in `resolve`; a bootstrap run rests in
  `triage`, and finalize refuses a non-terminal phase). Fields: `principle_path`, **`principle_content_sha256`**
  (the SHA-256 of the exact PRINCIPLE.md bytes — the *falsifiable* binding: if the file is later
  edited, its live hash no longer matches and the stale agreement is detectable), `agreed_by`,
  `agreed_at`, `derived_from`.

## Output templates

**`PRINCIPLE.md`** (project root):

```markdown
---
name: <project>-principle
kind: principle
status: agreed
derived_from: implementation-first
evidence_base: [ <the readers / files the derivation grounded on> ]
---
# PRINCIPLE — <Project>

> **<one-sentence statement: what this project is trying to achieve>**

## What holding this principle commits the project to
1. <sacred invariant, grounded in a mechanism>
   …

## The frontier — where intended reality exceeds built reality
<the honest gap + the engineer-confirmed forward vector>
```

**`uacp.principle_agreement`** (governed node) fields:

```yaml
principle_path: "PRINCIPLE.md"
principle_content_sha256: "<sha-256 hex of PRINCIPLE.md's bytes>"   # REQUIRED — the falsifiable binding
agreed_by: "<operator id>"
agreed_at: "<timestamp>"
derived_from: "<the derivation record / evidence>"
```

## How the principal is consumed (do not re-implement here)

Once written, `PRINCIPLE.md` is injected into every session by the **neutral** session-start hook
(`inject_uacp_md.py`), read from the workspace root — the same surface that carries `UACP.md`, fenced
as untrusted project-supplied content. It is **not** wired into `CLAUDE.md` (platform-specific). The
two axes (developing a repo directly vs an installed UACP governing a foreign project) are just two
values of the workspace root the hook already resolves; this skill only *produces* the file, it does
not inject it.

## Scope & limits (this layer)

Grounding is **cognition-only** in this layer: the principal is *injected* so the agent carries the
project's purpose, but **no gate yet DERIVES OBLIGATIONS from it** — triage does not yet ground its
delta against the telos, the reviewer does not yet align to it, and dimensional mandates are not yet
derived from it. Those *teeth* are the deferred next layer. Do not claim a run is "grounded against
the principle" on the strength of injection alone.

## Rules

- Implementation-first: the code grounds the principle; the engineer confirms and supplies the vector.
- No self-authored principal: the statement is *derived*, the agreement is *the engineer's*.
- A drift between implementation and stated intent is a finding, not something to smooth over.
- Keep `PRINCIPLE.md` concise — the whole file is injected into every session.

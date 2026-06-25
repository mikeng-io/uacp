---
kind: handoff
workstream: verification-generator
title: Capsule #3 of the verification-method initiative — the generative gate (author→freeze→replay checks)
status: active
scope:
  in: [the generative gate (design bundle nodes 10/30-34 + 11), the replay-engine/projection-arm BUILD, slice ordering]
  out: [builds #1/#2/residual-#1/F2 (already MERGED via PR #18), the Codeflair code/SCIP plane, the generator SKILL authoring (slice 1)]
attribution:
  generated_by: { agent: claude-code, model: claude-opus-4-8, runtime: cc }
  updated_at: '2026-06-25'
edges:
  - {dst: 'branch:verification-generator', rel: anchored_to, provenance: parsed}
  - {dst: 'commit:6b58a94', rel: anchored_to, provenance: parsed}      # slice 0a (replay engine + projection arm)
  - {dst: 'commit:5f454f5', rel: anchored_to, provenance: parsed}      # design council corrections
  - {dst: 'commit:c03a599', rel: anchored_to, provenance: parsed}      # design bundle (nodes 30-34)
  - {dst: 'commit:bab0fab', rel: derived_from, provenance: parsed}     # PR #18 merge: builds #1/#2/residual#1/F2
  - {dst: 'design/verification-method/10-generative-gate.md', rel: relates_to, provenance: asserted}
  - {dst: 'design/verification-method/30-assertion-model.md', rel: relates_to, provenance: asserted}
  - {dst: 'design/verification-method/34-adequacy-and-coverage.md', rel: relates_to, provenance: asserted}
  - {dst: 'verification-method-resume.md', rel: superseded_by, provenance: asserted}  # the predecessor capsule (builds #1/#2 phase)
---

# Handoff — verification-generator

## Intent
Capsule #3 of the verification-method initiative: the **generative gate**. Make an agent's
*"I verified this — it's done"* trustworthy by forcing it to author a **specific runnable check per
claimed target**, freeze it, and have the kernel **re-run it and block "done" if any check is missing,
weak, or failing**. Motivated by Trustless #503 (7 review rounds, bugs still shipped — checks were
rubber stamps). This session: designed the whole gate (council-reviewed) + built the first vertical
(the replay spine). The deeper goal is to close #503 classes **B/C/D** (the comprehend→measure
generation failures) that hardcoded checks can't.

## Decisions & rationale
- [locked] **Typed CLOSED check catalog** (`uacp.check.*`; agent SELECTS + PARAMETERIZES from content,
  never free-form code-gen) — the only way the gate stays auditable + fail-closed; free-form = the black
  box node 10 warns against.
- [locked] **Checks are registered entities projected as `check` nodes with `measured_by` edges** — so
  the gate reuses the whole registration/projection/forced-gate/Engine-Violation spine hardened this
  session, not new machinery.
- [locked] **3 layers of anti-gaming, but framed HONESTLY** — structural coverage (L1) + required-kinds
  floor (L2) + council (L3). The council corrected my overclaim: determinism only **NARROWS the
  council's surface to classification-honesty**; it does NOT make the gate "ungameable." The floor keys
  off an agent-DECLARED class; L2b (content cross-check) shrinks but does not close that; only the code
  plane (class entailed from the real symbol) closes it. **Do not re-write "can't be gamed."**
- [locked] **RELATION + artifact plane FIRST** (buildable now, binds to the manifest graph + governed
  artifacts); code/SCIP + behavioral planes designed but gated on Codeflair — a code/behavior bind
  ERROR-blocks until wired (fail-closed-until-wired), it never false-passes.
- [locked] **Build directly via TDD, NOT through a governed UACP run.** This Claude Code session has only
  UACP's SKILLS wired in (`.claude/skills` symlinks) — NOT the governed-writer tools (`uacp_entity_write`
  /`uacp_state_write`) or the Heartgate MCP. And you don't bootstrap the framework by running it through
  itself; kernel dev is plain repo software-dev (exempt from the governed-writer rule, like all session work).
- [open] **Where the replay engine binds on the FORCED path.** It is registered in `ENGINES` (so it runs
  at CLOSURE via `run_all_engines`) but is NOT in the phase-keyed `_SCOPE_CHECKS`. Deciding which
  phase-exit replays which checks (and wiring it onto the forced transition gate) is unresolved.

## Rejected / not-this
- **Free-form predicate DSL** for checks — black box; can't validate fail-closed. (→ closed catalog.)
- **Checks inline in the PIV / one check-set artifact per run** — doesn't reuse the projection +
  registration spine; coarser provenance. (→ per-check registered entities + `measured_by`.)
- **Blocking the whole gate on the Codeflair code plane** — slice 0 ships real value on RELATION/artifact
  without it. (→ slice ordering; code plane is slice 3.)
- **gemini as a council reviewer** — mike DROPPED it (2026-06-25). Cross-providers = **kimi + opencode/
  MiniMax-M3** (exact opencode id `minimax-cn-coding-plan/MiniMax-M3`; the obvious spellings 404'd).

## Open threads & watch-outs
- **The classification loophole (the residual the council led with, unanimously).** The required-kinds
  floor's target-class is agent-declared → a mislabel passes L1+L2 with a weak check. L2b + council
  shrink it; full closure needs the code plane. When building L2, do NOT claim it deterministic-closed.
- **Honest #503 scope of slice 0:** closes classes **A** (ERROR≠PASS), **D** (partial — every target has
  a check), **F** (frozen replay, no drift) + the artifact slice of **C**. It does **NOT** close **B**
  (the headline `grep route_mounted` weak-proxy → needs `symbol_resolves`, code-plane) or **E**. The
  node-10 route example is code-plane (slice 3) — say so.
- watch-out: a new `uacp.check.*` kind needs BOTH a schema in `engines/domain/schema.py` AND a layout
  `Entry` (`layout.fmt_of`/`plane_of`) — the entity-writer refuses an unknown kind BEFORE validation.
  Schema alone is not enough. (Council finding; slice 0c.)
- watch-out: `projection._project` is a HARDCODED extractor — the `uacp.check.*` arm is net-new; never
  describe checks as projecting "for free" (the exact built-vs-new dishonesty this initiative fights).
- watch-out: Pyright flags `validate_check_replay` as an unknown import after I added it (stale index) —
  the runtime import works (tests pass). Restart the LSP after structural changes.
- **Manifest integrity (carried from the merged phase):** `manifest.artifacts` — which every check/coverage
  gate trusts — was forgeable via `uacp_state_write`; FIXED in F2 (carve-out). The replay gate inherits
  that trust, so don't re-open it.
- **mike's product note (act on this):** the uacp-handoff skill currently only writes the capsule FILE;
  mike wants it to ALSO emit a **copy-pasteable RESUME PROMPT** for the user to start a fresh session.
  That belongs as a skill enhancement (a RESUME-PROMPT verb/output), tracked here.

## Now → next
- **Position:** see Anchors (branch + commits live there).
- **Next intent:** slice **0b** — the **check-coverage gate** (`GP_UNCHECKED_TARGET`): reuse this
  session's coverage pattern so every scope_item/work_unit must be `measured_by` ≥1 check (Layer 1, the
  thing that makes "prove each task" enforced). Then **0c** — the `uacp.check.*` schemas + layout Entries
  (the governed authoring path) + `obligation_satisfied`; and decide the forced-phase-gate wiring for the
  replay engine. Floor (L2/2b), council (L3), generator SKILL (slice 1), code plane (slice 3) are later.

## Anchors
- branch: `verification-generator` (off merged `main`; pushed)
- commit: `6b58a94` — slice 0a: replay engine (`validate_check_replay`, 4 kinds) + `_project` check arm; suite 1894 green
- commit: `5f454f5` — design council corrections (honesty fixes: anti-gaming framing, projection overclaim, slice-0 #503 scope)
- commit: `c03a599` — capsule #3 design bundle (nodes 30-34 + business overview)
- commit: `bab0fab` — PR #18 merged to main (builds #1/#2 + residual #1 + SC containment fix + F2)
- design: `design/verification-method/` — nodes 10 (root+overview), 30-34 (the gate build), 11 (harness), `_index.yaml`
- run: none — kernel dev, no governed UACP run (tooling not wired; see decisions)

---
type: design
title: "UACP — Claude-Code-First Hardening & Simplification (Design)"
description: "Design for making UACP provably work end-to-end under Claude Code with a behavioral E2E test harness"
tags: ["claude-code", "hardening", "testing", "simplification"]
timestamp: 2026-06-14
status: archived
---

# UACP — Claude-Code-First Hardening & Simplification (Design)

> **For Claude:** REQUIRED NEXT STEP: hand this to `superpowers:writing-plans` to produce a task-by-task implementation plan. Do not implement directly from this doc.

**Date:** 2026-06-14
**Status:** approved (brainstorm → design)

---

## Goal

Make UACP **provably work end-to-end under Claude Code**, then strip it to a single
config plus grammar-as-code, with a behavioral test harness guarding the whole
refactor — so it can be used for real work without the governance layer interrupting
that work.

## Motivation

The operator wants to use UACP at their job with Claude Code. The blocking fear:
*"I hit an error during my work and have to stop and fix the framework before I can
continue."* Two open questions drove this design:

1. How do we know it works (E2E testing)?
2. What are we missing?

### Reframe: `trustless` is not a test foundation to copy

The sibling `trustless` repo embeds its ACP *inside* a product. Everything it tests
end-to-end is the **product** (triple-entry ledger, Fabric anchoring, ZK proofs,
Postgres/Redis containers) — the control plane rode along and was never given its own
test foundation. So there is nothing to copy, and the "capabilities UACP lacks" list
derived from `trustless` (crypto state ledger, Fabric, ZK, ERC-8004) is almost all
*product*, irrelevant to a governance control plane. UACP is the first time this
control plane stands alone and needs its own proof.

### The four failure modes that "interrupt work"

Naming them *is* the design — each phase below kills specific ones.

| #  | Failure that stops work | Killed by |
|----|--------------------------|-----------|
| F1 | Guardian **false-blocks** a legit tool call | Phase 1 harness |
| F2 | Heartgate **refuses a valid transition** (gate logic / glob wrong) | Phase 1 harness |
| F3 | A **governed writer throws** on reasonable input | Phase 1 harness |
| F4 | Claude **gets lost in prose** / loops / silently skips governance | Phase 3 hook + Phase 5 smoke |

### Industry alignment (web research, 2026)

Standard agent-E2E practice = mock the LLM layer (`unittest.mock`), assert on the
**trajectory** (sequence of tool calls + resulting state artifacts), keep deterministic
checks for CI gates, reserve LLM-as-judge for nuance. UACP is unusually well-positioned:
most frameworks reconstruct the trajectory from logs, whereas **UACP already emits it as
first-class durable artifacts** (gate-ledger JSONL + state history + run manifest). The
harness just drives the real governance code with canned agent outputs and asserts on
those files.

### Config finding (load-bearing vs ceremony)

Of 15 config files (~4,000 lines), the **kernel code loads only 5**
(`guardian-policy`, `phase-transitions` @859 lines, `artifact-schemas`,
`autonomy-policy`, `state.yaml`). The other ~10 (~2,400 lines, incl. `review-routing`
@786) are consumed — if at all — as **prose the agent interprets loosely**. A config
only an agent reads is interpreted loosely anyway, so a 786-line "soft guidance" YAML is
pure ceremony; three clear sentences in the owning skill do the same job. The Claude
Code integration gap was also confirmed here: **no `.claude/` dir, no `settings.json`
hooks** — Guardian is not wired into the Claude Code tool-call path at all today.

---

## Locked decisions

1. **E2E scope:** both a deterministic harness and one live smoke test; **harness first
   as a safety net**, then the config diet, with the harness proving no regression.
2. **Claude Code enforcement:** build a real `PreToolUse` hook calling the existing
   Guardian Python — **gated behind the harness** proving no false-blocks.
3. **Config:** collapse 15 files → **one `config.toml` + `config.py` accessor** for all
   tunable knobs (global, shared by every skill/phase); move the framework **grammar**
   (phase graph, gates, artifact schemas) into **Python** (Pydantic + constants), where
   the kernel already half-keeps it (`VALID_TRANSITIONS` is hardcoded; `RunManifest` is
   Pydantic). Delete the prose-tier YAMLs.
4. **Reviewers:** add **Pi** ([earendil-works/pi](https://github.com/earendil-works/pi),
   print/JSON mode) as the cheap "simple verification" tier alongside Codex/Kimi.
5. **Bridges:** consolidate the 6 `bridge-*` skills into **one `uacp-bridge` skill** —
   `bridge-commons` becomes its `SKILL.md` (shared contract); each provider becomes a
   file under `providers/`. Adding Pi is then one file, not a new skill.

---

## Phased design (each phase gates the next)

### Phase 1 — Behavioral E2E harness (safety net)

- Location: `tests/e2e/`. No LLM.
- A fake-agent fixture emits canned **valid** artifacts and drives a run
  TRIAGE→PROPOSE→PLAN→EXECUTE→VERIFY→RESOLVE through the **real** Guardian, Heartgate,
  state machine, and governed writers.
- Assertions on the **trajectory UACP already emits**: gate-ledger JSONL entries in
  order; `state/runs/<id>.yaml` history shows every phase; manifest reaches `resolved`;
  no exception thrown.
- **Negative paths:** feed a deliberately-missing/invalid artifact → assert Heartgate
  **blocks with a clear reason, not a stack trace**.
- **Assert on behavior, not file paths** — so the suite survives Phase 2's config
  collapse and serves as the regression guard.
- Ship a **fixture registry** (`tests/e2e/fixtures/`) of golden artifacts (these double
  as the templates a real run produces) and a **`.github/workflows`** CI job running
  `pytest` + this harness (UACP has no CI today).
- *Kills F1–F3.*

### Phase 2 — Config collapse (harness guards it)

- 15 files → **`config.toml`** (all knobs) + **`config.py`** (typed accessor used by all
  skills/phases and the kernel).
- Move grammar into Python: phase graph + gate definitions + artifact schemas as
  Pydantic models + constants.
- Delete the ~10 prose-tier YAMLs; fold any still-needed guidance into the owning skill.
- **Harness stays green throughout** = proof nothing regressed. This is the payoff of
  the Phase 1 → Phase 2 ordering.

### Phase 3 — Claude Code enforcement hook

- `.claude/settings.json` `PreToolUse` hook → thin **`guardian_hook.py`** shim that:
  1. reads the Claude Code hook payload (tool name + input on stdin),
  2. **reconstructs Guardian context from `state/current.yaml` + the run manifest**
     (Hermes injects this inline; in Claude Code the hook reads it from state — the one
     genuinely new piece of code),
  3. calls the **existing** `Guardian.evaluate()`,
  4. emits Claude Code's block/allow decision.
- Reuses 100% of the Guardian Python. Gated behind the harness being green.
- *Makes governance real in Claude Code instead of voluntary; addresses F4.*

### Phase 4 — `bridge-pi` reviewer + bridge consolidation

- Consolidate `bridge-*` → `skills/uacp-bridge/` (`SKILL.md` = shared contract;
  `providers/{claude,codex,gemini,kimi,opencode,pi}.md`).
- Add **Pi** as the cheap "simple verification" tier: availability check (`pi --version`),
  invoke in print/JSON mode with a review prompt, parse verdict, register in reviewer
  routing (now in `config.toml`).
- **Read-only posture** for Pi enforced by prompt + throwaway/worktree (Pi has no
  `--sandbox read-only` flag and its tools include `bash`/`write`/`edit`).
- Update references in `AGENTS.md` / `CLAUDE.md` that point at old `bridge-*/SKILL.md`
  paths.

### Phase 5 — One live smoke test

- `claude -p --dangerously-skip-permissions` on a trivial safe task in a throwaway
  worktree.
- Asserts: (a) run reaches RESOLVE with **zero governance errors** in the gate ledger;
  (b) a deliberate `Write` to `main` is **blocked by the Phase 3 hook**.
- *Confirms F4 is closed end-to-end with a real agent.*

---

## Explicitly deferred (YAGNI — logged in the gap ledger)

- `bwrap` / contained-shell attestation (not implemented in UACP; not needed for use)
- Multi-run concurrency E2E
- Adaptive-gate **selection-predicate** testing (harness covers gate *enforcement*, not
  the prose that decides *which* gate applies)
- LLM-as-judge (gates are deterministic)
- Crypto state ledger / Fabric / ZK / ERC-8004 (that was `trustless` *product*)

---

## Touch-points & risks

- **`phase-transitions.yaml` @859 lines** is the riskiest thing to port to Python in
  Phase 2 — do it under the harness, one stage at a time.
- **Context reconstruction in the hook** (Phase 3) is the only net-new logic; everything
  else reuses existing kernel code.
- **`AGENTS.md` / `CLAUDE.md` / `docs/INDEX.md`** reference old config and `bridge-*`
  paths — update them in the same phase that moves the targets.
- **`config.py` is now a hard dependency** for every code path that reads config; its
  accessor API and validation must be settled early in Phase 2.

## Success criteria

- `pytest tests/e2e/` drives a full lifecycle green, in CI, in seconds.
- Config is one `config.toml` + `config.py`; grammar lives in Python; the ~10 prose
  YAMLs are gone; the harness is still green.
- A Claude Code session cannot write to `main` — the hook blocks it — and a real
  `claude -p` task reaches RESOLVE with zero governance errors.
- Pi runs as a reviewer via the unified `uacp-bridge`.

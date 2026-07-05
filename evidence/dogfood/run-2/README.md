# Dogfood run #2 — `uacp-dogfood-002` (agent-through-tools drivability evidence)

The first **real** UACP dogfood: a fresh Claude Code session (Agent B) with the UACP
plugin live drove one governed run end-to-end through the actual
`mcp__plugin_uacp_uacp__*` tools + `uacp-*` skills — **not** a scripted handler drive.
Ground-verified by an independent witness session against the run's own state files.

> Run #1 (2026-07-05) was a puppet: a Python script calling `state_machine.*` handlers
> in-process, reaching *around* the product surface. It proved nothing about real
> drivability. This is the run that did.

## Verdict
| Measure | Result | Basis (ground-verified, not self-reported) |
|---|---|---|
| **M1 — Drivability** | **PASS** | manifest `status: resolved`, `finalized_at` stamped; finalize `closure: pass`, `warnings: []`; 5 timestamped transitions triage→…→resolved |
| **M2 — Surface completeness** | **9 findings** | see below — the real payload |
| **M3 — Independence** | **PASS** | 19 governed-writer watermarks in `state/hashes.json`; no reach-around; missing-tool steps were skipped + recorded, not scripted around |

Run: `uacp-dogfood-002`, track `standard`, granularity 2. Workspace: worktree
`chore/uacp-dogfood`. Created `2026-07-05T15:59:07Z` → finalized `16:11:45Z` (~12 min live).
Work product was a 1-line test comment, left uncommitted (no-commit rule) — **this PR
contains ZERO core code changes; it is state/evidence only.**

## Contents
- `state/manifest.yaml` — the run manifest (state_history + 17 registered artifacts).
- `state/gate-ledger.jsonl` — 7 gate records, all pass (incl. `PLAN_VALIDATION` with `pv_1..pv_6` evidence + notes).
- `state/hashes.json` — 19 governed-writer content hashes (the M3 independence proof).
- `full-run-bundle.tar.gz` — the complete run (state + all 34 phase artifacts), preserved because the live `.uacp/` tree is gitignored/ephemeral.

## Findings (board #7)
Parent: **#112**. Findings: **#113** (F3 `uacp_run_registry_update` crashes on its own
documented `started_at`) · **#114** (F4 resolve/resolved schism, user-visible) · **#115**
(F5 `evidence_refs` must be node-ids) · **#116** (F6 `artifact_integrity` can't bind
`.txt`) · **#117** (proposal `title` schema/skill gap) · **#118** (checkpoint `invariants`
shape) · **#119** (F9 RESOLVE corpus steps have no governed tool) · **#120** (F10
`uv`/egg-info write_paths footgun) · **#121** (frozen checks rewritable pre-transition).

The gates that blocked B were **correct** to block; error messages named the exact defect;
corrected re-writes passed. UACP's gates work; its docs / tool-schema consistency have gaps.

## Caveat
Witnesses were **not** armed in this worktree — this measured *drivability*, not the
witness/forecast lane. A witness-armed agent-through-tools dogfood remains a separate run.

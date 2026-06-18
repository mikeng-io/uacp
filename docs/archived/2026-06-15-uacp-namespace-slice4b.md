# Config Collapse — Slice 4b (phase-transitions.yaml → code) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox tracking. THIS SLICE TOUCHES GUARDIAN/HEARTGATE ENFORCEMENT — smallest steps, heaviest review, behavior-preserving unless explicitly changing (F-T3-01).

**Goal:** Move `config/phase-transitions.yaml` (the phase graph + gates that drive Guardian Layer-B + Heartgate) into code, fix its 3 landmines (consolidate the 3 load paths behind one shim; dedup `state_machine.VALID_TRANSITIONS`; normalize adaptive gates to F-T3-01 fail-closed), and repoint the 9 `authority_source:` SKILL.md refs. Suite green after every step (baseline **432 passed, 2 skipped**).

**Scope (operator-confirmed):** codify the phase GRAPH; review-routing/gate-selection DOCTRINE stays YAML. Tier split: pure grammar (graph structure, exits_to, allowed/forbidden_tools, phase_exit_invariants, gate check-ID lists) → code; operator-TUNABLE selectors/thresholds (coherence `min_composite_granularity`, adaptive-gate `selected_when_any` risk_levels/domains, `run_registry_rule.enforcement`) → `uacp.toml` knobs. Doc-only blocks (`example_artifact`, `council_synthesis_schema` narrative) → `docs/` or delete.

**Discovery dossier (this session, Discovery A) is the detailed spec** — 14 top-level keys, every reader with file:line, the Wave staging, the two F-T3-01 gate idioms. Cross-check against it.

**Landmine facts (verified on branch):**
- 3 load paths: Heartgate `core.py:718-729` (inline `yaml.safe_load`), Hermes adapter `__init__.py:60-66` (`_phase_config`, inline), validator `validate_configs`. ONE shim already exists: `engines/io/loaders.py:201 load_phase_transitions()` (used only by `evidence_completeness`).
- `state_machine.py:42 VALID_TRANSITIONS` (5 edges, terminal=`resolved`) vs phase-transitions `exits_to` (7 edges, `resolve`→`terminal`) — DIFFERENT terminal conventions; dedup must reconcile semantics, not just import.
- F-T3-01: Pattern A (`self.config.get(key) or {}`, ~950/2015) vs Pattern B (`if not isinstance(self.config.get(key), Mapping): return`, ~1308/1339/1378 — self-DISABLE on absent). Normalize ALL to fail-closed (absent ⇒ enforce) + regression test.

---

## ✅ STATUS (SLICE 4b COMPLETE — 2026-06-16): all of T1–T6 done. T5 `43e4a1b` (repointed 7 `authority_source:` lines + 2 uacp-plan grammar anchors to the code modules + uacp.toml knobs; council_synthesis ref left for Slice 5). T6: final gate GREEN (suite **504/2**, ruff clean, residual scans clean — no inline phase-transitions load, Pattern-B self-disable gone, single-source graph). **Council (3 lenses):** enforcement auditor → PASS (enforcement identical to main modulo intended F-T3-01); F-T3-01 auditor → PASS (fix real/complete/content-independent; regression test proven via revert); devil's-advocate → CONCERNS, one MATERIAL **M-1** (asymmetric absent→enforce / explicit-empty→disable gate semantic was an undocumented foot-gun) → **RESOLVED** `59094a6` (operator-facing note in phase-transitions.yaml + decision-log entry; deferred `enabled: false` sentinel option). M-2 (validator copy `skills/scripts/` drift) → MINOR, runtime path uses the updated `scripts/` copy; folded into the Slice-5 validator dedup. Auditors corrected one premise: the 5 adaptive-gate doctrine blocks + the 2 artifact schemas were NOT slimmed (intentional — doctrine stays YAML; schemas deferred), so F-T3-01 is production-inert hardening. Branch merged --no-ff to main; suite re-verified; branch deleted.

## STATUS (2026-06-15): T1 done + merged to main (`load_phase_transitions` shim consolidation, behavior-preserving). T2-T6 deferred to a FRESH SESSION (operator decision — enforcement-grammar precision wants clean context).

## STATUS (cont. session): T3 + T4a + T4b DONE on branch `feat/config-collapse-slice4b-cont`. T3 `157da14` (graph dedup). T4a `1b18079` (deleted unconsumed transition_rule/followthrough_gate/example_artifact). T4b `202a740` (F-T3-01: 3 Pattern-B adaptive gates fail-closed + regression test + lifecycle seeding). Suite 441/2. Operator decision (this session): T4 = **FULL EMPTY** — codify all consumed grammar incl. stages tool-lists, Guardian Layer-B + Heartgate code-default fallback, fixture overhaul, slim production YAML to grammar-free. KEY FINDING: adaptive-gate `selected_when_any`/`block_when`/`required_*` are UNCONSUMED by the kernel (LLM-read doctrine) → STAY YAML, NOT codified. Remaining split: **T4c** (knobs→uacp.toml + codify plan_validation_gate/run_registry_rule/piv_rule/heartgate_coherence_required_when/Pattern-A gate grammar) → **T4d** (stages tool-lists/phase_exit_invariants + artifact_schema/council_synthesis required_fields + Guardian Layer-B fallback + T3 agreement-test update + final YAML slim) → T5 → T6.

## STATUS (T4 COMPLETE): T4c-1 `2a64d27` (coherence/run_registry/Pattern-A grammar → gate_rules.py + knobs → uacp.toml [heartgate.coherence]/[heartgate.run_registry]). T4c-2 `1c281bc` (plan_validation_gate + piv_rule → gate_rules.py, fail-closed default). T4d-1 `0dad2cb` (stages → engines/domain/phase_transitions.py with exits_to derived from phase_graph; Guardian Layer-B + Heartgate + evidence-engine fallback via loader injection; T3 agreement test updated). Suite 504/2; every wave two-stage-reviewed (spec + quality). **T4d-2 (artifact_schema + council_synthesis_schema required_fields) DEFERRED to Slice 5** — operator decision: those blocks are consumed by the 2-divergent-copy validator scheduled for dedup in Slice 5, so codify them there with one clean home (avoid double-wiring). End state of phase-transitions.yaml after Slice 4b: header + LLM-read adaptive-gate doctrine + the 2 (transitional) artifact-schema blocks. Remaining: **T5** (repoint authority_source SKILL.md refs) → **T6** (council + finish).

## (superseded) T3-first STATUS: T3 DONE on branch `feat/config-collapse-slice4b-cont` (commit `157da14`) — canonical `engines/domain/phase_graph.py`; `state_machine.VALID_TRANSITIONS`/`TERMINAL_PHASES` derive from it via a documented `resolve`→`resolved`/`terminal`-drop projection; repo-level agreement test pins all 4 representations; two-stage review (spec + quality) passed; suite 438/2. T4-T6 remain.

## REORDER NOTE (discovered during T1): **fold T2 (F-T3-01) into T4 (gate codification).** "Fail-closed on absent gate config" only makes clean sense once each gate's required-evidence lives in CODE as a default — otherwise there's nothing to enforce when config is absent. So: codify the gates with enforce-by-default behavior (T4), and F-T3-01 falls out naturally (a missing uacp.toml override cannot disable the code default). Do NOT do a standalone idiom-flip for T2. Revised order: T3 (graph dedup) → T4 (gate+invariant codification, incl. F-T3-01 fail-closed defaults + regression test) → T5 (SKILL.md authority repoints) → T6 (council + finish).

## Staging (landmines first — they de-risk the codification; each independently green + reviewed)

# Task 1: C-3 — consolidate the 3 load paths behind `load_phase_transitions()`

**Files:** `skills/uacp-core/scripts/core.py` (`Heartgate.load` ~718), `runtime-adapters/hermes/plugins/uacp_guardian/__init__.py` (`_phase_config` ~50-67). Leave the validator's `validate_configs` (multi-config loader) for now. **Behavior-preserving refactor. Opus review.**

- [ ] **Step 1:** `Heartgate.load` → use `from engines.io import load_phase_transitions`; `loaded = load_phase_transitions(root)`; on `loaded.error` raise `HeartgateError(...)` (preserve the not-found/parse error semantics); else `raw = loaded.value`. Keep everything downstream identical.
- [ ] **Step 2:** Hermes `_phase_config` → use `load_phase_transitions(policy.uacp_root)`; on error → `{}` (preserve current fail-open-Layer-B behavior + module cache). Keep the cache + the `isinstance dict` guard.
- [ ] **Step 3:** `python3 -m pytest tests/ -q` → 432/2 (behavior identical). `grep -rn 'phase-transitions.yaml' skills/uacp-core/scripts/core.py runtime-adapters/.../__init__.py` → no inline `yaml.safe_load` of it remains (the shim is the one loader). Ruff. Commit `refactor(heartgate,guardian): load phase-transitions via the single load_phase_transitions shim (C-3)`.

# Task 2: F-T3-01 — normalize adaptive gates to fail-closed + regression test

**Files:** `core.py` (the gate-entry idioms ~950/1308/1339/1378/2015/2188). Test: new. **SECURITY change — opus review, decision-log already records the intent.**

- [ ] **Step 1 (failing regression test):** for each adaptive gate, a test that with the gate's config key ABSENT, a transition requiring that gate's evidence BLOCKS (fail-closed), not silently passes. Run → some FAIL (Pattern B gates currently self-disable).
- [ ] **Step 2:** Normalize Pattern B gates (execute/verify/resolve evidence gates, `~1308/1339/1378`) so an absent/empty config key ⇒ ENFORCE (demand the gate's evidence) rather than `return` (skip). Keep Pattern A gates enforcing. Preserve behavior when the key IS present.
- [ ] **Step 3:** `python3 -m pytest tests/ -q` → green (new regression + no break; the production `config/phase-transitions.yaml` defines all keys, so present-key behavior is unchanged). Ruff. Commit `fix(heartgate): adaptive gates fail-closed on absent config (F-T3-01) + regression test`.

# Task 3: dedup `state_machine.VALID_TRANSITIONS` against the single graph

**Files:** `engines/domain` (new `phase_graph.py` — the canonical graph), `state_machine.py` (derive VALID_TRANSITIONS), `core.py` (Heartgate `_transition_allowed`/`stages` consume the same graph). **Reconcile the `resolved` vs `resolve`/`terminal` naming — opus review.**

- [ ] **Step 1:** Define the canonical phase graph in `engines/domain/phase_graph.py` (the 6 stages + exits_to, FROM phase-transitions.yaml `stages`). Decide the terminal-naming reconciliation explicitly (map state-machine `resolved` ↔ lifecycle `resolve`+`terminal`) and document it. Provide accessors both consumers need.
- [ ] **Step 2:** `state_machine.VALID_TRANSITIONS` → derive from the canonical graph (so it can't drift). Preserve its exact current edges/terminal semantics (state-machine tests must stay green) — if the canonical graph differs, reconcile carefully, NOT by weakening state-machine tests.
- [ ] **Step 3:** Heartgate `_transition_allowed`/`self.stages` → consume the canonical graph (or keep reading from the loaded phase-transitions dict, which now must agree with the canonical graph — add a consistency assertion/test). `validate_transition_config_consistency` already cross-checks exits_to vs uacp.toml; extend it to also cover the canonical graph.
- [ ] **Step 4:** suite green; add a test asserting state_machine and Heartgate agree on the graph. Ruff. Commit `refactor(state): VALID_TRANSITIONS derives from the canonical phase graph (dedup)`.

# Task 4: codify the remaining phase grammar → engines/domain; extract knobs → uacp.toml

**Files:** `engines/domain` (stages allowed/forbidden_tools, phase_exit_invariants, gate check-ID lists), `uacp.toml` (tunable selectors/thresholds), `core.py`/`loaders.py` readers, `config/phase-transitions.yaml` (slim/remove codified blocks). Doc-only blocks → docs. **Staged per dossier Waves 1-4; opus review.**

- [ ] Per the dossier's Wave classification: Wave 1 (doc-only: `example_artifact` → delete; `council_synthesis_schema`/`artifact_schema` narrative → docs or code), Wave 2 (`phase_exit_invariants`, `piv_rule`/`plan_validation_gate` check lists → typed), Wave 3 (Heartgate rule blocks), Wave 4 (adaptive gate configs — grammar→code, tunable selectors→uacp.toml). Each wave: codify → repoint reader → remove from YAML → suite green → commit. (This task may split into 4-T4a..d during execution.)
- [ ] Extract operator-tunable knobs to `uacp.toml` with human-readable comments: `[heartgate.coherence] min_composite_granularity`, adaptive-gate `selected_when_any` selectors, `run_registry_rule.enforcement`.
- [ ] After all waves: `config/phase-transitions.yaml` is grammar-free (graph+gates in code, knobs in toml). If fully consumed, mark for deletion (Slice 5) or delete if clean.

# Task 5: repoint the 9 `authority_source:` SKILL.md refs (C-3)

**Files:** `skills/uacp-{triage,propose,plan,execute,verify,resolve,state,heartgate,core}/SKILL.md`.

- [ ] Repoint each `authority_source: config/phase-transitions.yaml (mirror; config wins on conflict)` to cite the code module (e.g. `engines/domain/phase_graph.py` + the relevant uacp.toml knob sections) as the new authority. Leave historical references. Suite green.

# Task 6: final gate + council + finish branch

- [ ] Suite + ruff + residual scan (no inline phase-transitions load; VALID_TRANSITIONS derived; gates fail-closed; graph single-source). 
- [ ] **Council (3 lenses):** (1) **enforcement auditor** — Guardian Layer-B allowed_tools + Heartgate exits_to/gates behave identically to `main` (diff-test); the canonical graph matches the old YAML; no transition newly allowed/blocked except the intended F-T3-01 fail-closed. (2) **F-T3-01 auditor** — every adaptive gate fails closed on absent config; regression test real; present-key behavior unchanged. (3) **devil's advocate** — VALID_TRANSITIONS/Heartgate/graph all agree (no split-brain); knobs round-trip from uacp.toml; SKILL.md authority repoints correct; doc-only blocks relocated not lost.
- [ ] Finish branch.

---

## Self-Review
- Landmines (C-3 shim T1, F-T3-01 T2, VALID_TRANSITIONS dedup T3) FIRST — highest value, de-risk T4's codification.
- Grammar→code vs knob→uacp.toml split applied per dossier. Doctrine (review/gate) untouched.
- `resolved`/`resolve`/`terminal` naming reconciliation is the key correctness risk (T3) — explicit decision + agreement test.
- Behavior-preserving except the intended F-T3-01 fail-closed change (which only affects absent-config, a non-production case — production defines all keys).

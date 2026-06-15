# Config Collapse — Slice 4a (grammar schemas → code) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox (`- [ ]`) tracking.

**Goal:** Move the validator-enforced **schemas + enums** from `config/{artifact-schemas,evidence-clusters,state}.yaml` into Pydantic models/constants in `skills/uacp-core/scripts/engines/domain`, repoint readers, and relocate 2 operator knobs to `uacp.toml`. Leave doctrine/policy/examples as YAML (operator decision). `phase-transitions.yaml` (the phase graph + gates) is **Slice 4b** (separate branch). Suite green throughout (baseline **360 passed, 2 skipped**).

**Scope decisions (operator-confirmed):** codify ONLY real schemas/enums; **leave review-routing + gate-selection doctrine and `non_waivable_invariants` as YAML** (LLM-read doctrine / authority chain — codifying = category error). Split sequencing: 4a now, 4b later. When a schema block is codified, REMOVE it from its YAML (avoid two-source drift); keep doctrine/examples/deferred-registry blocks in place.

**Tech Stack:** Python 3.13+ (`python3`), Pydantic v2, pytest, ruff (`/Users/mike/.local/bin/ruff`, `E,F,I,UP,B`). Existing `engines/domain` already has `RunManifest`, `CurrentPointer`, `LedgerEntry`, `RunRegistry`, `Scope`, `DeferredItem`.

**Discovery dossiers (this session) are the detailed spec** — they map every reader + line. Cross-check against them.

---

# Task 1: evidence-clusters.yaml → `engines/domain/evidence_cluster.py`

**Files:** Create `skills/uacp-core/scripts/engines/domain/evidence_cluster.py`; modify `engines/domain/__init__.py`, both `scripts/validate_uacp_artifacts.py` + `skills/scripts/validate_uacp_artifacts.py` (`validate_evidence_cluster`, `VALID_CLUSTER_STATES`), `config/evidence-clusters.yaml`. Test: `tests/unit/uacp_core/test_evidence_cluster_model.py`.

- [ ] **Step 1 (TDD):** failing test asserting `ClusterState` = `{pass,warn,block,not_applicable,deferred}`, `EvidenceCluster.model_validate` accepts a valid cluster + rejects a bad `state`/missing required field, and `INVARIANT_CLUSTER_FAMILIES` contains the 7 invariant families (authority, side_effects, write_containment, privacy_safety, traceable_state, conservative_failure, handled_negative_result_followthrough).
- [ ] **Step 2:** Implement the model + `ClusterState`/`ClusterPhase` `Literal`s + `INVARIANT_CLUSTER_FAMILIES` frozenset (values FROM the YAML — read `config/evidence-clusters.yaml`). Export via `engines/domain/__init__.py`.
- [ ] **Step 3:** Repoint BOTH validator copies: replace hardcoded `VALID_CLUSTER_STATES = {...}` with `set(get_args(ClusterState))` (import from domain), and `validate_evidence_cluster` required-list/enum checks → `EvidenceCluster.model_validate` (keep the same BLOCK messages; validation errors → issues). Keep `validate_evidence_registry` (reads `evidence_domain_registry.implementation_status` — that block STAYS in YAML, deferred).
- [ ] **Step 4:** Remove the codified blocks from `config/evidence-clusters.yaml` (`cluster_states` enum, `artifact_schema` field grammar) — leave `universal_cluster_families` (doctrine), `evidence_domain_registry` (deferred), `example_artifact`. Header note: "cluster_states + artifact_schema codified in engines/domain/evidence_cluster.py (Slice 4a)."
- [ ] **Step 5:** `python3 -m pytest tests/ -q` → green; both validators `--help` OK; ruff. Commit `feat(domain): codify EvidenceCluster + ClusterState (Slice 4a)`.

# Task 2: artifact-schemas.yaml → domain models + move 2 knobs to uacp.toml

**Files:** Create `engines/domain/artifact_schema.py` (or extend existing); modify `core.py` (`_load_artifact_schemas` ~680 + 5 reader sites: `_validate_intent_doc` 1616, `_validate_scope_artifact` 1682/1735, `_tool_path_capabilities` 1808, `_validate_evidence_dispositions` 1839/1906, `_validate_lessons_artifact` 2265), `engines/scope_conformance.py` (`_load_blast_radius_enum` ~101), `config/uacp.toml` (+`[scope.tool_path_capabilities]`/`[scope.handler_refusals]`), `config/artifact-schemas.yaml`. Test: `tests/unit/uacp_core/test_artifact_schema_model.py`. **Kernel-touching → opus review.**

- [ ] **Step 1 (TDD):** failing test: `BlastRadius` enum = `{low,medium,high,critical}`; typed schema objects expose `intent`/`scope`/`lessons`/`evidence_disposition` (`required_for_transition`, `path_template`, `required_fields`/`required_sections`) matching the YAML values.
- [ ] **Step 2:** Implement Pydantic models (`BlastRadius` enum + `TransitionArtifactSchema` base + the 4 typed schemas). Values FROM `config/artifact-schemas.yaml`. Export via domain `__init__`.
- [ ] **Step 3:** Repoint `_load_artifact_schemas` to build typed objects (or a typed accessor) and the 5 Heartgate call sites to typed-attribute access. Repoint `scope_conformance._load_blast_radius_enum` to the `BlastRadius` enum (drop the `_FALLBACK_BLAST_RADIUS` + the live YAML read). Keep behavior identical (same blockers/messages).
- [ ] **Step 4:** Move the 2 OPERATOR KNOBS to `uacp.toml` (with comments): `cross_checks.scope_write_paths_vs_layer_b.tool_path_capabilities` → `[scope.tool_path_capabilities]`; `handler_refusals` → `[scope.handler_refusals]`. Repoint `_tool_path_capabilities` (core.py:1808) + the `_validate_scope_artifact` handler_refusals read (1735) to read these from `config.py` (`get_config(root)`). Remove from YAML.
- [ ] **Step 5:** Remove codified schema blocks from `config/artifact-schemas.yaml`; if the file is left empty/near-empty, note it for Slice 5 deletion (don't delete here unless trivially empty). Header note.
- [ ] **Step 6:** `python3 -m pytest tests/ -q` → green (esp. Heartgate intent/scope/lessons/evidence-disposition + scope_conformance tests); ruff. Commit `feat(domain): codify artifact schemas + BlastRadius; scope path-capabilities -> uacp.toml (Slice 4a)`.

# Task 3: state.yaml schemas → reconcile `engines/domain` models

**Files:** Modify `engines/domain/pointer.py` (`CurrentPointer`), `engines/domain/ledger.py` (`LedgerEntry`), create `engines/domain/escalation.py` (`EscalationRecord`); reconcile `RunManifest` in `skills/uacp-state/scripts/state_machine.py` (carefully); repoint `validate_current_state` (both validator copies), `skills/uacp-state/scripts/state.py` (`_handle_uacp_escalation_event`); modify `config/state.yaml`. Test: `tests/unit/...`. **State/kernel-touching → opus review.**

- [ ] **Step 1 (TDD):** failing tests: `CurrentPointer` accepts the full field set (`mutation_policy`, `current_transition_artifact`, `kanban_*`, `bootstrap_closed`, `governed_mutation_active`, optional `uacp_mode`); `LedgerEntry` carries `phase`/`result`(enum `pass|warn|block`)/`reviewer`; `EscalationRecord` validates the escalations record_schema (mode/severity enums, required fields).
- [ ] **Step 2:** Expand `CurrentPointer` + `LedgerEntry` (optional fields, defaults; keep `extra="allow"`); create `EscalationRecord`. Values/enums FROM `config/state.yaml`. Export.
- [ ] **Step 3 — RunManifest reconciliation (careful):** `state.yaml run_manifest_schema` has DRIFTED from `state_machine.RunManifest`. Do NOT blindly expand. Add only the load-bearing optional fields the engines actually need (`deferred_items` — read by deferral_completeness; `invariants`; `kanban` if the adapter needs it). Tombstone dead YAML-only fields (current_stage, transition_artifact, council_synthesis_artifact, bootstrap_closed/governed_mutation_active on the manifest). Document each decision in the commit.
- [ ] **Step 4:** Repoint `validate_current_state` (both validator copies) to derive its required-field list from `CurrentPointer.model_fields` instead of the hardcoded list. Repoint `state.py:_handle_uacp_escalation_event` to build/validate an `EscalationRecord` (`.model_dump()`), preserving the same error strings.
- [ ] **Step 5:** Remove the codified schema blocks from `config/state.yaml` (`current_pointer_schema`, `gate_ledger.record_schema`, `escalations.record_schema`, `run_manifest_schema`). LEAVE the doctrine/example blocks (`state_principles`, `lifecycle_skill_contracts`, `mutation_rules`, `version_control_binding`, examples) as-is (operator decision: leave doctrine). `state_layer` paths are already covered by live `[paths]` — drop or leave with a pointer comment. Header note.
- [ ] **Step 6:** Full suite green; `phase4_verify.py` (reads current_pointer_schema/escalations — repoint or confirm it reads the YAML blocks that remain / the new models); ruff. Commit `feat(domain): reconcile CurrentPointer/LedgerEntry + EscalationRecord from state.yaml (Slice 4a)`.

> **phase4_verify.py caveat:** it asserted on `state.yaml current_pointer_schema`/`escalations` fields. If those blocks are removed, repoint its checks to the new domain models (or to the residual YAML). Keep it exit-0 (degrade-with-note if needed).

# Task 4: final gate + council + finish branch

- [ ] **Step 1:** `python3 -m pytest tests/ -q` → 360+ green. Ruff over changed `.py`. Residual scan: codified schema blocks removed from the 3 YAMLs; doctrine/registry/examples retained; no validator reads a removed block.
- [ ] **Step 2: Council** (2 lenses): (1) **schema-fidelity auditor** — every codified enum/required-field/schema matches the old YAML values (diff vs `main`); the 5 Heartgate artifact-schema call sites + both validators behave identically; no validator-enforced field dropped. (2) **devil's advocate** — doctrine/invariants correctly LEFT in YAML; the 2 moved knobs (tool_path_capabilities/handler_refusals) resolve from uacp.toml; RunManifest reconciliation didn't drop a load-bearing field; phase4_verify still green.
- [ ] **Step 3:** Finish branch (superpowers:finishing-a-development-branch).

---

## Self-Review
- Coverage: artifact-schemas (T2), evidence-clusters (T1), state.yaml schemas (T3). Doctrine/invariants explicitly LEFT in YAML. 2 knobs → uacp.toml (T2). phase-transitions → Slice 4b (out of scope). F-T3-01 → 4b (with the adaptive gates).
- Risk order: T1 (evidence-clusters, lowest — validator-only) → T2 (artifact-schemas, 5 Heartgate sites) → T3 (state.yaml, RunManifest reconciliation, highest in 4a).
- Each codified block REMOVED from YAML to prevent two-source drift; readers derive from code.

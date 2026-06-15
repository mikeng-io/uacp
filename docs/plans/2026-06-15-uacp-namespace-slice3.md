# Config Collapse — Slice 3 (knob YAMLs → `uacp.toml`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) tracking.

**Goal:** Collapse the 8 knob config YAMLs into `config/uacp.toml` read through `config.py`: fully fold + delete 6 (`guardian-policy`, `autonomy-policy`, `version-control`, `memory-policy`, `model-registry`, `runtime-bindings`); slim 2 (`review-routing`, `gate-selection` — extract knobs, leave grammar for Slice 4). Suite green throughout (baseline **356 passed, 2 skipped**).

**Architecture:** `uacp.toml` already carries dormant `[guardian]`/`[models]`/`[bridges]`/`[council]`/`[phases]`/`[heartgate]`/`[output]`/`[telemetry]` stubs (read by nobody — only `[paths]` is live via Slice 2). Slice 3 **reconciles + wires** them. The one live security reader is `GuardianPolicy.load` (`core.py:149`); the validator (`validate_configs`, invoked in-process by Heartgate) loads `guardian-policy.yaml` + `review-routing.yaml`. Everything else is consumed by SKILL.md prose. `config.py` `UacpConfig` uses `extra="allow"`, so new sections are retained without model changes; add typed models only where a live reader needs them (Guardian).

**Tech Stack:** Python 3.13+ (`python3`), Pydantic v2, `tomllib`, PyYAML, pytest, ruff (`/Users/mike/.local/bin/ruff`, `E,F,I,UP,B`).

**Authoring convention (operator-required):** every collapsed `uacp.toml` section MUST carry human-readable `#` comments — a section header stating what it controls + which YAML it was collapsed from + any canonical prose-authority doc, and inline comments on non-obvious knobs (enums, thresholds, weights, reserved/inert markers). The YAMLs carried `purpose:`/`description:` prose; that intent must survive the move so the single config stays self-documenting.

**Decisions (operator-confirmed):** all 8 in scope; model-registry + runtime-bindings included despite discovery's risk/plane warnings (runtime-bindings config/state plane-mix accepted — record in `docs/decisions/decision-log.md`). guardian-policy YAML is source of truth (the `[guardian]` toml stub is divergent — 3-of-10 self-attesting tools; do NOT trust it).

---

## Reference (verified by discovery dossiers, 2026-06-15)

| YAML | Live code reader | uacp.toml section | Action |
|---|---|---|---|
| `guardian-policy.yaml` | `core.py:149` `GuardianPolicy.load` + validator `validate_configs`/`validate_transition_config_consistency` (both copies) + 8 verify scripts | `[guardian]`+`[heartgate]` (PARTIAL/divergent) | **Reconcile→full**, wire reader+validator, delete |
| `autonomy-policy.yaml` | none (declared stub); `phase4_verify.py` 4 checks; `import_loader_verify.py` | none | Add `[autonomy]`, drop `canonical_state_paths`, delete |
| `version-control.yaml` | none | none | Add `[version_control]`, delete |
| `memory-policy.yaml` | none | none | Add reserved `[memory]` (inert), delete |
| `model-registry.yaml` | none (6 bridge SKILL.md read it) | `[models.tiers]` is a DIFFERENT concept | Add `[models.providers]`+`[models.tier_mappings]`, repoint 6 bridges, delete |
| `runtime-bindings.yaml` | `live_guardian_probe.py:338` (parse-smoke) | none | Add `[runtime_bindings]`, delete (plane-mix decision logged) |
| `review-routing.yaml` | validator existence-check only | none (`[council]` adjacent) | **Slim**: `[review]` knobs; grammar stays |
| `gate-selection.yaml` | none (zero readers) | none | **Slim**: `[gates.scoring]` knobs; invariants/schemas stay |

**Validator coupling (C-A — invoked in-process by Heartgate `core.py:1247-1261`):** `validate_configs` (both `scripts/` + `skills/scripts/` copies) loads `[phase-transitions, review-routing, evidence-clusters, guardian-policy, state]`. `validate_transition_config_consistency` reads `guardian_cfg["heartgate"]["allowed_transitions"]`. Deleting guardian-policy/review-routing WITHOUT repointing the validator + adding `[heartgate].allowed_transitions` to TOML fail-closes real transitions. The `scripts/` copy is the runtime-critical one.

**conftest impact:** `tests/conftest.py` writes a per-test `config/guardian-policy.yaml`. Once `GuardianPolicy.load` reads `[guardian]` via `config.py` (which loads the repo-default `config/uacp.toml` deep-merged with `<root>/.uacp/config.toml`), tests must inject a policy via the deep-merge override OR rely on the repo default. T2/T5 handle this.

---

## Sequencing (lowest-risk first; guardian last among the live ones is impossible since validator couples them — so guardian block is T1-T5, done carefully first to establish the pattern)

Order: **guardian (T1-T5, the hard live one) → version-control (T6) → memory (T7) → autonomy (T8) → model-registry (T9) → runtime-bindings (T10) → review-routing slim (T11) → gate-selection slim (T12) → final gate (T13).**

---

# Task 1: Populate `[guardian]` in `uacp.toml` from `guardian-policy.yaml` (authoring only, not wired)

**Files:** Modify `config/uacp.toml`.

- [ ] **Step 1:** Read `config/guardian-policy.yaml` end-to-end. Translate its full structure into TOML under `[guardian]`, REPLACING the divergent 3-line stub (lines ~210-212). Map: `mode`; `[guardian.protected_categories.<name>]` (each with `description`, `default_decision`, optional `allowed_tools`); `[guardian.tool_classification]`; `[guardian.tool_pattern_classification]`; `[guardian.tool_provenance.classification_by_provider]`; `[guardian.path_rules]` (incl. `protected_write_enforcement.required_for`); `[guardian.self_attesting_tools]` with `names = [all 10]`; `[guardian.runtime_modes]`; `[guardian.audit]`. Fold the YAML's `heartgate` block (`allowed_transitions`, `transition_config`, `decision_values`) into the existing `[heartgate]` section (ADD `allowed_transitions` — the validator needs it).
- [ ] **Step 2:** Validate it parses + the self-attesting list has all 10: `python3 -c "import tomllib; d=tomllib.load(open('config/uacp.toml','rb')); g=d['guardian']; assert len(g['self_attesting_tools']['names'])==10, g['self_attesting_tools']; assert 'state.uacp' in g['tool_classification'].values() or any('state' in v for v in g['tool_classification'].values()); print('ok', sorted(g))"` → `ok`.
- [ ] **Step 3:** `python3 -m pytest tests/ -q` (still 356/2 — nothing reads it yet). Commit `feat(config): populate [guardian]+[heartgate] in uacp.toml from guardian-policy.yaml`.

# Task 2: Wire `GuardianPolicy.load` to read `[guardian]` via `config.py` (TDD — live security reader)

**Files:** Modify `skills/uacp-core/scripts/config.py` (add typed `Guardian` model + accessor), `skills/uacp-core/scripts/core.py:146-162` (`GuardianPolicy.load`). Test: `tests/unit/uacp_core/test_policy.py`, `tests/unit/uacp_core/test_config.py`.

- [ ] **Step 1:** Read `GuardianPolicy.load`/`__init__`/`validate`/`evaluate`/`classify` (core.py ~113-230). `__init__` is structure-driven (`data.get(...)`), so the goal is to feed it the SAME dict shape from TOML instead of YAML. In `config.py`, add a way to get the guardian sub-dict: simplest is `get_config(root).model_dump().get("guardian", {})` (extra fields appear in model_dump with `extra="allow"`). Confirm `extra="allow"` surfaces `[guardian]` in `model_dump()`.
- [ ] **Step 2 (failing test):** add to `test_policy.py` a test that `GuardianPolicy.load(root)` returns a policy whose `self_attesting_tools` has 10 entries and `tool_classification` is populated (proving it reads the full `[guardian]`, not the old 3-tool stub). Run → FAIL (still reads YAML / stub).
- [ ] **Step 3:** Repoint `GuardianPolicy.load` (core.py:146-162): replace `yaml.safe_load(root/config/guardian-policy.yaml)` with the guardian dict from `config.py` (`from config import get_config`; `raw = get_config(root).model_dump().get("guardian", {})`). Preserve `UACP_GUARDIAN_MODE` env override. `__init__`/`validate` unchanged (same dict shape). Keep the `validate()` invariant (every self-attesting tool ∈ tool_classification ∧ governed category).
- [ ] **Step 4: conftest.** `tests/conftest.py` writes a minimal `config/guardian-policy.yaml`. Since `GuardianPolicy.load` now reads the repo-default `config/uacp.toml` `[guardian]` (deep-merged with `<root>/.uacp/config.toml`), the per-test policy must come from the repo default OR a `<root>/.uacp/config.toml` override. Update conftest: drop the `guardian-policy.yaml` write; if a test needs a custom minimal policy, write `<root>/.uacp/config.toml` with a `[guardian]` table. Most tests can use the repo-default `[guardian]` (now complete). Check `test_policy.py` expectations.
- [ ] **Step 5:** `python3 -m pytest tests/ -q` → GREEN (Guardian/policy tests + the new one). Ruff. Commit `feat(guardian): GuardianPolicy.load reads [guardian] from uacp.toml via config.py`.

# Task 3: Repoint the validator (both copies) off `guardian-policy.yaml`/`review-routing.yaml`

**Files:** Modify `scripts/validate_uacp_artifacts.py` + `skills/scripts/validate_uacp_artifacts.py` (`validate_configs` ~1438/1416, `validate_transition_config_consistency` ~1451/1432).

- [ ] **Step 1:** In `validate_configs`, change the hardcoded load list: drop `config/guardian-policy.yaml` and `config/review-routing.yaml`. For the guardian consistency check, load the `[heartgate].allowed_transitions` from `config/uacp.toml` (read via `tomllib` or `config.py`) into the `configs` dict under a stable key (e.g. `configs["uacp.toml#heartgate"]`). review-routing was never read downstream — just drop it.
- [ ] **Step 2:** In `validate_transition_config_consistency`, replace `guardian_cfg["heartgate"]["allowed_transitions"]` with the value read from uacp.toml `[heartgate].allowed_transitions`. Keep the WARN-on-drift semantics + message (update the message to cite `uacp.toml [heartgate]`).
- [ ] **Step 3:** Apply identically to BOTH copies (they're byte-identical in this logic). `grep -n 'guardian-policy\|review-routing' scripts/validate_uacp_artifacts.py skills/scripts/validate_uacp_artifacts.py` → no `guardian-policy.yaml`/`review-routing.yaml` load remains.
- [ ] **Step 4:** `python3 scripts/validate_uacp_artifacts.py --help` works; `python3 -m pytest tests/ -q` → GREEN (the adaptive-gate regression test `tests/e2e/test_adaptive_evidence_gate_uacp.py` exercises the in-process validator — must still pass). Commit `fix(validator): read heartgate.allowed_transitions from uacp.toml; drop guardian-policy/review-routing loads`.

# Task 4: Repoint verify scripts off `guardian-policy.yaml`

**Files:** `scripts/phase0_verify.py`, `phase1_verify.py`, `phase2_verify.py`, `phase3_verify.py`, `phase4_verify.py`, `import_loader_verify.py`, `live_guardian_probe.py` (sites in dossier).

- [ ] **Step 1:** These copy `config/guardian-policy.yaml` into a temp root then `GuardianPolicy.load`. Since the policy now lives in `config/uacp.toml [guardian]`, change them to copy `config/uacp.toml` into the temp root's `config/` (and stop copying the deleted guardian-policy.yaml). For scripts that assert on policy fields, repoint to read `[guardian]` from the copied uacp.toml.
- [ ] **Step 2:** Run each: `for s in phase1_verify phase2_verify phase3_verify phase4_verify import_loader_verify; do python3 scripts/$s.py >/dev/null 2>&1 && echo "$s ok" || echo "$s FAIL"; done`; `python3 scripts/live_guardian_probe.py 2>&1 | tail -3` (only documented pc_7/pc_8 + env failures). Commit `fix(scripts): verify harnesses load [guardian] from uacp.toml`.

# Task 5: Delete `guardian-policy.yaml`

**Files:** Delete `config/guardian-policy.yaml`. Modify skill/doc refs.

- [ ] **Step 1:** `grep -rln 'guardian-policy' skills/ docs/ | grep -vE '2026-06-1|skills/references/.*-2026'` — repoint operational refs (`uacp-guardian/SKILL.md:20`, `uacp-core/SKILL.md:61`, `uacp-web/SKILL.md:278`, `docs/INDEX.md`, `docs/runtime/runtime-enforcement.md`, etc.) to cite `config/uacp.toml [guardian]`. Leave historical/ADR/decision-log.
- [ ] **Step 2:** `git rm config/guardian-policy.yaml`. `python3 -m pytest tests/ -q` → GREEN. `python3 scripts/validate_uacp_artifacts.py --help` works. Commit `feat(config): collapse guardian-policy.yaml into uacp.toml [guardian]; delete YAML`.

# Task 6: `version-control.yaml` → `[version_control]` (cleanest, 0 readers)

**Files:** Modify `config/uacp.toml` (add `[version_control]`), delete `config/version-control.yaml`, repoint refs.

- [ ] **Step 1:** Read `config/version-control.yaml`; add `[version_control]` with subtables `[version_control.repository]`, `[version_control.branch_policy]`, `[version_control.commit_policy]`, `[version_control.runtime_repositories.hermes_agent]`. NOTE: `current_runtime_porting_branch` is time-bound — keep as a config value with a comment (or omit; decide and note). Parse-check.
- [ ] **Step 2:** `grep -rln 'version-control\.yaml\|version-control' skills/ docs/ | grep -vE '2026-06-1|-2026'` — repoint `docs/INDEX.md:58` + `uacp-plan/SKILL.md` prose. Leave decision-log.
- [ ] **Step 3:** `git rm config/version-control.yaml`. Suite GREEN. Commit `feat(config): collapse version-control.yaml into uacp.toml [version_control]`.

# Task 7: `memory-policy.yaml` → reserved `[memory]` (inert)

**Files:** Modify `config/uacp.toml` (`[memory]`), delete `config/memory-policy.yaml`, relocate schema, repoint refs.

- [ ] **Step 1:** Add `[memory]` with the operational boundaries (`[memory.storage_boundaries.*]` allowed/forbidden, `[memory.local_knowledge_locations]`) + an `enforcement_status`/`status = "reserved"` marker (Honcho is later — NO code wired to read `[memory]`). Do NOT cram `learning_artifact_schema`/`example_artifact` into TOML — move those to `docs/reference/learning-artifact-schema.md` (or keep as a reference doc).
- [ ] **Step 2:** Repoint `uacp-resolve/SKILL.md:31` + `docs/INDEX.md:54` + `lifecycle-reference.md:332` + `README.md:184`.
- [ ] **Step 3:** `git rm config/memory-policy.yaml`. Suite GREEN. Commit `feat(config): reserve [memory] in uacp.toml; collapse memory-policy.yaml`.

# Task 8: `autonomy-policy.yaml` → `[autonomy]` (stub; drop `canonical_state_paths`)

**Files:** `config/uacp.toml` (`[autonomy]`), delete `config/autonomy-policy.yaml`, repoint `phase4_verify.py` + 7 SKILL.md + docs.

- [ ] **Step 1:** Add `[autonomy]` (preserve `enforcement_status = "stub_only_phase_4"` honesty marker), `[autonomy.modes.<mode>]` (the 4 modes), `[[autonomy.escalation_triggers.triggers]]` (array-of-tables, 7 triggers), `[autonomy.enforcement_status_legend]`, `[autonomy.advisory_field_convention]`, `[autonomy.hermes_core_seam]`. DROP `canonical_state_paths` (superseded by live `[paths]` — do not create a second path source). Parse-check.
- [ ] **Step 2:** Repoint `scripts/phase4_verify.py` Checks 3/13/17/19 (read `[autonomy]` from uacp.toml; Check 13 `canonical_state_paths` → assert against `[paths]` instead, or drop with a note; Check 19 `docs/INDEX.md` inventory string → update) + `import_loader_verify.py:57`. Repoint the 7 lifecycle `SKILL.md` autonomy stubs + `config/state.yaml:209` prose + docs.
- [ ] **Step 3:** `git rm config/autonomy-policy.yaml`. `python3 scripts/phase4_verify.py` completes (no new failures). Suite GREEN. Commit `feat(config): collapse autonomy-policy.yaml into uacp.toml [autonomy]`.

# Task 9: `model-registry.yaml` → `[models.providers]` + `[models.tier_mappings]` (6 bridge skills)

**Files:** `config/uacp.toml`, delete `config/model-registry.yaml`, repoint 6 bridge SKILL.md.

- [ ] **Step 1:** Add `[models.providers.<provider>]` (anthropic/openai/google/moonshot: `name`, `base_url`, `[models.providers.<p>.models.<alias>]` = `concrete_id`+`description`) and `[models.tier_mappings.<bridge>]` (claude/codex/gemini/kimi: tier `0-4` → `{alias, reasoning}`; OpenCode intentionally absent). Keep alongside the existing `[models.tiers.*]`/`[models.tier_derivation]` (complementary). Parse-check; assert e.g. `claude-sonnet` concrete_id present.
- [ ] **Step 2:** Repoint the 6 bridge skills (`bridge-commons`, `bridge-claude`, `bridge-codex`, `bridge-gemini`, `bridge-kimi` read; `bridge-opencode` explicitly skips) — every prose + bash snippet that reads `config/model-registry.yaml` now reads the `[models]` section of `config/uacp.toml` (the per-project override is `.uacp/config.toml`, replacing the old `config/model-registry.local.yaml` mechanism — update `bridge-commons` resolution contract accordingly).
- [ ] **Step 3:** `git rm config/model-registry.yaml`. Suite GREEN. Commit `feat(config): collapse model-registry.yaml into uacp.toml [models.providers/tier_mappings]; repoint bridges`.

# Task 10: `runtime-bindings.yaml` → `[runtime_bindings]` (+ decision-log entry for plane-mix)

**Files:** `config/uacp.toml`, `docs/decisions/decision-log.md`, delete `config/runtime-bindings.yaml`, repoint `live_guardian_probe.py` + docs.

- [ ] **Step 1:** Add a `docs/decisions/decision-log.md` entry recording that runtime-bindings (a stateful registry) is collapsed into `uacp.toml` per operator decision, overriding the AGENTS.md Cognitive-Planes config/state separation for this case (the Authority Chain requires an explicit decision-log entry to override).
- [ ] **Step 2:** Add `[runtime_bindings]` with `[runtime_bindings.hermes]` (runtime_role, source_root, adapters with binding/migration_status/verification pointers) + `[runtime_bindings.future_runtimes.<name>]`. Parse-check.
- [ ] **Step 3:** Repoint `live_guardian_probe.py:338` (parse-smoke → drop or point at uacp.toml) + `docs/INDEX.md:57` + `runtime-integration-guide.md` + `runtime-porting-*` refs.
- [ ] **Step 4:** `git rm config/runtime-bindings.yaml`. Suite GREEN; `live_guardian_probe.py` no new failures. Commit `feat(config): collapse runtime-bindings.yaml into uacp.toml [runtime_bindings] (plane-mix per decision-log)`.

# Task 11: `review-routing.yaml` SLIM → `[review]` knobs (grammar stays for Slice 4)

**Files:** `config/uacp.toml` (`[review]`), `config/review-routing.yaml` (slim), repoint 5 lifecycle SKILL.md.

- [ ] **Step 1:** Extract ONLY the knobs into `[review]`: `intensity_bands` (granularity→intensity from `review_intensity.*.use_when`), `[[review.escalation_rules]]` (the 8 condition→route rules), `operating_mode = "manual_semi_auto"` (from `locked_current_operating_mode`), optional `triage_council_min_granularity`/`followthrough.max_followup_depth`. Parse-check.
- [ ] **Step 2:** Remove ONLY those extracted knobs from `config/review-routing.yaml`, leaving the grammar (routing_inputs, granularity_model, council_model, review_surfaces, domain_routing_notes, schemas) for Slice 4. Add a header note that knobs moved to `uacp.toml [review]`.
- [ ] **Step 3:** Repoint the 5 lifecycle SKILL.md pointers (`uacp-triage:37`, `uacp-propose:126`, `uacp-plan:56`, `uacp-execute:102`, `uacp-verify:38`): knobs → `uacp.toml [review]`; grammar/doctrine → still `config/review-routing.yaml`. Validator already drops review-routing (T3) — confirm no validator change needed.
- [ ] **Step 4:** Suite GREEN. Commit `feat(config): slim review-routing — knobs to uacp.toml [review]; grammar stays (Slice 4)`.

# Task 12: `gate-selection.yaml` SLIM → `[gates.scoring]` knobs (invariants/schemas stay)

**Files:** `config/uacp.toml` (`[gates.scoring]`), `config/gate-selection.yaml` (slim), repoint `uacp-triage`/`uacp-propose` + policy docs.

- [ ] **Step 1:** Extract knobs into `[gates.scoring]`: `weights` (impact 0.30/reversibility 0.20/domain_count 0.15/runtime_count 0.15/verification_difficulty 0.20), `method = "weighted_max_plus_average"`, `[gates.scoring.route_bands]` (granularity→route), `[gates.scoring.risk_weight]` (low/med/high/critical), `escalation_factor_threshold = 9`. Drop `path_resolution` (redundant with `[paths]`). Parse-check.
- [ ] **Step 2:** Remove the extracted knobs from `config/gate-selection.yaml`, LEAVING `non_waivable_invariants` (kernel invariants — cited by constitution.md/alignment-spec.md), `classification_inputs`, the artifact schemas, etc. for Slice 4. Header note.
- [ ] **Step 3:** Repoint `uacp-triage/SKILL.md:36` (scoring factors → `uacp.toml [gates.scoring]`); `uacp-propose/SKILL.md:63` schema-source pointer stays `config/gate-selection.yaml`. Confirm `constitution.md`/`alignment-spec.md` invariant citations still resolve (invariants stayed in the YAML).
- [ ] **Step 4:** Suite GREEN. Commit `feat(config): slim gate-selection — triage scoring knobs to uacp.toml [gates.scoring]`.

# Task 13: Final gate + council

- [ ] **Step 1:** `python3 -m pytest tests/ -q` → GREEN (≈ baseline 356/2 + new tests).
- [ ] **Step 2:** Ruff over changed `.py`: `git diff --name-only main...HEAD | grep '\.py$' | xargs /Users/mike/.local/bin/ruff check` → clean.
- [ ] **Step 3:** Residual scan — the 6 deleted YAMLs are gone and no stale reader remains:
  `for f in guardian-policy autonomy-policy version-control memory-policy model-registry runtime-bindings; do echo "$f:"; ls config/$f.yaml 2>/dev/null && echo "  STILL EXISTS (bug)" || echo "  deleted ok"; grep -rln "$f\.yaml" skills/ scripts/ runtime-adapters/ --include='*.py' | grep -v 2026-06-1; done` → no live code refs to deleted YAMLs. Confirm `review-routing.yaml` + `gate-selection.yaml` still exist (slimmed) and `uacp.toml` parses with all new sections.
- [ ] **Step 4: Council** (kernel/policy change): 3 lenses over `git diff main...HEAD` — (1) **Guardian-policy auditor**: did the `[guardian]` reconcile preserve all 10 self-attesting tools, full tool_classification, path_rules containment, and the `validate()` anti-bypass invariant? Any field dropped vs the old YAML? (2) **Validator/Heartgate auditor**: does the in-process validator still work (allowed_transitions from uacp.toml, no missing-file block)? Regression test green? (3) **Devil's advocate**: skill-prose repoints complete (no skill reads a deleted YAML)? model-registry override mechanism intact? autonomy enforcement_status honesty preserved? Resolve every material finding.
- [ ] **Step 5:** Finish branch (superpowers:finishing-a-development-branch).

---

## Self-Review (author checklist)
- **Coverage:** all 8 YAMLs have a task (6 delete, 2 slim). Validator coupling (C-A) handled T3 before deletions. conftest handled T2/T4. decision-log plane-mix T10. Skill-prose repoints per-task + residual scan T13.
- **Risk ordering:** guardian block (T1-T5) first to establish the config.py-knob-reader pattern on the one live security reader; dormant/skill-only knobs follow.
- **Placeholders:** none — each task cites dossier content maps + exact reader sites. TOML translations are authored per-task by reading the source YAML (faithful), guided by the dossier structure.

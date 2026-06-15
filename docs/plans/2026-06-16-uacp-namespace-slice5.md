# Config Collapse — Slice 5 (validator dedup + final codification + cleanup) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (two-stage review per task). This slice touches IN-PROCESS ENFORCEMENT (the validator Heartgate loads + the last consumed schema grammar). Smallest steps, behavior-preserving. Suite green after every wave (baseline **504 passed, 2 skipped**).

**Goal:** Finish the `.uacp/` namespace + config-collapse refactor: dedup the two `validate_uacp_artifacts.py` copies, codify the last consumed `phase-transitions.yaml` grammar (the deferred T4d-2 schemas), delete the two inert config files, and finalize the top-level docs. After this slice the config-collapse is COMPLETE.

**Architecture:** Same conventions as Slices 2–4b. Grammar → code (`skills/uacp-core/scripts/engines/domain/`), knobs → `config/uacp.toml`, doctrine stays YAML. Code-default + loaded-override pattern with production-equivalence pins; fixture opt-out stubs preserve test laxity; council before merge.

**Tech stack:** `python3` (3.14 — NOT the default anaconda 3.8). Lint: `/Users/mike/.local/bin/ruff check` (E,F,I,UP,B). Tests: `python3 -m pytest tests/ -q`.

---

## Recon facts (verified this session)

- **Validator copies:** `scripts/validate_uacp_artifacts.py` (1607 lines) is the ACTIVE superset — Heartgate loads it in-process by path (`core.py` `_offline_validate_artifacts`, builds `self.uacp_root / "scripts" / "validate_uacp_artifacts.py"`, `spec_from_file_location` + `exec_module`); the e2e seeders copy it into temp roots; CLI/docs cite it. `skills/scripts/validate_uacp_artifacts.py` (1556 lines) is **ORPHANED** — referenced ONLY in historical plan docs (slice2/3/4a), no code/CLI/skill/hook loads it. It is also STALE (missing `_path_bound_to_run_id()` ~1427-1433, the accepted_exceptions run-binding checks ~249-253, and the `validate_current_state` run-binding call ~1454, plus the Slice-4b canonical cross-check + T4d-1 NOTE). **Dedup = delete the orphan; `scripts/` is canonical.** The by-path in-process load design (validator travels with the governed repo) is intentional and STAYS — do NOT convert to an imported module this slice (that changes the "validator version = target-repo's version" semantic and Heartgate's load mechanism; out of scope).
- **T4d-2 consumed schema bits (the ONLY remaining consumed grammar in `phase-transitions.yaml`):**
  - `artifact_schema.required_fields` — read by `core.py` (`self.required_fields`, ~line 725) AND validator `validate_phase_transition` (`scripts/...:224`).
  - `artifact_schema.fields.terminal_kind.values` — read by validator `validate_phase_transition` (`scripts/...:230`) for the terminal_kind enum check. NOTHING ELSE under `fields` is consumed.
  - `council_synthesis_schema.required_fields` — read by validator `validate_council_synthesis` (`scripts/...:341`). No other sub-field consumed.
  - NO test fixture supplies either block (grep: 0 matches) → both are currently OFF in tests (required_fields=[]). Codifying default-ON will require fixture opt-out stubs and/or seeding (same as 4b). The rest of both blocks (`artifact_schema.fields` map, `council_synthesis_schema` narrative/`artifact_conventions`/`heartgate_council_extension`) is UNCONSUMED schema-doctrine → STAYS YAML.
- **`config/roots.yaml`** (60 lines): purely advisory path-root doctrine. NO code reads it. Doc refs: `docs/INDEX.md:56`, `README.md` tree, `decision-log.md`, the two namespace design/roadmap docs, `skills/references/state-mutation-protocol.md`, `skills/uacp-state/SKILL.md`. Safe to delete.
- **`config/artifact-schemas.yaml`** (22-line stub): codified to `engines/domain/artifact_schema.py` in Slice 4a; NO code reads it (its own header + `core.py:_load_artifact_schemas` confirm). Refs: `docs/INDEX.md:50`, README tree, `tests/e2e/fixtures/README.md`, `scripts/phase{2,3,4}_verify.py` + `import_loader_verify.py` (VERIFY these don't require the file). Safe to delete.
- **Doc finalize:** `docs/INDEX.md` rows for roots.yaml (56) + artifact-schemas.yaml (50) must be removed; row 48 (phase-transitions.yaml) updated to reflect "grammar-free, doctrine+schemas only"; `README.md` config tree; `tests/e2e/fixtures/README.md` repoint to `engines/domain/artifact_schema.py`; the roadmap doc `docs/plans/2026-06-15-uacp-namespace-and-config-collapse.md` gets a Slice-5-complete marker. `AGENTS.md`/`CLAUDE.md`: grep for stale refs to deleted files / the config-collapse status.

---

## Wave staging (dependency order; each independently green + two-stage reviewed)

# Task 1 (S5-W1): dedup the validator — delete the orphaned stale copy

**Files:** Delete `skills/scripts/validate_uacp_artifacts.py`. (No code change — `scripts/` is the sole loaded copy.)

- [ ] **Step 1 (verify orphan, fail-safe):** Re-grep the whole repo (`.py`,`.md`,`.toml`,`.sh`, hooks, `.github/`, `Makefile*`) for `skills/scripts/validate` AND for any loader that could resolve to it. Confirm ONLY historical `docs/plans/*` mention it. If ANY live code/CLI/skill/hook references it → STOP and report (dedup strategy changes).
- [ ] **Step 2:** `git rm skills/scripts/validate_uacp_artifacts.py`.
- [ ] **Step 3:** `python3 -m pytest tests/ -q` → 504/2 (the in-process path uses `scripts/`; the e2e seeders copy from `scripts/` — unaffected). Confirm `tests/e2e/test_adaptive_evidence_gate_uacp.py` + `test_full_lifecycle.py` still pass (they copy the `scripts/` validator). Commit `refactor(validator): remove orphaned stale skills/scripts/ copy; scripts/ is canonical (Slice 5 W1)`.

# Task 2 (S5-W2): codify the deferred T4d-2 schema grammar (artifact_schema + council_synthesis_schema required_fields + terminal_kind enum)

**Files:** `engines/domain/` (extend `artifact_schema.py` or a fitting module — the artifact-schema domain already lives there), `engines/domain/__init__.py`, `core.py` (`Heartgate.__init__` required_fields), `scripts/validate_uacp_artifacts.py` (`validate_phase_transition` + `validate_council_synthesis`), `config/phase-transitions.yaml` (slim the consumed bits), `tests/conftest.py` (opt-out stubs if needed), `tests/unit/uacp_core/` (pins). **Same code-default + loaded-override + fixture-stub + production-equivalence-pin pattern as Slice 4b T4c/T4d. Opus review.**

- [ ] **Step 1 (capture + codify):** Capture the exact current production values from `config/phase-transitions.yaml`: `artifact_schema.required_fields` (the ~15 fields), `artifact_schema.fields.terminal_kind.values` (the enum), `council_synthesis_schema.required_fields`. Codify as typed code-defaults in `engines/domain` (reuse the existing artifact-schema home if natural). Re-export via `__init__.py`.
- [ ] **Step 2 (wire consumers, fail-closed):** `core.py` `self.required_fields` → use loaded `artifact_schema.required_fields` when present, else code-default (matches the established `"block" in self.config`/`or code-default` idiom). Validator `validate_phase_transition` → use code-default for required_fields + terminal_kind values when the block is absent; `validate_council_synthesis` → code-default required_fields when absent. The validator imports the code-default from `engines.domain` (it already bootstraps the kernel path for `base_dir`; confirm the import works both in-process AND standalone-CLI).
- [ ] **Step 3 (fixture firing analysis + stubs):** Determine which tests build `uacp.phase_transition` / `uacp.council_synthesis` artifacts and would newly-enforce required_fields after codify-default-ON (the fixture omits both blocks today → currently OFF). Preserve test laxity via fixture opt-out stubs (e.g. `artifact_schema: {required_fields: []}`, `council_synthesis_schema: {required_fields: []}`) OR genuine seeding — pick the one that doesn't weaken any assertion. Report the analysis.
- [ ] **Step 4 (slim + pin):** Remove ONLY the consumed bits (`required_fields` from both blocks; `fields.terminal_kind.values` — decide whether to slim the whole `fields` map: it's unconsumed-except-terminal_kind, so either slim just terminal_kind.values to a breadcrumb or leave the `fields` map as schema-doctrine and codify only the enum — prefer leaving the unconsumed `fields` doc-map as YAML doctrine, codify the consumed enum). Leave the unconsumed schema doctrine (the `fields` map, council narrative). Add production-equivalence pins (code-default == pre-slim production values, field-by-field) + a behavioral test that the gate/validator ENFORCES required_fields when the block is absent (production state). `python3 -m pytest tests/ -q` green + ruff. Commit `refactor(heartgate): codify artifact_schema/council_synthesis required_fields + terminal_kind enum to code (Slice 5 W2; closes T4d-2)`.

# Task 3 (S5-W3): delete the two inert config files

**Files:** Delete `config/roots.yaml`, `config/artifact-schemas.yaml`. Update `docs/INDEX.md` (remove rows), `README.md` (config tree). Verify `scripts/phase{2,3,4}_verify.py` + `import_loader_verify.py` + `tests/e2e/test_fixtures_valid.py` don't require the deleted files.

- [ ] **Step 1 (verify no hard dependency):** Read `scripts/phase{2,3,4}_verify.py` + `import_loader_verify.py` + `test_fixtures_valid.py`; confirm none asserts the existence of / loads `roots.yaml` or `artifact-schemas.yaml` (the recon says they reference them as fixture-copies/checks — confirm deletion won't break them; if one does, fix it minimally or report).
- [ ] **Step 2:** `git rm config/roots.yaml config/artifact-schemas.yaml`. Update `docs/INDEX.md` (delete the two registry rows; the registry is authority layer 1 — keep it accurate) and `README.md` config tree.
- [ ] **Step 3:** `python3 -m pytest tests/ -q` → 504/2 (or adjusted if W2 changed counts). Commit `chore(config): delete inert roots.yaml + artifact-schemas.yaml stub (Slice 5 W3)`.

# Task 4 (S5-W4): finalize top-level docs

**Files:** `AGENTS.md`, `CLAUDE.md`, `docs/INDEX.md`, `docs/plans/2026-06-15-uacp-namespace-and-config-collapse.md` (roadmap), `tests/e2e/fixtures/README.md`, `skills/references/state-mutation-protocol.md`, `skills/uacp-state/SKILL.md` (roots.yaml refs).

- [ ] **Step 1:** Grep `AGENTS.md`/`CLAUDE.md`/`docs/INDEX.md` for stale refs to deleted files, moved grammar, and the config-collapse status. Update: doc-INDEX phase-transitions.yaml row → "grammar codified to engines/domain + knobs in uacp.toml; YAML holds adaptive-gate doctrine + artifact schemas"; remove dangling roots.yaml/artifact-schemas.yaml mentions in the listed docs (leave genuinely-historical ones, repoint live "authority/reads" ones to `engines/domain/artifact_schema.py`). Mark the config-collapse roadmap doc Slice-5-COMPLETE.
- [ ] **Step 2:** Suite green (docs only — sanity). Commit `docs: finalize AGENTS/CLAUDE/INDEX + roadmap after config-collapse completion (Slice 5 W4)`.

# Task 5 (S5-W5): final gate + council + finish branch

- [ ] Suite (504/2 or adjusted) + ruff (all changed .py) + residual scan: no live ref to the deleted orphan validator; `phase-transitions.yaml` consumed-grammar-free (only doctrine + the now-codified-default schemas' unconsumed doc remnants); roots.yaml/artifact-schemas.yaml gone with no broken readers.
- [ ] **Council (≥2 lenses):** (1) **enforcement/equivalence auditor** — the validator dedup changed nothing the in-process path uses; the schema codification reproduces pre-slim required_fields + terminal_kind enforcement EXACTLY (production-equivalence); no artifact newly accepted/rejected except the intended fail-closed-on-absent. (2) **devil's advocate** — no live consumer of the deleted files/copy; fixture stubs don't mask a production change; doc registry (INDEX.md) still accurate & authority-chain intact; nothing in `phase-transitions.yaml` is still consumed-but-uncodified. Zero material findings unresolved.
- [ ] Finish: merge `--no-ff` to main, re-verify suite on main, delete branch. Update the project memory (Slice 5 done → config-collapse COMPLETE).

---

## Self-Review
- Lowest-risk-first is impossible here (dedup is low-risk but W2 depends on a single validator); ordering is dependency-driven: dedup (W1) → schema codify into the single validator (W2) → deletions (W3) → docs (W4).
- W1 is a pure deletion of a verified orphan (no behavior change). W2 is the only enforcement-touching wave (gets opus + council). W3/W4 are cleanup/docs.
- Behavior-preserving throughout except the intended fail-closed-on-absent for the codified schemas (production defines them today, so present-key behavior unchanged; absent-key now enforces — consistent with the Slice-4b F-T3-01 invariant + the documented codified-gate resolution semantic).
- After Slice 5: config-collapse COMPLETE. `config/phase-transitions.yaml` retains only LLM-read doctrine; all consumed grammar is in `engines/domain`; knobs in `uacp.toml`; one validator copy; roots.yaml/artifact-schemas.yaml gone.

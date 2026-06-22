---
type: reference
title: UACP Code Naming & Module-Layout Conventions
description: The naming standard for CODE symbols and module files in the kernel decomposition — engine/gate subpackage layout, function/class/constant naming (codifying the de-facto kernel conventions), and the re-export discipline that keeps a pure move from breaking importers. Locked BEFORE the extractions so A1+ and every new symbol coined in A2–D follow one standard. Companion to 26 (artifact kinds) / 27 (dir taxonomy) / 28 (component kinds) / 31 (target module graph); read before creating or renaming a module or symbol.
tags: [uacp, naming, conventions, modules, refactor, standard, decomposition]
timestamp: 2026-06-22
edges:
  - {dst: 28-component-registry, rel: depends_on, provenance: asserted}
  - {dst: 29-ddd-ca-reference, rel: depends_on, provenance: asserted}
  - {dst: 31-target-module-graph, rel: depends_on, provenance: asserted}
---

# Code Naming & Module-Layout Conventions

> **Why this exists.** The decomposition (node 31) splits `core.py` into engine/gate
> subpackages and — from Phase A2 on — coins **new** symbols (loaders, validators, the
> Manifest entity-writer). Node 28 fixes the component *kinds* and node 31 fixes the target
> *file names*, but the kernel's symbol/module naming was only ever **de-facto**. This node
> writes it down so every extraction and every new name follow ONE standard. It **codifies
> what the kernel already does** (grounded below); it does not invent new style.
>
> **Scope.** CODE symbols + module files only. NOT artifact kinds ([26](26-nomenclature.md)),
> NOT the `.uacp/` directory/file taxonomy ([27](27-directory-taxonomy.md)), NOT component
> KINDS ([28](28-component-registry.md)), NOT the target module graph ([31](31-target-module-graph.md)).
> This is the naming layer those four assume.

## 0. Relationship to industry standards (the base layer)

There is **no RFC or ISO standard for source-code identifier naming** — ISO/IEC software standards
(e.g. ISO/IEC 25010, the SQuaRE quality model) target *qualities* like maintainability, not how an
identifier is spelled. The authoritative industry standard for Python is **PEP 8** (style + naming)
with **PEP 257** (docstrings): community standards, not ISO/RFC, but universal in the ecosystem and
already what this kernel follows.

This node is therefore **PEP 8 + PEP 257 as the base, plus two UACP layers PEP 8 does not cover**:

- the **domain verb-prefix families** (§2: `load_` / `validate_` / `make_` / `create_` / `is_` …) —
  PEP 8 fixes *case*; UACP fixes the *verb vocabulary* so a name's family signals its role;
- the **component-kind taxonomy** ([28](28-component-registry.md)) — what a thing IS (Engine / Gate /
  Check / Leaf), which §1's module layout reflects.

PEP 8 baseline inherited verbatim: `snake_case` functions/variables/modules, `CapWords` classes,
`UPPER_SNAKE` constants, a single leading underscore for non-public names, short all-lowercase
module names.

**Normative language.** Rules here use **RFC 2119 / RFC 8174** keywords — **MUST** (an invariant, a
Guardian/Heartgate-class rule), **SHOULD** (strong default; deviate only with a recorded reason),
**MAY** (allowed) — matching how the rest of the bundle states contracts.

**Enforcement (tooling-imposed rigor, per D40) — wired in CI** (`.github/workflows/ci.yml`), three
mechanized gates on the clean engine paths:

- **PEP 8 layout** — `ruff` (`E`/`F`/`I`/`UP`/`B`) on `engines/` + `tests/e2e/`.
- **PEP 8 naming** — `ruff` **`N`** (`pep8-naming`) is in `select`; the legacy tree is relaxed via
  `per-file-ignores` (and the pre-existing `engines/oracle` `*Unavailable` exceptions grandfather
  `N818` only). New engine code is held to full `N`.
- **Type safety (PEP 484)** — **`pyright`** runs in CI (the `types` job). Strict mode is **scoped**
  (`pyproject [tool.pyright].strict`) to the freshly-extracted, fully-typed engine packages
  (`engines/guardian`, `engines/domain/paths.py` today); the legacy tree stays `basic`. **Grow the
  strict list as each package is extracted and typed** (A2 `io`, A3 `heartgate`, …).

**Type-safety rules — strict engine code MUST.** No explicit **`Any`** (the "JavaScript types"
failure mode — a type the checker cannot verify): heterogeneous data is **`object`** (callers narrow
with `isinstance`); a structured record is a **`TypedDict`** (e.g. the Guardian audit record); a
loosely-typed external blob (a config table) is modelled by a `TypedDict` and **`cast` once at the
boundary**, so field access downstream is precise rather than `Any`-propagating. Annotations are
runtime-inert, so typing a *pure move* stays behavior-preserving — the test suite is the guard.

## 1. Module layout within an engine/gate subpackage

The `engines/<component>/` pattern (locked by [31](31-target-module-graph.md)). Each module is
**one cohesive responsibility**; these are the conventional module names and what they hold:

| Module | Holds | May import |
|---|---|---|
| `models.py` | dataclasses, enums, error types, decision/vocabulary constants — **pure data** | stdlib · dataclasses · typing · (pydantic/jsonschema) only — no I/O, no sibling classes |
| `<component>.py` (`guardian.py`, `heartgate.py`, `manifest.py`) | the component's namesake class — the gate/engine behavior | `.models`, `.policy`, domain leaves, `config` |
| `policy.py` | a config-derived rules/policy object where one exists (`GuardianPolicy`); its `load()` lives here | `.models`, `config` |
| `events.py` | event / DTO construction factories (`make_event`, `infer_*`) | `.models` |
| `audit.py` | audit / telemetry sinks (`write_*_record`) | stdlib only |
| `validators/` | a gate's **Checks**, one file per cohesive check-group (Heartgate; node 31) | `.models`, `engines.io`, domain leaves |
| `__init__.py` | the **public door**: re-import the public names + declare `__all__`. Nothing else. | the submodules above |

**Split rule** (node 29 litmus): split a module when it (a) imports from ≥2 rings, OR (b) exceeds
~600 lines with ≥3 responsibilities, OR (c) holds logic that *should* be independently testable
but is only reachable through the parent. **Do not over-shatter** — a single cohesive concept
stays one module.

## 2. Symbol naming (codifies the de-facto kernel conventions)

Each rule below is grounded in real kernel symbols (cited).

- **Classes** — PascalCase, noun. `Guardian`, `GuardianPolicy`, `GuardianEvent`,
  `GuardianDecision`, `Heartgate`, `RunManifest`, `Violation`.
- **Load-from-config/disk constructors** — `load()` / `load(uacp_root=…)` **classmethod**
  returning the type. `GuardianPolicy.load`, `Heartgate.load`.
- **Validators** — `validate()` (self-check) and `validate_<kind>(…)` (per-artifact). A **Check**
  returns a `list[Violation]` / error strings and **never raises** (Check contract, node 28).
  `validate`, `validate_transition`, `validate_closure`, `validate_graph_projection`,
  `validate_evidence_completeness`, the 27 `validate_*` in the artifact validator.
- **Factories / builders** — `make_<thing>` (`make_event`), `create_<entity>` (`create_session`;
  the D43 entity-writer = `create_work_unit` / `edit_<entity>` / `supersede_<entity>`),
  `build_<thing>` (`build_index`).
- **Loaders / projectors** — `load_<thing>` / `project_<thing>`.
- **Predicates (bool)** — `is_<x>` (public: `is_uacp_bound`, `is_allowed_tool_for_category`,
  `is_config_file`) / `_is_<x>`, `_has_<x>`, `_path_is_under_<x>` (private:
  `_is_protected`, `_is_direct_uacp_artifact_write`, `_path_is_under_state`).
- **Functions** — verb-first `snake_case`.
- **Constants** — `UPPER_SNAKE` at module level (`DECISION_ALLOW`, `DECISION_BLOCK`);
  `_UPPER_SNAKE` for private/module-internal (`_UACP_ARTIFACT_ROOTS`, `_GOVERNED_ARTIFACT_ROOTS`,
  `_AGG_DIR`, `_READONLY_CATEGORIES`).
- **Private** — a leading underscore marks module- or class-internal; private names are **never**
  in `__all__` and **never** re-exported.

## 3. Public surface & re-export discipline

- Each subpackage's `__init__.py` declares **`__all__`** = the public names; callers import
  `from engines.<component> import X`.
- **One definition per symbol** — no authority mirrors. The module a symbol lives in is its single
  source of truth.
- **During decomposition, the module a symbol moves OUT of keeps a THIN re-export**
  (`from engines.<component> import X`) so existing importers (`from core import Guardian, …`)
  don't break, until callers are migrated. `core.py` is the canonical example: after A1 it
  re-exports `Guardian` / `GuardianPolicy` / `GuardianEvent` / `GuardianDecision` /
  `GuardianPolicyError` / `make_event` / `write_audit_record` / `infer_tool_provider` / the
  `DECISION_*` constants from `engines.guardian`.
- A re-export carries **no logic** (no wrapping, no aliasing of behavior) — it is an import line only.
- `_private` names are never re-exported (they have no external consumers — **confirm with LSP
  `findReferences` ⊕ grep before relying on this**, per the repo's lookup contract).

## 4. Dependency-rule corollary (ties to [29](29-ddd-ca-reference.md))

- A file's **directory encodes its ring**: domain leaves in `engines/domain/`; engines/gates/checks
  in `engines/`; adapters at the `scripts/` root. **Imports point inward only** — a module that
  needs to import an outer ring is a design error.
- **Prefer constructor injection over lazy method-body imports** to break cycles (node 29/30). A
  transitional lazy import is permitted **only** as documented decomposition debt with a named
  removal owner — e.g. A1's `resolve_uacp_root` lazy import inside `guardian/policy.py::load`,
  removed when `resolve_uacp_root` moves to `engines/domain/paths.py` (node 31 step 8).

## 5. DRIFT GUARD

| ❌ wrong | ✅ right |
|---|---|
| renaming a symbol during a "pure move" extraction | keep the name **verbatim**; renames are a separate, tested change |
| a new "validation **engine**" | it is a **Check** (node 28) — `validate_<kind>`, returns Violations, never raises |
| re-exporting a `_private` helper "to be safe" | privates have no external callers; verify (LSP ⊕ grep) and leave them module-internal |
| duplicating a moved symbol's definition in the old + new module | one source of truth + a thin `from engines.<component> import X` re-export |
| a fresh lazy `import` inside a method to dodge a cycle | constructor injection; a lazy import only as documented debt with a removal owner |
| inventing a per-engine module name | use the layout in §1 (`models`/`<component>`/`policy`/`events`/`audit`/`validators`/`__init__`) |

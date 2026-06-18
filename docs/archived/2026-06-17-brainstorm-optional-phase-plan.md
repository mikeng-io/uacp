---
type: plan
title: "Brainstorm Optional Kernel Phase — Implementation Plan"
description: "Implementation plan to add `brainstorm` as a formal entry phase in the lifecycle graph with governed-writer access"
tags: ["brainstorm", "lifecycle", "phase-graph", "kernel"]
timestamp: 2026-06-17
status: archived
---

# Brainstorm Optional Kernel Phase — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Promote `brainstorm` from an informal pre-TRIAGE skill into a formal, optional, state-registered UACP entry phase with `enters_from=["none"]`, `exits_to={triage}`, Heartgate-validated exit invariant (the phase-8 admission contract), and governed-writer access.
**Architecture:** `brainstorm` is prepended to `_PHASE_ORDER` and added to `LIFECYCLE_GRAPH` as a new entry node with one outgoing edge (`triage`); `STAGE_ENTERS_FROM["triage"]` grows to `["none","brainstorm"]`; the admission contract from `phase-8-admission.md` becomes a real `STAGE_PHASE_EXIT_INVARIANTS["brainstorm"]` entry; `uacp-brainstorm/SKILL.md` gains governed writers and registers a run on entry. The four agreement-enforced representations (`LIFECYCLE_GRAPH`, `config/uacp.toml [heartgate].allowed_transitions`, `stages_default()` exits_to, `state_machine.VALID_TRANSITIONS`) are all updated in lockstep, as the existing test suite demands.
**Tech Stack:** Python, pytest, ruff, TOML config, codified phase grammar
**Depends on:** nothing (independent slice). Related: design doc `2026-06-17-brainstorm-optional-phase-design.md`. Build order: **A must land before C** (Plan C appends to the brainstorm SKILL.md that this plan rewrites). A is otherwise standalone.

> **Anchor edits on the symbol/string shown** (e.g. the `_PHASE_ORDER =` assignment), not on literal line numbers — line numbers shift after the first insertion.

> **Build-order constraint (phase_transitions.py tasks):** Keep T2 and T6 contiguous — `stages_default()` will `KeyError` on `brainstorm` between the constant-add (T2) and the invariant-add (T6) because `_PHASE_ORDER` includes `brainstorm` but `STAGE_PHASE_EXIT_INVARIANTS` does not yet. Do not interleave other slices' commits between T2 and T6.

---

## Overview of tasks

| # | Task | Files touched |
|---|------|--------------|
| T1 | Agreement-test stubs for the new phase order | `tests/unit/uacp_core/test_phase_graph.py` |
| T2 | `phase_transitions.py` — add `brainstorm` constants | `skills/uacp-core/scripts/engines/domain/phase_transitions.py` |
| T3 | `phase_graph.py` — add `brainstorm` node + edges | `skills/uacp-core/scripts/engines/domain/phase_graph.py` |
| T4 | `state_machine.py` — allow `brainstorm` initial phase | `skills/uacp-state/scripts/state_machine.py` |
| T5 | `config/uacp.toml` — `[phases.brainstorm]` + heartgate edges | `config/uacp.toml` |
| T6 | `phase_transitions.py` — brainstorm exit invariant | `skills/uacp-core/scripts/engines/domain/phase_transitions.py` |
| T7 | `stages_model` pin-test update | `tests/unit/uacp_core/test_phase_transitions_stages_model.py` |
| T8 | `uacp-brainstorm/SKILL.md` — governed-writer rewrite | `skills/uacp-brainstorm/SKILL.md` |
| T9 | Transition tests (new edges + illegal-edge guard) | `tests/unit/uacp_state/test_state_machine_brainstorm.py` (new file) |
| T10 | Heartgate invariant integration test | `tests/unit/uacp_core/test_heartgate_brainstorm_invariant.py` (new file) |

---

## T1 — Add failing agreement tests for the new graph shape

### Purpose
The existing agreement tests in `test_phase_graph.py` pin `LIFECYCLE_GRAPH == uacp.toml allowed_transitions` and `state_machine.VALID_TRANSITIONS == state_machine_projection()`. Add two new tests that will FAIL until T3 and T5 are done: one asserting `brainstorm` is a node in `LIFECYCLE_GRAPH` with `exits_to == {"triage"}` (this slice; explore-and-bail via the abort-status path is a tracked follow-up), and one asserting the historic-five-edges test is updated to the new six-edge projection.

### Step 1 — Write the failing tests

Append to `/Users/mike/Workplace/uacp/tests/unit/uacp_core/test_phase_graph.py` (after line 105, before the final blank line):

```python
def test_brainstorm_is_a_lifecycle_node() -> None:
    """brainstorm must be a node in LIFECYCLE_GRAPH with exits_to {triage}."""
    assert "brainstorm" in phase_graph.LIFECYCLE_GRAPH, (
        "brainstorm not yet in LIFECYCLE_GRAPH — add it in phase_graph.py T3"
    )
    assert phase_graph.LIFECYCLE_GRAPH["brainstorm"] == {"triage"}, (
        "brainstorm exits must be {triage} for this slice "
        "(explore-and-bail via abort-status path is a tracked follow-up)"
    )


def test_projection_reproduces_the_new_six_edges() -> None:
    """After brainstorm lands, state_machine_projection() gains brainstorm->triage."""
    assert phase_graph.state_machine_projection() == {
        "brainstorm": {"triage"},
        "triage": {"propose"},
        "propose": {"plan"},
        "plan": {"execute"},
        "execute": {"verify"},
        "verify": {"resolved"},
    }
```

### Step 2 — Run, expect FAIL

```bash
python3 -m pytest tests/unit/uacp_core/test_phase_graph.py::test_brainstorm_is_a_lifecycle_node \
    tests/unit/uacp_core/test_phase_graph.py::test_projection_reproduces_the_new_six_edges \
    -v 2>&1 | tail -20
```

Expected: both tests `FAILED`. `test_brainstorm_is_a_lifecycle_node` will show `AssertionError: brainstorm not yet in LIFECYCLE_GRAPH`. `test_projection_reproduces_the_new_six_edges` will show dict mismatch (brainstorm key absent).

Note: `test_projection_reproduces_the_historic_five_edges` (line 92) will still PASS here (graph not yet changed). It will break in T3; that is expected and handled there.

### Step 3 — No implementation yet (intentionally red)

### Step 4 — Commit

```bash
git add tests/unit/uacp_core/test_phase_graph.py
git commit -m "test(phase_graph): add failing agreement tests for brainstorm node + new projection"
```

---

## T2 — Add `brainstorm` constants to `phase_transitions.py`

### Purpose
Add the five new constants (`STAGE_ALLOWED_TOOLS["brainstorm"]`, `STAGE_FORBIDDEN_TOOLS["brainstorm"]`, `STAGE_PURPOSE["brainstorm"]`, `STAGE_ENTERS_FROM["brainstorm"]`, update `STAGE_ENTERS_FROM["triage"]`) and prepend `"brainstorm"` to `_PHASE_ORDER`. The exit invariant comes in T6 so the constant shape stays clean.

`STAGE_PHASE_EXIT_INVARIANTS["brainstorm"]` is left out until T6; its absence means `stages_default()` will `KeyError` on `brainstorm` — acceptable since the test that exercises `brainstorm` in `stages_default()` is not added until T7.

### Step 1 — Write failing unit test

Create `/Users/mike/Workplace/uacp/tests/unit/uacp_core/test_brainstorm_constants.py`:

```python
"""Unit tests for brainstorm phase_transitions constants (T2)."""
from __future__ import annotations

import pytest
from engines.domain.phase_transitions import (
    STAGE_ALLOWED_TOOLS,
    STAGE_ENTERS_FROM,
    STAGE_FORBIDDEN_TOOLS,
    STAGE_PURPOSE,
    _PHASE_ORDER,
)


def test_brainstorm_first_in_phase_order() -> None:
    assert _PHASE_ORDER[0] == "brainstorm"


def test_brainstorm_allowed_tools_present() -> None:
    assert "brainstorm" in STAGE_ALLOWED_TOOLS
    tools = STAGE_ALLOWED_TOOLS["brainstorm"]
    # Must have the governed writers declared in the design doc.
    for required in ("uacp_state_write", "uacp_artifact_write", "uacp_heartgate_check"):
        assert required in tools, f"expected {required!r} in brainstorm allowed_tools"


def test_brainstorm_forbidden_tools_present() -> None:
    assert "brainstorm" in STAGE_FORBIDDEN_TOOLS
    # Exploratory phase; must forbid shell execution.
    assert "terminal" in STAGE_FORBIDDEN_TOOLS["brainstorm"]
    assert "execute_code" in STAGE_FORBIDDEN_TOOLS["brainstorm"]


def test_brainstorm_purpose_present() -> None:
    assert "brainstorm" in STAGE_PURPOSE
    assert STAGE_PURPOSE["brainstorm"]  # non-empty string


def test_brainstorm_enters_from_none() -> None:
    assert STAGE_ENTERS_FROM["brainstorm"] == ["none"]


def test_triage_enters_from_includes_brainstorm() -> None:
    assert set(STAGE_ENTERS_FROM["triage"]) == {"none", "brainstorm"}
```

### Step 2 — Run, expect FAIL

```bash
python3 -m pytest tests/unit/uacp_core/test_brainstorm_constants.py -v 2>&1 | tail -25
```

Expected: all five tests `FAILED` with `KeyError: 'brainstorm'` or `AssertionError` on `_PHASE_ORDER[0]`.

### Step 3 — Implement

Edit `/Users/mike/Workplace/uacp/skills/uacp-core/scripts/engines/domain/phase_transitions.py`:

**3a. Line 87 — prepend `"brainstorm"` entry to `STAGE_ALLOWED_TOOLS`** (insert before `"triage":` block):

```python
STAGE_ALLOWED_TOOLS: dict[str, list[str]] = {
    "brainstorm": [
        "Read",
        "Glob",
        "Grep",
        "Task",
        "Write",
        "uacp_state_write",
        "uacp_artifact_write",
        "uacp_heartgate_check",
    ],
    "triage": [
        # ... existing content unchanged ...
```

**3b. Line 152 — prepend `"brainstorm"` entry to `STAGE_FORBIDDEN_TOOLS`**:

```python
STAGE_FORBIDDEN_TOOLS: dict[str, list[str]] = {
    "brainstorm": ["terminal", "execute_code"],
    "triage": ["terminal", "execute_code"],
    # ... existing content unchanged ...
```

**3c. Line 218 — prepend `"brainstorm"` entry to `STAGE_PURPOSE`**:

```python
STAGE_PURPOSE: dict[str, str] = {
    "brainstorm": "Exploration and scope clarification before entering UACP governance.",
    "triage": "Calibrate scope, score granularity, and route the request.",
    # ... existing content unchanged ...
```

**3d. Lines 231–238 — update `STAGE_ENTERS_FROM`**:

```python
STAGE_ENTERS_FROM: dict[str, list[str]] = {
    "brainstorm": ["none"],
    "triage": ["none", "brainstorm"],
    "propose": ["triage"],
    "plan": ["propose"],
    "execute": ["plan"],
    "verify": ["execute"],
    "resolve": ["verify"],
}
```

**3e. Line 320 — update `_PHASE_ORDER`** (prepend `"brainstorm"`):

```python
_PHASE_ORDER: tuple[str, ...] = ("brainstorm", "triage", "propose", "plan", "execute", "verify", "resolve")
```

> **Note:** `stages_default()` iterates `_PHASE_ORDER` and reads `STAGE_PHASE_EXIT_INVARIANTS[phase]`, which does not yet have a `"brainstorm"` key. This will raise `KeyError` if `stages_default()` is called before T6. The test suite for `stages_default()` is gated behind T7, so this is safe.

### Step 4 — Run, expect PASS

```bash
python3 -m pytest tests/unit/uacp_core/test_brainstorm_constants.py -v 2>&1 | tail -15
```

Expected: all five tests `PASSED`.

### Step 5 — Commit

```bash
git add skills/uacp-core/scripts/engines/domain/phase_transitions.py \
        tests/unit/uacp_core/test_brainstorm_constants.py
git commit -m "feat(phase_transitions): add brainstorm constants to STAGE_* dicts and _PHASE_ORDER"
```

---

## T3 — Add `brainstorm` node to `phase_graph.py`

### Purpose
Add `"brainstorm": {"triage"}` to `LIFECYCLE_GRAPH` (this slice; explore-and-bail via `brainstorm→terminal` is a tracked follow-up needing the `aborted`-status path designed). This is the single source of truth; it cascades automatically to `stages_default()` exits_to (via `_exits_to()`) and to `state_machine.VALID_TRANSITIONS` (via `state_machine_projection()`). This will break `test_projection_reproduces_the_historic_five_edges`; we update it in this task.

### Step 1 — Confirm tests are currently failing (from T1)

```bash
python3 -m pytest tests/unit/uacp_core/test_phase_graph.py::test_brainstorm_is_a_lifecycle_node -v 2>&1 | tail -5
```

Expected: `FAILED`.

### Step 2 — Implement

Edit `/Users/mike/Workplace/uacp/skills/uacp-core/scripts/engines/domain/phase_graph.py`.

Replace lines 86–93 (`LIFECYCLE_GRAPH` literal):

```python
LIFECYCLE_GRAPH: dict[str, set[str]] = {
    "brainstorm": {"triage"},
    "triage": {"propose", "terminal"},
    "propose": {"plan"},
    "plan": {"execute"},
    "execute": {"verify"},
    "verify": {"resolve"},
    "resolve": {"terminal"},
}
```

> **Note:** `brainstorm→terminal` (explore-and-bail) is NOT included in this slice. It requires the `aborted`-status path to be designed first; it is tracked as an explicit follow-up. Add it to `LIFECYCLE_GRAPH` only when that path ships.

### Step 3 — Update the now-broken historic-five-edges test

The test at lines 92–100 of `test_phase_graph.py` will now fail because the projection includes `brainstorm`. Replace that test:

```python
def test_projection_reproduces_the_historic_five_edges() -> None:
    """The projection must reproduce the canonical 6-edge state-machine graph.

    Updated in Brainstorm-phase slice: brainstorm->triage is a new edge.
    The `historic five edges` comment is updated to reflect the current graph.
    triage->terminal is dropped (terminal sink rule);
    resolve->resolved is the phase-collapse rule.
    brainstorm->terminal is not in LIFECYCLE_GRAPH for this slice
    (explore-and-bail is a tracked follow-up).
    """
    assert phase_graph.state_machine_projection() == {
        "brainstorm": {"triage"},
        "triage": {"propose"},
        "propose": {"plan"},
        "plan": {"execute"},
        "execute": {"verify"},
        "verify": {"resolved"},
    }
```

### Step 4 — Run, expect PASS

```bash
python3 -m pytest tests/unit/uacp_core/test_phase_graph.py -v 2>&1 | tail -20
```

Expected: all tests `PASSED` including `test_brainstorm_is_a_lifecycle_node` and `test_projection_reproduces_the_new_six_edges` (added in T1). `test_canonical_graph_matches_uacp_toml_allowed_transitions` will now `FAIL` until T5 (uacp.toml not yet updated) — this is expected and intentional.

### Step 5 — Commit

```bash
git add skills/uacp-core/scripts/engines/domain/phase_graph.py \
        tests/unit/uacp_core/test_phase_graph.py
git commit -m "feat(phase_graph): add brainstorm node with exits_to={triage}"
```

---

## T4 — `state_machine.py` — allow `brainstorm` as initial phase

### Purpose
`RunManifest.current_phase` defaults to `"triage"` (line 95). A brainstorm-entry run should be initializable at `"brainstorm"`. `VALID_TRANSITIONS` is derived automatically from `state_machine_projection()`, so it gains `brainstorm->triage` without manual edits after T3. The only code change is allowing `handle_init` to accept `initial_phase="brainstorm"`.

### Step 1 — Write failing test

Create `/Users/mike/Workplace/uacp/tests/unit/uacp_state/test_state_machine_init_brainstorm.py`:

```python
"""Test that handle_init accepts initial_phase='brainstorm' (T4)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import yaml


def _make_workspace(tmp: Path) -> Path:
    uacp_dir = tmp / ".uacp"
    uacp_dir.mkdir()
    return tmp


def test_handle_init_accepts_brainstorm_phase(tmp_path: Path) -> None:
    """handle_init with initial_phase='brainstorm' must create manifest at brainstorm."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]
                          / "skills" / "uacp-state" / "scripts"))
    from state_machine import handle_init

    ws = _make_workspace(tmp_path)
    result = json.loads(handle_init({
        "workspace": str(ws),
        "run_id": "bs-test-001",
        "source": "operator-request",
        "initial_phase": "brainstorm",
    }))
    assert result.get("ok"), f"unexpected error: {result}"

    manifest_path = ws / ".uacp" / "state" / "runs" / "bs-test-001.yaml"
    assert manifest_path.exists()
    manifest = yaml.safe_load(manifest_path.read_text())
    assert manifest["current_phase"] == "brainstorm"


def test_handle_init_default_phase_still_triage(tmp_path: Path) -> None:
    """When initial_phase is omitted, current_phase must still default to triage."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]
                          / "skills" / "uacp-state" / "scripts"))
    from state_machine import handle_init

    ws = _make_workspace(tmp_path)
    result = json.loads(handle_init({
        "workspace": str(ws),
        "run_id": "triage-test-001",
        "source": "operator-request",
    }))
    assert result.get("ok"), f"unexpected error: {result}"

    manifest_path = ws / ".uacp" / "state" / "runs" / "triage-test-001.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    assert manifest["current_phase"] == "triage"
```

### Step 2 — Run, expect FAIL

```bash
python3 -m pytest tests/unit/uacp_state/test_state_machine_init_brainstorm.py -v 2>&1 | tail -15
```

Expected: `test_handle_init_accepts_brainstorm_phase` FAILED — `handle_init` ignores `initial_phase` and always creates manifest with `current_phase: triage`.

### Step 3 — Implement

Edit `/Users/mike/Workplace/uacp/skills/uacp-state/scripts/state_machine.py`.

In `handle_init` (starting at line 150), after the `track` validation block (around line 174), add the following immediately before `authority = Authority(source=source, status="pass")` (around line 205):

```python
        # Optional initial_phase: allows a run to start at 'brainstorm' instead
        # of the default 'triage'. Fail closed on unknown phases.
        initial_phase = str(args.get("initial_phase") or "triage").strip()
        _VALID_INITIAL_PHASES = {"triage", "brainstorm"}
        if initial_phase not in _VALID_INITIAL_PHASES:
            return json.dumps({"error": f"invalid initial_phase '{initial_phase}': must be one of {sorted(_VALID_INITIAL_PHASES)}"})
```

Then in the `manifest = RunManifest(...)` call (around line 220), add `current_phase=initial_phase`:

```python
        manifest = RunManifest(
            run_id=run_id,
            current_phase=initial_phase,
            authority=authority,
            workspace=workspace_obj,
            track=track,
            goal_id=goal_id,
            inherits_from=inherits_from,
            inherited_artifacts=inherited_artifacts,
        )
```

### Step 4 — Run, expect PASS

```bash
python3 -m pytest tests/unit/uacp_state/test_state_machine_init_brainstorm.py -v 2>&1 | tail -10
```

Expected: both tests `PASSED`.

### Step 5 — Commit

```bash
git add skills/uacp-state/scripts/state_machine.py \
        tests/unit/uacp_state/test_state_machine_init_brainstorm.py
git commit -m "feat(state_machine): accept initial_phase=brainstorm in handle_init"
```

---

## T5 — `config/uacp.toml` — add `[phases.brainstorm]` and heartgate edges

### Purpose
This makes the external config agree with `LIFECYCLE_GRAPH` so `test_canonical_graph_matches_uacp_toml_allowed_transitions` passes. Add two new heartgate transition strings and a `[phases.brainstorm]` section.

### Step 1 — Confirm test is currently failing

```bash
python3 -m pytest tests/unit/uacp_core/test_phase_graph.py::test_canonical_graph_matches_uacp_toml_allowed_transitions -v 2>&1 | tail -10
```

Expected: `FAILED` (phase_graph has brainstorm; toml does not).

### Step 2 — Implement

Edit `/Users/mike/Workplace/uacp/config/uacp.toml`.

**5a. Add `[phases.brainstorm]` after the existing `[phases.resolve]` block (search for the `[phases.resolve]` header, not a line number)**:

```toml
[phases.brainstorm]
council_mode = "brainstorm"
```

> **Note:** verify the `council_mode` enum in `uacp.toml` accepts `"brainstorm"`. If the live accepted values are only `research/design/plan/implement/audit`, reuse `"research"` instead and add a comment: `# reusing 'research' until council_mode gains a 'brainstorm' value`.

**5b. Update `[heartgate].allowed_transitions`** (search for `allowed_transitions = [` in the `[heartgate]` section). Add ONE new line — insert `brainstorm->triage` before the closing `]`:

```toml
allowed_transitions = [
    "brainstorm->triage",
    "execute->verify",
    "plan->execute",
    "propose->plan",
    "resolve->terminal",
    "triage->propose",
    "triage->terminal",
    "verify->resolve",
]
```

> **Note:** `brainstorm->terminal` is NOT added here (that edge is not in `LIFECYCLE_GRAPH` for this slice; see T3). Keep the list sorted alphabetically to match the convention used by the agreement test's set comparison.

### Step 3 — Run, expect PASS

```bash
python3 -m pytest tests/unit/uacp_core/test_phase_graph.py -v 2>&1 | tail -15
```

Expected: all tests `PASSED`, including `test_canonical_graph_matches_uacp_toml_allowed_transitions`.

### Step 4 — Commit

```bash
git add config/uacp.toml
git commit -m "feat(config): add [phases.brainstorm] + heartgate edge brainstorm->triage"
```

---

## T6 — Add brainstorm exit invariant to `phase_transitions.py`

### Purpose
The design doc promotes the phase-8 admission contract (from `references/phase-8-admission.md`) into a real `STAGE_PHASE_EXIT_INVARIANTS["brainstorm"]` entry. The invariant checks that a scope-package artifact glob exists. This also unblocks `stages_default()` from `KeyError` on `"brainstorm"`, completing the phase constants.

### Step 1 — Write failing test

Append to `/Users/mike/Workplace/uacp/tests/unit/uacp_core/test_brainstorm_constants.py`:

```python
from engines.domain.phase_transitions import STAGE_PHASE_EXIT_INVARIANTS, stages_default


def test_brainstorm_phase_exit_invariant_present() -> None:
    assert "brainstorm" in STAGE_PHASE_EXIT_INVARIANTS
    invs = STAGE_PHASE_EXIT_INVARIANTS["brainstorm"]
    assert isinstance(invs, list) and len(invs) >= 1

    # The scope-package artifact glob is required.
    scope_inv = next(
        (i for i in invs if "artifact_glob" in i and "brainstorm" in i["artifact_glob"]),
        None,
    )
    assert scope_inv is not None, "No artifact_glob invariant for brainstorm scope-package"
    assert scope_inv["required"] is True


def test_stages_default_includes_brainstorm() -> None:
    stages = stages_default()
    assert "brainstorm" in stages
    body = stages["brainstorm"]
    assert body["enters_from"] == ["none"]
    assert set(body["exits_to"]) == {"triage"}
    assert body["allowed_tools"]
    assert "terminal" in body["forbidden_tools"]
```

### Step 2 — Run, expect FAIL

```bash
python3 -m pytest tests/unit/uacp_core/test_brainstorm_constants.py::test_brainstorm_phase_exit_invariant_present \
    tests/unit/uacp_core/test_brainstorm_constants.py::test_stages_default_includes_brainstorm \
    -v 2>&1 | tail -15
```

Expected: both FAILED — `KeyError: 'brainstorm'` on `STAGE_PHASE_EXIT_INVARIANTS` and `stages_default()` KeyError.

### Step 3 — Implement

Edit `/Users/mike/Workplace/uacp/skills/uacp-core/scripts/engines/domain/phase_transitions.py`.

**3a. Add `"brainstorm"` entry to `STAGE_PHASE_EXIT_INVARIANTS`** (search for the `STAGE_PHASE_EXIT_INVARIANTS` assignment, before `"triage":` key):

```python
STAGE_PHASE_EXIT_INVARIANTS: dict[str, list[dict[str, Any]]] = {
    "brainstorm": [
        {
            "artifact_glob": "brainstorm/*/07-scope-package.yaml",
            "required": True,
            "description": (
                "Brainstorm admission contract: a selected scope-package artifact must "
                "exist with non-empty title/description/in_scope, declared_side_effects "
                "present, authority.source documented, and a valid routing_advisory. "
                "Promoted from references/phase-8-admission.md."
            ),
        },
    ],
    "triage": [
        # ... existing content unchanged ...
```

### Step 4 — Run, expect PASS

```bash
python3 -m pytest tests/unit/uacp_core/test_brainstorm_constants.py -v 2>&1 | tail -15
```

Expected: all tests (7) `PASSED`.

### Step 5 — Commit

```bash
git add skills/uacp-core/scripts/engines/domain/phase_transitions.py \
        tests/unit/uacp_core/test_brainstorm_constants.py
git commit -m "feat(phase_transitions): add brainstorm exit invariant (scope-package artifact glob)"
```

---

## T7 — Update `test_phase_transitions_stages_model.py` pin-tests

### Purpose
`test_phase_transitions_stages_model.py` parametrizes over `_PHASES = ("triage", ...)` and asserts `stages[phase] == _PRESLIM_*[phase]`. These must be extended to include `brainstorm`, and the module-level `_PHASES` tuple updated. The `_PRESLIM_*` pin tables must include the new phase.

### Step 1 — Confirm affected tests

```bash
python3 -m pytest tests/unit/uacp_core/test_phase_transitions_stages_model.py -v 2>&1 | tail -20
```

If `stages_default()` is now fixed (T6 done), these should currently PASS for the six existing phases but not test `brainstorm`. We need to extend them.

### Step 2 — Implement (file edits)

Edit `/Users/mike/Workplace/uacp/tests/unit/uacp_core/test_phase_transitions_stages_model.py`:

**2a. Line 193 — update `_PHASES`**:

```python
_PHASES = ("brainstorm", "triage", "propose", "plan", "execute", "verify", "resolve")
```

**2b. After line 95 (`_PRESLIM_ALLOWED_TOOLS` dict) — add `"brainstorm"` key as first entry**:

```python
_PRESLIM_ALLOWED_TOOLS = {
    "brainstorm": [
        "Read",
        "Glob",
        "Grep",
        "Task",
        "Write",
        "uacp_state_write",
        "uacp_artifact_write",
        "uacp_heartgate_check",
    ],
    "triage": [
        # ... existing content unchanged ...
```

**2c. After line 104 (`_PRESLIM_FORBIDDEN_TOOLS` dict) — add `"brainstorm"` key**:

```python
_PRESLIM_FORBIDDEN_TOOLS = {
    "brainstorm": ["terminal", "execute_code"],
    "triage": ["terminal", "execute_code"],
    # ... existing content unchanged ...
```

**2d. Update `_PRESLIM_EXITS_TO`** (line 107) — add `"brainstorm"` key:

```python
_PRESLIM_EXITS_TO = {
    "brainstorm": ["triage"],  # this slice only; explore-and-bail is a follow-up
    "triage": ["propose", "terminal"],
    # ... existing content unchanged ...
```

**2e. Update `_PRESLIM_PHASE_EXIT_INVARIANTS`** (line 116) — add `"brainstorm"` key:

```python
_PRESLIM_PHASE_EXIT_INVARIANTS = {
    "brainstorm": [
        {
            "artifact_glob": "brainstorm/*/07-scope-package.yaml",
            "required": True,
            "description": (
                "Brainstorm admission contract: a selected scope-package artifact must "
                "exist with non-empty title/description/in_scope, declared_side_effects "
                "present, authority.source documented, and a valid routing_advisory. "
                "Promoted from references/phase-8-admission.md."
            ),
        },
    ],
    "triage": [
        # ... existing content unchanged ...
```

**2f. Update `_PRESLIM_PURPOSE`** (line 163) — add `"brainstorm"` key:

```python
_PRESLIM_PURPOSE = {
    "brainstorm": "Exploration and scope clarification before entering UACP governance.",
    "triage": "Calibrate scope, score granularity, and route the request.",
    # ... existing content unchanged ...
```

**2g. Update `_PRESLIM_ENTERS_FROM`** (line 176) — add `"brainstorm"` key and update `"triage"`:

```python
_PRESLIM_ENTERS_FROM = {
    "brainstorm": ["none"],
    "triage": ["none", "brainstorm"],
    "propose": ["triage"],
    "plan": ["propose"],
    "execute": ["plan"],
    "verify": ["execute"],
    "resolve": ["verify"],
}
```

**2h. Update `test_triage_routing_outcomes_and_terminate_flag_pin`** (line 242) — the list of phases that must NOT have `routing_outcomes` now excludes `brainstorm`:

```python
def test_triage_routing_outcomes_and_terminate_flag_pin(stages: dict) -> None:
    assert stages["triage"]["routing_outcomes"] == _PRESLIM_TRIAGE_ROUTING_OUTCOMES
    assert stages["triage"]["can_terminate_without_full_lifecycle"] is True
    # routing_outcomes / can_terminate are triage-only; absent on other phases.
    for phase in ("brainstorm", "propose", "plan", "execute", "verify", "resolve"):
        assert "routing_outcomes" not in stages[phase]
        assert "can_terminate_without_full_lifecycle" not in stages[phase]
```

### Step 3 — Run, expect PASS

```bash
python3 -m pytest tests/unit/uacp_core/test_phase_transitions_stages_model.py -v 2>&1 | tail -30
```

Expected: all tests `PASSED`. Parametrized tests will now run for 7 phases.

### Step 4 — Run full unit suite to check for regressions

```bash
python3 -m pytest tests/unit/ -v --tb=short 2>&1 | tail -40
```

Expected: all pass.

### Step 5 — Commit

```bash
git add tests/unit/uacp_core/test_phase_transitions_stages_model.py
git commit -m "test(stages_model): extend pin-tests to cover brainstorm phase constants"
```

---

## T8 — Update `uacp-brainstorm/SKILL.md` to use governed writers

### Purpose
The current `SKILL.md` declares itself informal and lacks governed writers. Per the design doc, brainstorm gains `uacp_state_write`, `uacp_artifact_write`, and `uacp_heartgate_check`; the "informal / not registered" stance and the phase-8 note are replaced; the lifecycle-position diagram is updated.

This is a documentation/skill edit — no kernel test. Verify with skill-readiness lint if available.

### Step 1 — Implement

Replace the contents of `/Users/mike/Workplace/uacp/skills/uacp-brainstorm/SKILL.md`:

```markdown
---
name: uacp-brainstorm
description: >
  Optional UACP entry phase for exploration and scope clarification. Registers a
  formal run at phase=brainstorm, writes the scope package as a governed artifact,
  and runs Heartgate to validate brainstorm->triage admission before handing off.
kind: orchestration
location: managed
dependencies:
  - uacp-context
  - domain-registry
  - uacp-bridge
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(ls *)
  - Bash(git log *)
  - Bash(git diff *)
  - Task
  - Write
  - Bash(mkdir *)
  - uacp_state_write
  - uacp_artifact_write
  - uacp_heartgate_check
---

# UACP Brainstorm: Optional Entry Phase

Use this skill when the user has a vague idea, ambiguous scope, or multiple possible directions. Brainstorming is an **optional formal entry phase** of the UACP lifecycle. Its job is to help the user understand what they actually want and trim it down to a bounded scope before TRIAGE.

**This skill is a governed phase.** On entry it registers a UACP run at `phase: brainstorm` using `uacp_state_write`, writes the scope package as a real lifecycle artifact using `uacp_artifact_write`, and runs `uacp_heartgate_check` for the `brainstorm→triage` transition before handing off. Brainstorm artifacts are state-persistent.

**Hard rule:** do not invoke implementation skills during brainstorming. Exploration only.

---

## Skill-Level Exploration Gate

Read: references/exploration-gate.md

---

## Quick-Start

1. Register run at `phase: brainstorm` using `uacp_state_write`.
2. Read: references/phase-1-context.md — Gather signals and classify intent
3. Read: references/phase-2-explore.md — Explore possibilities and constraints
4. Read: references/phase-3-questions.md — Ask clarifying questions one at a time
5. Read: references/phase-4-approaches.md — Sketch 2–3 candidate approaches
6. Read: references/phase-5-trim.md — Trim scope with the user
7. Read: references/phase-6-vault.md — Write rough notes to brainstorm vault
8. Read: references/phase-7-selected-scope.md — Produce the scope package (governed artifact via `uacp_artifact_write`)
9. Read: references/phase-8-admission.md — Run `uacp_heartgate_check` for brainstorm→triage
10. Read: references/phase-9-triage.md — Transition to TRIAGE (`uacp_heartgate_check` transition)

---

## Lifecycle Position

```text
BRAINSTORM → TRIAGE → PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE
 ^              ^
 optional       formal UACP governance (always required for propose onward)
 entry phase
```

- A run may begin at `brainstorm` (optional) or at `triage` (direct entry).
- Brainstorm **always precedes** TRIAGE — it never skips it.
- `brainstorm → triage` is the only exit in this slice. Explore-and-bail (stopping before any formal artifact) is a follow-up requiring the `aborted`-status path.
- Scope package path: `.uacp/brainstorm/{session_id}/07-scope-package.yaml` (registered via `uacp_artifact_write`).

---

## Notes

- **One question at a time** — never overwhelm the user with bundled questions
- **YAGNI ruthlessly** — the goal is to trim scope, not expand it
- **Explore alternatives** — always sketch 2-3 approaches before settling
- **The vault is supporting evidence** — it is raw thinking material; the scope package is the governed artifact
- **Only selected scope enters TRIAGE** — Heartgate checks the admission boundary
- **Anti-collapse** — one phase = one markdown file. Never merge phases.
```

### Step 2 — Verify skill-readiness lint (if available)

```bash
python3 -m pytest tests/ -k "skill" -v 2>&1 | tail -20
```

If no skill lint tests exist, this step is informational. Confirm no regressions.

### Step 3 — Commit

```bash
git add skills/uacp-brainstorm/SKILL.md
git commit -m "feat(uacp-brainstorm): gain governed writers; replace informal stance with phase registration"
```

---

## T9 — State-machine transition tests (new edges + illegal-edge guard)

### Purpose
Verify at the `state_machine.py` layer that `none→brainstorm` (via `handle_init`) and `brainstorm→triage` work; that `triage` still accepts `none`; and that illegal edges (`brainstorm→plan`, `brainstorm→propose`) are blocked. These use the `handle_transition` function.

> **Note:** `brainstorm→terminal` (explore-and-bail) is NOT tested here because `brainstorm→terminal` is not in `LIFECYCLE_GRAPH` for this slice and `state_machine_projection()` drops every `→terminal` edge. Explore-and-bail (brainstorm→abort) is a tracked follow-up needing the `aborted`-status path designed.

### Step 1 — Write tests

Create `/Users/mike/Workplace/uacp/tests/unit/uacp_state/test_state_machine_brainstorm_transitions.py`:

```python
"""State-machine transition tests for the brainstorm phase (T9)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
import yaml

import pytest

_STATE_DIR = Path(__file__).resolve().parents[3] / "skills" / "uacp-state" / "scripts"
if str(_STATE_DIR) not in sys.path:
    sys.path.insert(0, str(_STATE_DIR))

from state_machine import VALID_TRANSITIONS, handle_init, handle_transition


@pytest.fixture()
def bs_workspace(tmp_path: Path) -> Path:
    """Workspace with a run initialized at brainstorm."""
    ws = tmp_path
    (ws / ".uacp").mkdir()
    result = json.loads(handle_init({
        "workspace": str(ws),
        "run_id": "bs-trans-001",
        "source": "operator-request",
        "initial_phase": "brainstorm",
    }))
    assert result.get("ok"), result
    return ws


@pytest.fixture()
def triage_workspace(tmp_path: Path) -> Path:
    """Workspace with a run initialized directly at triage (existing behavior)."""
    ws = tmp_path
    (ws / ".uacp").mkdir()
    result = json.loads(handle_init({
        "workspace": str(ws),
        "run_id": "triage-direct-001",
        "source": "operator-request",
    }))
    assert result.get("ok"), result
    return ws


# --- VALID_TRANSITIONS graph assertions ---

def test_valid_transitions_includes_brainstorm_to_triage() -> None:
    assert "brainstorm" in VALID_TRANSITIONS
    assert "triage" in VALID_TRANSITIONS["brainstorm"]


def test_valid_transitions_triage_still_accepts_propose() -> None:
    """triage->propose must still work (existing edge unbroken)."""
    assert "propose" in VALID_TRANSITIONS.get("triage", set())


# --- handle_transition tests ---

def test_brainstorm_to_triage_allowed(bs_workspace: Path) -> None:
    result = json.loads(handle_transition({
        "workspace": str(bs_workspace),
        "run_id": "bs-trans-001",
        "from_phase": "brainstorm",
        "to_phase": "triage",
    }))
    assert result.get("ok"), f"expected ok, got: {result}"
    assert result["from_phase"] == "brainstorm"
    assert result["to_phase"] == "triage"


def test_triage_still_accepts_none_entry(triage_workspace: Path) -> None:
    """Direct triage entry (without brainstorm) must still be possible."""
    # A run started at triage should be able to advance to propose.
    result = json.loads(handle_transition({
        "workspace": str(triage_workspace),
        "run_id": "triage-direct-001",
        "from_phase": "triage",
        "to_phase": "propose",
    }))
    assert result.get("ok"), f"expected ok, got: {result}"


# NOTE: test_brainstorm_to_terminal is intentionally omitted from this slice.
# state_machine_projection() drops every ->terminal edge, so brainstorm->terminal
# is not in VALID_TRANSITIONS and handle_transition will refuse it. The explore-and-bail
# path (brainstorm->abort) is a tracked follow-up needing the aborted-status path designed.
# Add a test here when that slice ships.


def test_brainstorm_to_plan_blocked(bs_workspace: Path) -> None:
    """brainstorm->plan must be refused (phase-skipping)."""
    result = json.loads(handle_transition({
        "workspace": str(bs_workspace),
        "run_id": "bs-trans-001",
        "from_phase": "brainstorm",
        "to_phase": "plan",
    }))
    assert not result.get("ok")
    assert "not allowed" in result.get("error", "")


def test_brainstorm_to_propose_blocked(bs_workspace: Path) -> None:
    """brainstorm->propose must be refused (must flow through triage first)."""
    result = json.loads(handle_transition({
        "workspace": str(bs_workspace),
        "run_id": "bs-trans-001",
        "from_phase": "brainstorm",
        "to_phase": "propose",
    }))
    assert not result.get("ok")
    assert "not allowed" in result.get("error", "")
```

### Step 2 — Run, expect PASS

```bash
python3 -m pytest tests/unit/uacp_state/test_state_machine_brainstorm_transitions.py -v 2>&1 | tail -20
```

Expected: all tests `PASSED`.

### Step 3 — Commit

```bash
git add tests/unit/uacp_state/test_state_machine_brainstorm_transitions.py
git commit -m "test(state_machine): transition tests for brainstorm->triage, illegal edges, direct triage entry"
```

---

## T10 — Heartgate exit-invariant integration test (non-vacuous mutation)

### Purpose
Verify the brainstorm exit invariant is non-vacuous: a `brainstorm→triage` Heartgate artifact WITH a conformant scope-package artifact file PASSES; one WITHOUT the file (or with an under-specified package) results in a BLOCK. This exercises the real `_validate_phase_exit_invariants` path in `core.py`.

### Step 1 — Write test

Create `/Users/mike/Workplace/uacp/tests/unit/uacp_core/test_heartgate_brainstorm_invariant.py`:

```python
"""Heartgate invariant integration test: brainstorm exit invariant is non-vacuous (T10)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

_CORE_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "uacp-core" / "scripts"
if str(_CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CORE_SCRIPTS))

from core import Heartgate
from engines.io import load_phase_transitions

REPO_ROOT = Path(__file__).resolve().parents[3]


def _make_heartgate(uacp_root: Path) -> Heartgate:
    """Construct Heartgate with the real signature: Heartgate(config, *, uacp_root=None).
    governed_root is derived internally as uacp_root/.uacp — do NOT pass governed_root=.
    """
    loaded = load_phase_transitions(REPO_ROOT)
    assert loaded.error is None
    return Heartgate(loaded.value or {}, uacp_root=uacp_root)


def _minimal_brainstorm_triage_artifact(run_id: str) -> dict:
    """Minimal valid brainstorm->triage transition artifact."""
    return {
        "transition_id": f"{run_id}-brainstorm-triage",
        "run_id": run_id,
        "from_phase": "brainstorm",
        "to_phase": "triage",
        "decision": "pass",
        "invariant_summary": [],
        "cluster_summary": [],
        "blockers": [],
        "warnings": [],
        "deferred_items": [],
        "authority": {"source": "operator-request"},
        "artifact_paths": [],
        "phase_local_granularity": 5,
        "composite_granularity": 5,
        "human_involvement": {"required": False},
    }


def test_brainstorm_exit_passes_when_scope_package_present(tmp_path: Path) -> None:
    """brainstorm->triage PASSES when the scope-package artifact exists."""
    # governed_root = tmp_path/.uacp; artifact lives at governed_root/brainstorm/<session>/07-scope-package.yaml
    session_id = "test-session-001"
    scope_pkg_dir = tmp_path / ".uacp" / "brainstorm" / session_id
    scope_pkg_dir.mkdir(parents=True)
    scope_pkg_path = scope_pkg_dir / "07-scope-package.yaml"
    scope_pkg_path.write_text("kind: uacp.brainstorm_scope_package\n", encoding="utf-8")

    hg = _make_heartgate(tmp_path)
    artifact = _minimal_brainstorm_triage_artifact("bs-hg-pass-001")
    decision = hg.validate_transition(artifact)

    assert decision.decision != "block", (
        f"Expected PASS or WARN, got BLOCK. blockers={decision.blockers}"
    )


def test_brainstorm_exit_blocks_when_scope_package_missing(tmp_path: Path) -> None:
    """brainstorm->triage BLOCKS when no scope-package artifact exists."""
    # Do NOT create .uacp/brainstorm/*/07-scope-package.yaml
    (tmp_path / ".uacp").mkdir()

    hg = _make_heartgate(tmp_path)
    artifact = _minimal_brainstorm_triage_artifact("bs-hg-block-001")
    decision = hg.validate_transition(artifact)

    assert decision.decision == "block", (
        f"Expected BLOCK (no scope-package), got {decision.decision}. "
        f"blockers={decision.blockers}"
    )
    assert any("07-scope-package.yaml" in b for b in decision.blockers), (
        f"Expected blocker mentioning scope-package path. blockers={decision.blockers}"
    )


def test_illegal_transition_blocked_by_heartgate(tmp_path: Path) -> None:
    """brainstorm->plan is rejected as a disallowed transition by Heartgate."""
    (tmp_path / ".uacp").mkdir()
    hg = _make_heartgate(tmp_path)
    artifact = _minimal_brainstorm_triage_artifact("bs-hg-illegal-001")
    artifact["from_phase"] = "brainstorm"
    artifact["to_phase"] = "plan"
    decision = hg.validate_transition(artifact)
    assert decision.decision == "block"
    assert any("not allowed" in b for b in decision.blockers)
```

### Step 2 — Run, expect PASS

```bash
python3 -m pytest tests/unit/uacp_core/test_heartgate_brainstorm_invariant.py -v 2>&1 | tail -20
```

Expected: all three tests `PASSED`. Specifically `test_brainstorm_exit_blocks_when_scope_package_missing` proves the invariant is non-vacuous (it actually blocks when the file is absent).

### Step 3 — Run full test suite

```bash
python3 -m pytest tests/unit/ -v --tb=short 2>&1 | tail -50
```

Expected: all tests `PASSED`.

### Step 4 — Commit

```bash
git add tests/unit/uacp_core/test_heartgate_brainstorm_invariant.py
git commit -m "test(heartgate): non-vacuous mutation test for brainstorm exit invariant"
```

---

## Out-of-scope follow-up (tracked, not implemented here)

**AGENTS.md invariant-text clarification:** The current AGENTS.md Invariant #1 reads: *"TRIAGE-first — All non-trivial work enters via TRIAGE. No phase-skipping."* After this slice, the correct statement is: *"Non-trivial work enters formal governance via TRIAGE; an optional brainstorm phase may precede it."* This is a docs edit to `AGENTS.md`. It is explicitly out of scope for this skills-focused implementation slice per the design doc, section "Invariant text", and is tracked as a separate follow-up.

---

## Ambiguities found vs. the design doc

1. **`brainstorm→terminal` (explore-and-bail) is descoped from this slice**: `state_machine_projection()` drops every `→terminal` edge, so `brainstorm→terminal` can never be a real transition. DECISION: for this slice, `brainstorm exits_to = {triage}` ONLY. The design doc originally said `exits_to = {triage, terminal}` — that is corrected here and in the design doc. Explore-and-bail (brainstorm→abort) is a tracked follow-up needing the `aborted`-status path designed.

2. **`phase-8-admission.md` references `python3 skills/uacp-core/scripts/core.py check-preflight uacp-brainstorm`**: This CLI sub-command does not exist in `core.py` (grep confirmed). The design doc says "admission contract promoted to real exit invariant", which replaces the check-preflight call — so `phase-8-admission.md` becomes outdated. This plan treats the invariant in `STAGE_PHASE_EXIT_INVARIANTS` as the authoritative enforcement and leaves the reference doc for a follow-up rewrite.

3. **Run-registry semantics for explore-and-bail runs**: The design doc notes "register but mark non-advancing" as an open item. This is deferred together with the `brainstorm→abort` path (item 1 above) — both land in the same follow-up slice.

4. **`uacp_oracle_query` in `STAGE_ALLOWED_TOOLS["brainstorm"]`**: The design doc lists it as a future tool ("once Doc C lands"). This plan omits it from the constant because Doc C (Oracle retrieval engine) does not exist yet. Adding a non-existent tool to the allowlist would confuse Guardian. Add it when Doc C ships.

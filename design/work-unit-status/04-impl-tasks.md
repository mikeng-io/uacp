---
type: design
title: Implementation Task Checklist
description: >-
  The ordered implementation task checklist for shipping work-unit status tracking:
  worktree setup, PIV schema extension (required field), Heartgate gate extension,
  skill doc updates, and the Codeflair blast-radius check.
tags: [tasks, implementation, checklist, worktree, codeflair]
timestamp: 2026-06-26
edges: []
---

# Implementation Task Checklist

> **For agentic workers:** All work happens in a dedicated worktree.
> Run Codeflair blast-radius before touching any shared method.
> Commit per-task when suite is green.
> Automated agents: commit only on `keep` checkpoint verdict.

**Goal:** Extend `forced_execute_evidence_blockers` to derive work_unit
coverage from `after_work_unit` checkpoints, blocking EXECUTE→VERIFY when
required units lack completion. No new artifact kind. No new writer obligation.

**Architecture:** Pure derivation inside Heartgate. PIV `work_unit` schema
gets an optional `required` field. Skill docs add the resume procedure and
`after_work_unit` completion obligation.

**Tech Stack:** Python 3.12+, pytest, PyYAML, existing UACP patterns.

---

## Global Constraints

- **All work in worktree:** `git worktree add .worktrees/wu-status-tracking -b feat/wu-status-tracking`
- Run all tests: `uv run pytest tests/ -x -q` from worktree root
- Gate extension: `skills/uacp-core/scripts/engines/heartgate/heartgate.py`
  method `forced_execute_evidence_blockers` (lines 299–352)
- Schema: `skills/uacp-core/scripts/engines/domain/schema.py`
- Validator: `scripts/validate_uacp_artifacts.py` (repo root)
- **Commit boundary:** one commit per task when suite is green;
  Task 1 (schema only, no test) batches with Task 2 (first test that uses it)
- **Automated agents:** commit only when checkpoint verdict is `keep`

---

### Pre-work: Worktree + Codeflair

Before any code change:

- [ ] Create worktree:
  ```bash
  git worktree add .worktrees/wu-status-tracking -b feat/wu-status-tracking
  cd .worktrees/wu-status-tracking
  ```

- [ ] Build Codeflair index (for blast-radius before editing shared methods):
  ```bash
  cd codeflair && uv run python scripts/bootstrap.py --root ..
  ```

- [ ] Run blast-radius on `forced_execute_evidence_blockers` before touching it:
  ```bash
  uv run python -c "
  from codeflair.query import query
  print(query('forced_execute_evidence_blockers', kind='callers'))
  "
  ```
  Review all callers — confirm no caller assumes the method returns only PIV-related
  messages (the new message format must not break caller expectations).

- [ ] Run baseline suite from worktree: `uv run pytest tests/ -x -q`
  Expected: full green (baseline before any change)

---

### Task 1: Add `required` field to PIV `work_unit` schema

**Files:**
- Modify: `skills/uacp-core/scripts/engines/domain/schema.py`

No new test (constants-only change; batched into Task 2 commit).

- [ ] Find `"work_unit"` shape (around line 67). In its `properties`, add:

```python
"required": {
    "type": "boolean",
    "description": (
        "Whether this work_unit must reach executed before EXECUTE->VERIFY. "
        "Absent = true (required by default)."
    ),
},
```

`required` stays out of the JSON Schema `"required"` list — it is optional
in the PIV shape.

- [ ] Run `uv run pytest tests/ -x -q` — must stay green

---

### Task 2: Extend `forced_execute_evidence_blockers` + tests

**Files:**
- Modify: `skills/uacp-core/scripts/engines/heartgate/heartgate.py`
- Create: `tests/test_wu_status_gate.py`

- [ ] Write the failing test first. Use the exact constructor and path layout
  from `tests/unit/uacp_core/test_transition_integrity.py`:
  - `Heartgate({}, uacp_root=root)` — config is `{}`, `uacp_root` is the temp dir
  - All artifacts live under `root / ".uacp" / ...` (governed namespace)
  - Import via `from core import Heartgate` with sys.path setup

```python
# tests/test_wu_status_gate.py
import sys, pytest, yaml, tempfile
from pathlib import Path

_CORE = Path(__file__).resolve().parents[2] / "skills" / "uacp-core" / "scripts"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from core import Heartgate


def _hg(root: Path) -> Heartgate:
    return Heartgate({}, uacp_root=root)


def _write(root: Path, rel: str, data: dict):
    # All UACP artifacts live under root/.uacp/
    p = root / ".uacp" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.dump(data))


def _piv(run_id, work_units):
    return {
        "kind": "uacp.phase_intent_verification_contract",
        "run_id": run_id, "phase": "plan", "applies_to_phase": "execute",
        "work_units": work_units,
    }


def _checkpoint(run_id, checkpoint_type, work_unit_id=None):
    d = {"kind": "uacp.execution_checkpoint", "run_id": run_id,
         "checkpoint_type": checkpoint_type}
    if work_unit_id:
        d["work_unit_id"] = work_unit_id
    return d


def test_no_checkpoint_no_block():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        assert _hg(root).forced_execute_evidence_blockers("run-bare") == []


def test_all_executed_passes():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root, "plans/r-piv.yaml", _piv("r", [{"id": "wu-1", "intent": "x", "expected_outputs": ["y"]}]))
        _write(root, "executions/r-checkpoint-001.yaml",
               _checkpoint("r", "after_work_unit", "wu-1"))
        assert _hg(root).forced_execute_evidence_blockers("r") == []


def test_missing_after_work_unit_blocks():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root, "plans/r-piv.yaml", _piv("r", [{"id": "wu-1", "intent": "x", "expected_outputs": ["y"]}]))
        _write(root, "executions/r-checkpoint-001.yaml",
               _checkpoint("r", "before_side_effect", "wu-1"))  # not after_work_unit
        blockers = _hg(root).forced_execute_evidence_blockers("r")
        assert any("wu-1" in b for b in blockers)


def test_optional_unit_not_blocking():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root, "plans/r-piv.yaml", _piv("r", [
            {"id": "wu-opt", "intent": "x", "expected_outputs": ["y"], "required": False}
        ]))
        _write(root, "executions/r-checkpoint-001.yaml",
               _checkpoint("r", "before_side_effect", "wu-opt"))
        assert _hg(root).forced_execute_evidence_blockers("r") == []


def test_piv_no_work_units_no_block():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root, "plans/r-piv.yaml", {
            "kind": "uacp.phase_intent_verification_contract",
            "run_id": "r", "phase": "plan", "applies_to_phase": "execute",
        })
        _write(root, "executions/r-checkpoint-001.yaml", _checkpoint("r", "deviation"))
        assert _hg(root).forced_execute_evidence_blockers("r") == []


def test_partial_execution_blocks():
    """Two work_units; only one has after_work_unit checkpoint."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root, "plans/r-piv.yaml", _piv("r", [
            {"id": "wu-a", "intent": "a", "expected_outputs": ["x"]},
            {"id": "wu-b", "intent": "b", "expected_outputs": ["y"]},
        ]))
        _write(root, "executions/r-checkpoint-001.yaml",
               _checkpoint("r", "after_work_unit", "wu-a"))
        # wu-b has no after_work_unit checkpoint
        blockers = _hg(root).forced_execute_evidence_blockers("r")
        assert any("wu-b" in b for b in blockers)
        assert not any("wu-a" in b for b in blockers)
```

- [ ] Run: `uv run pytest tests/test_wu_status_gate.py -v`
  Expected: FAIL (gate not extended yet)

- [ ] In `heartgate.py`, find `forced_execute_evidence_blockers`. Replace the
  final `return []` (line 352) with the derivation block from
  `design/work-unit-status/02-gate-integration.md` (the `# wu-coverage:` block).

- [ ] Run: `uv run pytest tests/test_wu_status_gate.py -v`
  Expected: all pass

- [ ] Run full suite: `uv run pytest tests/ -x -q` — must stay green

- [ ] Commit Tasks 1+2 together (first green suite):
  ```bash
  git add skills/uacp-core/scripts/engines/domain/schema.py \
          skills/uacp-core/scripts/engines/heartgate/heartgate.py \
          tests/test_wu_status_gate.py
  git commit -m "feat(wu-status): derive work_unit coverage in forced_execute_evidence_blockers"
  ```

---

### Task 3: Skill instruction updates

**Files:**
- Modify: `skills/uacp-plan/SKILL.md`
- Modify: `skills/uacp-execute/SKILL.md`

- [ ] In `skills/uacp-plan/SKILL.md`, add the `required` field guidance from
  `design/work-unit-status/03-skill-contract.md`

- [ ] In `skills/uacp-execute/SKILL.md`, add the completion checkpoint
  (`after_work_unit`) and resume procedure from `03-skill-contract.md`

- [ ] Run `uv run pytest tests/ -x -q` — must stay green

- [ ] Commit:
  ```bash
  git add skills/uacp-plan/SKILL.md skills/uacp-execute/SKILL.md
  git commit -m "docs(wu-status): add after_work_unit obligation and resume procedure to skill contracts"
  ```

---

### Task 4: Integration smoke test

**Files:**
- Create: `tests/test_wu_status_integration.py`

- [ ] Write and run:

```python
# tests/test_wu_status_integration.py
import sys, yaml, tempfile
from pathlib import Path

_CORE = Path(__file__).resolve().parents[2] / "skills" / "uacp-core" / "scripts"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from core import Heartgate


def test_resume_scenario():
    """Simulate interrupt + resume: two units, first done, second not yet."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_id = "run-resume"
        uacp = root / ".uacp"

        # PIV with two work_units
        plans = uacp / "plans"
        plans.mkdir(parents=True)
        (plans / f"{run_id}-piv.yaml").write_text(yaml.dump({
            "kind": "uacp.phase_intent_verification_contract",
            "run_id": run_id, "phase": "plan", "applies_to_phase": "execute",
            "work_units": [
                {"id": "wu-a", "intent": "first task", "expected_outputs": ["a.py"]},
                {"id": "wu-b", "intent": "second task", "expected_outputs": ["b.py"]},
            ],
        }))

        ex = uacp / "executions"
        ex.mkdir(parents=True)

        # Agent executes wu-a and is interrupted before wu-b
        (ex / f"{run_id}-checkpoint-001.yaml").write_text(yaml.dump({
            "kind": "uacp.execution_checkpoint",
            "run_id": run_id,
            "checkpoint_type": "after_work_unit",
            "work_unit_id": "wu-a",
        }))

        hg = Heartgate({}, uacp_root=root)

        # Gate blocks: wu-b not done
        blockers = hg.forced_execute_evidence_blockers(run_id)
        assert any("wu-b" in b for b in blockers), blockers
        assert not any("wu-a" in b for b in blockers), blockers

        # Agent resumes, completes wu-b
        (ex / f"{run_id}-checkpoint-002.yaml").write_text(yaml.dump({
            "kind": "uacp.execution_checkpoint",
            "run_id": run_id,
            "checkpoint_type": "after_work_unit",
            "work_unit_id": "wu-b",
        }))

        # Gate passes
        blockers = hg.forced_execute_evidence_blockers(run_id)
        assert blockers == [], blockers
```

- [ ] Run: `uv run pytest tests/test_wu_status_integration.py -v`
  Expected: pass

- [ ] Run full suite: `uv run pytest tests/ -x -q` — must stay green

- [ ] Commit:
  ```bash
  git add tests/test_wu_status_integration.py
  git commit -m "test(wu-status): add interrupt+resume integration test"
  ```

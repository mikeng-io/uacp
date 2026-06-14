# UACP Claude-Code-First Hardening — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a deterministic behavioral E2E harness that drives a full UACP run
(TRIAGE→RESOLVED) through the real Guardian, Heartgate, state machine, and governed
writers — the safety net that must stay green through the later config collapse,
enforcement hook, Pi reviewer, and live smoke test.

**Architecture:** A no-LLM "fake agent" driver issues the same tool calls a real agent
would, each one first evaluated by the real `Guardian` (so a false-block fails the test),
then executed by the real handler. The run is driven through every phase; assertions are
on the **trajectory UACP already emits** — the run manifest's `state_history`, the
gate-ledger JSONL, and the terminal `status` — never on file paths, so the suite survives
the Phase 2 config refactor.

**Tech Stack:** Python 3.14, pytest, Pydantic v2, PyYAML. Reuses
`skills/uacp-core/scripts/core.py` (Guardian, Heartgate), `skills/uacp-state/scripts/`
(`state_machine.py`, `state.py`), and the existing `tests/conftest.py` fixtures.

**Design doc:** `docs/plans/2026-06-14-uacp-cc-hardening-design.md`

---

## Reference: verified signatures (read before starting)

- `state_machine.handle_init(args) -> str(json)` — needs `workspace`, `run_id`, `source`.
  Creates `state/runs/<run_id>.yaml` (phase `triage`, status `active`) + `state/current.yaml`.
- `state_machine.handle_transition(args) -> str(json)` — needs `workspace`, `run_id`,
  `from_phase`, `to_phase`. Graph: `triage→propose→plan→execute→verify→resolved`.
  Returns `{"error": ...}` (not an exception) on a bad transition.
- `state_machine.handle_finalize(args) -> str(json)` — run must be in a terminal phase
  (`resolved`/`aborted`); sets `status=resolved`, stamps `finalized_at`.
- `state.handle_register_artifact(args)` lives in `state_machine` as
  `handle_register_artifact(args)`; gate ledger is `state._handle_uacp_gate_ledger_append(args)`.
- `core.Guardian(policy).evaluate(GuardianEvent) -> decision` with `.decision`,
  `.category`, `.blockers`. Allow constants: `DECISION_ALLOW`, `DECISION_ALLOW_WITH_AUDIT`.
- `core.Heartgate.load(workspace).validate_transition({from_phase,to_phase,run_id,artifact_path}) -> decision`
  with `.decision` (`"pass"`/`"warn"`/`"block"`) and `.blockers`.
- Fixtures (`tests/conftest.py`): `temp_uacp_root` (chdir'd temp root w/ minimal
  guardian-policy + phase-transitions), `valid_run_id`. **Note the fixture's
  phase-transitions stages differ from `VALID_TRANSITIONS`** (Task 1 reconciles this).

---

## Task 1: Extend the fixture so its phase graph matches `VALID_TRANSITIONS`

**Files:**
- Modify: `tests/conftest.py:65-94` (the `phase-transitions.yaml` body in `temp_uacp_root`)

The fixture's stages (`triage→propose`, `propose→execute`, ...) skip `plan` and don't end
in `resolved`, so Heartgate would block the real lifecycle. Make the fixture graph match
the kernel's `VALID_TRANSITIONS` exactly.

**Step 1:** In `temp_uacp_root`, replace the `phase_path.write_text(...)` stages block so
`exits_to` is: `triage→[propose]`, `propose→[plan]`, `plan→[execute]`, `execute→[verify]`,
`verify→[resolved]`. Keep `allowed_tools` permissive (include `uacp_state_write`,
`uacp_gate_ledger_append`, `read_file`, `write_file` in every stage).

**Step 2:** Run the existing suite to confirm no regression.

Run: `pytest tests/ -q`
Expected: PASS (same count as before; the fixture change must not break existing tests —
if `test_heartgate_*` asserts on the old graph, update those assertions to the new graph).

**Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: align test fixture phase graph with kernel VALID_TRANSITIONS"
```

---

## Task 2: The fake-agent driver helper

**Files:**
- Create: `tests/e2e/__init__.py` (empty)
- Create: `tests/e2e/driver.py`
- Test: (exercised by Task 3+)

**Step 1: Write the driver** — a Guardian-in-the-loop tool-call dispatcher. Each call is
evaluated by the real Guardian first; a block raises `AssertionError` (that IS the
F1 false-block test).

```python
"""Fake-agent driver: issues governed tool calls through the real Guardian + handlers."""
from __future__ import annotations

import json
from pathlib import Path

from core import DECISION_ALLOW, DECISION_ALLOW_WITH_AUDIT, Guardian, GuardianEvent, GuardianPolicy

_ALLOW = {DECISION_ALLOW, DECISION_ALLOW_WITH_AUDIT}


def make_event(tool_name: str, tool_args: dict, *, run_id: str, phase: str, root: Path) -> GuardianEvent:
    return GuardianEvent(
        runtime="test", adapter="e2e", event_type="tool_call", tool_provider="core",
        tool_name=tool_name, tool_args=tool_args, uacp_run_id=run_id, uacp_phase=phase,
        workspace=str(root), policy_version="0.1",
        declared_authority="plans/test.yaml", declared_side_effects=[],
    )


class Driver:
    """Drives governed tool calls; asserts Guardian never false-blocks a legit call."""

    def __init__(self, root: Path, run_id: str):
        self.root = root
        self.run_id = run_id
        self.guardian = Guardian(GuardianPolicy.load(str(root)))

    def call(self, tool_name: str, handler, args: dict, *, phase: str) -> dict:
        event = make_event(tool_name, args, run_id=self.run_id, phase=phase, root=self.root)
        decision = self.guardian.evaluate(event)
        assert decision.decision in _ALLOW, (
            f"Guardian FALSE-BLOCKED legit call {tool_name} in {phase}: "
            f"{decision.decision} / {getattr(decision, 'blockers', None)}"
        )
        return json.loads(handler(args))
```

**Step 2:** Sanity-check it imports under the fixture's `sys.path`.

Run: `pytest tests/e2e -q` (collects nothing yet)
Expected: no import errors.

**Step 3: Commit**

```bash
git add tests/e2e/__init__.py tests/e2e/driver.py
git commit -m "test: add fake-agent driver for E2E lifecycle harness"
```

---

## Task 3: Happy-path full-lifecycle test (the core safety net)

**Files:**
- Create: `tests/e2e/test_full_lifecycle.py`

**Step 1: Write the failing test.** Driver runs INIT → (per phase: gate-ledger append +
transition) → FINALIZE, asserting on the trajectory.

```python
"""E2E: a full run threaded through real Guardian/Heartgate/state machine/writers."""
from __future__ import annotations

import yaml
from pathlib import Path

import state_machine
from core import Heartgate
from state import _handle_uacp_gate_ledger_append
from tests.e2e.driver import Driver

PHASES = [("triage", "propose"), ("propose", "plan"), ("plan", "execute"),
          ("execute", "verify"), ("verify", "resolved")]


def test_full_lifecycle_reaches_resolved(temp_uacp_root: Path, valid_run_id: str):
    d = Driver(temp_uacp_root, valid_run_id)
    heartgate = Heartgate.load(str(temp_uacp_root))

    init = d.call("uacp_state_write", lambda a: state_machine.handle_init(a),
                  {"workspace": str(temp_uacp_root), "run_id": valid_run_id,
                   "source": "operator-request"}, phase="triage")
    assert init.get("ok") is True, init

    for frm, to in PHASES:
        ledger = d.call("uacp_gate_ledger_append", _handle_uacp_gate_ledger_append,
                        {"uacp_run_id": valid_run_id, "uacp_phase": frm,
                         "workspace": str(temp_uacp_root), "policy_version": "0.1",
                         "declared_side_effects": [], "gate": f"{frm.upper()}->{to.upper()}",
                         "record": {"result": "pass"}, "authority_artifact": "plans/test.yaml"},
                        phase=frm)
        assert ledger.get("ok") is True, ledger

        hg = heartgate.validate_transition({"from_phase": frm, "to_phase": to,
                                            "run_id": valid_run_id, "artifact_path": "plans/test.yaml"})
        assert hg.decision == "pass", f"Heartgate blocked legit {frm}->{to}: {hg.blockers}"

        tr = d.call("uacp_state_write", lambda a: state_machine.handle_transition(a),
                    {"workspace": str(temp_uacp_root), "run_id": valid_run_id,
                     "from_phase": frm, "to_phase": to}, phase=frm)
        assert tr.get("ok") is True, tr

    fin = d.call("uacp_state_write", lambda a: state_machine.handle_finalize(a),
                 {"workspace": str(temp_uacp_root), "run_id": valid_run_id}, phase="verify")
    assert fin.get("ok") is True and fin["status"] == "resolved", fin

    # --- Assert on the emitted trajectory ---
    manifest = yaml.safe_load((temp_uacp_root / "state" / "runs" / f"{valid_run_id}.yaml").read_text())
    assert manifest["status"] == "resolved"
    assert manifest["current_phase"] == "resolved"
    assert manifest["finalized_at"] is not None
    transitions = [h for h in manifest["state_history"] if h["event"] == "phase_transition"]
    assert [(h["from_phase"], h["to_phase"]) for h in transitions] == PHASES

    ledger_lines = (temp_uacp_root / "state" / "gate-ledger" / f"{valid_run_id}.jsonl").read_text().strip().split("\n")
    assert len(ledger_lines) == len(PHASES)
```

**Step 2: Run to verify it fails** (driver/import wiring or fixture graph).

Run: `pytest tests/e2e/test_full_lifecycle.py -v`
Expected: FAIL initially (e.g. Heartgate block if Task 1 incomplete, or import path).

**Step 3: Make it pass** — fix whatever the failure surfaces (most likely the fixture
graph from Task 1, or a `sys.path` entry for `tests.e2e` — add an `__init__.py` at
`tests/` if needed so `tests.e2e.driver` imports).

**Step 4: Run to verify it passes**

Run: `pytest tests/e2e/test_full_lifecycle.py -v`
Expected: PASS — full lifecycle reaches `resolved`, Guardian allowed every call,
Heartgate passed every transition.

**Step 5: Commit**

```bash
git add tests/e2e/test_full_lifecycle.py tests/__init__.py
git commit -m "test: E2E happy-path full-lifecycle harness (TRIAGE->RESOLVED)"
```

---

## Task 4: Full transition matrix (every from×to cell)

> **Premise (operator):** *each phase and transition will have lots of bugs.* The harness's
> job is to **surface** them in pytest, not to prove a single happy path. Every red test
> here is a bug found cheaply instead of mid-work. **Do not paper over a failure — open a
> fix-commit for it (Task 4b).**

**Files:**
- Create: `tests/e2e/test_transition_matrix.py`

**Step 1: Write the parametrized matrix.** For every ordered pair of phases, assert the
state machine + Heartgate agree: allowed pairs pass, every other pair is refused **cleanly
with a reason** (structured error / `block` + non-empty `blockers`), never a stack trace.

```python
import json, pytest, state_machine
from core import Heartgate
from tests.e2e.driver import Driver

PHASES = ["triage", "propose", "plan", "execute", "verify", "resolved"]
ALLOWED = {("triage","propose"),("propose","plan"),("plan","execute"),
           ("execute","verify"),("verify","resolved")}
PAIRS = [(f, t) for f in PHASES for t in PHASES if f != t]

@pytest.mark.parametrize("frm,to", PAIRS)
def test_transition_cell(temp_uacp_root, valid_run_id, frm, to):
    """Every from->to cell: state machine + Heartgate must agree and never raise."""
    state_machine.handle_init({"workspace": str(temp_uacp_root), "run_id": valid_run_id,
                               "source": "operator-request"})
    # Fast-forward the manifest to `frm` only via legal steps; skip cells whose `frm`
    # is unreachable as a no-op (the matrix still covers them from the Heartgate side).
    hg = Heartgate.load(str(temp_uacp_root)).validate_transition(
        {"from_phase": frm, "to_phase": to, "run_id": valid_run_id,
         "artifact_path": "plans/test.yaml"})
    if (frm, to) in ALLOWED:
        assert hg.decision == "pass", f"{frm}->{to} should pass: {hg.blockers}"
    else:
        assert hg.decision == "block", f"{frm}->{to} should block, got {hg.decision}"
        assert hg.blockers, f"{frm}->{to} blocked without a reason"
```

**Step 2: Run** — `pytest tests/e2e/test_transition_matrix.py -v`. Expected: most cells
PASS; **any unexpected pass/block is a real bug** — record it for Task 4b.

**Step 3: Commit** — `test: E2E full transition matrix (every from x to cell)`.

---

## Task 4b: Per-phase gate + tool-allowlist matrix

**Files:**
- Create: `tests/e2e/test_phase_gates.py`

For each phase, drive these through the real Guardian + Heartgate and assert clean
behavior (this is where most per-phase bugs live):

1. **Tool allowlist** — a tool *allowed* in that phase is permitted; a tool *forbidden*
   in that phase (e.g. `terminal`/`execute_code` outside `execute`) is blocked with a
   reason. Parametrize over (phase, tool).
2. **Exit invariant** — transition out of the phase with the required artifact/ledger
   entry **missing** → Heartgate blocks with a reason; with it **present** → passes.
3. **Malformed artifact** — register an artifact for the phase missing a required field
   (per `config/artifact-schemas.yaml`) → clean refusal, never a raise.

**Step 1:** Write the parametrized tests (one matrix per concern above).
**Step 2:** Run `pytest tests/e2e/test_phase_gates.py -v`. **Expect failures here** — log
each as a finding. **Step 3:** Commit `test: E2E per-phase gate + tool-allowlist matrix`.

---

## Task 4c: Triage and fix the surfaced bugs (loop until green)

For each failing cell from Tasks 4/4b: (a) confirm it's a real bug vs. a wrong test
expectation; (b) if a kernel bug, write the minimal fix in `core.py` / `state_machine.py`
/ `state.py`; (c) re-run; (d) commit one fix per bug: `fix(kernel): <phase/transition> —
<bug>`. If it's a test-expectation error, fix the test and say so in the message. Keep
looping until `pytest tests/e2e -v` is fully green. **Track the count of real bugs found**
— that number is the value Phase 1 delivered.

---

## Task 5: Fixture registry for golden artifacts

**Files:**
- Create: `tests/e2e/fixtures/README.md` (what these are; they double as real-run templates)
- Create: `tests/e2e/fixtures/proposal.yaml`, `plan.yaml`, `checkpoint.yaml`,
  `verification.yaml`, `closure.yaml` (minimal valid artifacts matching
  `config/artifact-schemas.yaml`)

**Step 1:** Read `config/artifact-schemas.yaml` and author one minimal valid instance per
artifact kind. **Step 2:** Add a test that loads each fixture and asserts it parses as a
YAML mapping with the schema's required top-level keys. **Step 3:** Run
`pytest tests/e2e -q` (PASS). **Step 4:** Commit
`test: golden artifact fixtures for E2E lifecycle`.

---

## Task 6: CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

**Step 1:** Write a workflow: on push/PR, set up Python 3.14, install
`pip install -e .` (or deps from `pyproject.toml`), run `pytest tests/ -q`. **Step 2:**
Validate YAML locally (`python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"`).
**Step 3:** Commit `ci: run pytest (incl. E2E harness) on push and PR`. **Step 4:** Push
the branch and confirm the run goes green on GitHub.

---

## Phase 1 done-when

- `pytest tests/e2e -v` is fully green: happy path reaches `resolved`, **and** the full
  transition matrix (Task 4) + per-phase gate/tool matrix (Task 4b) all pass.
- Every bug the matrices surfaced is either fixed (one `fix(kernel): ...` commit each) or
  consciously deferred with a logged reason — **none silently papered over**.
- No governed call raises; every illegal transition / missing-artifact / forbidden-tool
  case is refused with a human-readable reason, not a stack trace.
- CI runs the whole suite on every push/PR.
- **Deliverable metric:** the count of real per-phase/per-transition bugs found and fixed
  — the harness exists to make that number large now (in pytest) instead of later (mid-work).

---

# Roadmap — Phases 2–5 (own plans authored after Phase 1 lands)

These are intentionally **not** broken into bite-sized tasks yet: each depends on the
exact shape Phase 1 pins down (and Phase 2 changes where config lives). Author a dedicated
plan for each when its predecessor is green.

### Phase 2 — Config collapse (harness guards it)
- Introduce `config.toml` + `config.py` (typed accessor, validated). Migrate knobs from
  `guardian-policy`, `autonomy-policy`, `model-registry`, `runtime-bindings`, `roots`,
  `memory-policy`, `version-control`, `review-routing`, `uacp.toml`, `gate-selection`.
- Move grammar to Python: `phase-transitions.yaml` (859 lines) and `artifact-schemas.yaml`
  become Pydantic models + constants beside `VALID_TRANSITIONS`. Port **one stage at a
  time, harness green after each**.
- **F-T3-01 fix (decision-log 2026-06-15):** normalize ALL adaptive gates to
  **fail-closed** — absent config key = enforce. Add a regression test asserting an
  absent gate key enforces (kills the "advisory-in-disguise" F4 risk).
- Delete the prose-tier YAMLs; fold residual guidance into owning skills.
- Update `Guardian`/`Heartgate` load paths to read via `config.py`.
- **Gate:** `pytest tests/` stays 100% green throughout.

### Phase 3 — Claude Code enforcement hook
- `.claude/settings.json` `PreToolUse` → `guardian_hook.py`: read CC hook payload from
  stdin, reconstruct context from `state/current.yaml` + manifest, call
  `Guardian.evaluate()`, emit CC block/allow JSON.
- New tests: payload→GuardianEvent mapping; context reconstruction; block decision →
  CC-format deny.

### Phase 4 — `bridge-pi` + bridge consolidation
- Collapse `skills/bridge-{claude,codex,commons,gemini,kimi,opencode}` →
  `skills/uacp-bridge/` (`SKILL.md` = ex-`bridge-commons`; `providers/*.md`).
- Add `providers/pi.md`: `pi --version` availability; print/JSON invocation; verdict
  parse → bridge-commons output schema; read-only via prompt + worktree.
- Reviewer routing now lives in `config.toml`; register Pi as the cheap tier.
- Update `AGENTS.md`, `CLAUDE.md`, `docs/INDEX.md` references to old paths.

### Phase 5 — Live smoke test
- `claude -p --dangerously-skip-permissions` on a trivial safe task in a throwaway
  worktree. Assert: reaches RESOLVE w/ zero gate-ledger errors; a deliberate `Write` to
  `main` is blocked by the Phase 3 hook.

### Deferred (gap ledger)
bwrap/contained-shell · multi-run concurrency E2E · adaptive-gate selection-predicate
testing · LLM-as-judge · crypto/Fabric/ZK.

---

## Findings log (discovered during execution)

- **F-T3-01 (kernel inconsistency, → Phase 2):** `core.py` uses two different
  absent-config idioms. `~line 950` (`self.config.get(key) or {}`) makes the
  proposal/plan adaptive gates **enforce** when their config key is absent; `~line 1202`
  (`if not isinstance(self.config.get(key), Mapping): return`) makes the
  execute/verify/resolve gates **self-disable** when absent. Result: under a minimal
  `phase-transitions.yaml`, proposal/plan gates fire but execute/verify/resolve gates
  silently don't. **DECISION (2026-06-15, decision-log):** defer the kernel change to
  Phase 2 (which rewrites this grammar into Python); normalized behavior is
  **fail-closed** — absent config = enforce. Not a Task 4c item.
- **F-T3-02 (fidelity gap, → new follow-up task):** the happy-path lifecycle test only
  exercises ~2 of 5 adaptive gates with real evidence; the other 3 self-disable under the
  minimal conftest fixture. Add a follow-up E2E that runs against the real 859-line
  `config/phase-transitions.yaml` (or a fixture enabling all five adaptive gates) so
  execute/verify/resolve evidence gates are actually enforced.
- **F-T3-03 (environment, → Task 6 CI):** the default `python` on this machine is
  anaconda 3.8, which cannot parse the codebase's PEP-604 `X | None` syntax. Tests require
  Python 3.13+ (3.14 confirmed). CI must pin an appropriate interpreter. **[done — CI
  pins 3.13/3.14]**

### Final-review follow-ups (non-blocking, → Phase 2 / polish)

- **F-FR-01:** the happy-path lifecycle test reaches `resolved` while the
  execute/verify/resolve adaptive evidence gates self-disable under the minimal fixture —
  so it does NOT exercise them. Add a consequence-level note in the test, and (with
  F-T3-02) an E2E against the real config that enforces all five gates.
- **F-FR-02:** the transition matrix pins the **fixture's synthetic** graph (`resolved`),
  not the **production** graph (`resolve`→`terminal`). The production transition graph
  currently has zero E2E legality coverage. Add a production-graph matrix in Phase 2.
- **F-FR-03 (polish):** the `GuardianEvent` builder is duplicated (`driver.make_event` vs
  `test_phase_gates._make_event`, differing only by `filesystem_guard_verified`). Factor
  into `driver.make_event(..., filesystem_guard_verified=False)`.
- **F-FR-04 (polish):** CI — `pytest -q` conflicts with `addopts = -v` (cosmetic); add
  path filters + `concurrency` cancellation so doc-only pushes don't burn minutes.

---
type: analysis
title: Grounding defects — reality-capable tooling left agent-elected or advisory
description: D-04 to D-08. The sharpest is that a claimed fix is checked less than a claimed exception.
tags: [grounding, evidence, verification, findings]
timestamp: 2026-08-22
edges:
  - {dst: 00-register, rel: depends_on, provenance: derived}
  - {dst: 10-enforcement-bypass, rel: extends, provenance: asserted}
---

# Grounding defects

## D-04 — A claimed fix is checked less than a claimed exception · VERIFIED

The sharpest defect in the register, because the counter-example sits in the same validator.

`skills/uacp-core/scripts/engines/rework_completeness.py:261`:

```python
if cls in _REMEDIATION_CLASSES:              # {"remediated", "expanded"}
    return bool(_str_field(entry, "handling_artifact_path"))
```

A finding disposed as `remediated` discharges on a **non-empty string**. The path is never
resolved, never checked to exist, never bound to the run, never tied to a checkpoint or a diff.

Now `scripts/validate_uacp_artifacts.py:271-276`, on `accepted_exceptions[].artifact_path`:

```
:271  must start with "verification/" or "resolutions/"   → BLOCK
:273  must be run-bound                                    → BLOCK
:275  must exist on disk                                   → BLOCK
```

So UACP grounds the claim *"we decided not to fix this"* with three hard checks, and grounds the
claim *"we fixed this"* with a truthiness test on a string.

The asymmetry is what makes this a defect rather than a design choice. The disposition grammar
around it is genuinely rich — five finding classes, six handling classes partitioned
HARD_FOLLOWUP / CARRY_FORWARD, per-class required evidence, `rejected_with_reason` as a typed
pushback path, a bounded follow-up depth (`rework_completeness.py:104-148`). All of that
structure is enforced. The one field that would bind a fix to reality is not.

This is the mechanism behind *remediated-by-assertion*: not missing doctrine, a missing
existence check that already exists ten lines away in a sibling code path.

## D-05 — The generative gate is opt-in in code, mandatory in prose · VERIFIED

`skills/uacp-core/scripts/engines/manifest/projection.py:481`:

```python
if not any(n["kind"] == "check" for n in nodes.values()):
    return []
```

with the comment above it (`:478-480`) stating the consequence outright: *"it does NOT force a
zero-check run to adopt checks (L2). Structural coverage is necessary, not sufficient."*

`skills/uacp-verify/SKILL.md` and `skills/uacp-plan/SKILL.md` read as obligations to author
frozen verification checks. A run that authors none passes `plan_exit`, `execute_exit`,
`verify_exit`, and closure with no check-derived violation. The floor
(`config/verification-floor.yaml`) then constrains only the classes the agent itself declared.

What is genuinely strong here, and worth not breaking: once a check exists, it is honest. Replay
hardcodes `sev = "block"` for FAIL *and* ERROR so an agent cannot author `severity: warn` and
ship failing work; `catalog_version` is writer-injected; checks are write-once and id-unique per
run. The freeze is real. Adoption is not.

## D-06 — The code plane is unreachable · VERIFIED

`engines/code_plane.py` answers `symbol_resolves` against a SCIP SQLite index and ERRORs (→
block) when the index is absent. The index is built by `engines/code_index_build.py`.

`build_code_index` has **zero production callers**. Every reference in the repo is
`tests/e2e/test_code_index_build.py` or a worktree copy of it, plus one prose instruction in
`skills/uacp-core/references/generative-gate-authoring.md` telling the agent to call it.

So the strongest static-grounding plane UACP has is reachable only if an agent manually builds
its index first, and nothing builds it as part of any lifecycle operation. Combined with D-05,
the practical default is that neither reality plane ever runs.

## D-07 — The only independent witness is advisory · VERIFIED

`engines/scope_conformance.py` computes the **actual git change set** and compares it against
the declared `write_paths` — the one place in the kernel where an external observer, not the
agent's own record, supplies the input. Both outcomes are `severity="warn"`:

- `SC_DIFF_UNAVAILABLE` (`:513`)
- `SC_DIFF_OUT_OF_SCOPE` (`:526`)

Every blocking check in the engine compares declaration against declaration. The module says so
itself (`:24-27`): the kernel keeps no per-write audit log, so containment *"is NOT computable
from state alone"*. Git is the answer to that, and it is wired to warn.

## D-08 — The rework cap has no breaker, though the pattern exists in-repo · VERIFIED

`rework_completeness.py:159` sets `_DEFAULT_MAX_REWORK_DEPTH = 5`, tunable via
`[heartgate] max_rework_depth`. On reaching it, `RW_REWORK_DEPTH_ESCALATION` fires as a
**warning, never a block**. Nothing defines what must happen when a run has reworked itself five
times: no forced adjudication, no requirement to record why the loop is not converging, no
change of question.

UACP already knows how to build this. `heartgate/validators/ppv.py:202-211`:

```python
action = str(ppv_rule.get("second_failure_action") or "block_unconditional")
...
if len(failing_attempts) >= max_attempts and action == "block_unconditional":
    blockers.append(f"ppv_rule: {len(failing_attempts)} failed PPV attempts …")
```

A cap **with** a defined, fail-closed trip action, codified as code-default grammar
(`engines/domain/gate_rules.py:392-393`). The defect is that this pattern was built once, for
PPV, and not applied to the loop that most needs it.

---
type: design-node
title: Heartgate Gate Integration
bundle: work-unit-status
tags: [heartgate, gate, execute, verify, goal-driven]
timestamp: 2026-06-26
---

# Heartgate EXECUTE→VERIFY Gate Integration

## Seam: `forced_execute_evidence_blockers` (standard track branch)

File: `skills/uacp-core/scripts/engines/heartgate/heartgate.py`, lines 299–352.

The method already branches on track type (line 335). The new derivation
goes in the standard-track path, after the PIV identity check, replacing
the final `return []`:

```python
        # wu-coverage: derive executed units from after_work_unit checkpoints.
        # Only runs when a PIV with work_units is present (already loaded above).
        work_units = doc.get("work_units", [])
        if work_units:
            executed_ids: set[str] = set()
            for cp_path in executions.glob(f"{run_id}-checkpoint-*.yaml"):
                try:
                    cp = yaml.safe_load(cp_path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if isinstance(cp, dict) and cp.get("checkpoint_type") == "after_work_unit":
                    wu_id = cp.get("work_unit_id")
                    if wu_id:
                        executed_ids.add(wu_id)
            missing = [
                wu["id"]
                for wu in work_units
                if wu.get("required", True) and wu["id"] not in executed_ids
            ]
            if missing:
                return [
                    f"{prefix} required work_units lack after_work_unit checkpoint: {missing}"
                ]
        return []
```

## Self-Gate (adaptive boundary)

The existing self-gate on checkpoint presence (line 332) already covers this:
```python
if not any(executions.glob(f"{run_id}-checkpoint-*.yaml")):
    return []
```
No checkpoints → bare/ungoverned EXECUTE → no ripple. The new code only runs
when checkpoints exist AND a PIV is present with `work_units`.

A PIV with no `work_units` list (empty or absent) → `if work_units:` is False
→ skip derivation → `return []`. No regression for runs without work_units.

## Goal-Driven Branch (unchanged)

Lines 335–338 handle goal-driven runs before reaching the new code:
```python
if self._run_track(run_id) == "goal-driven":
    blockers: list[str] = []
    self._validate_goal_driven_checkpoint_gate(run_id, blockers)
    return blockers
```
Goal-driven runs exit here. The wu-status derivation is never reached.

## No Gate Constants Needed

Because the logic lives inside `forced_execute_evidence_blockers` and is not
a separate rule, no new constants in `gate_rules.py` are required. The
existing `prefix` variable from that method covers error message formatting.

## VERIFY Integration

No change. VERIFY already consumes the PIV + checkpoints to assess obligations.
The derivation above is Heartgate's read path only — VERIFY does not write
status anywhere.

#!/usr/bin/env python3
"""Executable calibration set — P1 and P2, demonstrated against the CURRENT tree.

Node 70 rests its non-convergence verdict on two defects an external reviewer found and
UACP's own verify did not. Citing them to a branch made them unreproducible; transcribing
excerpts made them abridged. This probe removes both objections: it DEMONSTRATES each
defect by running against whatever tree it is invoked in, so the evidence is executable
rather than quoted, and it fails loudly if a defect has been fixed (which is the outcome
you want — it then becomes a regression guard).

    python3 design/kernel-defect-register/evidence/p1-p2-calibration-probe.py

Exit 0 = both defects still present (the state node 70 describes).
Exit 1 = at least one is fixed — update node 70's Status/Checkpoint.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "uacp-state" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "uacp-core" / "scripts"))

findings: list[tuple[str, bool, str]] = []

# ---------------------------------------------------------------- P1
# The transition path replays `deferred_items` by reading the RAW manifest, because the
# RunManifest model does not carry the field. _save_manifest serializes RunManifest — so
# the first save after a run records deferred_items DELETES them from disk.
import state_machine as sm  # noqa: E402

model_fields = set(sm.RunManifest.model_fields)
p1_present = "deferred_items" not in model_fields
findings.append((
    "P1  RunManifest drops deferred_items on save",
    p1_present,
    f"RunManifest.model_fields has {len(model_fields)} fields; 'deferred_items' "
    f"{'ABSENT (defect present)' if p1_present else 'now modelled (defect FIXED)'}",
))

# Demonstrate the loss end-to-end: a raw manifest carrying deferred_items, round-tripped
# through the model the saver uses, comes back without them.
raw = {
    "run_id": "probe-run",
    "authority": {"source": "probe", "status": "pass"},
    "deferred_items": [{"id": "d1", "owner": "probe", "next_phase_obligation": "carry it"}],
}
round_tripped = sm.RunManifest(**{k: v for k, v in raw.items() if k in model_fields}).model_dump()
p1_roundtrip_loses = "deferred_items" not in round_tripped
findings.append((
    "P1  round-trip actually loses the obligations",
    p1_roundtrip_loses,
    f"in={sorted(raw)} -> out={sorted(round_tripped)[:6]}...  "
    f"deferred_items {'LOST' if p1_roundtrip_loses else 'preserved'}",
))

# ---------------------------------------------------------------- P2
# _state_policy()'s docstring promises the workspace copy is "overlaid"; the body assigns
# `out = raw`, so a PARTIAL workspace override replaces the shipped doctrine wholesale.
import inspect  # noqa: E402

# The function was `_state_policy` at 545e3886 and is `_load_state_yaml` on main — resolve
# whichever this tree has, so the probe survives a rename.
_fn = getattr(sm, "_state_policy", None) or getattr(sm, "_load_state_yaml", None)
if _fn is None:
    print("neither _state_policy nor _load_state_yaml exists — inspect manually"); sys.exit(1)
src = inspect.getsource(_fn)
p2_present = "out = raw" in src and "overlaid" in src
findings.append((
    "P2  state-policy loader replaces instead of overlaying",
    p2_present,
    "docstring says 'overlaid' AND body assigns 'out = raw'"
    if p2_present
    else "no longer both — inspect the function (defect FIXED or reworded)",
))

# ---------------------------------------------------------------- report
width = max(len(n) for n, _, _ in findings)
print("calibration probe — P1/P2 against", ROOT)
print()
for name, still_present, detail in findings:
    print(f"  [{'DEFECT PRESENT' if still_present else 'FIXED'}] {name:<{width}}  {detail}")
print()
all_present = all(p for _, p, _ in findings)
print("VERDICT:", "both defects reproduce — node 70 stands as written"
      if all_present else "at least one is fixed — update node 70's Status/Checkpoint")
sys.exit(0 if all_present else 1)

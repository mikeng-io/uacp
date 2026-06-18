"""Regression test for the RESOLVE-phase exit invariant against the REAL repo
``config/phase-transitions.yaml`` (closes the F-EV-01 coverage gap).

WHY THIS EXISTS — the bug this locks closed:
Slice 2 relocated UACP runtime dirs under ``.uacp/`` and renamed the flat
``.outputs/`` artifact dir to ``resolutions/``. Stored path strings are
BASE-RELATIVE: the kernel resolves an ``artifact_glob`` under ``.uacp/`` (see
``engines.io.glob_in_workspace``). A residual ``.outputs/`` token in the RESOLVE
``phase_exit_invariant`` therefore makes the kernel glob under the nonexistent
``.uacp/.outputs/`` and wrongly emit ``EV_RESOLVED_WITHOUT_EVIDENCE`` — a false
"missing artifact" block on closure of an otherwise-complete run.

WHY IT WASN'T CAUGHT:
The conftest ``temp_uacp_root`` fixture seeds a MINIMAL
``config/phase-transitions.yaml`` with NO ``phase_exit_invariants``, and the
existing ``test_evidence_completeness`` suite overwrites the workspace config
with a SYNTHETIC ``_EVIDENCE_CONFIG``. Neither path ever reads the REAL repo
config's resolve invariant, so reverting its glob token to ``.outputs/{run_id}*``
would not fail any test. This test copies the REAL repo config into the workspace
and exercises that invariant, so the token shape is now load-bearing under CI.

DESIGN:
* The happy-path run finishes with ``status == 'resolved'`` and a ``verify->resolved``
  transition (so ``resolve`` is NOT in ``_completed_phases``). That triggers the
  engine's dedicated "resolved without evidence" branch (branch 2), which checks
  the ``resolve`` stage's own required exit invariants on disk/ledger.
* The real ``resolve`` stage declares TWO required invariants:
  ``artifact_glob: resolutions/{run_id}*`` and ``gate_ledger_entry: VERIFY->RESOLVE``.
  The happy path emits the ``VERIFY->RESOLVED`` gate (note the trailing D), so we
  append the ``VERIFY->RESOLVE`` gate to satisfy the ledger invariant and ISOLATE
  the artifact-glob token as the single variable under test.
* Positive: lessons artifact present under ``.uacp/resolutions/`` ->
  NO ``EV_RESOLVED_WITHOUT_EVIDENCE``.
* Negative: same run, artifact removed -> the invariant DOES block.

If someone reverts the real config's glob to ``.outputs/{run_id}*``, the positive
assertion fails (the artifact lives under ``.uacp/resolutions/`` but the kernel
would glob ``.uacp/.outputs/``), re-surfacing the bug. That is the lock.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from engines.evidence_completeness import validate_evidence_completeness

from tests.e2e.test_coherence import seed_coherent_run

# The real lifecycle config that ships in the repo — the artifact under test.
_REPO_CONFIG = Path(__file__).resolve().parents[2] / "config" / "phase-transitions.yaml"


def _install_real_config(root: Path) -> None:
    """Replace the workspace's minimal conftest config with the REAL repo config,
    so the engine reads the actual ``resolve`` phase_exit_invariants (incl. its
    ``resolutions/{run_id}*`` artifact-glob token)."""
    shutil.copyfile(_REPO_CONFIG, root / "config" / "phase-transitions.yaml")


def _satisfy_resolve_ledger_gate(root: Path, run_id: str) -> None:
    """The real ``resolve`` stage also requires a ``VERIFY->RESOLVE`` gate-ledger
    entry; the happy path emits ``VERIFY->RESOLVED`` (different gate). Append the
    required gate so the LEDGER invariant is satisfied and the ARTIFACT-glob token
    is the only variable this test exercises."""
    ledger_path = root / ".uacp" / "state" / "gate-ledger" / f"{run_id}.jsonl"
    line = json.dumps({"gate": "VERIFY->RESOLVE", "run_id": run_id, "ts": 0, "result": "pass"})
    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _codes(violations) -> set[str]:
    return {v.code for v in violations}


def _resolved_run_against_real_config(root: Path, run_id: str) -> None:
    """A genuinely-resolved happy-path run, read against the REAL repo config, with
    the resolve-phase ledger gate satisfied. ``seed_coherent_run`` already authored
    the lessons artifact under ``.uacp/resolutions/{run_id}-lessons.yaml``."""
    seed_coherent_run(root, run_id)
    _install_real_config(root)
    _satisfy_resolve_ledger_gate(root, run_id)


# --------------------------------------------------------------- positive (lock)
def test_resolve_invariant_satisfied_by_resolutions_artifact(
    temp_uacp_root: Path, valid_run_id: str
):
    """The RESOLVE exit artifact lives under ``.uacp/resolutions/`` and the REAL
    config globs ``resolutions/{run_id}*`` (base-relative, resolved under .uacp/),
    so a resolved run is NOT falsely blocked.

    This FAILS if the config glob token is reverted to ``.outputs/{run_id}*`` —
    the artifact resolves under ``.uacp/resolutions/`` but the kernel would glob
    ``.uacp/.outputs/`` (nonexistent), re-introducing the F-EV-01 false block.
    """
    _resolved_run_against_real_config(temp_uacp_root, valid_run_id)

    # Sanity: the artifact really is on disk under the resolutions namespace.
    lessons = temp_uacp_root / ".uacp" / "resolutions" / f"{valid_run_id}-lessons.yaml"
    assert lessons.exists(), lessons

    codes = _codes(validate_evidence_completeness(temp_uacp_root, valid_run_id))
    assert "EV_RESOLVED_WITHOUT_EVIDENCE" not in codes, (
        "resolved run with its lessons artifact under .uacp/resolutions/ was "
        f"falsely flagged as evidence-less: {codes}. If the config resolve "
        "artifact_glob was reverted to '.outputs/{run_id}*', that is the bug."
    )


# --------------------------------------------------------------- negative (teeth)
def test_resolve_invariant_blocks_when_artifact_absent(temp_uacp_root: Path, valid_run_id: str):
    """With the resolve exit artifact ABSENT, the same invariant DOES block — the
    "no self-attesting closure" guarantee still bites against the real config."""
    _resolved_run_against_real_config(temp_uacp_root, valid_run_id)

    # Remove the resolve-phase required exit artifact (resolutions/{run_id}*).
    (temp_uacp_root / ".uacp" / "resolutions" / f"{valid_run_id}-lessons.yaml").unlink()

    codes = _codes(validate_evidence_completeness(temp_uacp_root, valid_run_id))
    assert "EV_RESOLVED_WITHOUT_EVIDENCE" in codes, codes

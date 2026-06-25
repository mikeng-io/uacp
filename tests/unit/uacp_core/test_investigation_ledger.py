"""Unit tests for the investigation ledger (capsule #3, design node 13).

The verify loop serialized: a typed `uacp.investigation_entry` projects as an `investigation_entry`
node; an OPEN move (a non-superseded `fail`/`error` entry) blocks closure (GP_OPEN_INVESTIGATION,
fail-closed); a later entry that `supersedes` it clears it (revisable, history kept); and the
`investigation_status` dry-predicate reports converged-vs-keep-going.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from engines.graph_projection import (
    investigation_status,
    validate_graph_invariants,
    validate_graph_projection,
)


def _entry(eid: str, move: str, verdict: str | None = None, supersedes: str | None = None) -> dict:
    d: dict = {"kind": "uacp.investigation_entry", "entry_id": eid, "run_id": "r", "phase": "verify",
               "move": move}
    if verdict is not None:
        d["verdict"] = verdict
    if supersedes is not None:
        d["supersedes"] = supersedes
    return d


def _ws(tmp_path: Path, entries: list[dict]) -> Path:
    base = tmp_path / ".uacp"
    (base / "state" / "runs").mkdir(parents=True)
    (base / "verification").mkdir(parents=True)
    arts = {}
    for i, e in enumerate(entries, 1):
        rel = f"verification/inv-{i}.yaml"
        (base / rel).write_text(yaml.safe_dump(e), encoding="utf-8")
        arts[f"inv{i}"] = rel
    (base / "state" / "runs" / "r.yaml").write_text(
        yaml.safe_dump({"kind": "uacp.run_state", "run_id": "r", "artifacts": arts})
    )
    return tmp_path


def _codes(vs) -> set[str]:
    return {v.code for v in vs}


def test_open_failing_entry_blocks_closure(tmp_path):
    ws = _ws(tmp_path, [_entry("e1", "run", verdict="fail")])
    vs = validate_graph_projection(ws, "r")
    assert any(v.code == "GP_OPEN_INVESTIGATION" and v.detail.get("entry") == "e1" for v in vs), vs
    assert all(v.severity == "block" for v in vs if v.code == "GP_OPEN_INVESTIGATION")


def test_error_entry_is_fail_closed(tmp_path):
    # an `error` verdict (couldn't even measure) is open too — never a silent pass.
    ws = _ws(tmp_path, [_entry("e1", "run", verdict="error")])
    assert "GP_OPEN_INVESTIGATION" in _codes(validate_graph_projection(ws, "r"))


def test_supersede_clears_an_earlier_failure(tmp_path):
    # e1 failed; e2 (a remediation) supersedes it and passes -> no open investigation (history kept).
    ws = _ws(tmp_path, [_entry("e1", "run", verdict="fail"),
                        _entry("e2", "reconcile", verdict="pass", supersedes="e1")])
    assert "GP_OPEN_INVESTIGATION" not in _codes(validate_graph_projection(ws, "r"))


def test_self_supersede_does_not_clear_a_failure(tmp_path):
    # fail-closed: an entry that supersedes ITSELF must NOT drop out of the open set.
    ws = _ws(tmp_path, [_entry("e1", "run", verdict="fail", supersedes="e1")])
    assert "GP_OPEN_INVESTIGATION" in _codes(validate_graph_projection(ws, "r"))


def test_passing_and_nonmeasuring_entries_do_not_block(tmp_path):
    # a passing run + a non-measuring enumerate move (no verdict) are not open.
    ws = _ws(tmp_path, [_entry("e1", "enumerate"), _entry("e2", "run", verdict="pass")])
    assert "GP_OPEN_INVESTIGATION" not in _codes(validate_graph_projection(ws, "r"))


def test_open_investigation_fires_at_verify_exit(tmp_path):
    ws = _ws(tmp_path, [_entry("e1", "run", verdict="fail")])
    assert "GP_OPEN_INVESTIGATION" in _codes(validate_graph_invariants(ws, "r", "verify_exit"))


def test_dry_predicate_reports_open_then_converged(tmp_path):
    # not dry while a failure is open; dry once it is superseded by a pass.
    open_ws = _ws(tmp_path / "open", [_entry("e1", "run", verdict="fail")])
    st = investigation_status(open_ws, "r")
    assert st["dry"] is False and st["open"] == ["e1"]
    dry_ws = _ws(tmp_path / "dry", [_entry("e1", "run", verdict="fail"),
                                    _entry("e2", "reconcile", verdict="pass", supersedes="e1")])
    st2 = investigation_status(dry_ws, "r")
    assert st2["dry"] is True and st2["open"] == [] and st2["entries"] == 1


def test_dry_predicate_no_manifest_is_trivially_dry_but_load_error_is_not(tmp_path):
    assert investigation_status(tmp_path, "nope")["dry"] is True  # nothing to investigate
    assert investigation_status("", "")["dry"] is False  # bad input -> fail-closed, not false-dry


def test_investigation_entry_governed_authoring(tmp_path):
    # BOTH-registries: a layout Entry AND a schema, so the entity-writer accepts it + the move enum
    # is enforced at write (an unknown move is rejected).
    from engines.manifest.entity_writer import create_entity
    from state_machine import handle_init

    handle_init({"workspace": str(tmp_path), "run_id": "r", "source": "operator-request"})
    ok = create_entity(
        str(tmp_path), "r", "uacp.investigation_entry",
        {"entry_id": "e1", "phase": "verify", "move": "run", "verdict": "pass"}, seq="1",
    )
    assert ok.get("ok") is True, ok
    bad = create_entity(
        str(tmp_path), "r", "uacp.investigation_entry",
        {"entry_id": "e2", "phase": "verify", "move": "not_a_move"}, seq="2",
    )
    assert "error" in bad and "validate-on-write rejected" in bad["error"], bad

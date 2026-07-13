"""Unit tests for the witness-advisory ledger (#80 promotion-evidence substrate).

The ledger RECORDS which conformance-witness codes fired at a run's closure so a promotion
report can tally firing across runs. It is pure observation — writing it promotes no witness
and changes no gate. The writer is atomic (same-dir temp + os.replace) and never raises.
"""

from __future__ import annotations

from pathlib import Path

import engines.io.witness_ledger_io as wl


def test_witness_counts_tallies_only_witness_codes():
    codes = [
        "SC_DIFF_OUT_OF_SCOPE",
        "SC_UNDECLARED_CASCADE",
        "SC_UNDECLARED_CASCADE",
        "C6_WRITE_PATHS_DISAGREE",  # a scope code, NOT a witness — must be dropped
        "CHK_FLOOR_UNMET",  # a check code, NOT a witness feed — dropped
        "DF_DEFERRAL_MISSING_OWNER",  # unrelated — dropped
    ]
    assert wl.witness_counts(codes) == {"SC_DIFF_OUT_OF_SCOPE": 1, "SC_UNDECLARED_CASCADE": 2}


def _family(name):
    return next(f for f in wl.WITNESS_FAMILIES if f.name == name)


def test_family_status_is_independent_per_family():
    diff, cascade = _family("scope_diff"), _family("scope_cascade")
    assert wl.family_status(diff, ["SC_DIFF_OUT_OF_SCOPE"]) == "unstarved"
    assert wl.family_status(diff, ["SC_DIFF_UNAVAILABLE"]) == "unavailable"
    assert wl.family_status(cascade, ["SC_WITNESS_UNRESOLVED_TOUCHED"]) == "unresolved"
    # KEY (council #80 P2): the diff witness is UNSTARVED even when the CLASS witness starved
    assert (
        wl.family_status(diff, ["SC_DIFF_OUT_OF_SCOPE", "CHK_CLASS_WITNESS_UNAVAILABLE"])
        == "unstarved"
    )
    assert wl.family_status(_family("class"), ["CHK_CLASS_WITNESS_UNAVAILABLE"]) == "unavailable"


def test_build_record_is_per_family_and_no_cross_masking():
    """P2 fix: a run where the diff witness FIRED a substantive advisory but the class witness
    is UNAVAILABLE must record scope_diff as unstarved+substantive (not masked)."""
    rec = wl.build_witness_record(
        "run-1", ["SC_DIFF_OUT_OF_SCOPE", "CHK_CLASS_WITNESS_UNAVAILABLE"], witnessed_at=123.0
    )
    assert rec["kind"] == "uacp.witness_ledger" and rec["run_id"] == "run-1"
    assert rec["witnessed_at"] == 123.0
    fam = rec["families"]
    # scope_diff: witnessable, with a substantive advisory — NOT masked by the class starvation
    assert fam["scope_diff"] == {"status": "unstarved", "substantive": 1}
    # class: correctly out of its own FP population
    assert fam["class"]["status"] == "unavailable"
    assert fam["class"]["substantive"] == 0
    assert rec["counts"]["CHK_CLASS_WITNESS_UNAVAILABLE"] == 1


def test_already_blocking_codes_recorded_but_not_substantive():
    """P3 fix: CHK_CLASS_UNDERCLAIM ships as BLOCK (already enforced) — recorded in counts but
    never counted as an advisory awaiting promotion."""
    rec = wl.build_witness_record("run-2", ["CHK_CLASS_UNDERCLAIM"], witnessed_at=1.0)
    assert rec["counts"]["CHK_CLASS_UNDERCLAIM"] == 1  # observed
    assert rec["families"]["class"]["substantive"] == 0  # but NOT advisory evidence
    assert "CHK_CLASS_UNDERCLAIM" not in _family("class").substantive


def test_clean_run_records_every_family_unstarved_zero():
    """A run where witnesses ran and found nothing is the promotion DENOMINATOR — every family
    records unstarved/0, not omitted."""
    rec = wl.build_witness_record("run-clean", [], witnessed_at=1.0)
    for fname in ("scope_diff", "scope_cascade", "class"):
        assert rec["families"][fname] == {"status": "unstarved", "substantive": 0}
    assert rec["counts"] == {}


def test_write_then_load_roundtrips(tmp_path: Path):
    rec = wl.build_witness_record("run-io", ["SC_DIFF_OUT_OF_SCOPE"], witnessed_at=9.0)
    assert wl.write_witness_ledger(tmp_path, "run-io", rec) is True
    loaded, err = wl.load_witness_ledger(tmp_path, "run-io")
    assert err is None and loaded == rec


def test_load_absent_is_none_none(tmp_path: Path):
    assert wl.load_witness_ledger(tmp_path, "nope") == (None, None)


def test_replace_failure_returns_false_and_leaves_no_partial(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(wl.os, "replace", lambda _s, _d: (_ for _ in ()).throw(OSError("full")))
    assert wl.write_witness_ledger(tmp_path, "run-io", {"kind": "uacp.witness_ledger"}) is False
    path = wl.witness_ledger_path(tmp_path, "run-io")
    assert path is not None and not path.exists()
    leftovers = [p for p in path.parent.iterdir() if p.name.startswith(f".{path.name}.")]
    assert leftovers == []

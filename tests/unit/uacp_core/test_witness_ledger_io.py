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


def test_traversal_run_id_is_rejected_and_writes_nothing(tmp_path: Path):
    """A path-traversal run_id must NOT resolve the ledger write out of the sub-namespace and
    overwrite governed state (Codex #80). The write is skipped (returns False), and the target
    it would have hit (e.g. state/run-registry.yaml) is untouched."""
    base = tmp_path / ".uacp"
    (base / "state").mkdir(parents=True, exist_ok=True)
    registry = base / "state" / "run-registry.yaml"
    registry.write_text("active_runs: []\n", encoding="utf-8")

    for bad in ("../../state/run-registry", "a/b", "..\\x", ".hidden"):
        assert wl.witness_ledger_path(tmp_path, bad) is None
        assert wl.write_witness_ledger(tmp_path, bad, {"kind": "uacp.witness_ledger"}) is False
    # the governed file the traversal targeted is intact
    assert registry.read_text(encoding="utf-8") == "active_runs: []\n"


def test_symlinked_ledger_dir_is_rejected_and_writes_nothing(tmp_path: Path):
    """A symlinked witness-ledgers directory must NOT let the atomic replace write THROUGH the
    link onto governed state (Codex #80). If verification/witness-ledgers is a symlink to
    state/runs, the write is skipped (False) and the victim dir is untouched — parity with the
    governed writers' symlinked-component guard."""
    base = tmp_path / ".uacp"
    victim = base / "state" / "runs"
    victim.mkdir(parents=True, exist_ok=True)
    (base / "verification").mkdir(parents=True, exist_ok=True)
    # verification/witness-ledgers is a SYMLINK pointing at the governed state/runs dir
    (base / "verification" / "witness-ledgers").symlink_to(victim, target_is_directory=True)

    rec = wl.build_witness_record("run-io", ["SC_DIFF_OUT_OF_SCOPE"], witnessed_at=1.0)
    assert wl.write_witness_ledger(tmp_path, "run-io", rec) is False
    # nothing was written through the link into the governed dir
    assert not (victim / "run-io.yaml").exists()
    assert list(victim.iterdir()) == []


def test_symlinked_verification_dir_is_rejected_by_writer(tmp_path: Path):
    """dir_for RESOLVES a symlinked verification/ dir, so the writer must reconstruct the raw
    path and refuse (Codex #80): with .uacp/verification a symlink to .uacp/state, the ledger
    path is None, the write is skipped, and no ledger lands under the symlink target."""
    base = tmp_path / ".uacp"
    victim = base / "state"
    victim.mkdir(parents=True, exist_ok=True)
    (base / "verification").symlink_to(victim, target_is_directory=True)

    assert wl.witness_ledger_path(tmp_path, "run-io") is None
    rec = wl.build_witness_record("run-io", ["SC_DIFF_OUT_OF_SCOPE"], witnessed_at=1.0)
    assert wl.write_witness_ledger(tmp_path, "run-io", rec) is False
    assert not (victim / "witness-ledgers").exists()  # nothing written through the link


def test_safe_unresolved_verification_dir_rejects_escaping_config(tmp_path: Path, monkeypatch):
    """A config override with an escaping (``..``) or absolute verification segment must yield
    None (parity with dir_for's containment), so the writer/reader never touch an out-of-
    namespace dir (Codex #80)."""
    import config as cfgmod

    def _cfg(base: str, verif: str):
        paths = type("P", (), {"base": base, "verification": verif})()
        return type("C", (), {"paths": paths})()

    for base, verif in ((".uacp", "../state"), (".uacp", "/etc"), ("/abs", "verification")):
        monkeypatch.setattr(cfgmod, "get_config", lambda root, b=base, v=verif: _cfg(b, v))
        assert wl.safe_unresolved_verification_dir(tmp_path) is None


def test_ledger_does_not_pollute_the_verify_evidence_glob(tmp_path: Path):
    """The ledger must live UNDER verification/witness-ledgers/, not directly in verification/,
    so it never matches the non-recursive verify-evidence invariant glob `verification/{run_id}*`
    and can't falsely satisfy an evidence-presence check (Codex #80)."""
    rec = wl.build_witness_record("run-x", ["SC_DIFF_OUT_OF_SCOPE"], witnessed_at=1.0)
    assert wl.write_witness_ledger(tmp_path, "run-x", rec) is True
    base = tmp_path / ".uacp"
    # the verify-evidence-style glob (non-recursive) must NOT see the ledger
    assert list(base.glob("verification/run-x*")) == []
    # but it IS written + loadable under the sub-namespace
    assert (base / "verification" / "witness-ledgers" / "run-x.yaml").is_file()
    assert wl.load_witness_ledger(tmp_path, "run-x")[0] == rec


def test_replace_failure_returns_false_and_leaves_no_partial(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(wl.os, "replace", lambda _s, _d: (_ for _ in ()).throw(OSError("full")))
    assert wl.write_witness_ledger(tmp_path, "run-io", {"kind": "uacp.witness_ledger"}) is False
    path = wl.witness_ledger_path(tmp_path, "run-io")
    assert path is not None and not path.exists()
    leftovers = [p for p in path.parent.iterdir() if p.name.startswith(f".{path.name}.")]
    assert leftovers == []

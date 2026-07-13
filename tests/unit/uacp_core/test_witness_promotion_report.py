"""Unit tests for the witness promotion report (#80) — the read side of the evidence lane.

It aggregates per-run witness ledgers + forecast records into promotion evidence; it computes
NO promotion and touches no gate. Tests seed ledger/forecast files under the verification dir
and assert the aggregation + the coarse (advisory) readiness flag.
"""

from __future__ import annotations

from pathlib import Path

import engines.io.witness_ledger_io as wl
import witness_promotion_report as rep


def _seed_ledger(root: Path, run_id: str, codes: list[str], witnessed_at: float = 1.0) -> None:
    wl.write_witness_ledger(root, run_id, wl.build_witness_record(run_id, codes, witnessed_at))


def _seed_forecast(root: Path, run_id: str, precision, recall) -> None:
    from engines.io import forecastio

    forecastio.write_forecast_record(root, run_id, {"precision": precision, "recall": recall})


def test_empty_workspace_is_all_zero(tmp_path: Path):
    r = rep.build_report(tmp_path)
    assert r["total_runs"] == 0
    assert r["per_code"] == {}
    assert r["forecast"]["joined_runs"] == 0
    for fname in ("scope_diff", "scope_cascade", "class"):
        assert r["families"][fname] == {
            "unstarved": 0,
            "unresolved": 0,
            "unavailable": 0,
            "substantive_runs": 0,
        }


def test_aggregates_per_family_and_per_code(tmp_path: Path):
    _seed_ledger(tmp_path, "r1", ["SC_DIFF_OUT_OF_SCOPE"])  # scope_diff unstarved+substantive
    _seed_ledger(
        tmp_path, "r2", ["SC_DIFF_OUT_OF_SCOPE", "SC_UNDECLARED_CASCADE"]
    )  # both fam substantive
    _seed_ledger(tmp_path, "r3", [])  # all unstarved, no advisory
    _seed_ledger(tmp_path, "r4", ["SC_WITNESS_UNAVAILABLE"])  # scope_cascade unavailable
    _seed_ledger(tmp_path, "r5", ["SC_WITNESS_UNRESOLVED_TOUCHED"])  # scope_cascade unresolved

    r = rep.build_report(tmp_path)
    assert r["total_runs"] == 5
    # scope_diff: r1..r5 all UNSTARVED for the diff witness (none starve IT); r1,r2 substantive
    assert r["families"]["scope_diff"]["unstarved"] == 5
    assert r["families"]["scope_diff"]["substantive_runs"] == 2
    # scope_cascade: r1,r2,r3 unstarved; r4 unavailable; r5 unresolved; r2 substantive
    assert r["families"]["scope_cascade"] == {
        "unstarved": 3,
        "unresolved": 1,
        "unavailable": 1,
        "substantive_runs": 1,
    }
    assert r["per_code"]["SC_DIFF_OUT_OF_SCOPE"] == {"runs": 2, "total": 2}


def test_starved_witness_does_not_mask_another_families_advisory(tmp_path: Path):
    """Council #80 P2 at the REPORT level: a run with a real diff advisory but an unavailable
    class witness must NOT hide the diff advisory. 12 no-advisory runs + 1 such run → scope_diff
    counts the advisory, even though the class witness starved that run."""
    for i in range(12):
        _seed_ledger(tmp_path, f"clean{i}", [])
    _seed_ledger(tmp_path, "masked", ["SC_DIFF_OUT_OF_SCOPE", "CHK_CLASS_WITNESS_UNAVAILABLE"])
    report = rep.build_report(tmp_path)
    ready = rep.promotion_readiness(report, min_runs=10)
    # scope_diff saw the advisory (13 unstarved, 1 substantive) — NOT masked
    assert report["families"]["scope_diff"] == {
        "unstarved": 13,
        "unresolved": 0,
        "unavailable": 0,
        "substantive_runs": 1,
    }
    assert ready["families"]["scope_diff"]["substantive_advisory_runs"] == 1
    assert ready["families"]["scope_diff"]["no_advisory_yet"] is False
    # class witness: the masked run correctly starved it (unavailable), so its advisory count is
    # unaffected — per-family independence (the diff advisory is NOT its concern)
    assert report["families"]["class"]["unstarved"] == 12
    assert report["families"]["class"]["unavailable"] == 1
    assert ready["families"]["class"]["no_advisory_yet"] is True
    # and NO family gets an unsound CLEAN verdict — the clean denominator is not measurable
    assert all(f["clean_denominator_measurable"] is False for f in ready["families"].values())


def test_advisory_counted_even_when_same_family_also_starved(tmp_path: Path):
    """One sweep can emit BOTH a substantive advisory and a starvation code for the SAME family
    (Codex #80): scope_cascade gets SC_UNDECLARED_CASCADE (advisory) + SC_WITNESS_UNRESOLVED_
    TOUCHED (starvation). The family's status is 'unresolved', but its advisory must STILL be
    counted — not dropped — so no_advisory_yet cannot hide a real potential false positive."""
    _seed_ledger(tmp_path, "mixed", ["SC_UNDECLARED_CASCADE", "SC_WITNESS_UNRESOLVED_TOUCHED"])
    r = rep.build_report(tmp_path)
    cascade = r["families"]["scope_cascade"]
    assert cascade["unresolved"] == 1  # the starvation is recorded
    assert cascade["substantive_runs"] == 1  # AND the advisory is counted (not dropped)
    ready = rep.promotion_readiness(r)
    assert ready["families"]["scope_cascade"]["no_advisory_yet"] is False


def test_forecast_mean_precision_recall(tmp_path: Path):
    # each forecast run must ALSO have a ledger (= it resolved) to count (Codex #80)
    for rid, p, rc in [("r1", 1.0, 0.5), ("r2", 0.6, None), ("r3", None, 0.9)]:
        _seed_forecast(tmp_path, rid, p, rc)
        _seed_ledger(tmp_path, rid, [])  # ledger => this run resolved
    r = rep.build_report(tmp_path)
    # joined_runs counts a resolved run with EITHER precision or recall (gemini #80 P2): r1,r2,r3
    assert r["forecast"]["joined_runs"] == 3
    assert abs(r["forecast"]["mean_precision"] - 0.8) < 1e-9  # mean over r1,r2 only
    assert abs(r["forecast"]["mean_recall"] - 0.7) < 1e-9  # mean over r1(0.5),r3(0.9)


def test_forecast_from_a_blocked_closure_is_excluded(tmp_path: Path):
    """A cascade forecast joined during a blocked/reverted closure (no witness ledger, since the
    ledger is written only for non-blocked closures) must NOT pollute the promotion averages
    (Codex #80)."""
    _seed_forecast(tmp_path, "resolved", 1.0, 1.0)
    _seed_ledger(tmp_path, "resolved", [])  # resolved -> has a ledger -> counts
    _seed_forecast(tmp_path, "blocked", 0.1, 0.1)  # NO ledger -> blocked/reverted -> excluded
    r = rep.build_report(tmp_path)
    assert r["forecast"]["joined_runs"] == 1  # only the resolved run
    assert abs(r["forecast"]["mean_precision"] - 1.0) < 1e-9  # the 0.1 blocked run is NOT averaged


def test_readiness_reports_sound_signals_no_clean_verdict(tmp_path: Path):
    """The report must NOT emit an unmeasurable CLEAN verdict (Codex #80): a witness emits
    nothing both when it ran clean AND when it never ran, so 'clean' is not measurable. It
    reports the SOUND signals — advisory count (numerator) + no_advisory_yet — and withholds
    any clean verdict."""
    for i in range(12):
        _seed_ledger(tmp_path, f"clean{i}", [])  # all silent (no codes) — indeterminate, NOT clean
    ready = rep.promotion_readiness(rep.build_report(tmp_path), min_runs=10)
    sd = ready["families"]["scope_diff"]
    assert sd["no_advisory_yet"] is True  # sound: zero advisories recorded
    assert sd["substantive_advisory_runs"] == 0
    assert sd["clean_denominator_measurable"] is False  # honest: cannot certify clean
    assert "detection_evidence_clean" not in sd  # the unsound flag is GONE

    # a real advisory is soundly counted
    _seed_ledger(tmp_path, "dirty", ["SC_DIFF_OUT_OF_SCOPE"])
    ready2 = rep.promotion_readiness(rep.build_report(tmp_path), min_runs=10)
    assert ready2["families"]["scope_diff"]["no_advisory_yet"] is False
    assert ready2["families"]["scope_diff"]["substantive_advisory_runs"] == 1


def test_format_report_withholds_clean_and_names_the_gate(tmp_path: Path):
    _seed_ledger(tmp_path, "r1", ["SC_DIFF_OUT_OF_SCOPE"])
    out = rep.format_report(rep.build_report(tmp_path))
    assert "witness promotion report" in out
    assert "scope_diff" in out and "SC_DIFF_OUT_OF_SCOPE" in out
    # the report must NOT print a CLEAN verdict, and must name the attestation gap + the gate
    assert "no CLEAN verdict is computed" in out
    assert "positive witness attestation" in out
    assert "gated on" in out and "design/conformance-witnesses" in out

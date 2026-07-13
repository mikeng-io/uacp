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
            "witnessable": 0,
            "unresolved": 0,
            "unavailable": 0,
            "substantive_runs": 0,
        }


def test_aggregates_per_family_and_per_code(tmp_path: Path):
    _seed_ledger(tmp_path, "r1", ["SC_DIFF_OUT_OF_SCOPE"])  # scope_diff witnessable+substantive
    _seed_ledger(
        tmp_path, "r2", ["SC_DIFF_OUT_OF_SCOPE", "SC_UNDECLARED_CASCADE"]
    )  # both fam substantive
    _seed_ledger(tmp_path, "r3", [])  # all witnessable, clean
    _seed_ledger(tmp_path, "r4", ["SC_WITNESS_UNAVAILABLE"])  # scope_cascade unavailable
    _seed_ledger(tmp_path, "r5", ["SC_WITNESS_UNRESOLVED_TOUCHED"])  # scope_cascade unresolved

    r = rep.build_report(tmp_path)
    assert r["total_runs"] == 5
    # scope_diff: r1,r2,r3,r4,r5 are ALL witnessable for the diff witness (none starve IT);
    # r1,r2 substantive
    assert r["families"]["scope_diff"]["witnessable"] == 5
    assert r["families"]["scope_diff"]["substantive_runs"] == 2
    # scope_cascade: r1,r2,r3 witnessable; r4 unavailable; r5 unresolved; r2 substantive
    assert r["families"]["scope_cascade"] == {
        "witnessable": 3,
        "unresolved": 1,
        "unavailable": 1,
        "substantive_runs": 1,
    }
    assert r["per_code"]["SC_DIFF_OUT_OF_SCOPE"] == {"runs": 2, "total": 2}


def test_starved_witness_does_not_mask_another_families_advisory(tmp_path: Path):
    """Council #80 P2 at the REPORT level: a run with a real diff advisory but an unavailable
    class witness must NOT hide the diff advisory. 12 clean runs + 1 such run → scope_diff is
    NOT clean (its advisory is counted), even though the class witness starved that run."""
    for i in range(12):
        _seed_ledger(tmp_path, f"clean{i}", [])
    _seed_ledger(tmp_path, "masked", ["SC_DIFF_OUT_OF_SCOPE", "CHK_CLASS_WITNESS_UNAVAILABLE"])
    report = rep.build_report(tmp_path)
    ready = rep.promotion_readiness(report, min_runs=10)
    # scope_diff saw the advisory (13 witnessable, 1 substantive) → NOT clean (not masked!)
    assert report["families"]["scope_diff"] == {
        "witnessable": 13,
        "unresolved": 0,
        "unavailable": 0,
        "substantive_runs": 1,
    }
    assert ready["families"]["scope_diff"]["detection_evidence_clean"] is False
    assert "substantive" in ready["families"]["scope_diff"]["detection_reason"]
    # class witness: the masked run correctly starved it, so it saw only the 12 clean runs →
    # legitimately CLEAN (per-family independence: the diff advisory is NOT its concern)
    assert report["families"]["class"]["witnessable"] == 12
    assert ready["families"]["class"]["detection_evidence_clean"] is True


def test_forecast_mean_precision_recall(tmp_path: Path):
    _seed_forecast(tmp_path, "r1", 1.0, 0.5)
    _seed_forecast(tmp_path, "r2", 0.6, None)  # recall absent → excluded from recall mean
    _seed_forecast(tmp_path, "r3", None, 0.9)  # recall-only (nothing predicted) — still JOINED
    r = rep.build_report(tmp_path)
    # joined_runs counts a run with EITHER precision or recall (gemini #80 P2): r1,r2,r3
    assert r["forecast"]["joined_runs"] == 3
    assert abs(r["forecast"]["mean_precision"] - 0.8) < 1e-9  # mean over r1,r2 only
    assert abs(r["forecast"]["mean_recall"] - 0.7) < 1e-9  # mean over r1(0.5),r3(0.9)


def test_readiness_needs_enough_clean_witnessable_runs(tmp_path: Path):
    # 12 clean runs → EVERY family is CLEAN at min_runs=10 (all witnessable, zero substantive)
    for i in range(12):
        _seed_ledger(tmp_path, f"clean{i}", [])
    ready = rep.promotion_readiness(rep.build_report(tmp_path), min_runs=10)
    assert ready["families"]["scope_diff"]["detection_evidence_clean"] is True
    assert ready["families"]["scope_diff"]["witnessable_runs"] == 12

    # one substantive scope_diff run flips ONLY scope_diff to not-clean
    _seed_ledger(tmp_path, "dirty", ["SC_DIFF_OUT_OF_SCOPE"])
    ready2 = rep.promotion_readiness(rep.build_report(tmp_path), min_runs=10)
    assert ready2["families"]["scope_diff"]["detection_evidence_clean"] is False
    assert "substantive" in ready2["families"]["scope_diff"]["detection_reason"]
    # the cascade family is untouched by a diff advisory → still clean
    assert ready2["families"]["scope_cascade"]["detection_evidence_clean"] is True


def test_readiness_insufficient_runs(tmp_path: Path):
    _seed_ledger(tmp_path, "one", [])
    ready = rep.promotion_readiness(rep.build_report(tmp_path), min_runs=10)
    assert ready["families"]["scope_diff"]["detection_evidence_clean"] is False
    assert "insufficient" in ready["families"]["scope_diff"]["detection_reason"]


def test_format_report_renders_and_names_the_gate(tmp_path: Path):
    _seed_ledger(tmp_path, "r1", ["SC_DIFF_OUT_OF_SCOPE"])
    out = rep.format_report(rep.build_report(tmp_path))
    assert "witness promotion report" in out
    assert "scope_diff" in out and "SC_DIFF_OUT_OF_SCOPE" in out
    # promotion stays gated — the report must SAY so, not imply auto-promotion
    assert "gated on design/conformance-witnesses" in out

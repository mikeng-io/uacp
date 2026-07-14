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


def _seed_manifest(root: Path, run_id: str, status=None, finalized_at=None) -> None:
    """Seed a run manifest at the authoritative path ``load_manifest`` reads
    (``<root>/.uacp/state/runs/<run_id>.yaml``) with the minimal shape."""
    import yaml
    from config import dir_for

    runs = dir_for(Path(root).resolve(), "state") / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    body: dict = {"run_id": run_id}
    if status is not None:
        body["status"] = status
    if finalized_at is not None:
        body["finalized_at"] = finalized_at
    (runs / f"{run_id}.yaml").write_text(yaml.safe_dump(body), encoding="utf-8")


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


def test_forecast_resolved_by_manifest_without_ledger_is_counted(tmp_path: Path):
    """CORE FIX: a genuinely-resolved run (authoritative manifest status=resolved) whose
    best-effort witness ledger was skipped/failed — or predates the ledger writer — must STILL
    contribute its precision/recall. Keying off ledger presence silently dropped it."""
    _seed_forecast(tmp_path, "resolved_noledger", 1.0, 1.0)
    _seed_manifest(tmp_path, "resolved_noledger", status="resolved")  # authoritative resolved
    # deliberately NO witness ledger
    r = rep.build_report(tmp_path)
    assert r["forecast"]["joined_runs"] == 1  # the false-drop is gone
    assert abs(r["forecast"]["mean_precision"] - 1.0) < 1e-9
    assert abs(r["forecast"]["mean_recall"] - 1.0) < 1e-9


def test_forecast_resolved_by_finalized_at_is_counted(tmp_path: Path):
    """``finalized_at`` present (and status absent) is also an authoritative resolved-marker."""
    _seed_forecast(tmp_path, "fin", 0.7, 0.7)
    _seed_manifest(tmp_path, "fin", finalized_at="2026-07-14T00:00:00Z")
    r = rep.build_report(tmp_path)
    assert r["forecast"]["joined_runs"] == 1
    assert abs(r["forecast"]["mean_precision"] - 0.7) < 1e-9


def test_forecast_blocked_by_manifest_status_is_excluded(tmp_path: Path):
    """A run whose authoritative manifest is NOT resolved (blocked/reverted closure — see
    handle_finalize's fail-closed revert) and carries no finalized_at must be EXCLUDED even
    though a forecast file was joined during the failed closure attempt."""
    _seed_forecast(tmp_path, "blocked", 0.1, 0.1)
    _seed_manifest(tmp_path, "blocked", status="execute")  # not resolved, no finalized_at
    r = rep.build_report(tmp_path)
    assert r["forecast"]["joined_runs"] == 0
    assert r["forecast"]["mean_precision"] is None


def test_forecast_manifest_missing_falls_back_to_ledger_presence(tmp_path: Path):
    """When the manifest cannot be loaded, ledger presence remains a valid POSITIVE fallback
    (the ledger is written only on a non-blocked closure) — manifest-less workspaces are no
    worse than before."""
    _seed_forecast(tmp_path, "fallback", 0.9, 0.9)
    _seed_ledger(tmp_path, "fallback", [])  # ledger present, NO manifest -> fallback counts it
    r = rep.build_report(tmp_path)
    assert r["forecast"]["joined_runs"] == 1
    assert abs(r["forecast"]["mean_precision"] - 0.9) < 1e-9


def test_forecast_precision_ok_requires_enough_pairs(tmp_path: Path):
    """The node-04 bar is precision >= 0.8 over >= _MIN_FORECAST_RUNS joined pairs (Codex #80):
    a single perfect-precision pair must NOT flip forecast_precision_ok true. It clears only
    once BOTH the threshold and the sample size are met."""
    # one resolved forecast at precision 1.0 -> above threshold but far below the sample floor
    _seed_forecast(tmp_path, "solo", 1.0, 1.0)
    _seed_manifest(tmp_path, "solo", status="resolved")
    ready = rep.promotion_readiness(rep.build_report(tmp_path))
    assert ready["forecast_joined_runs"] == 1
    assert ready["forecast_precision"] == 1.0  # threshold met
    assert ready["forecast_precision_ok"] is False  # but sample floor not met -> NOT ok
    assert ready["min_forecast_runs"] == rep._MIN_FORECAST_RUNS

    # enough high-precision pairs -> both conditions met -> ok
    for i in range(rep._MIN_FORECAST_RUNS):
        _seed_forecast(tmp_path, f"run{i}", 0.9, 0.9)
        _seed_manifest(tmp_path, f"run{i}", status="resolved")
    ready2 = rep.promotion_readiness(rep.build_report(tmp_path))
    assert ready2["forecast_joined_runs"] >= rep._MIN_FORECAST_RUNS
    assert ready2["forecast_precision_ok"] is True


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

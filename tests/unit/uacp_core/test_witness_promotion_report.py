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

    # Auditable + CLEAN by default (graph_stamp.commit == base_commit) so the record is
    # bar-eligible; hindsight/unaudited variants are seeded explicitly via _seed_forecast_full.
    forecastio.write_forecast_record(
        root,
        run_id,
        {
            "run_id": run_id,  # embedded run_id matches the filename (real records do)
            "precision": precision,
            "recall": recall,
            "base_commit": "base",
            "graph_stamp": {"commit": "base"},
        },
    )


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


def test_symlinked_ledger_dir_is_not_followed_on_read(tmp_path: Path):
    """The report must NOT follow a symlinked witness-ledgers dir (Codex #80): pointed at
    state/runs it would read every run manifest as a ledger, inflating total_runs and seeding
    the forecast fallback from non-ledger files. Such a dir is skipped entirely."""
    base = tmp_path / ".uacp"
    runs = base / "state" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    # a run manifest that would masquerade as a ledger if the symlink were followed
    (runs / "victim.yaml").write_text("kind: uacp.run_manifest\nrun_id: victim\n", encoding="utf-8")
    (base / "verification").mkdir(parents=True, exist_ok=True)
    (base / "verification" / "witness-ledgers").symlink_to(runs, target_is_directory=True)

    r = rep.build_report(tmp_path)
    assert r["total_runs"] == 0  # the run manifest was NOT read as a ledger
    assert r["per_code"] == {}


def test_symlinked_verification_dir_is_not_followed(tmp_path: Path):
    """dir_for() RESOLVES symlinks, so a symlinked verification/ dir would be followed; the
    report must reconstruct the UNRESOLVED path and reject it (Codex #80). With .uacp/
    verification a symlink to a decoy holding a witness-ledgers/<manifest>, nothing is read."""
    base = tmp_path / ".uacp"
    base.mkdir(parents=True, exist_ok=True)
    decoy = tmp_path / "decoy"
    (decoy / "witness-ledgers").mkdir(parents=True, exist_ok=True)
    (decoy / "witness-ledgers" / "x.yaml").write_text(
        "kind: uacp.witness_ledger\nrun_id: x\ncounts: {SC_DIFF_OUT_OF_SCOPE: 1}\n", encoding="utf-8"
    )
    (decoy / "x-cascade-forecast.yaml").write_text("precision: 1.0\nrecall: 1.0\n", encoding="utf-8")
    (base / "verification").symlink_to(decoy, target_is_directory=True)

    r = rep.build_report(tmp_path)
    assert r["total_runs"] == 0  # the symlinked verification dir was NOT followed
    assert r["per_code"] == {}
    assert r["forecast"]["joined_runs"] == 0  # nor the forecast under it


def test_symlinked_yaml_leaf_is_not_read(tmp_path: Path):
    """Even inside a REAL verification tree, a symlinked YAML leaf (ledger or forecast) could
    point outside the governed tree; it must NOT be read/counted (Codex #80)."""
    base = tmp_path / ".uacp"
    ledgers = base / "verification" / "witness-ledgers"
    ledgers.mkdir(parents=True, exist_ok=True)
    # an external ledger-shaped file the symlink points at
    external = tmp_path / "external.yaml"
    external.write_text(
        "kind: uacp.witness_ledger\nrun_id: ext\ncounts: {SC_DIFF_OUT_OF_SCOPE: 5}\n",
        encoding="utf-8",
    )
    (ledgers / "ext.yaml").symlink_to(external)
    # an external forecast the symlink points at
    ext_fc = tmp_path / "ext-forecast.yaml"
    ext_fc.write_text("precision: 1.0\nrecall: 1.0\n", encoding="utf-8")
    (base / "verification" / "ext-cascade-forecast.yaml").symlink_to(ext_fc)

    r = rep.build_report(tmp_path)
    assert r["total_runs"] == 0  # the symlinked ledger leaf was not read
    assert r["per_code"] == {}
    assert r["forecast"]["joined_runs"] == 0  # nor the symlinked forecast leaf


def test_foreign_kind_in_ledger_dir_is_not_counted(tmp_path: Path):
    """Defense in depth: even in a real (non-symlinked) ledger dir, a stray file whose kind is
    not uacp.witness_ledger must not inflate the tally (Codex #80)."""
    _seed_ledger(tmp_path, "real", ["SC_DIFF_OUT_OF_SCOPE"])  # a genuine ledger
    stray = tmp_path / ".uacp" / "verification" / "witness-ledgers" / "stray.yaml"
    stray.write_text("kind: uacp.run_manifest\nrun_id: stray\n", encoding="utf-8")
    r = rep.build_report(tmp_path)
    assert r["total_runs"] == 1  # only the real ledger counts


def test_ledger_run_id_must_match_filename(tmp_path: Path):
    """A witness ledger whose embedded run_id != its filename (copied / renamed) must NOT be
    counted — otherwise one valid ledger renamed to <other>.yaml inflates the run tally and can
    mark <other> resolved for the forecast fallback (Codex #80)."""
    ldir = tmp_path / ".uacp" / "verification" / "witness-ledgers"
    ldir.mkdir(parents=True, exist_ok=True)
    (ldir / "other.yaml").write_text(
        "kind: uacp.witness_ledger\nrun_id: real\ncounts: {SC_DIFF_OUT_OF_SCOPE: 1}\n",
        encoding="utf-8",
    )
    r = rep.build_report(tmp_path)
    assert r["total_runs"] == 0  # embedded run_id 'real' != filename 'other' -> not counted
    assert r["per_code"] == {}


def test_forecast_run_id_must_match_filename(tmp_path: Path):
    """A forecast copied to <other>-cascade-forecast.yaml keeps its embedded run_id; even with a
    finalized manifest for <other>, the mismatch must exclude it so the same precision/recall
    sample is not counted again for another run (Codex #80)."""
    _seed_forecast_full(
        tmp_path, "other",
        {"run_id": "real", "precision": 1.0, "recall": 1.0,
         "base_commit": "a", "graph_stamp": {"commit": "a"}},
    )
    _seed_manifest(tmp_path, "other", finalized_at="2026-07-14T00:00:00Z")
    r = rep.build_report(tmp_path)
    assert r["forecast"]["joined_runs"] == 0  # embedded run_id 'real' != filename 'other'


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
    """CORE FIX: a genuinely-finalized run (authoritative manifest finalized_at) whose
    best-effort witness ledger was skipped/failed — or predates the ledger writer — must STILL
    contribute its precision/recall. Keying off ledger presence silently dropped it."""
    _seed_forecast(tmp_path, "resolved_noledger", 1.0, 1.0)
    _seed_manifest(tmp_path, "resolved_noledger", finalized_at="2026-07-14T00:00:00Z")
    # deliberately NO witness ledger
    r = rep.build_report(tmp_path)
    assert r["forecast"]["joined_runs"] == 1  # the false-drop is gone
    assert abs(r["forecast"]["mean_precision"] - 1.0) < 1e-9
    assert abs(r["forecast"]["mean_recall"] - 1.0) < 1e-9


def test_forecast_reverted_closure_with_resolved_status_is_excluded(tmp_path: Path):
    """The verify->resolved transition sets status=resolved BEFORE finalize, and a blocked
    handle_finalize reverts finalized_at to None while restoring that prior (resolved) status —
    so a failed closure ends status==resolved with NO finalized_at (Codex #80). Such a run's
    forecast, joined during the failed attempt, must be EXCLUDED: status alone is not the
    closure-complete marker, only finalized_at is."""
    _seed_forecast(tmp_path, "reverted", 0.1, 0.1)
    _seed_manifest(tmp_path, "reverted", status="resolved")  # resolved status, NO finalized_at
    r = rep.build_report(tmp_path)
    assert r["forecast"]["joined_runs"] == 0
    assert r["forecast"]["mean_precision"] is None


def test_forecast_blocked_by_manifest_status_is_excluded(tmp_path: Path):
    """A run whose authoritative manifest carries no finalized_at (a closure that never
    completed) must be EXCLUDED even though a forecast file was joined during the attempt."""
    _seed_forecast(tmp_path, "blocked", 0.1, 0.1)
    _seed_manifest(tmp_path, "blocked", status="execute")  # not finalized
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
    """The node-04 bar is precision >= 0.8 over >= _MIN_FORECAST_RUNS PRECISION-bearing samples
    (Codex #80): a single perfect-precision pair must NOT flip forecast_precision_ok true. It
    clears only once BOTH the threshold and the precision-sample size are met."""
    # one finalized forecast at precision 1.0 -> above threshold but far below the sample floor
    _seed_forecast(tmp_path, "solo", 1.0, 1.0)
    _seed_manifest(tmp_path, "solo", finalized_at="2026-07-14T00:00:00Z")
    ready = rep.promotion_readiness(rep.build_report(tmp_path))
    assert ready["forecast_precision_runs"] == 1
    assert ready["forecast_precision"] == 1.0  # threshold met
    assert ready["forecast_precision_ok"] is False  # but sample floor not met -> NOT ok
    assert ready["min_forecast_runs"] == rep._MIN_FORECAST_RUNS

    # enough high-precision pairs -> both conditions met -> ok
    for i in range(rep._MIN_FORECAST_RUNS):
        _seed_forecast(tmp_path, f"run{i}", 0.9, 0.9)
        _seed_manifest(tmp_path, f"run{i}", finalized_at="2026-07-14T00:00:00Z")
    ready2 = rep.promotion_readiness(rep.build_report(tmp_path))
    assert ready2["forecast_precision_runs"] >= rep._MIN_FORECAST_RUNS
    assert ready2["forecast_precision_ok"] is True


def test_forecast_precision_floor_counts_precision_not_recall_only(tmp_path: Path):
    """The sample floor must count PRECISION-bearing forecasts, not joined_runs (Codex #80):
    _MIN_FORECAST_RUNS recall-only joins (precision=None) plus ONE perfect prediction give
    joined_runs > the floor but only ONE precision sample — forecast_precision_ok must stay
    false, since precision has one-sample support."""
    for i in range(rep._MIN_FORECAST_RUNS):
        _seed_forecast(tmp_path, f"recallonly{i}", None, 0.9)  # recall only, no precision
        _seed_manifest(tmp_path, f"recallonly{i}", finalized_at="2026-07-14T00:00:00Z")
    _seed_forecast(tmp_path, "oneprecision", 1.0, 1.0)
    _seed_manifest(tmp_path, "oneprecision", finalized_at="2026-07-14T00:00:00Z")
    report = rep.build_report(tmp_path)
    assert report["forecast"]["joined_runs"] > rep._MIN_FORECAST_RUNS  # joined is above the floor
    assert report["forecast"]["precision_runs"] == 1  # but only one precision sample
    ready = rep.promotion_readiness(report)
    assert ready["forecast_precision_ok"] is False  # so the bar is NOT cleared


def _seed_forecast_full(root: Path, run_id: str, record: dict) -> None:
    from engines.io import forecastio

    # default the embedded run_id to the filename (real records embed it); an explicit run_id
    # in ``record`` wins, so a test can seed a deliberate filename/run_id MISMATCH.
    forecastio.write_forecast_record(root, run_id, {"run_id": run_id, **record})


def test_forecast_excludes_commit_early_hindsight_pairs(tmp_path: Path):
    """A record whose graph_stamp.commit != base_commit is commit-early hindsight (design node
    04 / council M1): it must be EXCLUDED from the precision bar's corpus but NOT silently
    dropped — surfaced as hindsight_runs for the human promotion decision (Codex #80)."""
    # a clean pair (commit == base_commit) contributes to the bar
    _seed_forecast_full(
        tmp_path, "clean", {"precision": 1.0, "recall": 1.0, "base_commit": "abc",
                            "graph_stamp": {"commit": "abc"}}
    )
    _seed_manifest(tmp_path, "clean", finalized_at="2026-07-14T00:00:00Z")
    # a hindsight pair (commit advanced past base) is excluded from the corpus but counted
    _seed_forecast_full(
        tmp_path, "hind", {"precision": 0.2, "recall": 0.2, "base_commit": "abc",
                           "graph_stamp": {"commit": "def"}}
    )
    _seed_manifest(tmp_path, "hind", finalized_at="2026-07-14T00:00:00Z")
    r = rep.build_report(tmp_path)
    assert r["forecast"]["precision_runs"] == 1  # only the clean pair feeds the bar
    assert r["forecast"]["hindsight_runs"] == 1  # the hindsight pair is surfaced, not dropped
    assert abs(r["forecast"]["mean_precision"] - 1.0) < 1e-9  # hindsight 0.2 is NOT averaged in
    out = rep.format_report(r)
    assert "commit-early hindsight" in out and "EXCLUDED" in out


def test_forecast_excludes_unauditable_pairs(tmp_path: Path):
    """A resolved forecast MISSING the audit fields (no base_commit / graph_stamp.commit) cannot
    be checked for the hindsight condition, so it is NOT verifiable-clean evidence and must be
    EXCLUDED from the bar — a separate surfaced bucket, not counted as clean (Codex #80)."""
    _seed_forecast_full(tmp_path, "clean", {"precision": 1.0, "recall": 1.0,
                                            "base_commit": "base", "graph_stamp": {"commit": "base"}})
    _seed_manifest(tmp_path, "clean", finalized_at="2026-07-14T00:00:00Z")
    _seed_forecast_full(tmp_path, "noaudit", {"precision": 0.3, "recall": 0.3})  # no audit fields
    _seed_manifest(tmp_path, "noaudit", finalized_at="2026-07-14T00:00:00Z")
    r = rep.build_report(tmp_path)
    assert r["forecast"]["precision_runs"] == 1  # only the auditable clean pair feeds the bar
    assert r["forecast"]["unaudited_runs"] == 1  # the unauditable pair is surfaced, not dropped
    assert abs(r["forecast"]["mean_precision"] - 1.0) < 1e-9  # the 0.3 unaudited is NOT averaged
    assert "unauditable" in rep.format_report(r)


def test_non_joined_forecast_is_not_bucketed_as_excluded(tmp_path: Path):
    """A resolved forecast that never JOINED (no numeric precision or recall — closure could not
    observe the diff) is not a promotion pair, so it must NOT be tallied into the hindsight /
    unaudited exclusion buckets even though it lacks audit fields (Codex #80)."""
    # unauditable-looking (no audit fields) AND no outcome -> not a pair -> not bucketed
    _seed_forecast_full(tmp_path, "noOutcome", {"precision": None, "recall": None})
    _seed_manifest(tmp_path, "noOutcome", finalized_at="2026-07-14T00:00:00Z")
    # a hindsight record that also never joined -> likewise not bucketed
    _seed_forecast_full(
        tmp_path, "hindNoOutcome",
        {"precision": None, "recall": None, "base_commit": "a", "graph_stamp": {"commit": "b"}},
    )
    _seed_manifest(tmp_path, "hindNoOutcome", finalized_at="2026-07-14T00:00:00Z")
    r = rep.build_report(tmp_path)
    assert r["forecast"]["joined_runs"] == 0
    assert r["forecast"]["unaudited_runs"] == 0  # no joined pair -> nothing excluded
    assert r["forecast"]["hindsight_runs"] == 0


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


def test_format_report_shows_precision_sample_size_not_joined(tmp_path: Path):
    """The formatted forecast line must display mean_precision's PRECISION-SAMPLE size and the
    bar verdict — not just joined_runs — so 20 recall-only joins + one perfect prediction does
    not read as ample precision evidence (Codex #80)."""
    for i in range(rep._MIN_FORECAST_RUNS):
        _seed_forecast(tmp_path, f"recallonly{i}", None, 0.9)
        _seed_manifest(tmp_path, f"recallonly{i}", finalized_at="2026-07-14T00:00:00Z")
    _seed_forecast(tmp_path, "oneprecision", 1.0, 1.0)
    _seed_manifest(tmp_path, "oneprecision", finalized_at="2026-07-14T00:00:00Z")
    out = rep.format_report(rep.build_report(tmp_path))
    # joined runs is above the floor, but the line makes the ONE precision sample explicit
    assert f"1/{rep._MIN_FORECAST_RUNS} precision samples" in out
    # and the bar verdict is shown as NOT met (one-sample support)
    assert "forecast precision bar" in out and "NOT met" in out

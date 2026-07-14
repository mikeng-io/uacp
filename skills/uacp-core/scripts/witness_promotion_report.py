"""Witness promotion report (#80) — the read side of the promotion-evidence lane.

Aggregates the per-run witness-advisory ledgers (``engines.io.witness_ledger_io``) and the
cascade-forecast records (``engines.io.forecastio``) written across a workspace's runs into
the numbers the advisory->blocking promotion decision needs:

* per witness code — how many runs it fired in, over the WITNESSABLE population (the
  false-positive-eligible denominator: runs where the witness actually ran on resolvable
  symbols, per design node 02);
* the forecast's mean precision / recall over witnessed runs (design node 04's ≥0.8 bar).

It computes NO promotion and changes NO gate — it is a reporting tool an operator reads
(feeding the GitHub Project #7 Scoreboard) before deciding to flip a witness to blocking.
Promotion itself stays gated on the locked criteria in ``design/conformance-witnesses/``
nodes 02-04 (and an operator decision) — this report only surfaces the evidence.

Run:  ``python skills/uacp-core/scripts/witness_promotion_report.py [UACP_ROOT]``
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml
from engines.io.loaders import load_manifest
from engines.io.witness_ledger_io import (
    WITNESS_CODES,
    WITNESS_FAMILIES,
    safe_unresolved_verification_dir,
)

# The node-02 minimum witnessable-run count before a zero-false-positive record is treated as
# promotion evidence. Advisory only — the report flags eligibility, it does not promote.
_MIN_WITNESSABLE_RUNS = 10
# node-04 forecast promotion bar: precision >= _MIN_FORECAST_PRECISION over AT LEAST
# _MIN_FORECAST_RUNS joined (predicted, outcome) pairs (design/conformance-witnesses/
# 04-prevention-redesign.md: "≥0.8 precision over ≥20 witnessed runs"). BOTH the threshold
# and the sample size must clear — a single 1.0 pair is not evidence (Codex #80).
_MIN_FORECAST_PRECISION = 0.8
_MIN_FORECAST_RUNS = 20


_WITNESS_LEDGER_KIND = "uacp.witness_ledger"


def _unresolved_governed_dir(root: Path, *extra: str) -> Path | None:
    """``<verification>/<extra...>`` as an UNRESOLVED path, returned only if it exists as a
    directory and NO component is a symlink.

    The verification dir comes from :func:`safe_unresolved_verification_dir` (shared with the
    ledger writer) — which reconstructs the raw path and rejects absolute/``..``/symlinked
    config segments, because ``dir_for``/``base_dir`` ``.resolve()`` would FOLLOW a symlinked
    ``verification`` dir into e.g. ``.uacp/state`` and let the report read ledgers/forecasts from
    the symlink target (Codex #80). Any symlinked ``extra`` component -> None. Never raises."""
    try:
        current = safe_unresolved_verification_dir(root)
        if current is None:
            return None
        for part in extra:
            current = current / part
            if current.is_symlink():
                return None
        return current if current.is_dir() else None
    except Exception:
        return None


def _load_yaml(path: Path) -> dict[str, Any] | None:
    try:
        # Never follow a symlinked LEAF: a witness-ledgers/*.yaml or *-cascade-forecast.yaml
        # symlink (even inside a real dir) could point OUT of the governed verification tree and
        # inflate advisory/forecast evidence from an external file (Codex #80). All report reads
        # go through here, so this one guard covers every leaf.
        if path.is_symlink():
            return None
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def build_report(root: Path | str) -> dict[str, Any]:
    """Aggregate every witness ledger + forecast record under a workspace's verification dir,
    PER WITNESS FAMILY (council #80): each family's unstarved/starved run counts and its own
    substantive-advisory runs are tallied independently, so one starved witness cannot mask
    another's advisory. NB (Codex #80): ``unstarved`` counts runs that emitted no starvation
    code — which conflates "ran clean" with "never ran", so it is NOT a clean-run denominator
    (see ``promotion_readiness``). Never raises — an unreadable/absent dir yields an empty
    report."""
    root_p = Path(str(root)).resolve()

    families: dict[str, dict[str, int]] = {
        f.name: {"unstarved": 0, "unresolved": 0, "unavailable": 0, "substantive_runs": 0}
        for f in WITNESS_FAMILIES
    }
    per_code: dict[str, dict[str, int]] = {}
    total_runs = 0

    ledger_dir = _unresolved_governed_dir(root_p, "witness-ledgers")
    if ledger_dir is not None:
        # ledgers live under verification/witness-ledgers/ (out of the verify-evidence glob,
        # Codex #80) — read them from there, one per run.
        for path in sorted(ledger_dir.glob("*.yaml")):
            rec = _load_yaml(path)
            if rec is None:
                continue
            # Only count REAL witness ledgers — a stray / foreign file (e.g. a run manifest
            # reachable via a symlinked dir) carries a different kind and must not inflate the
            # tally (Codex #80). And the embedded run_id MUST match the filename: a ledger copied
            # / renamed to <other-run>.yaml would otherwise be counted as another run.
            if rec.get("kind") != _WITNESS_LEDGER_KIND or rec.get("run_id") != path.stem:
                continue
            total_runs += 1
            counts = rec.get("counts")
            counts = counts if isinstance(counts, dict) else {}
            for code, n in counts.items():
                if code in WITNESS_CODES and isinstance(n, int):
                    slot = per_code.setdefault(code, {"runs": 0, "total": 0})
                    slot["runs"] += 1
                    slot["total"] += n
            rec_families = rec.get("families")
            rec_families = rec_families if isinstance(rec_families, dict) else {}
            for fname, agg in families.items():
                fdata = rec_families.get(fname)
                if not isinstance(fdata, dict):
                    continue
                status = fdata.get("status")
                if status in ("unstarved", "unresolved", "unavailable"):
                    agg[status] += 1
                # Count a substantive advisory INDEPENDENTLY of the starvation status (Codex
                # #80): one sweep can emit both an advisory (SC_UNDECLARED_CASCADE) and a
                # starvation code (SC_WITNESS_UNRESOLVED_TOUCHED) for the SAME family — the
                # advisory (a real potential false positive) must not be dropped just because
                # some other symbol in the same run could not be resolved.
                sub = fdata.get("substantive")
                if isinstance(sub, int) and sub > 0:
                    agg["substantive_runs"] += 1

    return {
        "total_runs": total_runs,
        "families": families,
        "per_code": {k: per_code[k] for k in sorted(per_code)},
        "forecast": _forecast_summary(root_p),
    }


def _run_is_resolved(root: Path, run_id: str, ledger_run_ids: set[str]) -> bool:
    """Decide, AUTHORITATIVELY, whether a forecast's run reached a COMPLETED closure.

    Primary signal is the run MANIFEST's ``finalized_at`` (via ``load_manifest``) — NOT
    ``status``. ``status == "resolved"`` is set by the verify->resolved transition BEFORE
    finalization (``state_machine`` ~784-788), and a blocked ``handle_finalize`` reverts
    ``finalized_at`` to None while restoring that PRIOR status — which is already
    ``resolved`` — so a failed closure attempt ends with ``status == "resolved"`` but no
    ``finalized_at`` (Codex #80). Only ``finalized_at`` is the finalize-specific,
    closure-complete marker: ``handle_finalize`` stamps it on success and clears it on any
    blocker, so it excludes blocked closures while a genuinely finalized run keeps it.

    FALLBACK: only when the manifest cannot be loaded (``.error`` set / missing / garbled)
    do we fall back to witness-ledger presence — the ledger is written only on a non-blocked
    closure, so it stays a valid POSITIVE fallback and keeps manifest-less workspaces no worse
    than the prior ledger-only signal. Never raises.
    """
    try:
        loaded = load_manifest(root, run_id)
    except Exception:  # load_manifest is documented not to raise; guard anyway
        loaded = None
    if loaded is not None and loaded.error is None and loaded.value is not None:
        raw = getattr(loaded.value, "raw", None)
        if isinstance(raw, dict):
            return bool(raw.get("finalized_at"))  # the ONLY closure-complete marker
        return False  # manifest loaded but shapeless -> authoritatively NOT resolved
    return run_id in ledger_run_ids  # manifest unavailable -> ledger-presence fallback


def _forecast_bar_eligibility(rec: dict[str, Any]) -> str:
    """Classify a resolved forecast for the precision bar (design node 04, council M1):

    * ``"eligible"`` — auditable AND clean: ``base_commit`` and ``graph_stamp.commit`` are both
      present and EQUAL (HEAD was the branch point), so the forecast is an honest prediction.
      Only these feed the bar.
    * ``"hindsight"`` — auditable but ``graph_stamp.commit != base_commit``: HEAD advanced past
      the branch point before plan_exit, so the forecast wore hindsight — MUST be excluded from
      the bar (but surfaced, not dropped).
    * ``"unaudited"`` — ``base_commit`` or ``graph_stamp.commit`` MISSING (older records, or a
      run with no resolvable default branch): the hindsight condition CANNOT be checked, so the
      pair is not verifiable-clean evidence and must NOT clear the bar either — a separate
      surfaced/excluded bucket (Codex #80).

    Never raises."""
    base = rec.get("base_commit")
    gs = rec.get("graph_stamp")
    commit = gs.get("commit") if isinstance(gs, dict) else None
    if not base or not commit:
        return "unaudited"
    return "eligible" if base == commit else "hindsight"


def _forecast_summary(root: Path) -> dict[str, Any]:
    """Mean precision/recall over forecast records that carry a joined outcome — restricted to
    genuinely RESOLVED runs, keyed off AUTHORITATIVE run status.

    The cascade forecast is joined during closure BEFORE ``handle_finalize`` knows whether a
    blocker will revert the run, and the joined file is not removed on a block, so a failed
    closure attempt would otherwise contribute precision/recall to a run that never resolved
    (Codex #80). The witness ledger is a BEST-EFFORT OBSERVATION artifact, not authoritative
    run state: a genuinely-resolved run can lack one (runs predating the ledger writer, or any
    resolved closure where the best-effort ledger write was skipped/failed). Keying off ledger
    presence therefore SILENTLY DROPPED valid forecasts.

    Instead, resolved-ness is decided by ``_run_is_resolved`` from the run MANIFEST — which
    EXCLUDES blocked closures (``handle_finalize`` reverts ``status``/``finalized_at`` on any
    blocker) while INCLUDING resolved runs that have no ledger. Ledger presence is retained
    ONLY as a fallback for when the manifest is unavailable. Never raises."""
    precisions: list[float] = []
    recalls: list[float] = []
    joined = 0
    hindsight = 0
    unaudited = 0
    root_p = Path(str(root)).resolve()
    # Symlink-safe UNRESOLVED dirs (dir_for resolves symlinks, so a symlinked verification /
    # ledger dir would otherwise be followed into e.g. state/ — Codex #80).
    vdir = _unresolved_governed_dir(root_p)
    if vdir is not None:
        # The ledger-presence fallback set: real witness ledgers under a NON-symlinked dir only
        # (a symlinked dir or a foreign kind must not seed the resolved-fallback — Codex #80).
        ledger_dir = _unresolved_governed_dir(root_p, "witness-ledgers")
        # A ledger only marks ITS OWN run resolved: require kind AND the embedded run_id to
        # match the filename, so a copied / renamed ledger cannot mark another run resolved.
        ledger_run_ids = (
            {
                p.stem
                for p in ledger_dir.glob("*.yaml")
                if (rec := _load_yaml(p)) is not None
                and rec.get("kind") == _WITNESS_LEDGER_KIND
                and rec.get("run_id") == p.stem
            }
            if ledger_dir is not None
            else set()
        )
        for path in sorted(vdir.glob("*-cascade-forecast.yaml")):
            run_id = path.name.removesuffix("-cascade-forecast.yaml")
            if not _run_is_resolved(root_p, run_id, ledger_run_ids):
                continue  # not authoritatively resolved -> exclude from the averages
            rec = _load_yaml(path)
            if rec is None:
                continue
            # The forecast's embedded run_id MUST match its filename: a forecast copied to
            # <other>-cascade-forecast.yaml would otherwise re-count the same precision/recall
            # sample for <other> and corrupt the promotion corpus (Codex #80).
            if rec.get("run_id") != run_id:
                continue
            # A forecast is JOINED only once the closure computed an OUTCOME — a numeric
            # precision AND/OR recall (precision is None when nothing was predicted, recall None
            # when nothing landed out-of-boundary; a run whose diff could not be observed has
            # NEITHER). A non-joined record is not a promotion pair at all, so it is neither
            # averaged NOR bucketed as excluded (Codex #80) — skip it before classifying.
            p, r = rec.get("precision"), rec.get("recall")
            has_p, has_r = isinstance(p, (int, float)), isinstance(r, (int, float))
            if not (has_p or has_r):
                continue  # no outcome sample -> nothing to average or exclude
            # Of the JOINED pairs, only AUDITABLE + CLEAN feed the bar (design node 04, council
            # M1). A commit-early hindsight pair (graph_stamp.commit != base_commit) OR an
            # unauditable one (missing audit fields — the hindsight condition cannot be checked)
            # is NOT verifiable-clean evidence; each is excluded from the precision/recall corpus
            # and surfaced (never silently dropped) as its own bucket for the human decision.
            eligibility = _forecast_bar_eligibility(rec)
            if eligibility == "hindsight":
                hindsight += 1
                continue
            if eligibility == "unaudited":
                unaudited += 1
                continue
            if has_p:
                precisions.append(float(p))
            if has_r:
                recalls.append(float(r))
            joined += 1
    return {
        "joined_runs": joined,
        # precision_runs is the sample SIZE behind mean_precision — records with a numeric
        # precision, NOT joined_runs (which also counts recall-only records). The sample floor
        # keys off this so a lone precision-bearing forecast among many recall-only joins cannot
        # clear the bar on one-sample support (Codex #80).
        "precision_runs": len(precisions),
        "recall_runs": len(recalls),
        # commit-early hindsight + unauditable pairs EXCLUDED from the bar above — surfaced
        # (never silently dropped) so the human promotion decision can review them (node 04).
        "hindsight_runs": hindsight,
        "unaudited_runs": unaudited,
        "mean_precision": (sum(precisions) / len(precisions)) if precisions else None,
        "mean_recall": (sum(recalls) / len(recalls)) if recalls else None,
    }


def promotion_readiness(
    report: dict[str, Any], min_runs: int = _MIN_WITNESSABLE_RUNS
) -> dict[str, Any]:
    """Per-family SOUND signals — advisory only, and deliberately NOT a "ready to promote"
    verdict. A witness emits a code ONLY on a finding or on starvation; a run where it ran and
    found nothing emits nothing, indistinguishable from a run where it never ran at all — so
    the "zero-FP over the witnessable population" bar's DENOMINATOR (clean runs) is NOT directly
    measurable from closure output (Codex #80). What IS sound: the substantive-advisory count
    (numerator) and the starvation count. A trustworthy clean-run denominator requires the
    witness engines to emit POSITIVE attestation ("I ran, examined X"), which they do not yet —
    tracked as a follow-up. Until then this reports the sound numbers and WITHHOLDS any CLEAN
    verdict rather than overclaim one."""
    families: dict[str, dict[str, Any]] = {}
    for fname, agg in report.get("families", {}).items():
        families[fname] = {
            "substantive_advisory_runs": agg.get("substantive_runs", 0),
            "starved_runs": agg.get("unresolved", 0) + agg.get("unavailable", 0),
            "unstarved_runs": agg.get("unstarved", 0),  # ran-clean OR never-ran — indeterminate
            "no_advisory_yet": agg.get("substantive_runs", 0) == 0,
            "clean_denominator_measurable": False,
            "note": "clean-run denominator needs positive witness attestation (not yet emitted)",
        }
    forecast = report.get("forecast", {})
    prec = forecast.get("mean_precision")
    precision_runs = forecast.get("precision_runs", 0)
    precision_runs = precision_runs if isinstance(precision_runs, int) else 0
    # The forecast bar clears ONLY when precision meets the threshold AND it is measured over a
    # large-enough PRECISION sample — the count of precision-bearing forecasts, NOT joined_runs
    # (which also counts recall-only records), so a lone perfect prediction among many
    # recall-only joins cannot clear the bar on one-sample support (Codex #80).
    forecast_precision_ok = (
        isinstance(prec, float)
        and prec >= _MIN_FORECAST_PRECISION
        and precision_runs >= _MIN_FORECAST_RUNS
    )
    return {
        "families": families,
        "min_runs": min_runs,
        "forecast_precision_ok": forecast_precision_ok,
        "forecast_precision": prec,
        "forecast_precision_runs": precision_runs,
        "min_forecast_runs": _MIN_FORECAST_RUNS,
    }


def format_report(report: dict[str, Any]) -> str:
    """Render the report as a compact human-readable block for the Scoreboard."""
    header = "per witness FAMILY (advisory runs | starved | unstarved[ran-clean OR never-ran])"
    lines = [
        "UACP witness promotion report (#80) — evidence only, promotes nothing",
        "=" * 66,
        f"runs observed: {report['total_runs']}",
        "",
        header,
    ]
    ready = promotion_readiness(report)
    for fname, agg in report["families"].items():
        r = ready["families"].get(fname, {})
        flag = "no advisories yet" if r.get("no_advisory_yet") else "ADVISORIES present"
        lines.append(
            f"  {fname:<14} advisory_runs={agg['substantive_runs']:>3}  "
            f"starved={agg['unresolved'] + agg['unavailable']:>3}  "
            f"unstarved={agg['unstarved']:>3}  [{flag}]"
        )
    lines += ["", "per witness code (runs fired / total firings):"]
    if report["per_code"]:
        for code, s in report["per_code"].items():
            lines.append(f"  {code:<32} {s['runs']:>4} runs / {s['total']:>4} firings")
    else:
        lines.append("  (no witness codes fired in any recorded run)")
    fc = report["forecast"]
    mp, mr = fc["mean_precision"], fc["mean_recall"]
    p_runs, r_runs = fc.get("precision_runs", 0), fc.get("recall_runs", 0)
    # Show mean_precision's SAMPLE SIZE next to it, NOT joined_runs — a mean over few precision
    # records beside a large joined_runs (recall-only joins) would otherwise look like ample
    # precision evidence when the bar is not met (Codex #80). Also print the bar's verdict.
    forecast_line = (
        f"forecast joined runs: {fc['joined_runs']}  "
        f"mean_precision={'n/a' if mp is None else f'{mp:.3f}'} "
        f"(over {p_runs}/{_MIN_FORECAST_RUNS} precision samples)  "
        f"mean_recall={'n/a' if mr is None else f'{mr:.3f}'} (over {r_runs} recall samples)"
    )
    bar_line = (
        f"forecast precision bar (>={_MIN_FORECAST_PRECISION} over >={_MIN_FORECAST_RUNS} "
        f"precision samples): {'MET' if ready['forecast_precision_ok'] else 'NOT met'}"
    )
    hindsight = fc.get("hindsight_runs", 0)
    unaudited = fc.get("unaudited_runs", 0)
    if hindsight or unaudited:
        bar_line += (
            f"  [{hindsight} commit-early hindsight + {unaudited} unauditable pair(s) EXCLUDED "
            f"from the bar — review for promotion, not auto-dropped]"
        )
    gate_note = (
        "NB: no CLEAN verdict is computed — the clean-run denominator is not measurable without"
        " positive witness attestation (a follow-up). Promotion stays gated on"
        " design/conformance-witnesses nodes 02-04 + operator sign-off."
    )
    lines += ["", forecast_line, bar_line, "", gate_note]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    print(format_report(build_report(root)))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))

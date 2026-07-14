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
from engines.io.witness_ledger_io import WITNESS_CODES, WITNESS_FAMILIES

from config import dir_for

# The node-02 minimum witnessable-run count before a zero-false-positive record is treated as
# promotion evidence. Advisory only — the report flags eligibility, it does not promote.
_MIN_WITNESSABLE_RUNS = 10
# node-04 forecast precision bar.
_MIN_FORECAST_PRECISION = 0.8


def _load_yaml(path: Path) -> dict[str, Any] | None:
    try:
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
    try:
        vdir = dir_for(root_p, "verification")
    except Exception:
        vdir = None

    families: dict[str, dict[str, int]] = {
        f.name: {"unstarved": 0, "unresolved": 0, "unavailable": 0, "substantive_runs": 0}
        for f in WITNESS_FAMILIES
    }
    per_code: dict[str, dict[str, int]] = {}
    total_runs = 0

    if vdir is not None and vdir.is_dir():
        # ledgers live under verification/witness-ledgers/ (out of the verify-evidence glob,
        # Codex #80) — read them from there, one per run.
        for path in sorted(vdir.glob("witness-ledgers/*.yaml")):
            rec = _load_yaml(path)
            if rec is None:
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
    """Decide, AUTHORITATIVELY, whether a forecast's run genuinely resolved.

    Primary signal is the run MANIFEST (``load_manifest``): it loaded AND either
    ``status == "resolved"`` OR ``finalized_at`` is truthy. This is authoritative because
    ``state_machine.handle_finalize`` OPTIMISTICALLY sets both, then on ANY closure blocker
    REVERTS them (fail-closed) — so a blocked/reverted closure ends with ``status`` not
    resolved and ``finalized_at`` unset, while a genuine resolution keeps them.

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
            return raw.get("status") == "resolved" or bool(raw.get("finalized_at"))
        return False  # manifest loaded but shapeless -> authoritatively NOT resolved
    return run_id in ledger_run_ids  # manifest unavailable -> ledger-presence fallback


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
    root_p = Path(str(root)).resolve()
    try:
        vdir = dir_for(root_p, "verification")
    except Exception:
        vdir = None
    if vdir is not None and vdir.is_dir():
        ledger_run_ids = {p.stem for p in vdir.glob("witness-ledgers/*.yaml")}
        for path in sorted(vdir.glob("*-cascade-forecast.yaml")):
            run_id = path.name.removesuffix("-cascade-forecast.yaml")
            if not _run_is_resolved(root_p, run_id, ledger_run_ids):
                continue  # not authoritatively resolved -> exclude from the averages
            rec = _load_yaml(path)
            if rec is None:
                continue
            # A forecast is JOINED once the closure computed an outcome — which yields a
            # precision AND/OR a recall (precision is None when nothing was predicted, recall
            # None when nothing landed out-of-boundary). Count the run as joined if EITHER is
            # present, so joined_runs is the true denominator of both means (gemini #80 P2).
            p, r = rec.get("precision"), rec.get("recall")
            has_p, has_r = isinstance(p, (int, float)), isinstance(r, (int, float))
            if has_p:
                precisions.append(float(p))
            if has_r:
                recalls.append(float(r))
            if has_p or has_r:
                joined += 1
    return {
        "joined_runs": joined,
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
    prec = report.get("forecast", {}).get("mean_precision")
    return {
        "families": families,
        "min_runs": min_runs,
        "forecast_precision_ok": (isinstance(prec, float) and prec >= _MIN_FORECAST_PRECISION),
        "forecast_precision": prec,
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
    forecast_line = (
        f"forecast joined runs: {fc['joined_runs']}  "
        f"mean_precision={'n/a' if mp is None else f'{mp:.3f}'}  "
        f"mean_recall={'n/a' if mr is None else f'{mr:.3f}'}"
    )
    gate_note = (
        "NB: no CLEAN verdict is computed — the clean-run denominator is not measurable without"
        " positive witness attestation (a follow-up). Promotion stays gated on"
        " design/conformance-witnesses nodes 02-04 + operator sign-off."
    )
    lines += ["", forecast_line, "", gate_note]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    print(format_report(build_report(root)))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))

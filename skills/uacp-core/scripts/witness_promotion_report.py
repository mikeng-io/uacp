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
    PER WITNESS FAMILY (council #80): each family's witnessable/starved population and its own
    substantive-advisory runs are tallied independently, so one starved witness cannot mask
    another's advisory. Never raises — an unreadable/absent dir yields an empty report."""
    try:
        vdir = dir_for(Path(str(root)).resolve(), "verification")
    except Exception:
        vdir = None

    families: dict[str, dict[str, int]] = {
        f.name: {"witnessable": 0, "unresolved": 0, "unavailable": 0, "substantive_runs": 0}
        for f in WITNESS_FAMILIES
    }
    per_code: dict[str, dict[str, int]] = {}
    total_runs = 0

    if vdir is not None and vdir.is_dir():
        for path in sorted(vdir.glob("*-witness-ledger.yaml")):
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
                if status in ("witnessable", "unresolved", "unavailable"):
                    agg[status] += 1
                if (
                    status == "witnessable"
                    and isinstance(fdata.get("substantive"), int)
                    and fdata["substantive"] > 0
                ):
                    agg["substantive_runs"] += 1

    return {
        "total_runs": total_runs,
        "families": families,
        "per_code": {k: per_code[k] for k in sorted(per_code)},
        "forecast": _forecast_summary(vdir),
    }


def _forecast_summary(vdir: Path | None) -> dict[str, Any]:
    """Mean precision/recall over forecast records that carry a joined outcome."""
    precisions: list[float] = []
    recalls: list[float] = []
    joined = 0
    if vdir is not None and vdir.is_dir():
        for path in sorted(vdir.glob("*-cascade-forecast.yaml")):
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
    """A COARSE PER-FAMILY readiness flag from the aggregated report — advisory only. A witness
    family is "evidence-clean" when ITS witnessable population has reached ``min_runs`` and no
    witnessable run recorded a substantive advisory for it. Per-family so one starved witness
    cannot mask another (council #80). This does NOT encode the full node-02/03/04 criteria
    (hunk-level derivation, hub bound, trust-root pin, absence-escalation) — those remain a
    human read + the locked design gates."""
    families: dict[str, dict[str, Any]] = {}
    for fname, agg in report.get("families", {}).items():
        w = agg.get("witnessable", 0)
        enough = w >= min_runs
        clean = agg.get("substantive_runs", 0) == 0
        families[fname] = {
            "witnessable_runs": w,
            "min_runs": min_runs,
            "detection_evidence_clean": bool(enough and clean),
            "detection_reason": (
                "insufficient witnessable runs"
                if not enough
                else ("substantive advisories present" if not clean else "clean")
            ),
        }
    prec = report.get("forecast", {}).get("mean_precision")
    return {
        "families": families,
        "forecast_precision_ok": (isinstance(prec, float) and prec >= _MIN_FORECAST_PRECISION),
        "forecast_precision": prec,
    }


def format_report(report: dict[str, Any]) -> str:
    """Render the report as a compact human-readable block for the Scoreboard."""
    lines = [
        "UACP witness promotion report (#80) — evidence only, promotes nothing",
        "=" * 66,
        f"runs observed: {report['total_runs']}",
        "",
        "per witness FAMILY (witnessable / unresolved / unavailable — substantive-advisory runs):",
    ]
    ready = promotion_readiness(report)
    for fname, agg in report["families"].items():
        r = ready["families"].get(fname, {})
        verdict = "CLEAN" if r.get("detection_evidence_clean") else "not yet"
        lines.append(
            f"  {fname:<14} w={agg['witnessable']:>3} u={agg['unresolved']:>3} "
            f"n={agg['unavailable']:>3}  substantive_runs={agg['substantive_runs']:>3}  "
            f"[{verdict}: {r.get('detection_reason', '?')}]"
        )
    lines += ["", "per witness code (runs fired / total firings):"]
    if report["per_code"]:
        for code, s in report["per_code"].items():
            lines.append(f"  {code:<32} {s['runs']:>4} runs / {s['total']:>4} firings")
    else:
        lines.append("  (no witness codes fired in any recorded run)")
    fc = report["forecast"]
    mp, mr = fc["mean_precision"], fc["mean_recall"]
    lines += [
        "",
        f"forecast joined runs: {fc['joined_runs']}  "
        f"mean_precision={'n/a' if mp is None else f'{mp:.3f}'}  "
        f"mean_recall={'n/a' if mr is None else f'{mr:.3f}'}",
        f"forecast precision >= {_MIN_FORECAST_PRECISION}: "
        f"{'yes' if ready['forecast_precision_ok'] else 'no'}",
        "",
        "NB: promotion stays gated on design/conformance-witnesses nodes 02-04 "
        "+ operator sign-off.",
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    print(format_report(build_report(root)))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))

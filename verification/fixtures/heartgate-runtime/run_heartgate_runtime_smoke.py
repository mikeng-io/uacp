#!/usr/bin/env python3
"""Self-contained Heartgate runtime fixture smoke test.

Creates temporary gate-ledger entries required by legacy Post-Phase Verification,
runs pass and fail transition fixtures, then removes the temporary ledgers.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "runtime-adapters/hermes/plugins"))

from uacp_guardian.kernel import Guardian, GuardianPolicy, Heartgate, make_event  # noqa: E402


def write_ledger(run: str, prev_gate: str, phase: str) -> Path:
    ledger_dir = ROOT / "state/gate-ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    path = ledger_dir / f"{run}.jsonl"
    rows = [
        {"gate": prev_gate, "result": "pass", "phase": phase},
        {
            "gate": "PIV",
            "phase": phase,
            "piv_attempt": 1,
            "result": "pass",
            "checks": [{"id": f"piv_{idx}", "result": "pass"} for idx in range(1, 6)],
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return path


def main() -> int:
    created: list[Path] = []
    for run, gate, phase in [
        ("fixture-execute-pass", "PLAN->EXECUTE", "execute"),
        ("fixture-verify-pass", "EXECUTE->VERIFY", "verify"),
        ("fixture-resolve-pass", "VERIFY->RESOLVE", "resolve"),
        ("fixture-execute-missing-runtime", "PLAN->EXECUTE", "execute"),
        ("fixture-runtime-exec-deferred", "PLAN->EXECUTE", "execute"),
        ("fixture-runtime-resolve-dropped-risk", "VERIFY->RESOLVE", "resolve"),
    ]:
        created.append(write_ledger(run, gate, phase))
    try:
        hg = Heartgate.load(ROOT)
        passing = [
            "verification/fixtures/heartgate-runtime/pass-execute-transition.yaml",
            "verification/fixtures/heartgate-runtime/pass-verify-transition.yaml",
            "verification/fixtures/heartgate-runtime/pass-resolve-transition.yaml",
            "verification/fixtures/heartgate-runtime/pass-warn-accepted-exception-artifact.yaml",
        ]
        failing = {
            "verification/fixtures/heartgate-runtime/fail-execute-missing-runtime-gate.yaml": "adaptive_execute_evidence_gate",
            "verification/fixtures/heartgate-runtime/fail-execute-deferred-required-piv-ready.yaml": "required PIV evidence",
            "verification/fixtures/heartgate-runtime/fail-resolve-dropped-residual-risk.yaml": "residual risk",
            "verification/fixtures/heartgate-runtime/fail-coherence-path-escape.yaml": "heartgate_coherence artifact not found",
            "verification/fixtures/heartgate-runtime/fail-warn-missing-accepted-exception-artifact.yaml": "warns without accepted exception",
        }
        for rel in passing:
            decision = hg.validate_transition_file(rel)
            if decision.decision not in {"pass", "warn"}:
                raise AssertionError(f"expected pass/warn for {rel}: {decision}")
        for rel, needle in failing.items():
            decision = hg.validate_transition_file(rel)
            text = "\n".join(decision.blockers)
            if decision.decision != "block" or needle not in text:
                raise AssertionError(f"expected block containing {needle!r} for {rel}: {decision}")
        guardian = Guardian(GuardianPolicy.load(ROOT))
        command_variants = [
            f"touch {ROOT}/state/evil.txt",
            "touch ~/.hermes/uacp/state/evil.txt",
            "touch $HOME/.hermes/uacp/state/evil.txt",
            "cd ~/.hermes && touch uacp/state/evil.txt",
        ]
        for command in command_variants:
            event = make_event(
                tool_name="terminal",
                args={"command": command},
                tool_provider="functions",
            )
            if not guardian.is_uacp_bound(event):
                raise AssertionError(f"shell command touching UACP root not classified UACP-bound: {command}")
        print("HEARTGATE_RUNTIME_SMOKE_PASS")
        return 0
    finally:
        for path in created:
            try:
                path.unlink()
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
